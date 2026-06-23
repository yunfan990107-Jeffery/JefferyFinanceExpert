# T0-7 持仓看板页

**目标**：完成 `app/pages/3_portfolio.py`：录入持仓写飞书；列出并展示市值/盈亏/占比/集中度。
**现状**：UI 与 `portfolio.compute_position_metrics` / `concentration` 已就绪，待 T0-3 通飞书。
**要做什么**：接 `add_record`/`list_records`；P0 现价可手填或先用成本价，AkShare 取价留 P1（TODO 已标）。
**交付/验收**（FR-P-1/P-2, FR-U-3）：能录入并看到组合表与集中度提示。
**依赖**：T0-3。
