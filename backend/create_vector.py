import os
import json
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
from document_loader import load_documents
from utils.file_hash import get_file_hash
from utils.text_clean import clean_text



# ========== 加载 .env ==========
load_dotenv()

# ========== 从 .env 读取配置 ==========
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
CHUNK_SIZE = int(
    os.getenv(
        "CHUNK_SIZE",
        400
    )
)

print("API是否读取:", bool(api_key))
print("BASE_URL:", base_url)
print("Embedding模型:", embedding_model)


# ========== 初始化客户端 ==========
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)


def split_text(
    text,
    chunk_size=CHUNK_SIZE
):
    """
    文档切片：

    1. 优先按照自然段切分
    2. 对“字段：内容”形式进行智能组合
    3. 尽量让一个chunk围绕一个主题
    4. 超长内容再按照长度切
    5. 过滤过短内容
    """

    chunks = []

    min_chunk_size = 20

    # =========================
    # 第一步：按照空行切自然段
    # =========================

    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # =========================
        # 第二步：
        # 如果自然段本身不长，直接作为一个chunk
        # =========================

        if len(paragraph) <= chunk_size:

            if len(paragraph) >= min_chunk_size:

                chunks.append(
                    paragraph
                )

            continue

        # =========================
        # 第三步：
        # 超长自然段再按照句子切
        # =========================

        sentences = paragraph.replace(
            "。",
            "。\n"
        ).split("\n")

        current_chunk = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            # 如果加入后没有超过chunk_size
            if (
                len(current_chunk)
                +
                len(sentence)
                <= chunk_size
            ):

                current_chunk += sentence

            else:

                if len(current_chunk) >= min_chunk_size:

                    chunks.append(
                        current_chunk.strip()
                    )

                current_chunk = sentence

        # 保存最后一块
        if len(current_chunk) >= min_chunk_size:

            chunks.append(
                current_chunk.strip()
            )

    return chunks


def process_file(doc):
    """
    处理单个文件

    输入:
    {
        text:"",
        source:"xxx.txt"
    }

    输出:
    [
        chunk1,
        chunk2
    ]

    """

    chunks=[]


    file_path=os.path.join(
        "knowledge",
        doc["source"]
    )


    file_hash=get_file_hash(
        file_path
    )


    text=doc["text"]



    # 小文件不切
    if len(text)<=CHUNK_SIZE:

        doc_chunks=[
            text
        ]


    else:

        doc_chunks=split_text(
            text
        )



    for index,chunk in enumerate(doc_chunks):


        chunks.append(
            {
                "text":clean_text(chunk),

                "source":doc["source"],

                "chunk_id":
                f"{doc['source']}_{index}",

                "file_hash":
                file_hash,

                "file_type":
                os.path.splitext(
                    doc["source"]
                )[1]
            }
        )


    return chunks

def create_vector():
# 加载知识库所有文件
    documents = load_documents(
        "knowledge"
    )

    # 保存切片后的知识
    chunks=[]

    for doc in documents:


        file_chunks = process_file(
            doc
        )


        chunks.extend(
            file_chunks
        )

    print(
        "原始文件数量:",
        len(documents)
    )


    print(
        "切片数量:",
        len(chunks)
    )


    vectors=[]


    for i, chunk in enumerate(chunks):

        print(
            f"正在生成向量 {i+1}/{len(chunks)}"
        )


        print(
            "长度:",
            len(chunk["text"])
        )


        response = client.embeddings.create(

            model=embedding_model,

            input=clean_text(chunk["text"])

        )


        vector=response.data[0].embedding


        vectors.append(vector)


    vectors=np.array(vectors).astype("float32")


    dimension=vectors.shape[1]


    index=faiss.IndexFlatL2(dimension)


    index.add(vectors)

    # 查看FAISS里面保存了多少个向量
    print(
        "FAISS向量数量:",
        index.ntotal
    )

    print("正在保存FAISS索引...")
    faiss.write_index(
        index,
        "vector_db/index.faiss"  #知识的坐标地图
    )

    with open(
        "vector_db/documents.json",  #知识原文仓库
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            chunks,
            f,
            ensure_ascii=False,
            indent=2
        )
        print("documents保存完成")

        # ==========================
        # 保存向量管理信息
        # ==========================

        meta=[]


        for i, chunk in enumerate(chunks):

            meta.append(
                {
                    "faiss_id": i,
                    "chunk_id": chunk["chunk_id"],
                    "source": chunk["source"],
                    "file_hash": chunk["file_hash"]
                }
            )


        with open(
            "vector_db/meta.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                meta,
                f,
                ensure_ascii=False,
                indent=2
            )


        print(
            "meta保存完成"
        )

    #返回知识块数量
    return len(chunks)

def create_faiss_from_chunks(chunks):
    """
    根据已有chunk生成FAISS

    不负责:
    文件读取
    切片

    只负责:
    chunk -> embedding -> FAISS
    """


    vectors=[]


    for i, chunk in enumerate(chunks):

        print(
            f"生成向量 {i+1}/{len(chunks)}"
        )


        response = client.embeddings.create(

            model=embedding_model,

            input=chunk["text"]

        )


        vectors.append(
            response.data[0].embedding
        )


    vectors=np.array(
        vectors
    ).astype(
        "float32"
    )


    dimension=vectors.shape[1]


    index=faiss.IndexFlatL2(
        dimension
    )


    index.add(
        vectors
    )


    faiss.write_index(
        index,
        "vector_db/index.faiss"
    )


    print(
        "FAISS更新完成"
    )

def create_file_vector(filename):
    """
    只给一个文件生成向量

    用于:
    新增文件
    """

    print(
        "处理新增文件:",
        filename
    )


    documents = load_documents(
        "knowledge"
    )


    target = []


    for doc in documents:

        if doc["source"] == filename:

            target.append(doc)



    if not target:

        print(
            "没有找到文件"
        )

        return []



    chunks=[]


    for doc in target:

        text = doc["text"]


        if len(text)<=CHUNK_SIZE:

            doc_chunks=[
                text
            ]

        else:

            doc_chunks=split_text(
                text
            )


        for index,chunk in enumerate(doc_chunks):

            chunks.append(
                {
                    "text":clean_text(chunk),
                    "source":filename,
                    "chunk_id":
                    f"{filename}_{index}",
                    "file_hash":
                    get_file_hash(
                        os.path.join(
                            "knowledge",
                            filename
                        )
                    )
                }
            )


    return chunks

def create_embedding(chunks):
    """
    根据文本chunk生成向量

    输入:
    [
        {
          "text":"xxx"
        }
    ]

    返回:
    numpy向量数组
    """

    vectors=[]


    for i, chunk in enumerate(chunks):


        print(
            f"生成向量 {i+1}/{len(chunks)}"
        )


        response = client.embeddings.create(

            model=embedding_model,

            input=chunk["text"]

        )


        vector=response.data[0].embedding


        vectors.append(
            vector
        )


    return np.array(
        vectors
    ).astype(
        "float32"
    )

if __name__=="__main__":

    create_vector()