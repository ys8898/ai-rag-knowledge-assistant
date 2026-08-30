from FlagEmbedding import FlagReranker
import warnings

warnings.filterwarnings(
    "ignore"
)

reranker = FlagReranker(
    "BAAI/bge-reranker-base",
    use_fp16=True
)


def rerank_documents(
    question,
    documents
):

    """
    question:
        用户问题

    documents:
        FAISS召回的候选文本列表

    返回:
        按相关度排序后的结果
    """


    pairs=[]


    for doc in documents:

        pairs.append(
            [
                question,
                doc["text"]
            ]
        )


    scores = reranker.compute_score(
        pairs
    )


    result=[]


    for doc,score in zip(
        documents,
        scores
    ):

        doc["rerank_score"]=score

        result.append(
            doc
        )


    # 分数从高到低排序

    result.sort(
        key=lambda x:x["rerank_score"],
        reverse=True
    )


    return result