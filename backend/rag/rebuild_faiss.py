import json
import os

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from create_vector import clean_text


load_dotenv()
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
client = OpenAI(api_key=api_key, base_url=base_url)

DOCUMENT_PATH = "vector_db/documents.json"
INDEX_PATH = "vector_db/index.faiss"


def rebuild_faiss(documents=None, index_path=INDEX_PATH, empty_dimension=None):
    """Build and verify a FAISS file at index_path without publishing it."""
    if documents is None:
        with open(DOCUMENT_PATH, "r", encoding="utf-8") as file_handle:
            documents = json.load(file_handle)

    print("Chunk count:", len(documents))
    vectors = []
    for position, document in enumerate(documents):
        text = clean_text(document["text"]).replace("\x00", "").strip()
        if not text:
            raise ValueError(
                f"Cannot build FAISS: empty text at document position {position} "
                f"({document.get('source')} / {document.get('chunk_id')})"
            )
        try:
            response = client.embeddings.create(model=embedding_model, input=text)
            vectors.append(response.data[0].embedding)
        except Exception:
            print("Embedding failed at document position:", position)
            print("Source:", document.get("source"))
            print("Chunk:", document.get("chunk_id"))
            raise

    if vectors:
        vector_array = np.asarray(vectors, dtype="float32")
        if vector_array.ndim != 2 or vector_array.shape[0] != len(documents):
            raise ValueError("Embedding output count does not match documents")
        dimension = int(vector_array.shape[1])
    else:
        vector_array = None
        dimension = empty_dimension
        if dimension is None and os.path.exists(INDEX_PATH):
            dimension = int(faiss.read_index(INDEX_PATH).d)
        if dimension is None:
            raise ValueError(
                "Cannot build an empty FAISS index without a known embedding dimension"
            )

    index = faiss.IndexFlatL2(dimension)
    if vector_array is not None:
        index.add(vector_array)
    faiss.write_index(index, str(index_path))

    written_index = faiss.read_index(str(index_path))
    if written_index.ntotal != len(documents) or written_index.d != dimension:
        raise RuntimeError("Written FAISS candidate failed verification")
    print("FAISS candidate count:", written_index.ntotal)
    return written_index.ntotal


if __name__ == "__main__":
    rebuild_faiss()
