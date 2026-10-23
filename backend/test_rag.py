import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import json
from rag.search import search_vector
from llm.qwen import ask_qwen
from test_evaluator import evaluate_answer

# 读取测试问题

with open(
    "test_cases.json",
    "r",
    encoding="utf-8"
) as f:

    cases=json.load(f)



print(
    "测试数量:",
    len(cases)
)



success=0



for index,case in enumerate(cases):

    print("\n====================")
    print(
        "测试",
        index+1
    )

    question = case["question"]
    expected = case.get("expected", "")  

    print(
        "问题:",
        question
    )


    # RAG搜索

    result=search_vector(
        question
    )


    if not result["found"]:

        answer="知识库中没有相关信息。"

    else:

        answer=ask_qwen(
            "test_user",
            question,
            result["context"]
        )


    print(
        "回答:",
        answer
    )

    print(
        "期望:",
        expected
    )

    passed = evaluate_answer(
        question,      # 第1个参数：问题
        expected,      # 第2个参数：期望答案
        answer         # 第3个参数：实际回答
    )


    if passed:

        print("结果: 通过")

        success+=1

    else:

        print("结果:失败")
print("\n====================")

print(
    f"通过率: {success}/{len(cases)}"
)