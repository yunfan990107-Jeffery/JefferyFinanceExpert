# 开发约定（给承接开发的 AI agent）

## 怎么开始
1. 读 Feishu 的 PRD（需求文档集）与 开发文档集，理解全局与字段级 schema。
2. 在 `docs/tasks/` 选一张任务卡（P0 为 T0-1 ~ T0-8），按卡片的"交付/验收"实现。
3. 实现完跑 `pytest -q`，确保已有测试通过；新增逻辑补测试。

## 接口纪律（重要）
- **不要改 `core/` 已定义的函数签名与 `FeishuClient` 方法签名**，否则会破坏其他人的并行工作。确需变更，先在任务卡里记录并说明影响。
- 业务逻辑放 `core/`，界面放 `app/`，AI 角色提示词放 `agents/`。各司其职。
- 飞书是数据真相源；本地 `cache/` 只放可再生数据，且已 gitignore。

## 飞书资源归属（重要）
所有在飞书创建的文档与多维表格，**必须挂进知识库（Wiki），不得留在个人云空间 / Drive**。
- 知识库 `space_id` = `7652969095092014047`；首页(根)节点 = `E7G9wNDvYiMCQLkHRGEcF0APnLf`。
- 用 `lark-cli base/docs +create` 新建后，若 URL 是 `/base/` 或 `/drive/`（非 `/wiki/`），说明它在个人空间，**必须移入**：
  `lark-cli wiki +move --as user --obj-token <token> --obj-type bitable|docx --target-space-id 7652969095092014047 --target-parent-token <父节点>`
- 移动后 app_token / obj_token **不变**，API 与 `.env` 配置不受影响；记录最终 `/wiki/` 链接。
- 数据多维表格现位置：https://qcnsl9sevuhc.feishu.cn/wiki/QLDOw8ehRiypsRkemrVcNIFQnvd

## 红线
- 不写任何真实下单/交易执行代码。
- 不提交 `.env` 或任何密钥。
- 重要数据/结论在产出中标注来源。

## 任务依赖（P0）
T0-1(骨架) ─┬─ T0-2(飞书建表) ── T0-3(feishu_client) ─┬─ T0-5(记判断页)
            │                                          ├─ T0-6(复盘页)
            │                                          └─ T0-7(持仓页)
            └─ T0-4(calibration, 已基本实现+测试)
T0-8(质量审查角色 + 示范研究) 可并行。
