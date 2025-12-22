# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.7
#   kernelspec:
#     display_name: mcp312
#     language: python
#     name: python3
# ---

# %%
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


# %%
model = ChatOllama(
    model="Llama-3.1-Swallow-8B:latest",
    base_url="http://localhost:11434",  # 省略可
    temperature=0.2,
)

response = model.invoke(
    [HumanMessage(content="LangChainとOllamaの接続テスト")]
)

# %%
response.content
