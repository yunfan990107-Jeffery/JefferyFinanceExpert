# T0-6 复盘中心页 + 接 AI 角色

**目标**：完成 `app/pages/2_review_center.py` 闭环：列出到期判断→填结果→算 Brier→调质量审查角色生成复盘→写回飞书。
**要做什么**
- 用 `FeishuClient.get_due_judgments` 取到期判断（T0-3）。
- 填实际结果后：`calibration.brier_score` 算分；`build_review_prompt` 生成提示词。
- 调用 LLM（用 `agents/quality_review.md` 作 system prompt）产出复盘文本。
- `update_record` 写回 actual_result / brier_score / ai_review。原始判断字段不可改。
**交付/验收**（FR-J-3/J-4, FR-U-2）：到期判断能对答案、得到校准反馈并落库。
**依赖**：T0-3、T0-4、T0-8(角色)。
