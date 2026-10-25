"""BabyAGI 精简版 · 第 2 步：拆解任务函数

目标：写一个 create_tasks(objective, last_task, last_result) 函数，
     让 LLM 扮演"任务规划师"，根据已完成的结果，拆出下一步要做的子任务。

运行：
    cd E:/agent-learning/babyagi-mini
    python step2_create.py
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
    """最底层的 LLM 调用，返回纯文本结果。（和 step1 一模一样，照抄即可）"""
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


def create_tasks(objective, last_task, last_result):
    """任务规划师：根据总目标 + 刚完成的任务 + 其结果，拆出下一步子任务。"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个任务规划师（task creation agent）。"
                "你的职责：根据总目标和刚完成的任务结果，拆出下一步需要做的 2-3 个子任务。"
                "每个任务一行，直接列出来，不要编号、不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"总目标：{objective}\n\n"
                f"刚完成的任务：{last_task}\n\n"
                f"这个任务的结果：{last_result}\n\n"
                "请列出下一步要做的子任务（每行一个）："
            ),
        },
    ]
    return call_llm(messages)


if __name__ == "__main__":
    objective = "写一篇面向初学者的 AI Agent 科普文章"
    last_task = "列出这篇文章的 3 个小标题大纲"
    last_result = (
        "1. 什么是 AI Agent？——从聊天机器人到能动手的智能体\n"
        "2. AI Agent 是如何工作的？——感知、思考、行动三步看懂\n"
        "3. AI Agent 能做什么？——生活、学习与工作中的实际应用"
    )
    new_tasks = create_tasks(objective, last_task, last_result)
    print("【拆出的子任务】")
    print(new_tasks)
