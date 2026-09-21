from openai import OpenAI

client = OpenAI(
    api_key="",  # 你的 API Key
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",  # 注意：这个 ID 要去模型广场确认
    messages=[{"role": "user", "content": "你好"}]
)

print(response.choices[0].message.content)
