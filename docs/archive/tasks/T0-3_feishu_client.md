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

---

## ✅ 完成记录
- **任务**：T0-3 实现 feishu_client
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 采用方案 (a)：subprocess 调用本机 `lark-cli`（通过 `cmd /c` 兼容 Windows .CMD 脚本）
  2. `add_record` → `lark-cli base +record-upsert`（无 --record-id = 创建），返回 record_id
  3. `update_record` → `lark-cli base +record-upsert`（带 --record-id = 更新）
  4. `list_records` → `lark-cli base +record-list --format json`，解析返回体并解包单选项数组为字符串
  5. `get_due_judgments` → 取全量 judgments，Python 侧按 verify_date ≤ today 且 actual_result='待验证' 过滤
  6. 内置 `_unwrap_cell` 处理单选字段 `["待验证"]` → `"待验证"` 的自动解包
- **改动文件**：
  - 修改：`core/feishu_client.py`（从 NotImplementedError 桩实现为完整 lark-cli subprocess 封装）
  - 新增：`tests/test_feishu_client.py`（7 个集成测试，含 fixture 自动清理）
- **接口变更**：无（所有方法签名与原始桩完全一致）
- **新增依赖 / 配置**：无（复用已安装的 lark-cli，无需额外 pip 包）
- **测试**：
  - 新增 7 个集成测试：TestAddRecord(1) + TestListRecords(2) + TestGetDueJudgments(2) + TestUpdateRecord(2)
  - `pytest -q` → **11 passed in 11.92s**（calibration 4 + feishu_client 7）
- **自验收报告**（按 docs/ACCEPTANCE.md T0-3 清单）：

  | 验收项 | 验证命令/步骤 | 实际结果(证据) | 通过 |
  |---|---|---|---|
  | `add_record` 返回 record_id | 集成测试 `test_returns_record_id` + `python -c "from core.feishu_client import FeishuClient; ..."` | 返回 `recvnmL...` 格式 record_id（测试 fixture 创建两条均成功） | ✅ |
  | `list_records` 能读回刚写的记录 | 集成测试 `test_reads_back_created_records` | 写入后 `list_records` 返回列表中包含刚创建的 record_id | ✅ |
  | `update_record` 改某字段成功 | 集成测试 `test_update_fields` | actual_result 从"待验证"→"错误"，brier_score→0.81，读回确认 | ✅ |
  | `get_due_judgments` 过滤正确 | 集成测试 `test_only_due_returned` + `test_already_reviewed_excluded` | 造两条（verify_date=昨天待验证 + 30天后待验证），仅返回第一条；标记"正确"后不再返回 | ✅ |
  | 方法签名未变 | `python -c "import inspect; from core.feishu_client import FeishuClient; ..."` | add_record(table_id,fields)→str / update_record(table_id,record_id,fields)→None / list_records(table_id,filter_=None)→list[dict] / get_due_judgments(today)→list[dict] — 与原始桩完全一致 | ✅ |
  | 集成测试 + pytest -q 全绿 | `python -m pytest D:/Agent/PrivateFinanaceExpert/tests/ -q` | `11 passed in 11.92s` | ✅ |
  | Global DoD: 分层正确 | 检查 | 业务逻辑在 core/feishu_client.py，测试在 tests/test_feishu_client.py | ✅ |
  | Global DoD: 未改 core/ 签名 | 检查 | 确认签名无变化 | ✅ |
  | Global DoD: 未提交 .env / 密钥 | `git status` | 仅改 core/feishu_client.py + 新增 tests/test_feishu_client.py | ✅ |
  | Global DoD: 无交易代码 | 检查 | 纯飞书 API 封装，无交易逻辑 | ✅ |

- **数据来源**：所有测试数据均为 pytest 自动生成并自动清理的测试记录。
- **已知限制 / 遗留 TODO**：
  - `list_records` 当前 limit=200，超 200 条时 `has_more=true` 但未实现分页（P1 补）
  - `filter_` 参数为 Python 侧过滤，未使用 lark-cli `--filter-json`（P1 可优化为服务端过滤）
  - 每次调用起一个 lark-cli 子进程，高频场景可改为长连接/SDK（P1 优化）
- **解锁的下游任务**：T0-5（记判断页）、T0-6（复盘页）、T0-7（持仓页）
