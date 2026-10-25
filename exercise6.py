"""阶段 5a 练习：自己写 embedding + 相似度，用你自己的话测试。

任务（3 步）：
1. 参考 embedding_demo.py，写出 embed(text) 和 cosine(a, b) 函数（关键行加注释）。
2. 用你自己的 4 句话测试（比如关于健身、游戏、学习、美食），两两算相似度。
   提示：写一个循环，或者手动写 6 个 cosine 调用（4 句话两两组合 = 6 对）。
3. 运行 `python exercise6.py`，找出"最相似的一对"，把结果贴给我。

验收标准：
- 能跑通
- 能用自己的话说出"为什么这一对相似度最高"
- cosine 函数的 4 行关键代码有注释
"""
# ---- 从下面开始写你的代码 ----
# TODO: 复制 embedding_demo.py 的 embed + cosine，换你自己的 4 句话测试
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
    a = embed("无畏契约")
    b = embed("上海F1")
    c = embed("无畏契约上海冠军赛")

    print(f"'无畏契约' vs '上海F1' 相似度：{cosine(a, b):.3f}")
    print(f"'无畏契约' vs '无畏契约上海冠军赛'   相似度：{cosine(a, c):.3f}")