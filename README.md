# PrivateFinanceExpert · 个人 AI 投资分析系统

个人 A 股投资者的 AI 投资分析系统：系统化做研究、记录与校准判断、管理持仓、控制风险、复盘自己。
**核心边界：永不自动下单，不替用户做投资决策，只产出研究与认知支持。**

> **远程仓库**: https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert
> 克隆: `git clone https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert.git`
> 新 agent 如何上手见 [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md)（**新 AI 先读这个！**），老版见 [`docs/ONBOARDING.md`](docs/ONBOARDING.md)。

## 文档索引（开发 agent 必读，按此顺序）
| 文件 | 作用 |
|---|---|
| [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) | **新 AI 上下文速览**（当前状态+架构+已知问题+红线） |
| [`CHANGELOG.md`](CHANGELOG.md) | 面向 AI 的详细变更日志 |
| [`docs/DEVLOG.md`](docs/DEVLOG.md) | 人类可读开发日志 |
| [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) | 验收清单 + 自验收方式 |
| [`docs/archive/tasks/`](docs/archive/tasks/) | 已完成的 P0/P1/P2 任务卡（历史参考） |

> 飞书镜像（人类档案）：架构主文档「V0.2.1 人类易读版」、「需求文档集(PRD)」、「开发文档集」（含以上各手册镜像）。代码与文档以本仓库为准。

## 平台分工
- **飞书** = 云端数据库/系统记录源（判断、持仓、决策、研究、复盘）
- **Git** = 纯代码库（本仓库），不放数据
- **WebUI** = React SPA（`web/index.html`，CDN 单文件，7 页）+ FastAPI 后端（`api/main.py`）
- **本地数据** = K 线等可再生数据放 `data/`（不入 Git），通过 `scripts/build_*.py` 生成

## 技术栈
Python 3.13+ · FastAPI · React 18 (CDN) · Chart.js 4.4 · 通达信 pytdx · 飞书多维表格 · LLM(DeepSeek) · pandas

## 快速开始
```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env        # 填入飞书 app_id/secret 与各表 token

# 构建本地数据库（首次）
python scripts/build_kline_db.py --years 2 --workers 4
python scripts/build_concept_db.py --years 2

# 启动后端 + 前端
python -m uvicorn api.main:app --port 8000 &
npx serve web -l 3000 --no-clipboard
```

## 目录
```
web/        React SPA 前端（单文件 index.html）
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
