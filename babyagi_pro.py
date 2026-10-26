# -*- coding: utf-8 -*-
"""BabyAGI Pro：多角色 + 工具调用 + 记忆 + 技能路由 + 上下文管理

在 babyagi_demo.py 基础上，补两个「成熟 Agent」模块：

1. 技能路由（Skill Routing）—— 工具分三层：
     原子工具（calculator / write_file / read_file）
     → 技能（组合多个原子工具的"操作手册"，如「写文档」= 规划+写+存+校验）
     → 技能目录（每个技能带 description / tags / when_to_use / steps）
   任务进来先「二阶召回精排」：
     一阶：embedding 粗召回 top-2 候选技能
     二阶：LLM 从候选中精排出最合适的那个

2. 上下文管理 —— 工具返回的大结果外置存文件，prompt 里只留摘要，
   防止上下文窗口被大结果撑爆。

运行：python babyagi_pro.py
"""
import glob
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
WORKDIR = os.path.join(BASE, "agent_output")
CTXDIR = os.path.join(WORKDIR, "context")          # 外置上下文目录
MEMORY_FILE = os.path.join(BASE, "memory_pro.json")
os.makedirs(CTXDIR, exist_ok=True)

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
OLLAMA_EMBED_MODEL = "bge-m3"

MAX_TOOL_RESULT = 600   # 工具结果超过这个长度就外置 + 摘要


def load_env(path=None):
    path = path or os.path.join(BASE, "..", ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip())


load_env()
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def call_llm(messages, tools=None, temperature=None):
    payload = {"model": DEEPSEEK_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    if temperature is not None:
        payload["temperature"] = temperature
    req = urllib.request.Request(DEEPSEEK_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def embed(text):
    req = urllib.request.Request(OLLAMA_EMBED_URL,
                                 data=json.dumps({"model": OLLAMA_EMBED_MODEL, "input": text}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["embeddings"][0]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x * x for x in a)) ** 0.5
    nb = (sum(x * x for x in b)) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ============================================================
# 第一层：原子工具（atomic tools）
# ============================================================
TOOLS = [
    {"type": "function", "function": {"name": "calculator",
        "description": "计算一个数学表达式，返回数值结果。",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "write_file",
        "description": "把内容写入文件保存。",
        "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["filename", "content"]}}},
    {"type": "function", "function": {"name": "read_file",
        "description": "读取文件内容。",
        "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
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
    with open(_safe_path(filename), "w", encoding="utf-8") as f:
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


# ============================================================
# 第二层：技能目录（skill catalog）—— 每个技能是组合原子工具的操作手册
# ============================================================
def parse_skill_md(path):
    """解析 SKILL.md：frontmatter（name/description）+ 正文（流程/反模式/边界）。"""
    text = open(path, encoding="utf-8").read()
    name, description, body = "", "", text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        front, body = m.group(1), m.group(2)
        for line in front.split("\n"):
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
    return {"name": name, "description": description, "body": body.strip()}


def load_skills():
    """从 skills/*/SKILL.md 加载技能目录。"""
    skills = []
    for path in sorted(glob.glob(os.path.join(BASE, "skills", "*", "SKILL.md"))):
        skills.append(parse_skill_md(path))
    return skills


def skill_route(task):
    """技能路由：一阶 embedding 召回 + 二阶 LLM 精排。返回选中的技能。"""
    # 一阶召回：任务与每个技能的 description 算语义相似度，取 top-2
    skills = load_skills()
    tv = embed(task)
    scored = sorted(skills, key=lambda s: cosine(embed(s["description"]), tv), reverse=True)
    top2 = scored[:2]
    print(f"  🧭 一阶召回候选技能：{[s['name'] for s in top2]}")

    # 二阶精排：LLM 从候选中选最合适的（无则返回 none）
    candidate_desc = "\n".join(
        f"- {s['name']}：{s['description']}" for s in top2)
    messages = [
        {"role": "system", "content":
            "你是技能路由器。根据任务，从候选技能里选一个最合适的。"
            "只输出技能名；都不合适就输出 none。"},
        {"role": "user", "content": f"任务：{task}\n\n候选技能：\n{candidate_desc}\n\n选哪个？（只输出名字）"},
    ]
    chosen = call_llm(messages, temperature=0)["choices"][0]["message"]["content"].strip()
    for s in skills:
        if s["name"] in chosen:
            print(f"  🎯 二阶精排选中：{s['name']}")
            return s
    print("  🎯 二阶精排：无需特定技能")
    return None


# ============================================================
# 上下文管理：大结果外置 + 摘要
# ============================================================
def manage_result(result):
    """工具结果超长时，完整内容外置存文件，prompt 里只放摘要。"""
    text = str(result)
    if len(text) <= MAX_TOOL_RESULT:
        return text
    path = os.path.join(CTXDIR, f"ctx_{len(os.listdir(CTXDIR))}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    summary = text[:MAX_TOOL_RESULT]
    return f"[结果 {len(text)} 字，完整内容已外置到 {os.path.basename(path)}] 摘要：{summary}..."


# ============================================================
# 记忆系统
# ============================================================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE, encoding="utf-8"))
    return []


def save_memory(mem):
    json.dump(mem, open(MEMORY_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def remember(task, result):
    mem = load_memory()
    mem.append({"task": task, "result": result, "vector": embed(task + " " + result)})
    save_memory(mem)
    print(f"  🧠 记忆已沉淀：{task[:24]}...")


def recall(task, top_k=2):
    mem = load_memory()
    if not mem:
        return []
    v = embed(task)
    return sorted(mem, key=lambda m: cosine(m["vector"], v), reverse=True)[:top_k]


# ============================================================
# 三个角色（执行代理升级：技能路由 + 上下文管理）
# ============================================================
def execute_task(objective, task, max_tool_rounds=5):
    skill = skill_route(task)

    # 相关记忆注入
    hits = recall(task)
    mem_ctx = "\n".join(f"- 曾做过「{h['task'][:40]}」→ {h['result'][:60]}" for h in hits) or "（无）"

    skill_ctx = "无需特定技能"
    if skill:
        skill_ctx = f"技能「{skill['name']}」的完整说明：\n{skill['body']}"

    messages = [
        {"role": "system", "content":
            "你是执行代理（execution agent）。基于总目标完成任务，可调用工具真正执行。"
            "如果给了你技能操作步骤，请按步骤走。"},
        {"role": "user", "content":
            f"总目标：{objective}\n\n任务：{task}\n\n相关历史记忆：\n{mem_ctx}\n\n{skill_ctx}\n\n请完成任务："},
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
            print(f"  🔧 调工具 {name}({list(args.values())[:1] if args else ''}...)")
            raw = TOOL_IMPL[name](args)
            result = manage_result(raw)          # 上下文管理
            print(f"     → {str(result)[:60]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    return "（工具轮数用尽）"


def create_tasks(objective, last_task, last_result):
    messages = [
        {"role": "system", "content":
            "你是任务规划师。根据总目标和刚完成的结果，拆出下一步 2-3 个子任务，每行一个。"},
        {"role": "user", "content": f"总目标：{objective}\n刚完成：{last_task}\n结果：{last_result}\n\n下一步子任务（每行一个）："},
    ]
    return call_llm(messages)["choices"][0]["message"]["content"]


def prioritize_tasks(objective, task_list):
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(task_list))
    messages = [
        {"role": "system", "content": "你是优先级排序师。按'最该先做'重排任务列表，不删不增，每行一个。"},
        {"role": "user", "content": f"总目标：{objective}\n当前任务：\n{numbered}\n\n重排后（每行一个）："},
    ]
    return call_llm(messages)["choices"][0]["message"]["content"]


def run(objective, first_task, max_steps=3):
    task_list = [first_task]
    for step in range(max_steps):
        if not task_list:
            print("\n✅ 任务全部完成")
            break
        if len(task_list) > 1:
            task_list = [t.strip() for t in prioritize_tasks(objective, task_list).split("\n") if t.strip()]
        current = task_list.pop(0)
        print(f"\n=== 第 {step+1} 轮：执行「{current}」===")
        result = execute_task(objective, current)
        print(f"→ 结果：{result[:80]}")
        remember(current, result)
        for t in create_tasks(objective, current, result).split("\n"):
            t = t.strip()
            if t and t not in task_list and t != current:
                task_list.append(t)
        print(f"→ 剩余任务：{task_list}")


if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("请先设置 DEEPSEEK_API_KEY")
    run(
        objective="制定一份 AI Agent 学习计划并保存成文件",
        first_task="列出学习 AI Agent 需要掌握的 3 个核心概念，并写成一份学习计划文档保存",
        max_steps=3,
    )
    print("\n🏁 结束。产出在 agent_output/，记忆在 memory_pro.json")
