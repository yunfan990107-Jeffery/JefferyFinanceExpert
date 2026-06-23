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


# ── P1 新增测试 ──────────────────────────────────────────────

def test_monthly_calibration_report_basic():
    js = [
        {"confidence": 90, "actual_result": "错误", "date": "2026-06-01", "direction": "看多", "target": "沪深300"},
        {"confidence": 90, "actual_result": "错误", "date": "2026-06-15", "direction": "看多", "target": "沪深300"},
        {"confidence": 90, "actual_result": "错误", "date": "2026-06-20", "direction": "看空", "target": "新能源"},
    ]
    report = cal.monthly_calibration_report(js)
    assert report["sample_count"] == 3
    assert report["avg_brier"] > 0.5
    assert report["overconfident"] is True
    assert "过度自信" in report["bias_types"]
    assert report["period"] == "2026-06-01 ~ 2026-06-20"


def test_monthly_calibration_report_empty():
    report = cal.monthly_calibration_report([])
    assert report["sample_count"] == 0


def test_detect_bias_by_target():
    js = [
        {"confidence": 80, "actual_result": "正确", "target": "沪深300"},
        {"confidence": 80, "actual_result": "错误", "target": "沪深300"},
        {"confidence": 50, "actual_result": "正确", "target": "新能源"},
    ]
    bias = cal.detect_bias_by_target(js)
    assert "沪深300" in bias
    assert bias["沪深300"]["count"] == 2
    assert "新能源" in bias
    assert bias["新能源"]["count"] == 1


def test_existing_functions_unchanged():
    """确保 P1 新增函数不影响既有函数。"""
    assert cal.make_verify_date(date(2026, 6, 23), "次日") == date(2026, 6, 24)
    assert cal.brier_score(100, "正确") == 0.0
    assert cal.brier_score(100, "错误") == 1.0
    s = cal.calibration_summary([
        {"confidence": 90, "actual_result": "错误"} for _ in range(5)
    ])
    assert s["overconfident"] is True
