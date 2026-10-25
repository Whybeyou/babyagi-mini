# -*- coding: utf-8 -*-
"""BabyAGI 完整 Demo：多角色协作 + 任务循环 + 工具调用 + 记忆系统

架构（对应简历描述）：
  三个角色 —— 执行代理(execute_task，带工具) / 任务规划师(create_tasks) /
               优先级排序师(prioritize_tasks)，底层共用同一个 LLM 调用，
               仅靠 system prompt 区分职责。
  主循环   —— 排序 → 取任务 → 执行(连续调工具) → 拆新任务 → 去重。
  工具调用 —— 执行代理带 tool loop，可连续调 calculator / write_file / read_file。
  记忆系统 —— 每轮执行结果用本地 Ollama bge-m3 向量化存入 memory.json，
               新任务执行前检索最相关的历史记忆注入上下文，实现跨任务复用。

零第三方依赖：标准库 urllib/json + DeepSeek API + 本地 Ollama HTTP。

运行：python babyagi_demo.py
"""
import json
import os
import re
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 配置 ----------
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
OLLAMA_EMBED_MODEL = "bge-m3"          # 本地 BGE 中文 embedding
WORKDIR = os.path.join(BASE_DIR, "agent_output")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
os.makedirs(WORKDIR, exist_ok=True)


def load_env(path=None):
    path = path or os.path.join(BASE_DIR, "..", ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip())


load_env()
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


# ---------- 底层 LLM 调用 ----------
def call_llm(messages, tools=None):
    """调 DeepSeek，返回【完整响应】（要看有没有 tool_calls）。"""
    payload = {"model": DEEPSEEK_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------- 向量（本地 Ollama bge-m3） ----------
def embed(text):
    """把文本转成向量（本地 bge-m3，不花 API 钱）。"""
    payload = {"model": OLLAMA_EMBED_MODEL, "input": text}
    req = urllib.request.Request(
        OLLAMA_EMBED_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["embeddings"][0]


def cosine(a, b):
    """余弦相似度 0~1，越接近 1 越相似。"""
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x * x for x in a)) ** 0.5
    nb = (sum(x * x for x in b)) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ---------- 记忆系统（长期记忆：向量检索） ----------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE, encoding="utf-8"))
    return []


def save_memory(mem):
    json.dump(mem, open(MEMORY_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def remember(task, result):
    """把「任务 + 结果」向量化后存入记忆库。"""
    mem = load_memory()
    mem.append({"task": task, "result": result, "vector": embed(task + " " + result)})
    save_memory(mem)
    print(f"🧠 记忆已沉淀：{task[:30]}...")


def recall(task, top_k=2):
    """检索与当前任务最相关的历史记忆。"""
    mem = load_memory()
    if not mem:
        return []
    v = embed(task)
    scored = sorted(mem, key=lambda m: cosine(m["vector"], v), reverse=True)
    return scored[:top_k]


def memory_to_text(hits):
    if not hits:
        return "（暂无相关历史记忆）"
    lines = []
    for h in hits:
        lines.append(f"- 曾做过「{h['task'][:50]}」，结果：{h['result'][:80]}")
    return "\n".join(lines)


# ---------- 工具：定义 + 实现 ----------
TOOLS = [
    {"type": "function", "function": {
        "name": "calculator",
        "description": "计算一个数学表达式，返回数值结果。",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "如 '123*456'"}},
            "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "把内容写入文件，保存产出。",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string", "description": "文件名，如 'plan.txt'"},
            "content": {"type": "string", "description": "完整内容"}},
            "required": ["filename", "content"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "读取文件内容。",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string", "description": "文件名"}},
            "required": ["filename"]}}},
]


def _safe_path(filename):
    full = os.path.abspath(os.path.join(WORKDIR, filename))
    if not full.startswith(WORKDIR):
        raise ValueError(f"非法路径：{filename}")
    return full


def run_calculator(expression):
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


TOOL_IMPL = {
    "calculator": lambda a: run_calculator(a["expression"]),
    "write_file": lambda a: run_write_file(a["filename"], a["content"]),
    "read_file": lambda a: run_read_file(a["filename"]),
}


# ---------- 三个角色 ----------
def execute_task(objective, task, max_tool_rounds=5):
    """执行代理：带 tool loop，可连续调多个工具；执行前注入相关记忆。"""
    hits = recall(task)
    memory_ctx = memory_to_text(hits)

    messages = [
        {"role": "system", "content":
            "你是一个执行代理（execution agent）。基于总目标忠实完成交给你的任务，"
            "可以用工具（计算、读写文件）真正完成任务，而不是空想。"
            "任务彻底完成后，直接给出最终结果。"},
        {"role": "user", "content":
            f"总目标：{objective}\n\n相关历史记忆：\n{memory_ctx}\n\n请完成这个任务：{task}"},
    ]

    for _ in range(max_tool_rounds):
        resp = call_llm(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]
        if not msg.get("tool_calls"):
            return msg["content"]
        messages.append(msg)
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            print(f"  🔧 调工具 {name}({args})")
            result = TOOL_IMPL[name](args)
            print(f"     → {str(result)[:60]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})
    return "（工具轮数用尽）"


def create_tasks(objective, last_task, last_result):
    """任务规划师：根据上一步结果拆出 2-3 个下一步子任务。"""
    messages = [
        {"role": "system", "content":
            "你是任务规划师（task creation agent）。根据总目标和刚完成的结果，"
            "拆出下一步 2-3 个子任务，每行一个，不要编号、不要解释。"},
        {"role": "user", "content":
            f"总目标：{objective}\n刚完成：{last_task}\n结果：{last_result}\n\n下一步子任务（每行一个）："},
    ]
    return call_llm(messages)["choices"][0]["message"]["content"]


def prioritize_tasks(objective, task_list):
    """优先级排序师：按重要性重排（不删不增）。"""
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(task_list))
    messages = [
        {"role": "system", "content":
            "你是任务优先级排序师。按'最该先做'到'可以后做'重排任务列表，"
            "不要删除、不要新增，每行一个，直接输出。"},
        {"role": "user", "content": f"总目标：{objective}\n当前任务：\n{numbered}\n\n重排后（每行一个）："},
    ]
    return call_llm(messages)["choices"][0]["message"]["content"]


# ---------- 主循环 ----------
def run(objective, first_task, max_steps=4):
    task_list = [first_task]
    for step in range(max_steps):
        if not task_list:
            print("\n✅ 任务全部完成")
            break

        if len(task_list) > 1:                     # 排序（任务爆炸治理）
            task_list = [t.strip() for t in prioritize_tasks(objective, task_list).split("\n") if t.strip()]

        current = task_list.pop(0)
        print(f"\n=== 第 {step+1} 轮：执行「{current}」===")

        result = execute_task(objective, current)
        print(f"→ 结果：{result[:80]}")

        remember(current, result)                  # 沉淀记忆

        for t in create_tasks(objective, current, result).split("\n"):   # 拆新任务 + 去重
            t = t.strip()
            if t and t not in task_list and t != current:
                task_list.append(t)
        print(f"→ 剩余任务：{task_list}")


if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("请先设置 DEEPSEEK_API_KEY（E:\\agent-learning\\.env）")
    run(
        objective="制定一份 5 天的 AI Agent 入门学习计划，并把计划保存成文件",
        first_task="列出 AI Agent 入门必须掌握的 3 个核心概念",
        max_steps=4,
    )
    print("\n🏁 运行结束。查看产出：agent_output/ 目录；查看记忆：memory.json")
