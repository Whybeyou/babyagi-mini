"""BabyAGI 精简版 · 第 1 步：执行任务函数

目标：写一个 execute_task(objective, task) 函数，
     让 LLM 扮演"执行代理"，忠实完成交给你的一项具体任务。

运行：
    cd E:/agent-learning/babyagi-mini
    python step1_execute.py
"""
import json
import os
import urllib.request


def load_env(path):
    """简单的 .env 加载器，不依赖第三方包。"""
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip())


load_env(os.path.join(os.path.dirname(__file__), "..", ".env"))
API_KEY = os.environ["DEEPSEEK_API_KEY"]
URL = "https://api.deepseek.com/v1/chat/completions"


def call_llm(messages):
    """最底层的 LLM 调用，返回纯文本结果。

    所有"角色"（执行/拆解/排序）都只是 messages 不同，底层调用是同一个。
    """
    payload = {"model": "deepseek-v4-pro", "messages": messages}
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def execute_task(objective, task):
    """执行代理：基于总目标，完成交给你的一项具体任务。"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个执行代理（execution agent）。"
                "你的职责：基于给定的总目标，忠实完成交给你的这一项具体任务。"
                "直接给出结果，不要反问、不要解释过程。"
            ),
        },
        {
            "role": "user",
            "content": f"总目标：{objective}\n\n请完成这个任务：{task}\n\n直接给出结果：",
        },
    ]
    return call_llm(messages)


if __name__ == "__main__":
    # 演示：一个目标 + 一项具体任务
    objective = "写一篇面向初学者的 AI Agent 科普文章"
    task = "列出这篇文章的 3 个小标题大纲"
    result = execute_task(objective, task)
    print("【执行结果】")
    print(result)
