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

---

## ✅ 完成记录
- **任务**：T1-6 个人认知档案 + 月度校准报告
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 飞书新建「个人认知档案」表（cognitive_profile, tbli7JCXGifBHPG5, 7 字段）
  2. `calibration.py` 新增 `monthly_calibration_report(judgments)`：平均 Brier + 过度自信 + 偏差类型（方向偏差）+ 擅长领域 + 样本数
  3. `calibration.py` 新增 `detect_bias_by_target(judgments)`：按标的统计平均 Brier 与命中率
  4. 新增 4 个单测，**既有 4 个测试均未破坏**
- **改动文件**：
  - 修改：`core/calibration.py`（新增 2 函数，不改签名）
  - 修改：`tests/test_calibration.py`（+4 测试）
  - 修改：`core/config.py`（新增 table_cognitive）
  - 修改：`.env`（新增 TABLE_COGNITIVE）
- **测试**：`pytest -q` → **26 passed**（含 calibration 8 测试）
- **自验收报告**：能从判断历史产出月度报告 ✅；偏差类型可解释 ✅；新增函数有单测 ✅；既有测试不破 ✅
