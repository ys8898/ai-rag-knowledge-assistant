import faiss
import os
import json


INDEX_PATH = "vector_db/index.faiss"

DOCUMENT_PATH = "vector_db/documents.json"


def add_vectors(
    vectors,
    chunks
):
    """
    向已有FAISS增加新的向量

    参数:

    vectors:
        新生成的向量

    chunks:
        对应文本信息
    """


    # =====================
    # 读取旧FAISS
    # =====================

    index = faiss.read_index(
        INDEX_PATH
    )


    print(
        "原FAISS数量:",
        index.ntotal
    )



    # =====================
    # 增加新向量
    # =====================

    index.add(
        vectors
    )


    print(
        "新增后数量:",
        index.ntotal
    )



    # =====================
    # 保存FAISS
    # =====================

    faiss.write_index(
        index,
        INDEX_PATH
    )



    # =====================
    # 更新documents.json
    # =====================

    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        documents=json.load(f)



    # 追加新的chunk

    documents.extend(
        chunks
    )


    with open(
        DOCUMENT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            documents,
            f,
            ensure_ascii=False,
            indent=2
        )



    print(
        "documents更新完成"
    )