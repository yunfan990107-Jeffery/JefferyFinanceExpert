"""portfolio 归因单元测试。"""
from core import portfolio


class TestAttribution:
    def test_correct_and_profit(self):
        """看对且赚 → 执行好。"""
        pos = {"pnl_pct": 15.0, "linked_judgment_id": "J1"}
        j = {"direction": "看多", "actual_result": "正确", "confidence": 70}
        r = portfolio.attribution(pos, j)
        assert r["judgment_correct"] is True
        assert r["execution_quality"] == "好"
        assert r["judgment_score"] is not None

    def test_correct_but_loss(self):
        """看对没赚 → 执行问题。"""
        pos = {"pnl_pct": -5.0, "linked_judgment_id": "J2"}
        j = {"direction": "看多", "actual_result": "正确", "confidence": 60}
        r = portfolio.attribution(pos, j)
        assert r["judgment_correct"] is True
        assert r["execution_quality"] == "执行问题"

    def test_wrong_but_profit(self):
        """看错反赚 → 幸运。"""
        pos = {"pnl_pct": 8.0, "linked_judgment_id": "J3"}
        j = {"direction": "看多", "actual_result": "错误", "confidence": 80}
        r = portfolio.attribution(pos, j)
        assert r["judgment_correct"] is False
        assert r["execution_quality"] == "幸运"

    def test_wrong_and_loss(self):
        """看错且亏 → 一致。"""
        pos = {"pnl_pct": -10.0, "linked_judgment_id": "J4"}
        j = {"direction": "看空", "actual_result": "错误", "confidence": 50}
        r = portfolio.attribution(pos, j)
        assert r["judgment_correct"] is False
        assert r["execution_quality"] == "一致"

    def test_no_linked_judgment(self):
        """无关联判断 → 优雅降级。"""
        pos = {"pnl_pct": 3.0}
        r = portfolio.attribution(pos, None)
        assert r["judgment_correct"] is None
        assert r["execution_quality"] == "无关联"
        assert "未关联" in r["note"]

    def test_partial_result(self):
        """actual_result 为'部分'时也算正确。"""
        pos = {"pnl_pct": 2.0}
        j = {"direction": "中性", "actual_result": "部分", "confidence": 40}
        r = portfolio.attribution(pos, j)
        assert r["judgment_correct"] is True


class TestPortfolioAttribution:
    def test_aggregate(self):
        positions = [
            {"pnl_pct": 10, "linked_judgment_id": "J1"},
            {"pnl_pct": -5, "linked_judgment_id": "J2"},
            {"pnl_pct": 3, "linked_judgment_id": ""},  # 无关联
        ]
        judgments = {
            "J1": {"direction": "看多", "actual_result": "正确", "confidence": 70},
            "J2": {"direction": "看多", "actual_result": "错误", "confidence": 60},
        }
        r = portfolio.portfolio_attribution(positions, judgments)
        assert r["total_positions"] == 3
        assert r["with_link"] == 2
        assert r["without_link"] == 1
        assert r["avg_judgment_score"] is not None
        assert "好" in r["execution_summary"]
        assert "无关联" in r["execution_summary"]
