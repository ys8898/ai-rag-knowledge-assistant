import os
from create_vector import clean_text
from utils.file_hash import get_file_hash
from database.db import (
    get_knowledge_files,
    update_knowledge_file,
    delete_knowledge_file
)
import json
from rag.rebuild_faiss import rebuild_faiss
from rag.document_manager import add_document_chunks, create_file_chunks, remove_document_chunks

KNOWLEDGE_PATH = "knowledge"
DOCUMENT_PATH = "vector_db/documents.json"


def scan_knowledge_files():
    """
    扫描当前知识库目录

    返回:
    {
        文件名: hash
    }

    例如:
    {
        "company.txt":"71fdedxxx",
        "product.txt":"abc123"
    }
    """


    files = {}


    for filename in os.listdir(KNOWLEDGE_PATH):


        path = os.path.join(
            KNOWLEDGE_PATH,
            filename
        )


        # 只处理文件
        if not os.path.isfile(path):
            continue


        # 计算hash
        file_hash = get_file_hash(path)


        files[filename] = file_hash


    return files


def get_database_files():
    """
    获取数据库中的知识库记录

    返回:
    {
        文件名: hash
    }
    """


    result={}


    files=get_knowledge_files()


    for file in files:


        result[
            file["filename"]
        ] = file["file_hash"]


    return result


def check_changes():

    """
    比较:

    当前knowledge目录

    和

    数据库记录


    返回:

    新增文件
    修改文件
    删除文件

    """


    current_files = scan_knowledge_files()


    old_files = get_database_files()



    new_files=[]

    modified_files=[]

    deleted_files=[]



    # 判断新增和修改

    for filename, file_hash in current_files.items():


        # 数据库没有

        if filename not in old_files:

            new_files.append(filename)


        # 存在但是hash不同

        elif old_files[filename] != file_hash:

            modified_files.append(filename)



    # 判断删除

    for filename in old_files:


        if filename not in current_files:

            deleted_files.append(filename)



    return {

        "new":new_files,

        "modified":modified_files,

        "deleted":deleted_files

    }


#拿当前知识库
def load_documents_json():

    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


#保存documents.json
def save_documents_json(
    documents
):

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


def sync_knowledge():

    """
    同步知识库

    作用:

    1.检测文件变化

    2.删除旧记录

    3.重新生成知识索引

    """


    changes = check_changes()


    print(
        "检测结果:",
        changes
    )


    # =====================
    # 处理删除文件
    # =====================
    # 删除

    for filename in changes["deleted"]:
        print(
        "删除文件:",
        filename
    )

        remove_document_chunks(filename)

        delete_knowledge_file(filename)



    # 新增/修改

    for filename in (
        changes["new"]
        +
        changes["modified"]
    ):


        print(
            "处理文件:",
            filename
        )


        # 如果是修改文件
        # 先删除documents.json中的旧chunk

        if filename in changes["modified"]:

            remove_document_chunks(
                filename
            )


        # 重新读取文件
        # 重新生成chunk

        chunks = create_file_chunks(
            filename
        )


        # 保存新的chunk

        add_document_chunks(
            chunks
        )


        # =====================
        # 更新SQLite文件记录
        # =====================

        path = os.path.join(
            KNOWLEDGE_PATH,
            filename
        )


        file_type = os.path.splitext(
            filename
        )[1]


        file_size = os.path.getsize(
            path
        )


        file_hash = get_file_hash(
            path
        )


        chunk_count = len(
            chunks
        )


        update_knowledge_file(
            filename,
            file_type,
            file_size,
            chunk_count,
            file_hash
        )



    # 更新FAISS

    if (
        changes["new"]
        or
        changes["modified"]
        or
        changes["deleted"]
    ):

        rebuild_faiss()


    else:

        print(
            "知识库无变化"
        )

    return changes

if __name__=="__main__":

    sync_knowledge()