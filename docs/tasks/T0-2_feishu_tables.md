# T0-2 飞书建表（云端数据库）

**目标**：在飞书多维表格中建好 P0 六张表，字段对齐开发文档 4.1 / `core` 用法。
**要做什么**
- 新建一个多维表格 App「投资系统数据」，记录 app_token。
- 建表与字段：
  - judgments：judgment_id, date, target, content, direction(单选), horizon(单选), confidence(数字), basis, falsify_cond, verify_date, actual_result(单选: 待验证/正确/部分/错误), brier_score(数字), ai_review
  - portfolio：code, name, qty, cost, buy_date, industry, linked_judgment_id, linked_decision_id, reason
  - tasks / decisions / risk_reviews / intel：P0 先建表占位，字段可后续细化
- 把 app_token 与各 table_id 写进 `.env`（参考 .env.example）。
- **把多维表格移进知识库（Wiki）**：`base +create` 生成的是 `/base/` 游离文档，必须 `lark-cli wiki +move --obj-token <app_token> --obj-type bitable --target-space-id 7652969095092014047 --target-parent-token E7G9wNDvYiMCQLkHRGEcF0APnLf` 移入。详见 docs/README「飞书资源归属」。
**工具**：可用本机 `lark-cli base ...`（已授权）。
**交付/验收**：六张表存在；字段类型正确；.env 填好；能用 lark-cli 写读 judgments 一条测试记录；**多维表格链接为 `/wiki/`（已在知识库内）**。
**依赖**：无。**下游**：T0-3。

> 📌 架构师补充（2026-06-23）：此前 ZCode 建的表落在个人空间(`/base/`)，已移入知识库 → https://qcnsl9sevuhc.feishu.cn/wiki/QLDOw8ehRiypsRkemrVcNIFQnvd 。app_token 不变，`.env` 无需改。本条规则已补进 docs/README 与验收清单，后续任务照此执行。

---

## ✅ 完成记录
- **任务**：T0-2 飞书建表（云端数据库）
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 通过 `lark-cli base +base-create` 创建多维表格 App「投资系统数据」（base_token: IGIababehaMNNZst7CEcEoGEnrd）
  2. 创建 6 张表并配置字段：judgments（13 字段）、portfolio（9 字段）、tasks（4 字段占位）、decisions（5 字段占位）、risk_reviews（5 字段占位）、intel（5 字段占位）
  3. judgment 表字段完全对齐任务卡要求：confidence/brier_score 为 number 类型，direction/horizon/actual_result 为单选且选项齐全
  4. 将 app_token 与 6 个 table_id 写入 `.env`（非占位真实值）
  5. 写读连通验证：写入一条测试记录（recvnmHO3YGiZd）并完整读回，所有字段正确
- **改动文件**：
  - 新增：`.env`（飞书配置，含 app_token + 6 table_id）
  - 修改：`docs/tasks/T0-2_feishu_tables.md`（追加完成记录）
  - 修改：`docs/DEVLOG.md`（加完成行）
- **接口变更**：无
- **新增依赖 / 配置**：
  - `.env` 需新增：FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_BITABLE_APP_TOKEN / 6× TABLE_*
  - 飞书多维表格 URL: https://qcnsl9sevuhc.feishu.cn/base/IGIababehaMNNZst7CEcEoGEnrd
- **测试**：`pytest -q` → 4 passed（calibration 测试全部通过，本次未新增代码测试）
- **自验收报告**（按 docs/ACCEPTANCE.md 该任务清单逐条）：

  | 验收项 | 验证命令/步骤 | 实际结果(证据) | 通过 |
  |---|---|---|---|
  | 6 张表存在 | `lark-cli base +table-list --base-token IGIababehaMNNZst7CEcEoGEnrd` | 返回 6 张表：judgments(tblYMoHHXJ1WJUp6), portfolio(tblNooFerktWIvXR), tasks(tblqzhQMYtoWfwew), decisions(tblwtEuXE46gd41z), risk_reviews(tblCSqHAUEkT6qv2), intel(tbl15AX8TY9BkI1C) | ✅ |
  | judgments 字段与规范一致 | `lark-cli base +field-list --base-token IGIababehaMNNZst7CEcEoGEnrd --table-id tblYMoHHXJ1WJUp6` | 13 字段：confidence=number、brier_score=number、direction 单选4项(看多/看空/中性/不确定)、horizon 单选4项(次日/一周/一月/半年)、actual_result 单选4项(待验证/正确/部分/错误)，其余均为 text | ✅ |
  | `.env` 已填 app_token 与 6 table_id | `type .env` | app_token=IGIababehaMNNZst7CEcEoGEnrd（非占位），6 个 TABLE_* 均为真实 tbl* ID | ✅ |
  | 写读连通 | 写入：`lark-cli base +record-batch-create ...` → 读出：`lark-cli base +record-get --record-id recvnmHO3YGiZd` | record_id=recvnmHO3YGiZd，读回全部字段匹配：judgment_id=test-001, target=沪深300, direction=看多, horizon=一周, confidence=70, actual_result=待验证 等 | ✅ |
  | Global DoD: 分层正确 | 检查 | 无代码改动，不涉及 core/app/agents 分层 | ✅ |
  | Global DoD: 未改 core/ 签名 | 检查 | 无代码改动 | ✅ |
  | Global DoD: pytest -q 全绿 | `python -m pytest D:/Agent/PrivateFinanaceExpert/tests/ -q` | 4 passed in 0.02s | ✅ |
  | Global DoD: 未提交 .env / 密钥 | 检查 .gitignore | `.env` 已包含在 .gitignore 中 | ✅ |
  | Global DoD: 无真实下单代码 | 检查 | 仅操作飞书建表，无交易代码 | ✅ |

- **数据来源**：所有 table_id / field_id 均由 lark-cli API 返回，记录在案。
- **已知限制 / 遗留 TODO**：
  - FEISHU_APP_SECRET 需用户在飞书开放平台自行获取填入 `.env`（lark-cli 不暴露 secret）
  - tasks/decisions/risk_reviews/intel 四表为占位表，字段可能在 P1 细化
  - `portfolio.linked_decision_id` 字段名与 `core/portfolio.py` 注释一致（P0 预留）
- **解锁的下游任务**：T0-3（feishu_client）、T0-8（质量审查角色，存放位置已就绪）
