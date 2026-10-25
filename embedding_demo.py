"""BabyAGI 深化 · 记忆系统第一步：理解 embedding + 相似度

概念：embedding 把文本变成"向量"（一串数字）。语义相近的文本，向量也相近。
用"余弦相似度"衡量两个向量有多接近（1 = 完全一样，0 = 完全不相关）。

运行：
    python embedding_demo.py
"""
import json
import math
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"


def embed(text):
    """把一段文本变成向量（调用本地 Ollama，不花 API 钱）。"""
    payload = {"model": EMBED_MODEL, "input": text}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["embeddings"][0]  # 返回向量（一串数字）


def cosine(a, b):
    """余弦相似度：范围 0~1，越接近 1 表示语义越相似。"""
    dot = sum(x * y for x, y in zip(a, b))       # 点积：对应位置相乘再求和
    na = math.sqrt(sum(x * x for x in a))        # a 的长度
    nb = math.sqrt(sum(x * x for x in b))        # b 的长度
    return dot / (na * nb)                        # 余弦 = 点积 / (长度×长度)


if __name__ == "__main__":
    a = embed("北京今天的天气怎么样")
    b = embed("上海明天会下雨吗")
    c = embed("帮我写一段 Python 代码")

    print(f"'北京天气' vs '上海天气' 相似度：{cosine(a, b):.3f}")
    print(f"'北京天气' vs '写代码'   相似度：{cosine(a, c):.3f}")
