# 验收手册（Definition of Done & AI 自验收协议）

> 目的：让开发 agent 能**客观地自己验收**，而不是主观判断"差不多"。
> 原则：每条验收项 = **断言 + 如何验证(命令/步骤) + 实际结果(证据)**。没有证据 = 没通过。

## 0. 通用完成定义（Global DoD，每个任务都必须满足）
- [ ] 分层正确：业务逻辑在 core/、界面在 app/、AI 提示词在 agents/
- [ ] **未改动 core/ 既定函数与 FeishuClient 方法签名**（或已在任务卡记录"接口变更说明+影响+通知"）
- [ ] `pytest -q` 全绿（贴输出）
- [ ] 任务卡对应的验收清单逐条 ✅ 且附证据
- [ ] 完成记录 + DEVLOG 一行 + 提交信息以 `T0-X:` 开头
- [ ] 未提交 `.env` / 任何密钥；无任何真实下单/交易执行代码
- [ ] **在飞书新建的文档/表已挂入知识库（链接为 `/wiki/`，非 `/base/` 或 `/drive/` 游离）**
- [ ] 产出若含数据结论，已标注来源

## 1. 三类证据怎么取
| 验证对象 | 取证方式 |
|---|---|
| 代码逻辑 | 跑命令贴输出，如 `pytest -q`、`python -c "..."` |
| 飞书数据 | 用 lark-cli 查询确认，如 `lark-cli base ...` 读出记录，贴 record_id / 查询结果 |
| WebUI | `streamlit run app/main.py` 后操作，贴界面结果描述（或截图）与对应飞书记录 |

## 2. 各任务验收清单（DoD）

### T0-2 飞书建表
- [ ] 6 张表存在 → 列出表清单
- [ ] judgments 字段与开发文档 4.1 完全一致（类型对：confidence=数字、各单选选项齐）→ 贴字段列表
- [ ] `.env` 已填 app_token 与 6 个 table_id（非占位）
- [ ] 写读连通：用 lark-cli 写一条再读出 → 贴 record_id 与读回内容

### T0-3 feishu_client
- [ ] `add_record` 返回 record_id（写一条 judgment，贴 id）
- [ ] `list_records` 能读回刚写的记录
- [ ] `update_record` 改某字段成功（贴前后对比）
- [ ] `get_due_judgments` 过滤正确：造两条（一条 verify_date<=今天且待验证、一条未到期），只返回第一条
- [ ] 方法签名未变（与 docs/README 接口契约一致）
- [ ] 集成测试 + `pytest -q` 全绿

### T0-5 记今日判断页
- [ ] `streamlit run` 能起，页面①表单可见
- [ ] 提交后飞书 judgments 出现该记录 → 贴 record_id
- [ ] verify_date 按 horizon 正确（次日=+1，一周=+7…）
- [ ] 必填校验生效、置信度滑块 0-100

### T0-6 复盘中心页
- [ ] 到期判断被列出（来自 get_due_judgments）
- [ ] 填结果后显示 brier_score（数值与 calibration.brier_score 一致）
- [ ] 调用 quality_review 角色产出复盘文本
- [ ] `update_record` 写回 actual_result/brier_score/ai_review → 贴飞书前后对比
- [ ] 原始判断字段（content/confidence 等）未被改

### T0-7 持仓看板页
- [ ] 录入写入飞书 portfolio → 贴 record_id
- [ ] 列表显示市值/盈亏%/仓位占比（数值与 portfolio.compute_position_metrics 一致）
- [ ] 单标占比>30% 触发集中度提示

### T0-8 质量审查角色 + 示范研究
- [ ] 示范研究含全部要素：关键事实**带来源** / 反方观点 / 风险 / 证伪条件 / 不确定性标注
- [ ] 结论是研究判断+条件，**非买卖指令**
- [ ] 已存入飞书 → 贴链接

## 3. 自验收报告（写进完成记录，必填）
对该任务的验收清单逐条给出：

```markdown
| 验收项 | 验证命令/步骤 | 实际结果(证据) | 通过 |
|---|---|---|---|
| add_record 返回 id | python -c "..." | recXXXX | ✅ |
| ... | ... | ... | ✅/⚠️ |
```
有任一 ⚠️ 即为"部分完成"，必须说明原因与后续计划，不得标记为已完成。
