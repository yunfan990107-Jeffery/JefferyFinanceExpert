# T1-6 个人认知档案 + 月度校准报告

**目标**：基于判断历史统计认知偏差，生成个人认知档案与月度校准报告。
**要做什么**
- 飞书新建「个人认知档案」表（字段：period/avg_brier/overconfident/常见偏差类型/擅长领域/样本数），**建后按规则移入知识库**，table_id 写 `.env`。
- 扩展 `core/calibration.py`（**新增函数，不改既有签名**）：
  - `monthly_calibration_report(judgments: list[dict]) -> dict`　高置信准确率/平均 Brier/趋势
  - `detect_bias_by_target(judgments: list[dict]) -> dict`　按标的类型找系统性偏差
- 把月度报告写入认知档案表。
- （可选）复盘页加「校准趋势」展示。
**交付/验收**：能从判断历史产出月度报告并入库；偏差类型可解释；新增函数有单测、既有测试不破；满足 Global DoD。
**依赖**：T0 阶段（judgments 已有数据）；扩展 `calibration`。
