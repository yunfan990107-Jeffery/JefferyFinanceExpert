# T0-4 判断校准逻辑

**状态**：✅ 基本实现（`core/calibration.py`）+ 测试（`tests/test_calibration.py`）。
**已含**：make_verify_date、brier_score、calibration_summary（分桶命中率+过度自信标记）、build_review_prompt。
**可选增强（认领者可做）**：更多偏差类型（追涨杀跌、对某板块系统性偏差，需结合 target 分类）；月度报告聚合函数。增强时保持现有签名与测试通过。
**依赖**：无。
