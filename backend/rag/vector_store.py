import json


DOCUMENT_PATH = "vector_db/documents.json"


#读取旧知识
def load_old_documents():
    """
    读取已有知识切片

    返回:
    [
       {
          text:"",
          source:"",
          file_hash:""
       }
    ]
    """

    try:

        with open(
            DOCUMENT_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            documents=json.load(f)


        return documents


    except FileNotFoundError:

        # 第一次运行，没有旧数据

        return []


#删除指定文件产生的chunk
def remove_documents_by_file(
    documents,
    filename
):
    """
    删除指定文件产生的chunk


    例如:

    删除:
    product.txt


    保留:
    company.txt


    """


    new_documents=[]


    for doc in documents:


        if doc["source"] != filename:

            new_documents.append(
                doc
            )


    return new_documents

def update_documents(
    documents,
    filename,
    new_chunks
):
    """
    更新指定文件知识


    流程:

    1. 删除旧文件chunk

    2. 添加新chunk


    """

    # 删除旧知识

    documents = remove_documents_by_file(
        documents,
        filename
    )


    # 添加新知识

    documents.extend(
        new_chunks
    )


    return documents