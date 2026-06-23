# T0-3 实现 feishu_client

**目标**：实现 `core/feishu_client.py` 的 `FeishuClient`（当前为 NotImplementedError 桩）。
**接口契约（不可改签名）**
- `add_record(table_id, fields: dict) -> str`（返回 record_id）
- `update_record(table_id, record_id, fields: dict) -> None`
- `list_records(table_id, filter_=None) -> list[dict]`（每条含 record_id + 字段）
- `get_due_judgments(today: date) -> list[dict]`（verify_date<=today 且 actual_result=='待验证'）
**实现方式（二选一）**：(a) subprocess 调用本机 lark-cli base；(b) lark-oapi SDK + app_id/secret。
**交付/验收**：能对 judgments / portfolio 表增改查；`get_due_judgments` 过滤正确；写一个集成测试（用真实测试表或 mock）。
**依赖**：T0-2。**下游**：T0-5/6/7。
