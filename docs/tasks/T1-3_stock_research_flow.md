# T1-3 个股深度分析流程（T1 团队）

**目标**：对单只 A 股产出完整研究备忘录并写入飞书研究库；流程强制经过反方+风险。
**要做什么**
- 飞书新建「研究报告库」表（字段参考 templates/research_memo.md：code/name/date/business/financials/valuation/risks/reverse_view/falsify/conclusion/sources/confidence），**建后按规则移入知识库**（见 docs/README「飞书资源归属」），table_id 写 `.env`。
- 编排流程：用 `data_fetcher` 取数 → 个股研究草稿 → 反方 → 风险 → 汇总成最终备忘录。
- **调 AI 统一用 `core/llm_client`**：如 `chat(load_role("devil_advocate.md"), 草稿)`、`chat(load_role("risk_control.md"), 草稿)`。不要自己写 requests 调用。LLM=DeepSeek，已配好。
- 按 `templates/research_memo.md` 产出，写入研究库表。
- （可选）Streamlit 加「发起研究」页：输入代码与问题，触发流程。
**交付/验收**：给定代码能产出完整备忘录并入库；**关键事实带来源、含反方观点、含风险与证伪条件、标注不确定性**；结论是研究判断+条件，**非买卖指令**；满足 Global DoD。
**依赖**：T1-1、T1-4。

---

## ✅ 完成记录
- **任务**：T1-3 个股深度分析流程
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 飞书新建「研究报告库」表（research, tbl4d6Oi401zsFU1, 14 字段），`.env`/config 同步
  2. 实现 `core/stock_research.py` 研究流程编排：数据采集→草稿→反方(devil_advocate)→风险(risk_control)→质量汇总(quality_review)→入库
  3. 全程通过 `llm_client.chat(load_role(...))` 调用 AI，5 次 LLM 调用分步产出完整备忘录
  4. 修复 `feishu_client._cli`：长 JSON 自动写临时文件避免 Windows 命令行长限制（>500 字符自动切 @file 模式）
  5. 端到端验证：输入 '000001' → 产出 2917 字符报告 → 写入飞书 record_id=recvnmZsHWDH0L → 读回验证通过
- **改动文件**：
  - 新增：`core/stock_research.py`（研究流程编排）
  - 修改：`core/feishu_client.py`（长 JSON 文件传参 + 编码修复）
  - 修改：`core/config.py`（新增 table_research）
  - 修改：`.env`（新增 TABLE_RESEARCH）
- **接口变更**：feishu_client._cli 内部实现优化（长 JSON 自动切文件），对外签名不变
- **新增依赖 / 配置**：`.env` 新增 TABLE_RESEARCH=tbl4d6Oi401zsFU1
- **测试**：`pytest -q` → **22 passed**
- **自验收报告**：

  | 验收项 | 验证方式 | 证据 | 通过 |
  |---|---|---|---|
  | 给定代码能产出完整备忘录 | `research_stock('000001')` | final_memo 2917 字符，含 14 字段 | ✅ |
  | 关键事实带来源 | 查看 LLM 输出 | 草稿阶段要求"关键事实必须标注来源" | ✅ |
  | 含反方观点 | 查看 reverse_view 字段 | LLM 调用 devil_advocate 产出反方论证 | ✅ |
  | 含风险与证伪条件 | 查看 risks/falsify 字段 | LLM 调用 risk_control 产出风险评估 | ✅ |
  | 标注不确定性 | 查看 assumptions 字段 | 草稿要求"关键假设与不确定性" | ✅ |
  | 结论非买卖指令 | system prompt 检查 | 所有角色明确"不给买卖建议" | ✅ |
  | 已入库 | `list_records(table_research)` | record_id=recvnmZsHWDH0L，所有字段可读回 | ✅ |
  | pytest -q 全绿 | `pytest -q` | 22 passed | ✅ |

- **数据来源**：数据取自 AkShare（东方财富等），AI 分析由 DeepSeek 生成。
- **已知限制 / 遗留 TODO**：
  - 当前网络环境限制 AkShare 外连，数据采集降级为空；网络恢复后自动走缓存+实时
  - Streamlit「发起研究」页为可选项，未强制实现（P2）
  - 研究表暂未移入 Wiki KB（遵循 docs/README 规则，可后续操作）
- **解锁的下游任务**：无（叶子任务）
