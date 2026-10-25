"""BabyAGI 精简版 · 第 3 步：加循环，让它自己跑

目标：写一个任务列表 + 循环，让 Agent 自动"取任务→执行→拆新任务→加进列表"，
     直到任务清空或达到步数上限。

运行：
    cd E:/agent-learning/babyagi-mini
    python step3_loop.py
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
    """最底层的 LLM 调用，返回纯文本结果。"""
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
        {"role": "system", "content": "你是一个执行代理（execution agent）。你的职责：基于给定的总目标，忠实完成交给你的这一项具体任务。直接给出结果，不要反问、不要解释过程。"},
        {"role": "user", "content": f"总目标：{objective}\n\n请完成这个任务：{task}\n\n直接给出结果："},
    ]
    return call_llm(messages)


def create_tasks(objective, last_task, last_result):
    """任务规划师：根据总目标 + 刚完成的任务 + 其结果，拆出下一步子任务。"""
    messages = [
        {"role": "system", "content": "你是一个任务规划师（task creation agent）。你的职责：根据总目标和刚完成的任务结果，拆出下一步需要做的 2-3 个子任务。每个任务一行，直接列出来，不要编号、不要解释。"},
        {"role": "user", "content": f"总目标：{objective}\n\n刚完成的任务：{last_task}\n\n这个任务的结果：{last_result}\n\n请列出下一步要做的子任务（每行一个）："},
    ]
    return call_llm(messages)


if __name__ == "__main__":
    objective = "从零开始掌握 AI Agent"
    task_list = ["列出学习 AI Agent 需要掌握的前 3 个知识点"]
    MAX_STEPS = 5  # 安全阀：最多跑 5 轮，防止无限循环烧钱

    for step in range(MAX_STEPS):
        if not task_list:
            print("\n✅ 任务全部完成！")
            break

        # 1. 取出第一个任务（pop(0) = 取走并删除）
        current = task_list.pop(0)
        print(f"\n=== 第 {step + 1} 轮：执行「{current}」===")

        # 2. 执行它
        result = execute_task(objective, current)
        print(f"→ 结果：{result[:80]}...")

        # 3. 拆新任务，加进列表（split 拆行 + 去重）
        new_tasks = create_tasks(objective, current, result)
        for t in new_tasks.split("\n"):
            t = t.strip()
            if t and t not in task_list and t != current:
                task_list.append(t)

        # 4. 打印当前待办清单
        print(f"→ 剩余任务：{task_list}")
