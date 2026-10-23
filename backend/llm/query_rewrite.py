from llm.qwen import client, model

def rewrite_question(
    history,
    question
):

    prompt = f"""
根据聊天历史，把用户当前问题改写成完整的问题。

要求：
1. 消除“它”“他”“这个”等指代。
2. 不回答问题。
3. 只输出改写后的问题。


聊天历史:

{history}


当前问题:

{question}


改写:
"""


    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )


    return response.choices[0].message.content