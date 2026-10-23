import os
from dotenv import load_dotenv


load_dotenv()


LLM_MODEL = os.getenv(
    "LLM_MODEL"
)


EMBEDDING_MODEL = os.getenv(
    "LLM_EMBEDDING_MODEL"
)


RAG_TOP_K = int(
    os.getenv(
        "RAG_TOP_K",
        5
    )
)


CHUNK_SIZE = int(
    os.getenv(
        "CHUNK_SIZE",
        450
    )
)

FAISS_TOP_K=int(
    os.getenv(
        "FAISS_TOP_K",
        10
    )
)

RERANK_TOP_K=int(
    os.getenv(
        "RERANK_TOP_K",
        3
    )
)

RERANK_SCORE_THRESHOLD=float(
    os.getenv(
        "RERANK_SCORE_THRESHOLD",
        -2.5
    )
)