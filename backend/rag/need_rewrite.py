from rag.search import small_talk_reply


def need_rewrite(question, history):

    if not history:
        return False


    question = question.strip()


    # 先排除闲聊

    if small_talk_reply(question):
        return False



    rewrite_keywords = [
        "他",
        "她",
        "它",
        "这个",
        "那个",
        "刚才",
        "之前",
        "上面",
        "这个公司",
        "这家公司",
        "多少",
        "什么时候",
        "怎么样",
        "如何"
    ]


    for word in rewrite_keywords:

        if word in question:
            return True


    return False