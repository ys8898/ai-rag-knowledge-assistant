import json
import os
from document_loader import load_documents
from utils.file_hash import get_file_hash
from create_vector import CHUNK_SIZE, split_text, clean_text

DOCUMENT_PATH = "vector_db/documents.json"



def find_document_ids(filename):
    """
    查找某个文件对应的chunk编号


    返回:

    [
        0,
        1,
        2
    ]

    代表documents中的位置
    """


    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        documents=json.load(f)



    ids=[]


    for index,doc in enumerate(documents):


        if doc["source"] == filename:

            ids.append(
                index
            )


    return ids

def remove_document_chunks(filename):
    """
    删除指定文件的所有知识切片

    例如:

    product.txt

    原documents:

    company
    product_0
    product_1
    product_2
    service


    删除后:

    company
    service


    返回:
    删除了多少个chunk
    """


    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        documents = json.load(f)



    # 保存删除后的结果

    new_documents = []


    delete_count = 0


    for doc in documents:


        # 如果来源是目标文件
        if doc["source"] == filename:

            delete_count += 1

            continue


        new_documents.append(
            doc
        )



    # 覆盖保存

    with open(
        DOCUMENT_PATH,
        "w",
        encoding="utf-8"
    ) as f:


        json.dump(
            new_documents,
            f,
            ensure_ascii=False,
            indent=2
        )


    return delete_count


def create_file_chunks(filename):
    """
    只处理一个文件

    不重新读取整个knowledge目录


    返回:

    [
        {
            text:"",
            source:"",
            chunk_id:"",
            file_hash:""
        }
    ]

    """


    file_path = os.path.join(
        "knowledge",
        filename
    )


    # 读取单个文件

    documents = load_documents(
        "knowledge"
    )


    target = None


    for doc in documents:

        if doc["source"] == filename:

            target = doc

            break



    if target is None:

        return []



    text = target["text"]
    # 先清洗原始文本
    text = clean_text(
        text
    )

    file_hash = get_file_hash(
        file_path
    )


    # 和create_vector保持一致

    if len(text) <= CHUNK_SIZE:

        chunks = [
            text
        ]

    else:

        chunks = split_text(
            text
        )



    result=[]


    for index,chunk in enumerate(chunks):

        result.append(
            {
                "text":clean_text(chunk),

                "source":filename,

                "chunk_id":
                    f"{filename}_{index}",

                "file_hash":
                    file_hash,

                "file_type":
                    os.path.splitext(
                        filename
                    )[1]
            }
        )


    return result


def add_document_chunks(
    new_chunks
):
    """
    将新的知识块加入documents.json

    参数:

    new_chunks:
    create_file_chunks返回的数据

    """


    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        documents=json.load(f)



    # 添加新chunk

    documents.extend(
        new_chunks
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


    return len(new_chunks)