# BabyAGI Mini — 从零手写的任务驱动自主 Agent

一个用 **Python 标准库 + DeepSeek API** 从零实现的自主 Agent，复刻经典项目
[BabyAGI](https://github.com/yoheinakajima/babyagi) 的核心思想：**三个 LLM 角色 + 一个任务循环**。

零第三方依赖（不依赖 LangChain 等框架），跑起来就能看懂 Agent 的内部原理。

## 核心原理

Agent 不是"一个模型"，而是"多个角色 + 一个循环"：

| 角色 | 职责 | 类比 |
|---|---|---|
| `execute_task` | 完成一项具体任务，直接给结果 | 🖐 手 |
| `create_tasks` | 根据上一步结果，拆出下一步子任务 | 🧠 脑 |
| `prioritize_tasks` | 按重要性重排任务列表 | ⚖️ 判断力 |

**主循环（Agent 的"生命"）**：

```
任务列表（初始 = 目标）
循环：
  ① 按重要性排序任务列表
  ② 取出第一个任务
  ③ 执行它 → 得到结果
  ④ 根据结果拆出新任务 → 加进列表（去重）
  ⑤ 回到 ①
直到列表清空 / 达到步数上限
```

### 三个关键设计

1. **角色 = prompt**：三个角色底层是同一个 `call_llm`，区别只在 system prompt。
2. **反馈闭环**：`create_tasks` 的输入包含"上一步的执行结果"，Agent 据此决定下一步。
3. **任务爆炸问题**：每轮"产出 > 消耗"会让任务列表无限增长。解决：优先级排序（挑最重要的做）+ 步数上限（安全阀）。

## 快速开始

```bash
# 1. 设置 API key（二选一）
export DEEPSEEK_API_KEY=sk-xxx        # Linux / macOS
set DEEPSEEK_API_KEY=sk-xxx           # Windows
# 或者在本目录建一个 .env 文件，内容：DEEPSEEK_API_KEY=sk-xxx

# 2. 运行（Python 3，无第三方依赖）
python babyagi.py
```

## 技术栈

- Python 3（纯标准库：`urllib` / `json`）
- DeepSeek API（OpenAI 兼容接口）

## 待改进（TODO）

- [ ] **记忆系统**：用向量库存储历史结果，让 Agent 记住做过的事
- [ ] **结构化输出**：用 JSON mode 替代脆弱的文本解析
- [ ] **工具调用**：接入真实工具（搜索、计算器、文件操作）
