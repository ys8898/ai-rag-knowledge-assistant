import faiss
import json
import numpy as np
import time
from openai import OpenAI
from dotenv import load_dotenv
import os

from config import FAISS_TOP_K, RERANK_SCORE_THRESHOLD, RERANK_TOP_K
from rerank import rerank_documents
from utils.confidence import calculate_confidence
from utils.timer import Timer

load_dotenv()

# ========== 从 .env 读取配置 ==========
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")  # 默认值


if not api_key:
    raise ValueError("❌ 未找到 LLM_API_KEY，请检查 .env 文件")
if not base_url:
    raise ValueError("❌ 未找到 LLM_BASE_URL，请检查 .env 文件")


# ========== 初始化客户端 ==========
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# ========== 加载向量数据库 ==========
def load_vector_data():

    index = faiss.read_index(
        "vector_db/index.faiss"
    )


    with open(
        "vector_db/documents.json",
        "r",
        encoding="utf-8"
    ) as f:

        documents=json.load(f)


    return index, documents

#闲聊回复
def small_talk_reply(question):

    question = question.strip()


    if any(
        word in question
        for word in [
            "你好",
            "您好",
            "嗨",
            "hi"
        ]
    ):
        return "您好，我是智能助手，请问有什么可以帮您？"



    if any(
        word in question
        for word in [
            "谢谢",
            "感谢",
            "多谢"
        ]
    ):
        return "不客气，有需要随时可以问我。"



    if any(
        word in question
        for word in [
            "再见",
            "拜拜"
        ]
    ):
        return "好的，再见。"


    return None

def search_vector(question):

    total_timer=Timer()

    index, documents = load_vector_data()

    # 用户问题
    print("\n问题:", question)

    # =========================
    # 开始统计检索耗时
    # =========================
    retrieval_start = time.perf_counter()

    faiss_timer=Timer()

    # 问题转向量
    response = client.embeddings.create(
        model=embedding_model,  # 从 .env 读取
        input=question
    )


    query_vector=np.array(
        [
            response.data[0].embedding
        ]
    ).astype("float32")


    distance, indices = index.search(
        query_vector,
        FAISS_TOP_K
    )

    faiss_cost=faiss_timer.cost()

    retrieval_time = time.perf_counter() - retrieval_start

    # for rank, i in enumerate(indices[0]):

    #     print(
    #         "排名:",
    #         rank + 1
    #     )

    #     print(
    #         "距离:",
    #         distance[0][rank]
    #     )

    #     print(
    #         "来源:",
    #         documents[i]["source"]
    #     )

    #     print(
    #         "切片:",
    #         documents[i]["chunk_id"]
    #     )

    #     print(
    #         "内容:",
    #         documents[i]["text"][:100]
    #     )

    #     print("----------------")


    print("\n===== FAISS 检索 =====")

    print(
        "Top K:",
        FAISS_TOP_K
    )

    print(
        "耗时:",
        round(retrieval_time, 3),
        "秒"
    )

    print(
        "距离:",
        distance[0]
    )

    #  如果最接近的资料仍然太远
    # if distance[0][0] > rag_threshold:

    #     print("未找到相关知识")

    #     return {
    #     "context": "",
    #     "sources": [],
    #     "found": False
    #     }

    results=[]


    for rank, i in enumerate(indices[0]):

        doc = documents[i]


        results.append(
            {
                "text": doc["text"],
                "source": doc["source"],
                "chunk_id": doc["chunk_id"],
                "score": float(distance[0][rank])
            }
        )

    # =====================
    # Rerank重新排序
    # =====================

    rerank_start = time.perf_counter()

    rerank_timer=Timer()

    results = rerank_documents(
        question,
        results
    )

    rerank_cost=rerank_timer.cost()

    rerank_time = time.perf_counter() - rerank_start

    print("\n===== RERANK 原始结果 =====")

    for rank, item in enumerate(results):

        print(
            "排名:",
            rank + 1,
            "| score:",
            round(item["rerank_score"], 3),
            "| source:",
            item["source"],
            "| chunk:",
            item["chunk_id"]
        )

    # =====================
    # 去重
    # =====================

    rerank_count = len(results)

    seen = set()
    new_results = []

    for item in results:

        key = (
            item["source"],
            item["chunk_id"]
        )

        if key not in seen:

            new_results.append(item)

            seen.add(key)

    results = new_results

    deduplicated_count = len(results)

    # rerank分数过滤

    before_threshold_count = len(results)

    results = [
        item
        for item in results
        if item["rerank_score"]
        >= RERANK_SCORE_THRESHOLD
    ]

    after_threshold_count = len(results)


    # 没有相关知识
    if not results:

        return {
            "context":"",
            "sources":[],
            "found":False
        }


    # 最终top K

    results = results[:RERANK_TOP_K]

    print("\n===== RAG Pipeline =====")

    print(
        "FAISS候选:",
        FAISS_TOP_K
    )

    print(
        "Rerank结果:",
        rerank_count
    )

    print(
        "去重后:",
        deduplicated_count
    )

    print(
        "阈值过滤前:",
        before_threshold_count
    )

    print(
        "阈值过滤后:",
        after_threshold_count
    )

    print(
        "最终返回:",
        len(results)
    )

    print(
        "FAISS耗时:",
        round(retrieval_time, 3),
        "秒"
    )

    print(
        "Rerank耗时:",
        round(rerank_time, 3),
        "秒"
    )

    # =========================
    # 最终结果
    # =========================

    print("\n===== 最终 RAG 结果 =====")

    for rank, item in enumerate(results):

        print(
            "排名:",
            rank + 1,
            "| score:",
            round(item["rerank_score"], 3),
            "| source:",
            item["source"],
            "| chunk:",
            item["chunk_id"]
        )

    print(
    f"""
    ===== RAG性能 =====

    FAISS:
    {faiss_cost}s

    RERANK:
    {rerank_cost}s

    总耗时:
    {total_timer.cost()}s

    """
    )

    sources = []

    for item in results:

        sources.append(
            {
                "source": item["source"],
                "chunk_id": item["chunk_id"],
                "score": float(item["rerank_score"]),
                "text": item["text"]
            }
        )


    context = "\n\n".join(
        item["text"]
        for item in results
    )

    confidence = calculate_confidence(
    results
    )
    return {

        "context": context,

        "sources": sources,

        "found": True,

        "confidence":confidence

    }

# 测试代码
if __name__=="__main__":

    result = search_vector(
        "你们公司叫什么"
    )

    print(result)