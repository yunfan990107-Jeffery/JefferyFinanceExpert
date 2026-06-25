# T0-7 持仓看板页

**目标**：完成 `app/pages/3_portfolio.py`：录入持仓写飞书；列出并展示市值/盈亏/占比/集中度。
**现状**：UI 与 `portfolio.compute_position_metrics` / `concentration` 已就绪，待 T0-3 通飞书。
**要做什么**：接 `add_record`/`list_records`；P0 现价可手填或先用成本价，AkShare 取价留 P1（TODO 已标）。
**交付/验收**（FR-P-1/P-2, FR-U-3）：能录入并看到组合表与集中度提示。
**依赖**：T0-3。

---

## ✅ 完成记录
- **任务**：T0-7 持仓看板页
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 将 `app/pages/3_portfolio.py` 两处 `NotImplementedError` 占位替换为正式异常处理
  2. 录入表单接 `FeishuClient.add_record` → 写入飞书 portfolio 表
  3. 列表接 `FeishuClient.list_records` → 读取全部持仓
  4. 展示 `compute_position_metrics`（市值/盈亏%/占比）+ `concentration`（单标集中度 + 行业分布）
  5. 单标占比 >30% 触发集中度警告
- **改动文件**：
  - 修改：`app/pages/3_portfolio.py`（去掉 NotImplementedError 占位）
- **接口变更**：无
- **新增依赖 / 配置**：无
- **测试**：`pytest -q` → **11 passed in 10.88s**（端到端手动验证通过）
- **自验收报告**（按 docs/ACCEPTANCE.md T0-7 清单）：

  | 验收项 | 验证命令/步骤 | 实际结果(证据) | 通过 |
  |---|---|---|---|
  | 录入写入飞书 portfolio | 端到端 Python 模拟：add_record 三条持仓 | 平安银行 recvnmOapPVg4q / 茅台 recvnmOaIsBIJ9 / 宁德 recvnmOb1bWufu | ✅ |
  | 列表显示市值/盈亏%/仓位占比 | `portfolio.compute_position_metrics` 计算 | 茅台：市值 180000 / 盈亏 0% / 占比 60.5%；宁德：市值 105000 / 占比 35.29% | ✅ |
  | 集中度提示 | `portfolio.concentration` + 页面 `max_single_weight > 30` 警告 | 茅台 60.5% > 30% → ⚠️ 触发集中度警告 | ✅ |
  | 行业分布 | `concentration.by_industry` | {银行:4.2, 白酒:60.5, 新能源:35.29} | ✅ |
  | Global DoD: pytest -q 全绿 | `python -m pytest ... -q` | 11 passed | ✅ |
  | Global DoD: 未改 core/ 签名 | 检查 | 仅改 app/ | ✅ |

- **数据来源**：端到端测试数据为自动生成并已清理。
- **已知限制 / 遗留 TODO**：
  - P0 现价用成本价兜底（`prices = {p["code"]: p.get("cost", 0)}`），页面已有 `TODO(P1): AkShare 取现价` 注释
  - 买入日期 `buy_date` 字符串格式，未用飞书 dateTime 类型（保持与现有 schema 一致）
- **解锁的下游任务**：无（T0-7 为叶子任务）
