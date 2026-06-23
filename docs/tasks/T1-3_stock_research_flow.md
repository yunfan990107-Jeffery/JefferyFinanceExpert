# T1-3 个股深度分析流程（T1 团队）

**目标**：对单只 A 股产出完整研究备忘录并写入飞书研究库；流程强制经过反方+风险。
**要做什么**
- 飞书新建「研究报告库」表（字段参考 templates/research_memo.md：code/name/date/business/financials/valuation/risks/reverse_view/falsify/conclusion/sources/confidence），**建后按规则移入知识库**（见 docs/README「飞书资源归属」），table_id 写 `.env`。
- 编排流程：用 `data_fetcher` 取数 → 个股研究草稿 → 调 `agents/devil_advocate.md`（反方）→ 调 `agents/risk_control.md`（风险）→ 汇总成最终备忘录。
- 按 `templates/research_memo.md` 产出，写入研究库表。
- （可选）Streamlit 加「发起研究」页：输入代码与问题，触发流程。
**交付/验收**：给定代码能产出完整备忘录并入库；**关键事实带来源、含反方观点、含风险与证伪条件、标注不确定性**；结论是研究判断+条件，**非买卖指令**；满足 Global DoD。
**依赖**：T1-1、T1-4。
