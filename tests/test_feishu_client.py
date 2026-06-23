"""FeishuClient 集成测试 —— 需 lark-cli 可用且 .env 已配。

若无 lark-cli 或配置不全，跳过全部测试。
测试在真实 judgments 表中进行，结束后清理测试记录。
"""
from __future__ import annotations
import json
import shutil
from datetime import date, timedelta

import pytest
from core.config import config as cfg

# ── 前置检查 ──────────────────────────────────────────────────
LARK_CLI_AVAILABLE = shutil.which("lark-cli") is not None


def _ready() -> bool:
    return bool(LARK_CLI_AVAILABLE and cfg.bitable_app_token and cfg.table_judgments)


pytestmark = pytest.mark.skipif(not _ready(), reason="lark-cli 未就绪或 .env 未配置")


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from core.feishu_client import FeishuClient
    return FeishuClient()


@pytest.fixture(scope="module")
def test_ids(client):
    """创建两条测试判断，返回 (due_id, future_id)；模块结束时清理。"""
    today = date.today()
    due_id = client.add_record(cfg.table_judgments, {
        "judgment_id": "pytest-due-001",
        "date": today.isoformat(),
        "target": "pytest标的一号",
        "content": "集成测试：已到期待验证",
        "direction": "看多",
        "horizon": "次日",
        "confidence": 80,
        "basis": "pytest 测试数据",
        "falsify_cond": "pytest 证伪条件",
        "verify_date": (today - timedelta(days=1)).isoformat(),
        "actual_result": "待验证",
    })
    future_id = client.add_record(cfg.table_judgments, {
        "judgment_id": "pytest-future-001",
        "date": today.isoformat(),
        "target": "pytest标的二号",
        "content": "集成测试：未到期",
        "direction": "看空",
        "horizon": "一月",
        "confidence": 50,
        "basis": "pytest 测试数据",
        "falsify_cond": "pytest 证伪条件",
        "verify_date": (today + timedelta(days=30)).isoformat(),
        "actual_result": "待验证",
    })
    yield (due_id, future_id)
    # 清理
    from core.feishu_client import FeishuClient
    fc = FeishuClient()
    for rid in (due_id, future_id):
        try:
            fc._cli(
                "base", "+record-delete",
                "--base-token", cfg.bitable_app_token,
                "--table-id", cfg.table_judgments,
                "--record-id", rid,
                "--yes",
            )
        except Exception:
            pass


# ── 测试用例 ──────────────────────────────────────────────────

class TestAddRecord:
    def test_returns_record_id(self, client, test_ids):
        due_id, future_id = test_ids
        assert due_id.startswith("rec"), f"record_id 应以 rec 开头: {due_id}"
        assert future_id.startswith("rec"), f"record_id 应以 rec 开头: {future_id}"


class TestListRecords:
    def test_reads_back_created_records(self, client, test_ids):
        due_id, _ = test_ids
        records = client.list_records(cfg.table_judgments)
        record_ids = [r["record_id"] for r in records]
        assert due_id in record_ids, f"未找到刚创建的记录 {due_id}"

    def test_fields_unwrapped(self, client, test_ids):
        """单选项字段应解包为字符串。"""
        due_id, _ = test_ids
        records = client.list_records(cfg.table_judgments)
        due = next(r for r in records if r["record_id"] == due_id)
        assert due["actual_result"] == "待验证", f"actual_result 类型/值异常: {due['actual_result']!r}"
        assert due["direction"] == "看多", f"direction 类型/值异常: {due['direction']!r}"
        assert isinstance(due["confidence"], (int, float)), f"confidence 应为数字"


class TestGetDueJudgments:
    def test_only_due_returned(self, client, test_ids):
        due_id, future_id = test_ids
        due = client.get_due_judgments(date.today())
        due_ids = [j["record_id"] for j in due]
        assert due_id in due_ids, f"到期记录 {due_id} 应在结果中"
        assert future_id not in due_ids, f"未到期记录 {future_id} 不应在结果中"

    def test_already_reviewed_excluded(self, client, test_ids):
        """已复盘(actual_result≠待验证)的记录不应再出现。"""
        due_id, _ = test_ids
        # 先把该记录改成已复盘
        client.update_record(cfg.table_judgments, due_id, {
            "actual_result": "正确",
            "brier_score": 0.04,
        })
        due = client.get_due_judgments(date.today())
        due_ids = [j["record_id"] for j in due]
        assert due_id not in due_ids, (
            f"已复盘记录 {due_id} 不应再出现在 get_due_judgments 中"
        )


class TestUpdateRecord:
    def test_update_fields(self, client, test_ids):
        """使用另一条记录(future_id)测更新，不影响 get_due 逻辑。"""
        _, future_id = test_ids
        client.update_record(cfg.table_judgments, future_id, {
            "actual_result": "错误",
            "brier_score": 0.81,
        })
        records = client.list_records(cfg.table_judgments)
        updated = next(r for r in records if r["record_id"] == future_id)
        assert updated["actual_result"] == "错误", f"未更新 actual_result: {updated['actual_result']!r}"
        assert updated["brier_score"] == 0.81, f"未更新 brier_score: {updated['brier_score']!r}"

    def test_original_fields_unchanged(self, client, test_ids):
        """更新部分字段不应改其他字段。"""
        _, future_id = test_ids
        records = client.list_records(cfg.table_judgments)
        updated = next(r for r in records if r["record_id"] == future_id)
        assert updated["content"] == "集成测试：未到期", "原始 content 不应被改"
        assert updated["confidence"] == 50, "原始 confidence 不应被改"
