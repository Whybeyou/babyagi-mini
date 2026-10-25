"""BabyAGI 深化 · 工具调用（Function Calling）

给 Agent 接一个"计算器"工具：模型不再只会生成文字，而是能真的"动手计算"。

工具循环（tool loop）：
  1. 把问题 + 工具定义发给模型
  2. 模型判断"需要调工具" → 返回 tool_call（工具名 + 参数）
  3. 你的代码真正执行这个工具 → 拿到结果
  4. 把结果回传给模型 → 模型生成最终答案

运行：
    python tool_calling.py
"""
import json
import os
import urllib.request


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip())


load_env()
API_KEY = os.environ["DEEPSEEK_API_KEY"]
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"


def call_llm(messages, tools=None):
    """底层 LLM 调用。注意：现在返回【完整响应】，因为要看模型有没有要调工具。"""
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
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


# 工具定义（给模型看的"说明书"：叫什么、干什么、要什么参数）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个数学表达式，返回数值结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的表达式，例如 '123*456'",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]


def run_calculator(expression):
    """真正执行计算。⚠️ 生产环境别用 eval（会执行任意代码），这里教学简化。"""
    return eval(expression)


def chat_with_tools(user_msg):
    messages = [{"role": "user", "content": user_msg}]

    # 第 1 次调用：带工具定义
    resp = call_llm(messages, tools=TOOLS)
    msg = resp["choices"][0]["message"]

    # 模型想调工具吗？
    if msg.get("tool_calls"):
        tool_call = msg["tool_calls"][0]
        name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        print(f"🔧 模型想调工具：{name}({args})")

        # 你的代码真正执行工具
        result = run_calculator(args["expression"])
        print(f"   → 工具返回：{result}")

        # 把结果回传（两步：模型的 tool_call 消息 + 工具结果消息）
        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(result),
        })

        # 第 2 次调用：拿最终答案
        resp2 = call_llm(messages)
        return resp2["choices"][0]["message"]["content"]
    else:
        # 模型没要调工具，直接返回答案
        return msg["content"]


if __name__ == "__main__":
    answer = chat_with_tools("123 乘以 456 等于多少？")
    print("💬 最终答案：", answer)
