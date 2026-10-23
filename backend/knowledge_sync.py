import json
import os
import shutil
import tempfile
import threading

import faiss

from database.db import get_knowledge_files, replace_knowledge_files
from rag.document_manager import create_file_chunks
from rag.index_integrity import (
    MANIFEST_PATH,
    build_manifest,
    validate_vector_store,
    write_manifest_atomic,
)
from rag.rebuild_faiss import rebuild_faiss
from utils.file_hash import get_file_hash


KNOWLEDGE_PATH = "knowledge"
DOCUMENT_PATH = "vector_db/documents.json"
INDEX_PATH = "vector_db/index.faiss"
_SYNC_LOCK = threading.RLock()


def scan_knowledge_files():
    files = {}
    for filename in os.listdir(KNOWLEDGE_PATH):
        path = os.path.join(KNOWLEDGE_PATH, filename)
        if os.path.isfile(path):
            files[filename] = get_file_hash(path)
    return files


def get_database_files():
    return {
        record["filename"]: record["file_hash"]
        for record in get_knowledge_files()
    }


def check_changes():
    current_files = scan_knowledge_files()
    old_files = get_database_files()
    return {
        "new": [name for name in current_files if name not in old_files],
        "modified": [
            name
            for name, file_hash in current_files.items()
            if name in old_files and old_files[name] != file_hash
        ],
        "deleted": [name for name in old_files if name not in current_files],
    }


def load_documents_json():
    if not os.path.exists(DOCUMENT_PATH):
        return []
    with open(DOCUMENT_PATH, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_documents_json(documents):
    """Retained for compatibility; sync_knowledge uses staged candidate files."""
    with open(DOCUMENT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(documents, file_handle, ensure_ascii=False, indent=2)


def _write_json_candidate(path, documents):
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(documents, file_handle, ensure_ascii=False, indent=2)
        file_handle.flush()
        os.fsync(file_handle.fileno())


def _candidate_documents(existing_documents, changes):
    replaced = set(changes["deleted"] + changes["modified"])
    documents = [
        document
        for document in existing_documents
        if document.get("source") not in replaced
    ]
    chunks_by_filename = {}
    for filename in changes["new"] + changes["modified"]:
        chunks = create_file_chunks(filename)
        if not chunks:
            raise ValueError(f"No chunks were created for knowledge file: {filename}")
        chunks_by_filename[filename] = chunks
        documents.extend(chunks)
    return documents, chunks_by_filename


def _candidate_database(existing_records, changes, chunks_by_filename):
    replaced = set(changes["deleted"] + changes["modified"])
    records = [
        dict(record)
        for record in existing_records
        if record["filename"] not in replaced
    ]
    for filename in changes["new"] + changes["modified"]:
        path = os.path.join(KNOWLEDGE_PATH, filename)
        records.append(
            {
                "filename": filename,
                "file_type": os.path.splitext(filename)[1],
                "file_size": os.path.getsize(path),
                "upload_time": None,
                "chunk_count": len(chunks_by_filename[filename]),
                "file_hash": get_file_hash(path),
            }
        )
    return records


def _copy_backup(source, backup):
    if os.path.exists(source):
        shutil.copy2(source, backup)
        return True
    return False


def _restore_file(destination, backup, existed):
    if existed:
        os.replace(backup, destination)
    elif os.path.exists(destination):
        os.remove(destination)


def _existing_dimension():
    if os.path.exists(INDEX_PATH):
        return int(faiss.read_index(INDEX_PATH).d)
    return None


def sync_knowledge(force_rebuild=False):
    """Build a verified candidate generation, then publish it with rollback."""
    with _SYNC_LOCK:
        changes = check_changes()
        print("Knowledge changes:", changes)
        if not any(changes.values()) and not force_rebuild:
            print("Knowledge base unchanged")
            return changes

        existing_documents = load_documents_json()
        existing_records = get_knowledge_files()
        candidate_documents, chunks_by_filename = _candidate_documents(
            existing_documents, changes
        )
        candidate_records = _candidate_database(
            existing_records, changes, chunks_by_filename
        )

        vector_directory = os.path.dirname(DOCUMENT_PATH)
        os.makedirs(vector_directory, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=vector_directory, prefix=".sync-"
        ) as stage_directory:
            staged_documents = os.path.join(stage_directory, "documents.json")
            staged_index = os.path.join(stage_directory, "index.faiss")
            staged_manifest = os.path.join(stage_directory, "manifest.json")
            _write_json_candidate(staged_documents, candidate_documents)
            rebuild_faiss(
                candidate_documents,
                staged_index,
                empty_dimension=_existing_dimension(),
            )
            manifest = build_manifest(
                candidate_documents, staged_documents, staged_index
            )
            validate_vector_store(
                faiss.read_index(staged_index),
                candidate_documents,
                manifest,
                staged_documents,
                staged_index,
            )
            write_manifest_atomic(staged_manifest, manifest)

            backups = {
                DOCUMENT_PATH: os.path.join(stage_directory, "documents.backup"),
                INDEX_PATH: os.path.join(stage_directory, "index.backup"),
                MANIFEST_PATH: os.path.join(stage_directory, "manifest.backup"),
            }
            existed = {
                path: _copy_backup(path, backup)
                for path, backup in backups.items()
            }
            try:
                os.replace(staged_documents, DOCUMENT_PATH)
                os.replace(staged_index, INDEX_PATH)
                replace_knowledge_files(candidate_records)
                os.replace(staged_manifest, MANIFEST_PATH)
            except Exception as publish_error:
                rollback_errors = []
                for path in (DOCUMENT_PATH, INDEX_PATH, MANIFEST_PATH):
                    try:
                        _restore_file(path, backups[path], existed[path])
                    except Exception as rollback_error:
                        rollback_errors.append(f"{path}: {rollback_error}")
                try:
                    replace_knowledge_files(existing_records)
                except Exception as rollback_error:
                    rollback_errors.append(f"chat.db: {rollback_error}")
                if rollback_errors:
                    raise RuntimeError(
                        "Knowledge sync failed and rollback was incomplete: "
                        + "; ".join(rollback_errors)
                    ) from publish_error
                raise

        return changes


if __name__ == "__main__":
    sync_knowledge()
