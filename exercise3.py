"""第 3 步练习：写出循环，让 Agent 自己跑起来。

任务（3 步）：
1. 参考 step3_loop.py，写出完整的循环（load_env/call_llm/execute_task/create_tasks 都照抄，
   重点是 __main__ 里的 task_list + for 循环，这部分自己写，关键行加 # 注释）。
2. 换一个你感兴趣的目标，比如：
     objective = "制定一个一周的健身计划"
     task_list = ["列出这一周每天的训练主题"]
3. 运行 `python exercise3.py`，观察它自己跑完 5 轮，把输出贴给我。

验收标准：
- 能自己循环跑 5 轮，不用你干预
- 每轮都在"接着上一轮结果往下走"
- 关键行（task_list / for 循环 / pop / append / 去重）有注释

加分题（可选）：把 MAX_STEPS 改成 3，再跑一次，观察区别。
"""
# ---- 从下面开始写你的代码 ----
# TODO: 复制 step3_loop.py 的结构，自己写 __main__ 里的循环，并换一个目标测试
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
    objective = "制定一周的健身计划"
    task_list = ["确定每一天的饮食结构，做哪些健身动作（做几组），健身时长安排和注意事项"]#待办清单
    MAX_STEPS = 5  # 安全阀：最多跑 5 轮，防止无限循环烧钱

    for step in range(MAX_STEPS):#循环：重复做‘MAX_STEPS’次，MAX_STEPS是多少就跑多少轮
        if not task_list:#如果清单里面没了，就代表任务做完了
            print("\n✅ 任务全部完成！")
            break#跳出循环，结束

        # 1. 取出第一个任务（pop(0) = 取走并删除）
        current = task_list.pop(0)#pop(0)：取出并删除清单"最前面"的一个任务，交给 current
        print(f"\n=== 第 {step + 1} 轮：执行「{current}」===")

        # 2. 执行它
        result = execute_task(objective, current)#执行
        print(f"→ 结果：{result[:80]}...")

        # 3. 拆新任务，加进列表（split 拆行 + 去重）
        new_tasks = create_tasks(objective, current, result)#拆任务
        for t in new_tasks.split("\n"):#split("\n")：把一大段文字按"换行"切开成一行行；for 逐个看每一行
            t = t.strip()#strip()：去掉这行首尾的空格和空行
            if t and t not in task_list and t != current:# 三个条件：① t 非空  ② t 不在清单里（即去重） ③ t 不是刚做完的那个
                task_list.append(t)# append：把这个新任务加到清单"末尾"

        # 4. 打印当前待办清单
        print(f"→ 剩余任务：{task_list}")