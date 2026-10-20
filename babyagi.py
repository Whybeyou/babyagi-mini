"""BabyAGI Mini — 从零手写的任务驱动自主 Agent。

用三个 LLM 角色 + 一个任务循环，复刻 BabyAGI 的核心思想，纯标准库实现。

角色：
    execute_task      执行代理：完成一项具体任务
    create_tasks      任务规划师：根据结果拆出下一步子任务
    prioritize_tasks  优先级排序师：按重要性重排任务列表

运行：
    export DEEPSEEK_API_KEY=sk-xxx   # 或创建 .env 文件
    python babyagi.py
"""
import json
import os
import urllib.request

BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"


def load_env(path=".env"):
    """从 .env 文件读取环境变量（不覆盖已存在的）。"""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip())


def call_llm(messages):
    """底层 LLM 调用：三个角色共用，区别只在 messages。"""
    payload = {"model": MODEL, "messages": messages}
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def execute_task(objective, task):
    """执行代理：基于总目标，完成一项具体任务，直接给结果。"""
    messages = [
        {"role": "system", "content": "你是一个执行代理（execution agent）。基于总目标忠实完成交给你的任务，直接给结果，不要反问、不要解释过程。"},
        {"role": "user", "content": f"总目标：{objective}\n\n请完成这个任务：{task}\n\n直接给出结果："},
    ]
    return call_llm(messages)


def create_tasks(objective, last_task, last_result):
    """任务规划师：根据上一步结果，拆出 2-3 个下一步子任务。"""
    messages = [
        {"role": "system", "content": "你是一个任务规划师（task creation agent）。根据总目标和刚完成的任务结果，拆出下一步 2-3 个子任务。每行一个，直接列出，不要编号、不要解释。"},
        {"role": "user", "content": f"总目标：{objective}\n\n刚完成的任务：{last_task}\n\n这个任务的结果：{last_result}\n\n请列出下一步子任务（每行一个）："},
    ]
    return call_llm(messages)


def prioritize_tasks(objective, task_list):
    """优先级排序师：把任务列表按"最该先做"重新排序（不删不增）。"""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(task_list))
    messages = [
        {"role": "system", "content": "你是一个任务优先级排序师（task prioritization agent）。根据总目标，把任务按'最该先做'到'可以后做'重新排序。不要删除、不要新增，只重新排序。每行一个，直接输出，不要编号、不要解释。"},
        {"role": "user", "content": f"总目标：{objective}\n\n当前任务列表：\n{numbered}\n\n请按重要性重新排序（每行一个）："},
    ]
    return call_llm(messages)


def main(objective, first_task, max_steps=5):
    """Agent 主循环：排序 → 取任务 → 执行 → 拆新任务 → 去重 → 重复。"""
    task_list = [first_task]

    for step in range(max_steps):
        if not task_list:
            print("\n✅ 任务全部完成！")
            break

        # 取任务前先按重要性排序
        if len(task_list) > 1:
            ordered = prioritize_tasks(objective, task_list)
            task_list = [t.strip() for t in ordered.split("\n") if t.strip()]

        current = task_list.pop(0)
        print(f"\n=== 第 {step + 1} 轮：执行「{current}」===")

        result = execute_task(objective, current)
        print(f"→ 结果：{result[:100]}...")

        new_tasks = create_tasks(objective, current, result)
        for t in new_tasks.split("\n"):
            t = t.strip()
            if t and t not in task_list and t != current:
                task_list.append(t)
        print(f"→ 剩余任务：{task_list}")


if __name__ == "__main__":
    load_env()
    if "DEEPSEEK_API_KEY" not in os.environ:
        raise SystemExit("请先设置 DEEPSEEK_API_KEY（export 或写入 .env）")
    main(
        objective="从零开始掌握 AI Agent",
        first_task="列出学习 AI Agent 需要掌握的前 3 个知识点",
        max_steps=5,
    )
