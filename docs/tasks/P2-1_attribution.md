# P2-1 实现绩效归因 attribution（暗线① 落地）

**类别**：P2·夯实地基。**背景**：`core/portfolio.py` 的 `attribution()` 仍是桩(NotImplementedError)。这是 T4 的核心价值、也是系统两条暗线之一(「判断对不对 vs 执行对不对」),P1 留空。持仓表已有 `linked_judgment_id` / `linked_decision_id` 字段可用。

**要做什么**
- 实现 `attribution(position, linked_judgment)`（**保持签名**）：给定一笔持仓 + 它关联的判断，产出归因——
  - **判断质量**：用关联判断的 direction / confidence / actual_result，判断"当初看对没有"。
  - **执行质量**：用持仓 pnl_pct 与"判断看对与否"的落差，识别"看对了没赚到 / 看错了反而赚"这类择时/仓位问题。
  - 返回 dict，如：`{"judgment_correct": bool|score, "execution_quality": str, "pnl_pct": float, "note": str}`。
- 新增组合级汇总（可选）：`portfolio_attribution(positions, judgments) -> dict`，聚合全组合的"判断 vs 执行"分布。
- 关联判断的获取：用 `position["linked_judgment_id"]` 去 judgments 表（`FeishuClient`）查那条判断；无关联时优雅降级（返回 note 说明缺关联）。
- （可选）持仓看板 `app/pages/3_portfolio.py` 加"归因"展示。

**接口契约**：实现既有 `attribution(position: dict, linked_judgment: dict | None) -> dict`（签名勿改）；可新增 `portfolio_attribution(...)`。

**交付/验收**
- 给一笔有 `linked_judgment` 的持仓，能输出"判断对不对 / 执行对不对"的归因（贴示例输出）。
- 无关联判断时优雅降级、不报错。
- 新增单测覆盖（看对没赚 / 看错反赚 / 无关联 三种）；`pytest -q` 全绿。

**依赖**：现有 portfolio / calibration / feishu_client。
