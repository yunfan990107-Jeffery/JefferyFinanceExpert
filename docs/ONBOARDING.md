# 冷启动手册：如何让一个全新 agent 开始工作

> 适用于：完全没有上下文、没有 system prompt 的全新开发 agent。
> **仓库地址**: https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert

## 流程总览
```
你                          全新 Agent
│ ① 设 system prompt         │
│ ② 发首条消息(仓库+任务号) ─▶ ③ git clone 仓库
│                            │ ④ 读 docs/(任务卡+契约+约定)
│                            │ ⑤ 实现 → pytest → 写完成记录 → push
│ ⑥ 你验收(看 DEVLOG/提交)  ◀─┘
```
关键：agent 的全部上下文都在仓库 `docs/` 里。你只需给它「一份 system prompt + 一句去哪个仓库做哪张卡」。

## 前置（每次派活前确认）
| 任务类型 | 前置条件 |
|---|---|
| 纯代码（如 T0-4 增强） | 能 clone 仓库 + Python 环境 |
| 碰飞书的（T0-2/3/5/6/7） | agent 机器已 `lark-cli auth login`，或 `.env` 填好 FEISHU_APP_ID/SECRET 与表 token |
| 所有任务 | 能 `git push`（配好 GitHub 凭证），或它把结果交你手动提交 |

## ① system prompt（设给 agent）
```
你是一个软件开发 agent。请先克隆仓库 https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert ，
阅读并严格遵守 docs/DEV_AGENT_SYSTEM_PROMPT.md 中的全部规则作为操作准则，再开始我指派的任务。
动手前务必先读 docs/README.md 和被指派的那张 docs/tasks/ 任务卡。
```
（若该 agent 不能自动读取仓库文件，就把 `docs/DEV_AGENT_SYSTEM_PROMPT.md` 代码块内容整段贴成 system prompt。）

## ② 首条 user 消息（把 T0-3 换成目标任务号）
```
请完成任务卡 docs/tasks/T0-3_feishu_client.md。
步骤：① clone 仓库并读 docs/README.md 与该任务卡；② 按接口契约实现；
③ 跑 pytest -q 确保全绿；④ 逐条对照验收标准自检；
⑤ 按 docs/COMPLETION_RECORD.md 写完成记录、更新 docs/DEVLOG.md；
⑥ commit(信息以 T0-3: 开头)并 push。不清楚先问我，不要臆测。
```

## ③ 你如何验收
1. GitHub 有新提交，信息为 `T0-X: ...`
2. `docs/DEVLOG.md` 顶部多一行
3. 对应 `docs/tasks/T0-X.md` 末尾有「✅ 完成记录」（重点看"接口变更=无"和验收逐条对照）
4. `git pull` 后本地 `pytest -q` 全绿

## 派活顺序
T0-3 依赖 T0-2（飞书建表）。先派/先做 T0-2，再并行派 T0-3、T0-5/6/7。
