"""calibration 单元测试。定义期望行为，开发 agent 应保持通过。
运行： pytest -q
"""
from datetime import date
from core import calibration as cal


def test_make_verify_date():
    assert cal.make_verify_date(date(2026, 6, 23), "次日") == date(2026, 6, 24)
    assert cal.make_verify_date(date(2026, 6, 23), "一周") == date(2026, 6, 30)


def test_brier_score_perfect_and_worst():
    assert cal.brier_score(100, "正确") == 0.0      # 满信心且对 → 0
    assert cal.brier_score(100, "错误") == 1.0      # 满信心却错 → 1
    assert cal.brier_score(50, "部分") == 0.0       # 50% 信心、部分命中(0.5) → 0


def test_calibration_summary_overconfident():
    js = [{"confidence": 90, "actual_result": "错误"} for _ in range(5)]
    s = cal.calibration_summary(js)
    assert s["count"] == 5
    assert s["overconfident"] is True


def test_calibration_summary_empty():
    assert cal.calibration_summary([])["count"] == 0
