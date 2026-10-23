import hashlib
import json
import os
import tempfile
import uuid

import faiss


MANIFEST_PATH = "vector_db/manifest.json"
UPDATE_MARKER_PATH = "vector_db/update_in_progress.json"
MANIFEST_VERSION = 1


class VectorStoreConsistencyError(RuntimeError):
    """Raised when the FAISS index cannot be proven to match its documents."""


def begin_knowledge_update(path=UPDATE_MARKER_PATH):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    marker = {
        "version": 1,
        "operation_id": uuid.uuid4().hex,
    }
    try:
        with open(path, "x", encoding="utf-8") as file_handle:
            json.dump(marker, file_handle)
            file_handle.flush()
            os.fsync(file_handle.fileno())
    except FileExistsError as error:
        raise VectorStoreConsistencyError(
            "A previous knowledge update did not finish. Inspect and recover it before retrying."
        ) from error
    return marker["operation_id"]


def finish_knowledge_update(path=UPDATE_MARKER_PATH):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def ensure_no_update_in_progress(path=UPDATE_MARKER_PATH):
    if os.path.exists(path):
        raise VectorStoreConsistencyError(
            "Knowledge update is incomplete; retrieval is disabled until recovery finishes."
        )


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mapping_sha256(documents):
    ordered_mapping = [
        {
            "source": document.get("source"),
            "chunk_id": document.get("chunk_id"),
            "file_hash": document.get("file_hash"),
        }
        for document in documents
    ]
    encoded = json.dumps(
        ordered_mapping,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_manifest(documents, documents_path, index_path, generation=None):
    index = faiss.read_index(str(index_path))
    if index.ntotal != len(documents):
        raise VectorStoreConsistencyError(
            "Cannot create vector-store manifest: "
            f"FAISS contains {index.ntotal} vectors but documents contains "
            f"{len(documents)} records."
        )

    return {
        "version": MANIFEST_VERSION,
        "generation": generation or uuid.uuid4().hex,
        "document_count": len(documents),
        "index_dimension": int(index.d),
        "documents_sha256": _sha256_file(documents_path),
        "index_sha256": _sha256_file(index_path),
        "mapping_sha256": _mapping_sha256(documents),
    }


def write_manifest_atomic(path, manifest):
    destination = os.path.abspath(path)
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".manifest-",
            suffix=".tmp",
            delete=False,
        ) as file_handle:
            temp_path = file_handle.name
            json.dump(manifest, file_handle, ensure_ascii=False, indent=2)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def load_manifest(path=MANIFEST_PATH):
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise VectorStoreConsistencyError(
            f"Vector-store manifest is missing or invalid: {path}. "
            "The index must be rebuilt and published as one verified generation."
        ) from error


def validate_vector_store(index, documents, manifest, documents_path, index_path):
    required_fields = {
        "version",
        "generation",
        "document_count",
        "index_dimension",
        "documents_sha256",
        "index_sha256",
        "mapping_sha256",
    }
    if not isinstance(manifest, dict) or not required_fields.issubset(manifest):
        raise VectorStoreConsistencyError("Vector-store manifest is incomplete.")
    if manifest["version"] != MANIFEST_VERSION or not manifest["generation"]:
        raise VectorStoreConsistencyError("Vector-store manifest version or generation is invalid.")

    counts = (int(index.ntotal), len(documents), manifest["document_count"])
    if counts[0] != counts[1] or counts[1] != counts[2]:
        raise VectorStoreConsistencyError(
            "Vector-store count mismatch: "
            f"FAISS={counts[0]}, documents={counts[1]}, manifest={counts[2]}."
        )
    if int(index.d) != manifest["index_dimension"]:
        raise VectorStoreConsistencyError(
            "Vector-store dimension does not match the published manifest."
        )
    if _sha256_file(documents_path) != manifest["documents_sha256"]:
        raise VectorStoreConsistencyError(
            "documents.json does not belong to the published vector-store generation."
        )
    if _sha256_file(index_path) != manifest["index_sha256"]:
        raise VectorStoreConsistencyError(
            "index.faiss does not belong to the published vector-store generation."
        )
    if _mapping_sha256(documents) != manifest["mapping_sha256"]:
        raise VectorStoreConsistencyError(
            "The ordered document mapping does not match the published generation."
        )
    return True
