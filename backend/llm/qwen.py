from openai import OpenAI
from dotenv import load_dotenv
import os

from database.db import (
    get_history,
    save_message
)


load_dotenv()


# ========== 从 .env 读取配置 ==========
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL")

if not api_key:
    raise ValueError("❌ 未找到 LLM_API_KEY，请检查 .env 文件")
if not base_url:
    raise ValueError("❌ 未找到 LLM_BASE_URL，请检查 .env 文件")
if not model:
    raise ValueError("❌ 未找到 LLM_MODEL，请检查 .env 文件")

# ========== 初始化客户端 ==========
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)


def ask_qwen(
    user_id,
    question,
    context,
    
):

    history = get_history(user_id)

    messages = [
    {
        "role":"system",
        "content":f"""
你是企业知识库助手。

回答规则：

1. 只能根据知识回答。
2. 不允许使用外部知识。
3. 不允许猜测。
4. 如果知识中出现“暂无公开信息”，必须保留。
5. 如果知识为空：
回答：
知识库中没有相关信息。
6. 如果知识不足：
说明当前知识有限。
7. 回答简洁。

知识：
{context}
"""
    }
]
    messages.extend(history)


    messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    print("\n========== QWEN输入 ==========")

    print("问题:")
    print(question)

    print("\n知识:")
    print(context)

    print("\n历史:")
    print(history)

    print("==============================\n")

    response = client.chat.completions.create(

        model=model,

        messages=messages,

        temperature=0.1,

        stream=True

    )

    full_answer=""


    for chunk in response:

        if chunk.choices[0].delta.content:

            text=chunk.choices[0].delta.content

            full_answer += text

            yield f"event: token\ndata: {text}\n\n"



    save_message(
        user_id,
        "user",
        question
    )


    save_message(
        user_id,
        "assistant",
        full_answer
    )


if __name__=="__main__":

    for text in ask_qwen(
        "test",
        "公司叫什么",
        "公司名称：未来科技有限公司"
    ):

        print(
            text,
            end="",
            flush=True
        )
