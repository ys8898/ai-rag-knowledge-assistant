import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL")

if not api_key or not base_url or not model:
    raise ValueError(
        "LLM_API_KEY, LLM_BASE_URL and LLM_MODEL must be configured in the environment"
    )

client = OpenAI(api_key=api_key, base_url=base_url)

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "你好"}],
)

print(response.choices[0].message.content)
