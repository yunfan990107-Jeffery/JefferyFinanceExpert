# T2-2 本地报告 → 飞书脚本（纯脚本写入，避免 token 翻倍）

**类别**：工具/基础设施。**小而独立,可立即并行。**
**背景**：让"对话 agent 边生成边用 MCP 写飞书"会使报告全文流经 agent 上下文,token ~翻倍。正确做法是**生成归生成,落地用纯脚本**(lark-cli/Python,不经过任何 LLM)。本卡提供这个脚本。

**要做什么**
- 新增 `scripts/push_report_to_feishu.py`，CLI 用法：
  `python scripts/push_report_to_feishu.py <local_md> [--title 标题] [--parent <wiki_node_token>]`
- 流程（全程无 LLM 调用）：
  1. 读本地 `.md` 文件。
  2. `lark-cli wiki +node-create --space-id 7652969095092014047 --parent-node-token <parent 默认 E7G9wNDvYiMCQLkHRGEcF0APnLf> --obj-type docx --title <title>` 在**知识库内**建节点。
  3. `lark-cli docs +update --api-version v2 --command append --doc <新节点> --doc-format markdown --content @<local_md>` —— **必须用 `@file` 传内容**(内容从磁盘读,不进命令行/不经模型 token 化)。
  4. 打印返回的 `/wiki/` 链接。
- 同时暴露函数 `push_markdown_to_wiki(md_path: str, title: str, parent: str = "E7G9...") -> str`（返回 wiki url），供其它模块调用。
- 默认挂进知识库,遵守 docs/README「飞书资源归属」规则(链接须为 `/wiki/`)。

**接口契约**
- CLI：`push_report_to_feishu.py <local_md> [--title] [--parent]`
- 函数：`push_markdown_to_wiki(md_path, title, parent="E7G9wNDvYiMCQLkHRGEcF0APnLf") -> str`

**约束**：纯 lark-cli/Python，**零 LLM 调用**；不把全文塞进命令行(用 @file)；不写真实 key/密钥。

**交付/验收**
- 给一份本地 `.md`，运行脚本后飞书知识库出现对应文档，返回 `/wiki/` 链接(贴出来)。
- 全程无任何 LLM/MCP-agent 调用(代码可证)。
- 文档链接为 `/wiki/`(在知识库内,非 `/base/` 或 `/drive/`)。

**依赖**：lark-cli 已授权。无代码依赖,可立即做。
