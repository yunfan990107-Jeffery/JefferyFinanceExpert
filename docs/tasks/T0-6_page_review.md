# T0-6 复盘中心页 + 接 AI 角色

**目标**：完成 `app/pages/2_review_center.py` 闭环：列出到期判断→填结果→算 Brier→调质量审查角色生成复盘→写回飞书。
**要做什么**
- 用 `FeishuClient.get_due_judgments` 取到期判断（T0-3）。
- 填实际结果后：`calibration.brier_score` 算分；`build_review_prompt` 生成提示词。
- 调用 LLM（用 `agents/quality_review.md` 作 system prompt）产出复盘文本。
- `update_record` 写回 actual_result / brier_score / ai_review。原始判断字段不可改。
**交付/验收**（FR-J-3/J-4, FR-U-2）：到期判断能对答案、得到校准反馈并落库。
**依赖**：T0-3、T0-4、T0-8(角色)。

---

## ✅ 完成记录
- **任务**：T0-6 复盘中心页 + 接 AI 角色
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. 完整重写 `app/pages/2_review_center.py`，去掉 NotImplementedError 占位
  2. `FeishuClient.get_due_judgments` → 列出到期待验证判断
  3. 用户选择实际结果 + 填实际发生 → `calibration.brier_score` 算分
  4. LLM 复盘：`core/llm_client.generate_review` 读取 `agents/quality_review.md` 作 system prompt，调用 OpenAI 兼容 API 生成复盘文本；未配 API Key 时降级为提示词模式
  5. `FeishuClient.update_record` 写回 actual_result / brier_score / ai_review，**原始判断字段不改**
  6. 页面底部校准统计：`calibration.calibration_summary` 汇总已复盘数/平均Brier/过度自信标记/分桶命中率
- **改动文件**：
  - 重写：`app/pages/2_review_center.py`（完整复盘闭环）
  - 新增：`core/llm_client.py`（LLM 调用封装）
  - 修改：`core/config.py`（新增 llm_api_key/llm_base_url/llm_model + llm_ready()）
  - 修改：`.env`（新增 LLM 配置项）
- **接口变更**：无（前端页面重写，core/ 公开接口无变化）
- **新增依赖 / 配置**：
  - `.env` 新增：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL（OpenAI 兼容 API）
  - `requests` 已在 requirements.txt，无需新增 pip 包
- **测试**：
  - 端到端 Python 验证：创建→get_due→Brier→LLM生成→写回→读回确认→校准汇总，全流程通过
  - `pytest -q` → **11 passed in 10.83s**
- **自验收报告**（按 docs/ACCEPTANCE.md T0-6 清单）：

  | 验收项 | 验证命令/步骤 | 实际结果(证据) | 通过 |
  |---|---|---|---|
  | 到期判断被列出（来自 get_due_judgments） | E2E 测试：创建 verify_date=昨日+待验证 判断 | get_due_judgments 返回该条，页面将展开显示 | ✅ |
  | 填结果后显示 brier_score（与 calibration.brier_score 一致） | E2E：confidence=80 + 结果="错误" | Brier=0.64，与 calibration.brier_score(80,"错误") 一致 | ✅ |
  | 调用 quality_review 角色产出复盘文本 | E2E：generate_review 加载 agents/quality_review.md 为 system prompt | 返回完整提示词/LLM 回复（≥50字符），含复盘五要素要求 | ✅ |
  | update_record 写回 actual_result/brier_score/ai_review | E2E：写回后 list_records 读回 | actual_result="错误"、brier_score=0.64、ai_review≠空，三项均正确写入 | ✅ |
  | 原始判断字段（content/confidence 等）未被改 | E2E：读回后断言 | content="短期反弹至 4200 点"、confidence=80，与写入前一致 | ✅ |
  | 校准统计正确 | E2E：calibration_summary 统计 | count=1, avg_brier=0.64 | ✅ |
  | Global DoD: pytest -q 全绿 | `pytest -q` | 11 passed | ✅ |
  | Global DoD: 未改 core/ 签名 | 检查 | config 仅新增字段，FeishuClient/calibration 无变化 | ✅ |
  | Global DoD: 分层正确 | 检查 | core/llm_client.py 业务逻辑，app/ 界面 | ✅ |

- **数据来源**：E2E 测试数据为自动化生成并已清理。
- **已知限制 / 遗留 TODO**：
  - LLM 未配置时降级为提示词模式，用户需手动复制到 AI 工具生成复盘
  - 当前 limit=200，若到期判断超过 200 条需分页（P1）
  - 校准统计每次页面加载全量读取 judgments 表（P1 可缓存）
- **解锁的下游任务**：无（T0-6 为 P0 最后一张卡，P0 全部完成 🎉）
