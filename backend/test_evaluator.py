from llm.qwen import client
from config import LLM_MODEL


def evaluate_answer(
    question,
    expected,
    answer
):

    prompt=f"""
你是一个严格的AI回答评测员。

请判断下面回答是否符合期望答案。

问题:
{question}


期望答案:
{expected}


AI回答:
{answer}


评分规则:

如果AI回答表达的意思与期望一致:
输出 PASS

如果明显错误:
输出 FAIL

只输出 PASS 或 FAIL。
"""


    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )


    result=response.choices[0].message.content.strip()


    return result=="PASS"