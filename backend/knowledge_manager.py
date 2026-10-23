import json
import os
import shutil
import tempfile
import threading

from rag.index_integrity import begin_knowledge_update, finish_knowledge_update


KNOWLEDGE_PATH = "knowledge"
DELETE_BACKUP_PATH = os.path.join(KNOWLEDGE_PATH, ".delete-backups")
_FILE_UPDATE_LOCK = threading.RLock()


def _knowledge_path(filename):
    if not filename or filename != os.path.basename(filename) or filename in {".", ".."}:
        raise ValueError("Invalid knowledge filename")
    return os.path.join(KNOWLEDGE_PATH, filename)


def list_documents():
    result=[]
    files=os.listdir(KNOWLEDGE_PATH)
    if not os.path.exists("vector_db/documents.json"):
        documents=[]
    else:
        with open("vector_db/documents.json", "r", encoding="utf-8") as f:
            documents=json.load(f)

    for filename in files:
        path=os.path.join(KNOWLEDGE_PATH, filename)
        if not os.path.isfile(path):
            continue
        count=0
        for doc in documents:
            if doc["source"] == filename:
                count +=1
        size=os.path.getsize(path)
        file_type=os.path.splitext(filename)[1]
        result.append(
            {
                "filename":filename,
                "type":file_type,
                "size":size,
                "chunks":count
            }
        )
    return result


def _backup_path(filename):
    os.makedirs("vector_db", exist_ok=True)
    descriptor, path = tempfile.mkstemp(
        dir="vector_db",
        prefix=f".{os.path.basename(filename)}-",
        suffix=".backup",
    )
    os.close(descriptor)
    return path


def _delete_backup_path(filename):
    """Create a delete backup on the same mounted filesystem as the source."""
    os.makedirs(DELETE_BACKUP_PATH, exist_ok=True)
    descriptor, path = tempfile.mkstemp(
        dir=DELETE_BACKUP_PATH,
        prefix=f".{os.path.basename(filename)}-",
        suffix=".backup",
    )
    os.close(descriptor)
    return path


def _cleanup_delete_backup(backup):
    if backup and os.path.exists(backup):
        os.remove(backup)
    try:
        os.rmdir(DELETE_BACKUP_PATH)
    except OSError:
        pass


def save_document(filename, source_file, sync_callback):
    with _FILE_UPDATE_LOCK:
        return _save_document(filename, source_file, sync_callback)


def _save_document(filename, source_file, sync_callback):
    """Stage an upload and restore the source file if synchronization fails."""
    path = _knowledge_path(filename)
    os.makedirs(KNOWLEDGE_PATH, exist_ok=True)
    backup = None
    staged = None
    update_started = False
    rollback_complete = False
    sync_completed = False
    source_replaced = False
    try:
        descriptor, staged = tempfile.mkstemp(
            dir=KNOWLEDGE_PATH,
            prefix=f".{os.path.basename(filename)}-",
            suffix=".upload",
        )
        with os.fdopen(descriptor, "wb") as file_handle:
            shutil.copyfileobj(source_file, file_handle)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        begin_knowledge_update()
        update_started = True
        if os.path.exists(path):
            backup_candidate = _backup_path(filename)
            try:
                shutil.copy2(path, backup_candidate)
                backup = backup_candidate
            except Exception:
                try:
                    os.remove(backup_candidate)
                except OSError:
                    pass
                raise
        os.replace(staged, path)
        staged = None
        source_replaced = True
        result = sync_callback()
        sync_completed = True
        finish_knowledge_update()
        update_started = False
        return result
    except Exception as update_error:
        if sync_completed:
            raise RuntimeError(
                "Knowledge upload committed, but the update marker could not be cleared."
            ) from update_error
        try:
            if backup and os.path.exists(backup):
                os.replace(backup, path)
                backup = None
            elif source_replaced and os.path.exists(path):
                os.remove(path)
            rollback_complete = True
        except Exception as rollback_error:
            raise RuntimeError(
                f"Knowledge upload failed and source rollback was incomplete: {rollback_error}"
            ) from update_error
        if update_started and rollback_complete:
            finish_knowledge_update()
            update_started = False
        raise
    finally:
        for temporary in (backup, staged):
            if temporary and os.path.exists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass


def delete_document(filename, sync_callback=None):
    with _FILE_UPDATE_LOCK:
        return _delete_document(filename, sync_callback)


def _delete_document(filename, sync_callback=None):
    path = _knowledge_path(filename)
    if not os.path.exists(path):
        return False

    backup = None
    update_started = False
    source_moved = False
    sync_completed = False
    cleanup_backup = True
    try:
        begin_knowledge_update()
        update_started = True
        backup = _delete_backup_path(filename)
        os.replace(path, backup)
        source_moved = True
        if sync_callback is not None:
            sync_callback()
        sync_completed = True
        finish_knowledge_update()
        update_started = False
    except Exception as update_error:
        if sync_completed:
            raise RuntimeError(
                "Knowledge deletion committed, but the update marker could not be cleared."
            ) from update_error
        try:
            if source_moved and backup and os.path.exists(backup):
                os.replace(backup, path)
                backup = None
        except Exception as rollback_error:
            cleanup_backup = False
            raise RuntimeError(
                f"Knowledge deletion failed and source rollback was incomplete: {rollback_error}"
            ) from update_error
        if update_started:
            finish_knowledge_update()
            update_started = False
        raise
    finally:
        if cleanup_backup:
            try:
                _cleanup_delete_backup(backup)
            except OSError:
                pass
    return True
