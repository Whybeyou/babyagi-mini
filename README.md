# 自主任务驱动 Agent（BabyAGI 架构）

从零实现的任务驱动自主 Agent，**纯 Python 标准库**，不依赖 LangChain 等框架。
以「多角色协作 + 任务循环 + 工具调用 + 记忆系统」构建能真实执行任务的自主闭环。

> 主程序 `babyagi_demo.py` 可一键运行；其余 `step*.py` / `exercise*.py` 是从零到完整实现的学习过程记录。

## 核心特性

- **多角色协作**：执行代理 / 任务规划师 / 优先级排序师三个角色解耦，底层复用同一个 LLM 调用，仅靠 system prompt 区分职责——验证「角色本质即 prompt」。
- **工具调用闭环（Tool Loop）**：工具定义与执行解耦，模型按需连续多轮调用工具（计算器、文件读写）直至任务完成，让 Agent 从「生成文字」升级为「真实执行」。
- **记忆系统**：执行结果经本地 `bge-m3` 向量化沉淀，新任务执行前检索最相关的历史记忆注入上下文，实现跨任务经验复用。
- **任务爆炸治理**：优先级排序 + 步数上限 + 任务去重三层治理，实测任务列表从 3 项膨胀至 9 项后收敛。
- **安全约束**：计算工具 eval 白名单、文件读写路径沙箱，防任意代码执行与路径穿越。

## 架构

| 角色 | 职责 | 类比 |
|---|---|---|
| `execute_task` | 完成具体任务，可连续调用工具 | 手 |
| `create_tasks` | 根据上一步结果拆出下一步子任务 | 脑 |
| `prioritize_tasks` | 按重要性重排任务列表 | 判断力 |

主循环：

```
任务列表（初始 = 目标）
循环：
  ① 按重要性排序任务列表
  ② 取出第一个任务
  ③ 执行它（可连续调多个工具）
  ④ 结果向量化 → 存入记忆库
  ⑤ 根据结果拆出新任务 → 去重 → 加进列表
直到列表清空 / 达到步数上限
```

## 进阶版（babyagi_pro.py）

在基础版之上，补两个「成熟 Agent」模块：

- **技能路由（Skill Routing）**：工具分三层（原子工具 → 技能 → 技能目录），任务先「二阶召回精排」——embedding 粗召回候选技能，再 LLM 精选出最合适的技能，按技能步骤执行。
- **上下文管理**：工具返回的大结果外置存文件，prompt 里只留摘要，防止上下文窗口被撑爆。

运行：`python babyagi_pro.py`

## 快速开始

前置条件：

1. Python 3（仅标准库，无第三方依赖）
2. DeepSeek API Key（写入 `E:\agent-learning\.env` 的 `DEEPSEEK_API_KEY`）
3. 本地 Ollama 已运行，并拉取 `bge-m3`（用于记忆向量化）：`ollama pull bge-m3`

运行：

```bash
python babyagi_demo.py
```

默认目标「制定一份 5 天的 AI Agent 入门学习计划」，Agent 会自己拆任务、调工具、沉淀记忆，最终把计划写入 `agent_output/` 目录。

## 运行效果

```
=== 第 1 轮：执行「列出 AI Agent 入门必须掌握的 3 个核心概念」===
→ 结果：AI Agent 入门必须掌握的 3 个核心概念如下：...
🧠 记忆已沉淀：列出 AI Agent 入门必须掌握的 3 个核心概念...

=== 第 2 轮：执行「设计 5 天学习计划的整体结构...」===
  🔧 调工具 write_file({'filename': 'AI_Agent_5天入门学习计划.md', ...})
     → 已写入 AI_Agent_5天入门学习计划.md（3742 字）
  🔧 调工具 read_file({'filename': 'AI_Agent_5天入门学习计划.md'})
     → # AI Agent 入门 5 天学习计划 ...
🧠 记忆已沉淀：...
```

## 目录结构

```
babyagi-mini/
├── babyagi_demo.py      # 完整 demo：多角色 + 工具调用 + 记忆
├── babyagi.py           # 最小教学版（仅三角色 + 主循环）
├── step1_execute.py ~ step5_tool_loop.py   # 分步参考实现
├── exercise*.py         # 练习（照 step 抄改）
├── tool_calling.py      # Function Calling 单次工具调用
├── embedding_demo.py    # 本地 embedding + 余弦相似度
├── interview-notes.md   # 面试要点笔记
└── agent_output/        # Agent 产出的文件（运行时生成）
```

## 技术栈

- Python 3（纯标准库：`urllib` / `json`）
- DeepSeek API（OpenAI 兼容接口，Function Calling）
- 本地 Ollama（`bge-m3` embedding，用于记忆系统）
