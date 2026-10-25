"""BabyAGI 精简版 · 第 4 步：加优先级排序（第三个角色，Agent 完整了）

目标：写 prioritize_tasks(objective, task_list)，让 LLM 把任务列表按重要性
     重新排序；循环里在取任务前先排序，再取第一个。

运行：
    cd E:/agent-learning/babyagi-mini
    python step4_prioritize.py
"""
import json
import os
import urllib.request


def load_env(path):
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
    """执行代理：完成一项具体任务。"""
    messages = [
        {"role": "system", "content": "你是一个执行代理（execution agent）。你的职责：基于给定的总目标，忠实完成交给你的这一项具体任务。直接给出结果，不要反问、不要解释过程。"},
        {"role": "user", "content": f"总目标：{objective}\n\n请完成这个任务：{task}\n\n直接给出结果："},
    ]
    return call_llm(messages)


def create_tasks(objective, last_task, last_result):
    """任务规划师：拆出下一步子任务。"""
    messages = [
        {"role": "system", "content": "你是一个任务规划师（task creation agent）。你的职责：根据总目标和刚完成的任务结果，拆出下一步需要做的 2-3 个子任务。每个任务一行，直接列出来，不要编号、不要解释。"},
        {"role": "user", "content": f"总目标：{objective}\n\n刚完成的任务：{last_task}\n\n这个任务的结果：{last_result}\n\n请列出下一步要做的子任务（每行一个）："},
    ]
    return call_llm(messages)


def prioritize_tasks(objective, task_list):
    """优先级排序师：把任务列表按"最该先做"重新排序（不删除、不新增）。"""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(task_list))
    messages = [
        {"role": "system", "content": "你是一个任务优先级排序师（task prioritization agent）。你的职责：根据总目标，把任务列表按'最该先做'到'可以后做'重新排序。不要删除、不要新增任务，只重新排序。每行一个任务，直接输出排序后的结果，不要编号、不要解释。"},
        {"role": "user", "content": f"总目标：{objective}\n\n当前任务列表：\n{numbered}\n\n请按重要性重新排序（每行一个）："},
    ]
    return call_llm(messages)


if __name__ == "__main__":
    objective = "制定一周的健身计划"
    task_list = ["确定每一天的饮食结构，做哪些健身动作（做几组），健身时长安排和注意事项"]
    MAX_STEPS = 4

    for step in range(MAX_STEPS):
        if not task_list:
            print("\n✅ 任务全部完成！")
            break

        # ★ 第 4 步新增：取任务前，先按重要性重新排序
        if len(task_list) > 1:
            ordered = prioritize_tasks(objective, task_list)
            task_list = [t.strip() for t in ordered.split("\n") if t.strip()]
            print(f"\n📋 排序后清单：{task_list}")

        current = task_list.pop(0)
        print(f"\n=== 第 {step + 1} 轮：执行「{current}」===")

        result = execute_task(objective, current)
        print(f"→ 结果：{result[:80]}...")

        new_tasks = create_tasks(objective, current, result)
        for t in new_tasks.split("\n"):
            t = t.strip()
            if t and t not in task_list and t != current:
                task_list.append(t)
        print(f"→ 剩余任务：{task_list}")
