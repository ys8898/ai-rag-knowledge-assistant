import io
import errno
import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np


BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("LLM_EMBEDDING_MODEL", "test-embedding")

rerank_stub = types.ModuleType("rerank")
rerank_stub.rerank_documents = lambda question, documents: documents
sys.modules.setdefault("rerank", rerank_stub)

from database import db
import knowledge_manager
import knowledge_sync
from rag import search
from rag.index_integrity import (
    UPDATE_MARKER_PATH,
    VectorStoreConsistencyError,
    build_manifest,
    validate_vector_store,
    write_manifest_atomic,
)
from utils.file_hash import get_file_hash


def fake_rebuild(documents=None, index_path="vector_db/index.faiss", empty_dimension=None):
    documents = documents or []
    dimension = empty_dimension or 2
    index = faiss.IndexFlatL2(dimension)
    if documents:
        vectors = np.array(
            [[float(i), float(i + 1)] for i in range(len(documents))],
            dtype="float32",
        )
        index.add(vectors)
    faiss.write_index(index, str(index_path))
    return index.ntotal


class TemporaryKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        Path("knowledge").mkdir()
        Path("vector_db").mkdir()
        db.init_db()
        self.seed_files({"a.txt": "alpha knowledge", "b.txt": "beta knowledge"})

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp_dir.cleanup()

    def seed_files(self, files):
        documents = []
        records = []
        for filename, content in files.items():
            path = Path("knowledge") / filename
            path.write_text(content, encoding="utf-8")
            file_hash = get_file_hash(str(path))
            documents.append(
                {
                    "text": content,
                    "source": filename,
                    "chunk_id": f"{filename}_0",
                    "file_hash": file_hash,
                    "file_type": ".txt",
                }
            )
            records.append(
                {
                    "filename": filename,
                    "file_type": ".txt",
                    "file_size": path.stat().st_size,
                    "upload_time": None,
                    "chunk_count": 1,
                    "file_hash": file_hash,
                }
            )

        Path("vector_db/documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        fake_rebuild(documents, "vector_db/index.faiss", empty_dimension=2)
        manifest = build_manifest(
            documents,
            "vector_db/documents.json",
            "vector_db/index.faiss",
        )
        write_manifest_atomic("vector_db/manifest.json", manifest)
        db.replace_knowledge_files(records)

    def snapshot(self):
        return {
            "documents": Path("vector_db/documents.json").read_bytes(),
            "index": Path("vector_db/index.faiss").read_bytes(),
            "manifest": Path("vector_db/manifest.json").read_bytes(),
            "database": db.get_knowledge_files(),
        }

    def assert_store_valid(self):
        index, documents = search.load_vector_data()
        self.assertEqual(index.ntotal, len(documents))
        return documents


class SearchSafetyTests(TemporaryKnowledgeBase):
    def test_normal_candidates(self):
        index, documents = search.load_vector_data()
        self.assertEqual(index.ntotal, len(documents))
        results = search.collect_faiss_candidates(
            documents,
            np.array([[0.1, 0.2]], dtype="float32"),
            np.array([[0, 1]], dtype="int64"),
        )
        self.assertEqual([item["source"] for item in results], ["a.txt", "b.txt"])

    def test_minus_one_is_ignored(self):
        documents = json.loads(Path("vector_db/documents.json").read_text(encoding="utf-8"))
        results = search.collect_faiss_candidates(
            documents,
            np.array([[0.1, float("inf")]], dtype="float32"),
            np.array([[0, -1]], dtype="int64"),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "a.txt")

    def test_out_of_range_candidate_is_rejected(self):
        documents = json.loads(Path("vector_db/documents.json").read_text(encoding="utf-8"))
        with self.assertRaises(VectorStoreConsistencyError):
            search.collect_faiss_candidates(
                documents,
                np.array([[0.1]], dtype="float32"),
                np.array([[len(documents)]], dtype="int64"),
            )

    def test_index_count_larger_than_documents_is_rejected(self):
        documents = json.loads(Path("vector_db/documents.json").read_text(encoding="utf-8"))
        index = faiss.IndexFlatL2(2)
        index.add(np.zeros((len(documents) + 1, 2), dtype="float32"))
        manifest = json.loads(Path("vector_db/manifest.json").read_text(encoding="utf-8"))
        with self.assertRaises(VectorStoreConsistencyError):
            validate_vector_store(
                index,
                documents,
                manifest,
                "vector_db/documents.json",
                "vector_db/index.faiss",
            )

    def test_equal_counts_without_mapping_proof_are_rejected(self):
        Path("vector_db/manifest.json").unlink()
        with self.assertRaises(VectorStoreConsistencyError):
            search.load_vector_data()

    def test_equal_counts_with_reordered_documents_are_rejected_after_reload(self):
        documents = json.loads(Path("vector_db/documents.json").read_text(encoding="utf-8"))
        Path("vector_db/documents.json").write_text(
            json.dumps(list(reversed(documents)), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with self.assertRaises(VectorStoreConsistencyError):
            search.load_vector_data()


class SyncFailureTests(TemporaryKnowledgeBase):
    def assert_snapshot_unchanged(self, before):
        self.assertEqual(Path("vector_db/documents.json").read_bytes(), before["documents"])
        self.assertEqual(Path("vector_db/index.faiss").read_bytes(), before["index"])
        self.assertEqual(Path("vector_db/manifest.json").read_bytes(), before["manifest"])
        self.assertEqual(db.get_knowledge_files(), before["database"])
        self.assert_store_valid()

    def test_delete_embedding_failure_rolls_back_everything(self):
        before = self.snapshot()
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=RuntimeError("embedding failed")):
            with self.assertRaises(RuntimeError):
                knowledge_manager.delete_document("a.txt", knowledge_sync.sync_knowledge)
        self.assertTrue(Path("knowledge/a.txt").exists())
        self.assert_snapshot_unchanged(before)

    def test_add_embedding_failure_rolls_back_everything(self):
        before = self.snapshot()
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=RuntimeError("embedding failed")):
            with self.assertRaises(RuntimeError):
                knowledge_manager.save_document(
                    "new.txt",
                    io.BytesIO(b"new knowledge"),
                    knowledge_sync.sync_knowledge,
                )
        self.assertFalse(Path("knowledge/new.txt").exists())
        self.assert_snapshot_unchanged(before)

    def test_update_embedding_failure_restores_original_file_and_store(self):
        before = self.snapshot()
        original = Path("knowledge/a.txt").read_bytes()
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=RuntimeError("embedding failed")):
            with self.assertRaises(RuntimeError):
                knowledge_manager.save_document(
                    "a.txt",
                    io.BytesIO(b"changed knowledge"),
                    knowledge_sync.sync_knowledge,
                )
        self.assertEqual(Path("knowledge/a.txt").read_bytes(), original)
        self.assert_snapshot_unchanged(before)

    def test_publish_failure_rolls_back_files_database_and_source(self):
        before = self.snapshot()
        real_replace = knowledge_sync.os.replace

        def fail_manifest_publish(source, destination):
            if str(destination).endswith("manifest.json") and ".sync-" in str(source):
                raise OSError("simulated manifest publish failure")
            return real_replace(source, destination)

        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            with patch.object(knowledge_sync.os, "replace", side_effect=fail_manifest_publish):
                with self.assertRaises(OSError):
                    knowledge_manager.save_document(
                        "new.txt",
                        io.BytesIO(b"new knowledge"),
                        knowledge_sync.sync_knowledge,
                    )
        self.assertFalse(Path("knowledge/new.txt").exists())
        self.assert_snapshot_unchanged(before)

    def test_reload_rejects_generation_interrupted_before_manifest_publish(self):
        documents = json.loads(
            Path("vector_db/documents.json").read_text(encoding="utf-8")
        )
        changed_documents = [dict(document) for document in documents]
        changed_documents[0]["text"] = "half-published content"
        Path("vector_db/documents.json").write_text(
            json.dumps(changed_documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with self.assertRaises(VectorStoreConsistencyError):
            search.load_vector_data()

    def test_reload_rejects_source_update_interrupted_before_sync(self):
        Path(UPDATE_MARKER_PATH).write_text(
            '{"operation_id":"interrupted"}', encoding="utf-8"
        )
        with self.assertRaises(VectorStoreConsistencyError):
            search.load_vector_data()


class SyncSuccessTests(TemporaryKnowledgeBase):
    def run_with_fake_embedding(self, operation):
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            return operation()

    def test_delete_success_publishes_consistent_store(self):
        self.run_with_fake_embedding(
            lambda: knowledge_manager.delete_document("a.txt", knowledge_sync.sync_knowledge)
        )
        self.assertFalse(Path("knowledge/a.txt").exists())
        documents = self.assert_store_valid()
        self.assertEqual({item["source"] for item in documents}, {"b.txt"})
        self.assertEqual({item["filename"] for item in db.get_knowledge_files()}, {"b.txt"})

    def test_delete_backup_does_not_cross_the_knowledge_mount(self):
        real_replace = os.replace
        source_path = Path("knowledge/a.txt").resolve()
        knowledge_mount = Path("knowledge").resolve()
        delete_moves = []

        def reject_cross_mount_replace(source, destination):
            resolved_source = Path(source).resolve()
            resolved_destination = Path(destination).resolve()
            if resolved_source == source_path:
                delete_moves.append((resolved_source, resolved_destination))
                if not resolved_destination.is_relative_to(knowledge_mount):
                    raise OSError(errno.EXDEV, "Invalid cross-device link")
            return real_replace(source, destination)

        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            with patch.object(
                knowledge_manager.os,
                "replace",
                side_effect=reject_cross_mount_replace,
            ):
                knowledge_manager.delete_document(
                    "a.txt", knowledge_sync.sync_knowledge
                )

        self.assertTrue(delete_moves)
        self.assertFalse(Path("knowledge/a.txt").exists())
        self.assert_store_valid()

    def test_delete_missing_document_returns_false_without_sync(self):
        sync_called = False

        def sync_callback():
            nonlocal sync_called
            sync_called = True

        result = knowledge_manager.delete_document("missing.txt", sync_callback)
        self.assertFalse(result)
        self.assertFalse(sync_called)

    def test_delete_backup_directory_is_not_listed_as_a_document(self):
        backup_directory = Path(knowledge_manager.DELETE_BACKUP_PATH)
        backup_directory.mkdir()
        (backup_directory / ".a.txt-test.backup").write_bytes(b"backup")

        filenames = {
            item["filename"] for item in knowledge_manager.list_documents()
        }
        self.assertEqual(filenames, {"a.txt", "b.txt"})

    def test_add_success_publishes_consistent_store(self):
        self.run_with_fake_embedding(
            lambda: knowledge_manager.save_document(
                "new.txt", io.BytesIO(b"new knowledge"), knowledge_sync.sync_knowledge
            )
        )
        documents = self.assert_store_valid()
        self.assertEqual({item["source"] for item in documents}, {"a.txt", "b.txt", "new.txt"})
        self.assertEqual(
            {item["filename"] for item in db.get_knowledge_files()},
            {"a.txt", "b.txt", "new.txt"},
        )

    def test_update_success_replaces_old_chunks_and_keeps_store_consistent(self):
        self.run_with_fake_embedding(
            lambda: knowledge_manager.save_document(
                "a.txt", io.BytesIO(b"changed knowledge"), knowledge_sync.sync_knowledge
            )
        )
        documents = self.assert_store_valid()
        a_documents = [item for item in documents if item["source"] == "a.txt"]
        self.assertEqual(len(a_documents), 1)
        self.assertEqual(a_documents[0]["text"], "changed knowledge")

    def test_force_rebuild_publishes_manifest_without_file_changes(self):
        Path("vector_db/manifest.json").unlink()
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            changes = knowledge_sync.sync_knowledge(force_rebuild=True)
        self.assertEqual(changes, {"new": [], "modified": [], "deleted": []})
        self.assert_store_valid()

    def test_empty_knowledge_base_is_valid_after_deleting_last_file(self):
        knowledge_manager.delete_document("b.txt", lambda: None)
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            knowledge_manager.delete_document("a.txt", knowledge_sync.sync_knowledge)
        documents = self.assert_store_valid()
        self.assertEqual(documents, [])


class DeleteApiTests(TemporaryKnowledgeBase):
    def main_module(self):
        return importlib.import_module("main")

    def test_delete_api_returns_success_payload(self):
        main = self.main_module()
        with patch.object(main, "delete_document", return_value=True):
            response = main.remove_document("a.txt")
        self.assertEqual(response, {"message": "删除成功"})

    def test_delete_http_endpoint_updates_verified_store(self):
        from fastapi.testclient import TestClient

        main = self.main_module()
        with patch.object(knowledge_sync, "rebuild_faiss", side_effect=fake_rebuild):
            response = TestClient(main.app).delete("/documents/a.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "删除成功"})
        self.assertFalse(Path("knowledge/a.txt").exists())
        documents = self.assert_store_valid()
        self.assertEqual({item["source"] for item in documents}, {"b.txt"})
        self.assertEqual(
            {item["filename"] for item in db.get_knowledge_files()}, {"b.txt"}
        )

    def test_delete_api_returns_404_for_missing_file(self):
        from fastapi.testclient import TestClient

        main = self.main_module()
        with patch.object(main, "delete_document", return_value=False):
            response = TestClient(main.app).delete("/documents/missing.txt")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "文件不存在")

    def test_delete_api_returns_diagnostic_500_for_other_failures(self):
        from fastapi.testclient import TestClient

        main = self.main_module()
        with patch.object(
            main,
            "delete_document",
            side_effect=OSError(errno.EACCES, "permission denied"),
        ):
            response = TestClient(main.app).delete("/documents/a.txt")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"], "knowledge_delete_failed"
        )
        self.assertIn("permission denied", response.json()["detail"]["reason"])

    def test_delete_api_preserves_consistency_error_for_503_handler(self):
        from fastapi.testclient import TestClient

        main = self.main_module()
        error = VectorStoreConsistencyError("manifest mismatch")
        with patch.object(main, "delete_document", side_effect=error):
            response = TestClient(main.app).delete("/documents/a.txt")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "vector_store_inconsistent")
        self.assertEqual(response.json()["detail"], "manifest mismatch")


if __name__ == "__main__":
    unittest.main()
