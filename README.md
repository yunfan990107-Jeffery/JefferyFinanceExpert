# PrivateFinanceExpert · 个人 AI 投资分析系统

个人 A 股投资者的 AI 投资分析系统：系统化做研究、记录与校准判断、管理持仓、控制风险、复盘自己。
**核心边界：永不自动下单，不替用户做投资决策，只产出研究与认知支持。**

> **远程仓库**: https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert
> 克隆: `git clone https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert.git`
> 新 agent 如何上手见 [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md)（**新 AI 先读这个！**），老版见 [`docs/ONBOARDING.md`](docs/ONBOARDING.md)。

## 文档索引（开发 agent 必读，按此顺序）
| 文件 | 作用 |
|---|---|
| [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) | **新 AI 上下文速览**（当前状态+架构+已知问题） |
| [`docs/CHANGELOG.md`](CHANGELOG.md) | 面向 AI 的详细变更日志 |
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | 新 agent 冷启动流程 |
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | 新 agent 冷启动流程（先读） |
| [`docs/DEV_AGENT_SYSTEM_PROMPT.md`](docs/DEV_AGENT_SYSTEM_PROMPT.md) | 开发 agent 的 system prompt |
| [`docs/README.md`](docs/README.md) | 开发约定 + `core/` 接口契约 |
| [`docs/tasks/`](docs/tasks/) | P0 任务卡 T0-1~T0-8（认领一张） |
| [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) | 验收清单(DoD) + 自验收取证方式 |
| [`docs/COMPLETION_RECORD.md`](docs/COMPLETION_RECORD.md) | 完成后记录什么（含模板） |
| [`docs/DEVLOG.md`](docs/DEVLOG.md) | 开发日志（完成后加一行） |

> 飞书镜像（人类档案）：架构主文档「V0.2.1 人类易读版」、「需求文档集(PRD)」、「开发文档集」（含以上各手册镜像）。代码与文档以本仓库为准。

## 平台分工
- **飞书** = 云端数据库/系统记录源（判断、持仓、决策、研究、复盘）
- **Git** = 纯代码库（本仓库），不放数据
- **WebUI** = Streamlit 轻量界面（本仓库 `app/`），P0 三页
- **本地数据** = K 线等可再生数据放 `data/`（不入 Git），通过 `scripts/build_kline_db.py` 生成

## 技术栈
Python 3.11+ · Streamlit · 飞书多维表格(Bitable, 经 lark API) · LLM(DeepSeek, OpenAI 兼容) · AkShare(P1) · SQLite(P1) · pandas

## 快速开始
```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env        # 填入飞书 app_id/secret 与各表 token
streamlit run app/main.py
```

## 目录
```
app/        Streamlit 应用（main.py + pages/ 三页）
core/       业务逻辑模块（feishu_client / calibration / portfolio / llm_client / config）
agents/     AI 角色提示词（quality_review.md）
templates/  研究/风险/决策模板
docs/       开发约定 + 任务卡(tasks/)
tests/      单元测试
	data/       本地 K 线 + 概念板块数据库（gitignore，通过 build_*.py 生成）
	scripts/    建库脚本（build_kline_db.py / build_concept_db.py）
```

## 开发环境（本机）

| 项 | 值 |
|---|---|
| OS | Windows 11 x64 |
| Shell | Git Bash (MSYS2) |
| Python | 3.13.13 (Miniconda3 `C:\Users\Jeffery\miniconda3\`) |
| 虚拟环境 | `.venv`（项目根目录） |
| Node / npx | 可用 |
| 通达信服务器 | `218.75.126.9:7709`（pytdx 默认） |

### Git 远程

```
https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert.git
```

> 如果 HTTPS 连不上（部分网络 443 端口被墙），切到 SSH：
> ```
> git remote set-url origin git@github.com:yunfan990107-Jeffery/JefferyFinanceExpert.git
> ```
> SSH 密钥：`~/.ssh/id_ed25519`（已添加至 GitHub）。

---

## 现状
**P0 已全部完成 🎉**：飞书 6 表已建（在知识库内）、`feishu_client` / `calibration` / `portfolio` / `llm_client` 已实现、Streamlit 三页可用、复盘接 DeepSeek 自动点评、一份茅台示范研究已入库。
下一阶段 **P1**（数据层 AkShare / 个股深度研究 / 信息筛选 / 认知档案）任务卡见 `docs/tasks/T1-*.md`，可分配。
