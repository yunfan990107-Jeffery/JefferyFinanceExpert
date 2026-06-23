# T2-1 Agent 架构扩展性重构（配置化 + 工具注册 + function-calling）

**类别**：架构强化（非 P2 功能线）。**可分两步做**（先①②，后③④）。
**背景**：当前 agent = 写死的提示词文件，编排 = 写死的 Python 流水线（`core/stock_research.py`），且 agent **不能自主调工具**（数据都靠外层喂文本）。目标是让「加子专员」变成改配置、让 agent 能「装 skill（自主调工具）」。借鉴 `D:\Agent\TradingAgents-AShare` 的 **tool registry + agent 工厂 + DataCollector** 三个轻量模式（**不抄** LangGraph/FastAPI 重型栈）。

**要做什么**

① **Agent 配置化**
- 给每个 `agents/*.md` 加 YAML frontmatter：`name / team / inputs / tools / model_tier(cheap|strong)`。
- 新增 `agents/registry.py`：解析 frontmatter，提供 `get_agent(name) -> AgentSpec`、`list_agents(team=None)`。

② **工具注册表 + function-calling（这就是"装 skill"）**
- 新增 `core/tools.py`：`TOOL_REGISTRY = {name: callable}`，把现有 `data_fetcher` 的 get_price/get_kline/get_fundamentals/get_news 等注册为工具；`get_schemas(names) -> list`（OpenAI tools schema）。
- 扩展 `core/llm_client.py`，**新增** `chat_with_tools(system_prompt, user_prompt, tool_names: list[str], max_rounds=3) -> str`：把 schema 传给 DeepSeek（OpenAI 兼容 function-calling，**已确认支持**）→ 模型返回 tool_calls → 执行 TOOL_REGISTRY 中函数 → 结果回灌 → 循环至最终文本。**不改 chat()/generate_review()/load_role() 既有签名。**

③ **可配置流水线**
- 重构 `core/stock_research.py`：把写死的 draft→devil_advocate→risk_control→summary 改为由清单驱动的通用 runner，例如 `STOCK_RESEARCH_PIPELINE = ["draft","devil_advocate","risk_control","summary"]`。加专员 = 清单加一行 + 配置加一项。

④ **数据预取缓存（DataCollector）**
- 研究开始时一次性取 kline/fundamentals/news 进缓存，各 agent 从缓存读，避免重复调 data_fetcher（可复用现有 SQLite cache）。

⑤ **即插即用验证**
- 用新框架加一个 `technical_analysis` agent（agents/technical_analysis.md + 配置 + pipeline 一行 + 一个算 MA/MACD/KDJ 的 tool），**证明加专员只改配置、不改 runner 主体**。

**接口契约（新增，确定后勿改）**
- `core/tools.py`：`register(name, fn)` / `TOOL_REGISTRY` / `get_schemas(names) -> list`
- `core/llm_client.py`：`chat_with_tools(system_prompt, user_prompt, tool_names, max_rounds=3) -> str`
- agent frontmatter 字段格式（name/team/inputs/tools/model_tier）固定

**约束**：保持 P0/P1 既有测试全绿；不引入 LangGraph 等重框架；DeepSeek 做主力模型。

**交付/验收**
- 加 `technical_analysis` 仅靠"配置+提示词+1个tool"完成，runner 主体未改 → 贴 diff 证明。
- `chat_with_tools` 能让 agent 自主调用 ≥1 个工具（如 get_kline）并产出结果 → 端到端贴证据。
- 既有测试不破 + 新增 tools/registry/runner 单测；`pytest -q` 全绿。
- 更新 `docs/README`「LLM 调用」与「新增 agent/工具的写法」。

**依赖**：T1-1（data_fetcher）、T1-3（stock_research 已有流水线，在其上重构）、T1-4（已有独立角色）。
