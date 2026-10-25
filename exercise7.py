"""阶段 7 练习：把 Tool Loop 接进 BabyAGI（第 1 层收尾）

任务（3 步）：
1. 先跑 step5_tool_loop.py，观察模型怎么【连续】调 calculator → write_file → read_file。
2. 把 step5 里的 load_env / call_llm / TOOLS / TOOL_IMPL / execute_task 复制过来，
   并在 TOOLS 里再加一个「你自己的工具」（例如 get_weather 或 search_knowledge）。
3. 把 babyagi.py 主循环里的 execute_task 换成这个【带工具】的版本，
   用你自己的目标跑一遍，让 Agent 执行任务时能真的调用工具。

验收标准：
- 主循环跑通，执行代理能真的调工具（终端会打印「🔧 调用工具：...」）
- 能用自己的话说出 tool loop 和单次工具调用（tool_calling.py）的区别
"""
# ---- 从下面开始写你的代码 ----
# TODO 1: 复制 step5_tool_loop.py 的 load_env / call_llm（带 tools 参数）
# TODO 2: 复制 TOOLS（工具定义）+ TOOL_IMPL（按名分发），再加一个你自己的工具
# TODO 3: 复制带工具的 execute_task（while 循环版）
# TODO 4: 写主循环（参考 babyagi.py），但 execute_task 换成带工具版本，用你自己的目标跑
