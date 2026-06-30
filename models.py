import os
from langchain_openai import ChatOpenAI

# print(f"{os.getenv('DASHSCOPE_API_KEY')}")

# 千文模型
qwen = ChatOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    # model="qwen3-max-preview",
    model="qwen-plus",
    temperature=0.7,
    max_tokens=1000,
    timeout=30
)

