import json



DOCUMENT_PATH = "vector_db/documents.json"



def save_documents(documents):
    """
    保存知识切片


    documents:
        当前全部知识chunk

    写入:
        documents.json

    """


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