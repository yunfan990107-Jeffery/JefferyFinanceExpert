# T0-2 飞书建表（云端数据库）

**目标**：在飞书多维表格中建好 P0 六张表，字段对齐开发文档 4.1 / `core` 用法。
**要做什么**
- 新建一个多维表格 App「投资系统数据」，记录 app_token。
- 建表与字段：
  - judgments：judgment_id, date, target, content, direction(单选), horizon(单选), confidence(数字), basis, falsify_cond, verify_date, actual_result(单选: 待验证/正确/部分/错误), brier_score(数字), ai_review
  - portfolio：code, name, qty, cost, buy_date, industry, linked_judgment_id, linked_decision_id, reason
  - tasks / decisions / risk_reviews / intel：P0 先建表占位，字段可后续细化
- 把 app_token 与各 table_id 写进 `.env`（参考 .env.example）。
**工具**：可用本机 `lark-cli base ...`（已授权）。
**交付/验收**：六张表存在；字段类型正确；.env 填好；能用 lark-cli 写读 judgments 一条测试记录。
**依赖**：无。**下游**：T0-3。
