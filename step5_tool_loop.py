"""BabyAGI 深化 · 第 1 层：带工具的执行代理（Tool Loop）

把 tool_calling.py 的「单次工具调用」升级成「多轮工具循环」，接进执行代理。
执行代理不再只会生成文字，而是能真的调用工具、连续干活，直到任务完成。

Tool Loop（工具循环）：
  1. 把「总目标 + 任务 + 工具定义」发给模型
  2. 模型决定：调工具（返回 tool_calls）还是直接给答案
  3. 如果要调工具 → 你的代码真正执行 → 结果回传 → 回到第 2 步
  4. 直到模型不再调工具 → 返回最终答案

对比 tool_calling.py：那里只处理【一次】工具调用就返回答案；
这里用 while 循环，模型可以【连续】调 calculator → write_file → read_file ...

运行：python step5_tool_loop.py
"""
import json
import os
import re
import urllib.request

# ---------- 环境 ----------
def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip())

load_env(os.path.join(os.path.dirname(__file__), "..", ".env"))
API_KEY = os.environ["DEEPSEEK_API_KEY"]
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

# Agent 写文件的目录（安全：所有文件只能写到这里，防路径穿越）
WORKDIR = os.path.join(os.path.dirname(__file__), "agent_output")
os.makedirs(WORKDIR, exist_ok=True)


def call_llm(messages, tools=None):
    """底层 LLM 调用，返回【完整响应】（要看模型有没有 tool_calls）。"""
    payload = {"model": MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------- 工具：定义（给模型看的说明书） + 实现（你真正执行的代码） ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个数学表达式，返回数值结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的表达式，如 '123*456'"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把内容写入指定文件（保存 Agent 的产出）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "文件名，如 'result.txt'"},
                    "content": {"type": "string", "description": "要写入的完整内容"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "要读取的文件名，如 'result.txt'"}
                },
                "required": ["filename"],
            },
        },
    },
]


def _safe_path(filename):
    """把文件名锁在 WORKDIR 下，防 '../' 路径穿越。"""
    full = os.path.abspath(os.path.join(WORKDIR, filename))
    if not full.startswith(WORKDIR):
        raise ValueError(f"非法路径：{filename}")
    return full


def run_calculator(expression):
    """安全计算：只允许数字和 + - * / ( ) . 空格，禁止 eval 任意代码。"""
    if not re.fullmatch(r"[0-9+\-*/().\s]+", expression):
        return f"拒绝：表达式含非法字符 {expression!r}"
    return eval(expression, {"__builtins__": {}}, {})


def run_write_file(filename, content):
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入 {filename}（{len(content)} 字）"


def run_read_file(filename):
    path = _safe_path(filename)
    if not os.path.exists(path):
        return f"文件不存在：{filename}"
    return open(path, encoding="utf-8").read()


# 按工具名分发（dict 比 if/elif 更好扩展）
TOOL_IMPL = {
    "calculator": lambda args: run_calculator(args["expression"]),
    "write_file": lambda args: run_write_file(args["filename"], args["content"]),
    "read_file": lambda args: run_read_file(args["filename"]),
}


# ---------- 带工具的执行代理 ----------
def execute_task(objective, task, max_tool_rounds=5):
    """执行代理：完成一项任务，可连续调用多个工具。"""
    messages = [
        {"role": "system", "content":
            "你是一个执行代理（execution agent）。基于总目标忠实完成交给你的任务。"
            "你可以调用工具（计算、读写文件）来真正完成任务，而不是空想。"
            "任务彻底完成后，直接给出最终结果。"},
        {"role": "user", "content": f"总目标：{objective}\n\n请完成这个任务：{task}"},
    ]

    for _ in range(max_tool_rounds):
        resp = call_llm(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]

        # 模型没要调工具 → 任务完成，返回答案
        if not msg.get("tool_calls"):
            return msg["content"]

        # 模型要调工具 → 逐个真正执行 → 结果回传
        messages.append(msg)  # 模型的 tool_calls 消息
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            print(f"🔧 调用工具：{name}({args})")
            result = TOOL_IMPL[name](args)
            print(f"   → 返回：{str(result)[:80]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    return "（达到工具轮数上限，任务未完成）"


if __name__ == "__main__":
    # 一个需要连续调多个工具的真实任务：先算数，再存盘，再读回确认
    result = execute_task(
        objective="验证 Agent 能连续调用多个工具",
        task="计算 123*456 的结果，把结果保存到 result.txt 文件，然后读回这个文件确认内容正确。",
    )
    print("\n💬 最终结果：", result)
