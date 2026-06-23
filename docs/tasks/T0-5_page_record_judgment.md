# T0-5 记今日判断页

**目标**：完成 `app/pages/1_record_judgment.py`，把表单提交真正写入飞书。
**现状**：表单 UI 已就绪，提交时调用 `FeishuClient().add_record` —— 待 T0-3 实现后即通。
**要做什么**：T0-3 完成后，去掉 NotImplementedError 占位分支，做成功/失败提示；校验必填；置信度 0-100。
**交付/验收**（FR-J-1, FR-U-1）：提交后飞书 judgments 表出现该记录，verify_date 正确。
**依赖**：T0-3。
