import json
import numpy as np
import faiss

from openai import OpenAI
from dotenv import load_dotenv
import os

from create_vector import clean_text


# =====================
# 加载环境变量
# =====================

load_dotenv()


api_key = os.getenv(
    "LLM_API_KEY"
)

base_url = os.getenv(
    "LLM_BASE_URL"
)


embedding_model = os.getenv(
    "LLM_EMBEDDING_MODEL",
    "BAAI/bge-large-zh-v1.5"
)



client = OpenAI(
    api_key=api_key,
    base_url=base_url
)



DOCUMENT_PATH = (
    "vector_db/documents.json"
)


INDEX_PATH = (
    "vector_db/index.faiss"
)



def rebuild_faiss():

    """
    根据documents.json重新生成FAISS

    不读取knowledge目录

    只负责:

    documents
        ↓
    embedding
        ↓
    faiss
    """


    # =====================
    # 读取知识切片
    # =====================

    with open(
        DOCUMENT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        documents=json.load(f)



    print(
        "chunk数量:",
        len(documents)
    )



    vectors=[]



    # =====================
    # 生成向量
    # =====================

    for i,doc in enumerate(documents):

        text = clean_text(
        doc["text"]
        )

        text=text.replace("\x00","")
        text=text.strip()


        if not text:
            continue


        try:
           
            response = client.embeddings.create(

                model=embedding_model,

                input=text

            )
            
            vector = response.data[0].embedding
            vectors.append(vector)

        except Exception as e:

            print("===================")
            print("第几个失败:",i)
            print("来源:",doc["source"])
            print("chunk:",doc["chunk_id"])
            print("长度:",len(text))
            print("===================")

            raise e


    # list转numpy

    vectors=np.array(
        vectors
    ).astype(
        "float32"
    )



    # =====================
    # 创建FAISS索引
    # =====================

    dimension = vectors.shape[1]


    index = faiss.IndexFlatL2(
        dimension
    )


    index.add(
        vectors
    )



    print(
        "FAISS数量:",
        index.ntotal
    )



    # 覆盖旧索引

    faiss.write_index(
        index,
        INDEX_PATH
    )


    print(
        "FAISS重建完成"
    )


    return index.ntotal



if __name__=="__main__":

    rebuild_faiss()