"""阶段 4 练习：加第二个工具 get_weather，并学会"路由"。

任务（4 步）：
1. 参考 tool_calling.py，把整个结构复制过来（load_env / call_llm / chat_with_tools）。
2. 在 TOOLS 里再加一个 get_weather 工具（schema 如下）：
   {
       "type": "function",
       "function": {
           "name": "get_weather",
           "description": "查询某城市的天气",
           "parameters": {
               "type": "object",
               "properties": {
                   "city": {"type": "string", "description": "城市名，如 北京"}
               },
               "required": ["city"],
           },
       },
   }
3. 写 run_weather(city) 函数，返回假天气，比如 f"{city}今天晴，25度"。
4. 在 chat_with_tools 里，把写死的 run_calculator 改成"按工具名分发"：
       if name == "calculator":
           result = run_calculator(args["expression"])
       elif name == "get_weather":
           result = run_weather(args["city"])

然后测两个问题，看模型能不能自动选对工具：
    "98 加 7 等于多少？"      → 应该走 calculator
    "北京今天天气怎么样？"    → 应该走 get_weather

验收标准：
- 模型能根据问题类型，自动选择正确的工具
- 关键行（TOOLS 定义 / 分发逻辑 / 回传结果）有注释
"""
# ---- 从下面开始写你的代码 ----
# TODO: 复制 tool_calling.py，加 get_weather 工具 + 分发逻辑
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
    {#工具1：计算器
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
    },

    {#工具2：get_weather
        "type": "function",
       "function": {
           "name": "get_weather",#工具叫什么
           "description": "查询某城市的天气",#它是干嘛的
           "parameters": { #要什么参数
               "type": "object",
               "properties": {
                   "city": {"type": "string", "description": "城市名，如 北京"}
               },
               "required": ["city"],
           },
       },
   }
]


def run_calculator(expression):
    """真正执行计算。⚠️ 生产环境别用 eval（会执行任意代码），这里教学简化。"""
    return eval(expression)

def run_weather(city):
    return f"{city}今天晴，25度"

def chat_with_tools(user_msg):
    messages = [{"role": "user", "content": user_msg}]

    # 第 1 次调用：带工具定义
    resp = call_llm(messages, tools=TOOLS)
    msg = resp["choices"][0]["message"]

    # 模型想调工具吗？
    if msg.get("tool_calls"):#判断模型要不要调工具
        tool_call = msg["tool_calls"][0]#先取第一个工具进行调用
        name = tool_call["function"]["name"]#模型想调的工具名称
        args = json.loads(tool_call["function"]["arguments"])#参数
        print(f"🔧 模型想调工具：{name}({args})")

        # 你的代码真正执行工具
        if name == "calculator":
            result = run_calculator(args["expression"])
        elif name == "get_weather":
            result = run_weather(args["city"])#根据模型说的name，调用对应的工具，把参数传进去

        # 把结果回传（两步：模型的 tool_call 消息 + 工具结果消息）
        messages.append(msg)# 把模型"我要调工具"这句话加进对话
        messages.append({
            "role": "tool",#把调用工具的执行结果加进对话
            "tool_call_id": tool_call["id"],
            "content": str(result),
        })

        # 第 2 次调用：拿最终答案
        resp2 = call_llm(messages)#第二次调用，让模型带着结果生成答案
        return resp2["choices"][0]["message"]["content"]
    else:
        # 模型没要调工具，直接返回答案
        return msg["content"]

if __name__ == "__main__":
    print(chat_with_tools("98 加 7 等于多少？"))
    print(chat_with_tools("北京今天天气怎么样？"))AAAAAA
