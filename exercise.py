"""第 1 步练习：自己写一个执行代理，换一个任务测试。

任务（3 步）：
1. 参考同目录 step1_execute.py，自己写出 execute_task 函数
   （可以照着写，但每个关键行用 # 注释说明它在干嘛）。
2. 换一组 objective / task 测试，比如：
     objective = "计划一次周末旅行"
     task       = "列出出发前需要准备的 3 样东西"
3. 运行 `python exercise.py`，把输出贴给我看。

验收标准：
- 能跑通、不报错
- 输出是"直接给结果"，而不是反问或解释一堆过程
- 你的每行关键代码都有注释
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
    payload = {"model": "deepseek-v4-pro", "messages": messages}#把模型名和消息列表发给服务器
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
    return data["choices"][0]["message"]["content"]#从服务器返回的数据中将“答案/结果”抽出来


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


if __name__ == "__main__":
    # 演示：一个目标 + 一项具体任务
    objective = "从零开始掌握 AI Agent "
    task = "langchain和langgraph的定义和区别"
    result = execute_task(objective, task)
    print("【执行结果】")
    print(result)