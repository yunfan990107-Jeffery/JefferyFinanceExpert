"""飞书多维表格（Bitable）读写封装 —— 接口契约（待实现，见 docs/tasks/T0-3.md）。

实现方式二选一：
  (a) 复用本机已授权的 lark-cli：subprocess 调 `lark-cli base ...` / `lark-cli api ...`
  (b) 使用 lark-oapi（飞书官方 Python SDK），用 app_id/app_secret 取 tenant_access_token

所有方法操作的是 config 中的 bitable_app_token 下的各 table。
保持本类的方法签名稳定——上层 app/ 与 core/ 依赖它。
"""
from __future__ import annotations
from datetime import date
from .config import config


class FeishuClient:
    def __init__(self, app_id: str = "", app_secret: str = "", app_token: str = ""):
        self.app_id = app_id or config.app_id
        self.app_secret = app_secret or config.app_secret
        self.app_token = app_token or config.bitable_app_token

    def add_record(self, table_id: str, fields: dict) -> str:
        """新增一条记录，返回 record_id。"""
        raise NotImplementedError("见 docs/tasks/T0-3.md")

    def update_record(self, table_id: str, record_id: str, fields: dict) -> None:
        """更新指定记录的字段。"""
        raise NotImplementedError("见 docs/tasks/T0-3.md")

    def list_records(self, table_id: str, filter_: dict | None = None) -> list[dict]:
        """列出记录，可选过滤。返回 [{record_id, fields...}]。"""
        raise NotImplementedError("见 docs/tasks/T0-3.md")

    def get_due_judgments(self, today: date) -> list[dict]:
        """便捷方法：返回验证日期<=today 且 actual_result 为'待验证'的判断。"""
        raise NotImplementedError("见 docs/tasks/T0-3.md")
