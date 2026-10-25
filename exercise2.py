"""第 2 步练习：自己写一个任务规划师，并做一次"真·反馈"测试。

任务（3 步）：
1. 参考 step2_create.py，自己写出 create_tasks 函数（关键行加 # 注释）。
2. 做一次真实联动测试（这是本步的重点）：
   - 先用 execute_task 执行一个任务，拿到真实 result
   - 再把这个 result 喂给 create_tasks，看它拆出什么新任务
   提示：把 step1 的 execute_task 复制过来，然后：
       objective = "从零开始掌握 AI Agent"
       task1     = "列出学习 AI Agent 需要掌握的前 3 个知识点"
       result    = execute_task(objective, task1)        # 拿到真实结果
       tasks     = create_tasks(objective, task1, result) # 喂回去拆任务
       print(tasks)
3. 运行 `python exercise2.py`，把输出贴给我。

验收标准：
- 能跑通
- 拆出的子任务确实是在"接着上一个结果往下走"（不是从头乱说）
- 关键行有注释
"""
# ---- 从下面开始写你的代码 ----
# TODO: 复制 load_env / call_llm，写出 execute_task 和 create_tasks
# 然后做上面第 2 步的"真实联动测试"
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

def execute_task(objective, task):
    """执行代理：基于总目标，完成交给你的一项具体任务。"""
    messages = [
        {"role": "system","content": (
                "你是一个执行代理（execution agent）。"
                "你的职责：基于给定的总目标，忠实完成交给你的这一项具体任务。"
                "直接给出结果，不要反问、不要解释过程。"),},#给模型定义：你是谁，你的职责是什么，有哪些要求你要遵守
        {"role": "user","content":
            f"总目标：{objective}\n\n请完成这个任务：{task}\n\n直接给出结果：",},
        # f-string：把 objective 和 task 变量塞进这句话里
        #模型要完成的任务是什么，得到什么答案/结果
    ]
    return call_llm(messages)#角色函数execute_task最后调用底层函数call_llm

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
        },#给模型定义：你是谁，你的职责是什么，需要遵守哪些要求
        {
            "role": "user",
            "content": (
                f"总目标：{objective}\n\n"
                f"刚完成的任务：{last_task}\n\n"
                f"这个任务的结果：{last_result}\n\n"
                "请列出下一步要做的子任务（每行一个）："
            ),
        },# f-string：把 objective，last_task，last_result变量塞进这句话里
    ]
    return call_llm(messages)


if __name__ == "__main__":
    objective = "从零开始掌握 AI Agent"
    task1 = "列出学习 AI Agent 需要掌握的前 3 个知识点"
    result = execute_task(objective, task1)          # ← 真正执行，拿真实结果
    new_tasks = create_tasks(objective, task1, result)  # ← 把真实结果喂回去
    print("【第一步执行结果】")
    print(result)
    print("【拆出的子任务】")
    print(new_tasks)
