import os
import json


KNOWLEDGE_PATH = "knowledge"


def list_documents():

    result=[]


    # 获取知识库目录中的文件
    files=os.listdir(
        KNOWLEDGE_PATH
    )


    # 如果没有生成向量文件
    # 防止第一次启动报错

    if not os.path.exists(
        "vector_db/documents.json"
    ):

        documents=[]

    else:

        with open(
            "vector_db/documents.json",
            "r",
            encoding="utf-8"
        ) as f:

            documents=json.load(f)



    for filename in files:


        # 初始化切片数量

        count=0


        # 统计这个文件产生多少chunk

        for doc in documents:


            if doc["source"] == filename:

                count +=1



        # 文件完整路径

        path=os.path.join(
            KNOWLEDGE_PATH,
            filename
        )


        # 获取文件大小(byte)

        size=os.path.getsize(
            path
        )



        # 获取文件类型

        file_type=os.path.splitext(
            filename
        )[1]


        result.append(
            {
                "filename":filename,

                "type":file_type,

                "size":size,

                "chunks":count
            }
        )



    return result


#删除文件
def delete_document(filename):


    path=os.path.join(
        KNOWLEDGE_PATH,
        filename
    )


    # 文件不存在
    if not os.path.exists(path):

        return False


    # 删除文件
    os.remove(path)


    return True