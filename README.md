# PrivateFinanceExpert · 个人 AI 投资分析系统

个人 A 股投资者的 AI 投资分析系统：系统化做研究、记录与校准判断、管理持仓、控制风险、复盘自己。
**核心边界：永不自动下单，不替用户做投资决策，只产出研究与认知支持。**

> **远程仓库**: https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert
> 克隆: `git clone https://github.com/yunfan990107-Jeffery/JefferyFinanceExpert.git`
> 新 agent 如何上手见 [`docs/ONBOARDING.md`](docs/ONBOARDING.md)。

## 文档（先读）
- 架构主文档（人类易读）: Feishu「V0.2.1 人类易读版」
- 需求文档(PRD): Feishu「AI投资专家需求文档集」
- 开发文档(技术设计): Feishu「AI投资专家开发文档集」
- 仓库内开发约定与任务卡: [`docs/README.md`](docs/README.md) 、 [`docs/tasks/`](docs/tasks/)

## 平台分工
- **飞书** = 云端数据库/系统记录源（判断、持仓、决策、研究、复盘）
- **Git** = 纯代码库（本仓库），不放数据
- **WebUI** = Streamlit 轻量界面（本仓库 `app/`），P0 三页
- **本地缓存** = 行情等可再生数据放 `cache/`（不入 Git）

## 技术栈
Python 3.11+ · Streamlit · 飞书多维表格(Bitable, 经 lark API) · AkShare(P1) · SQLite(P1) · pandas

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
core/       业务逻辑模块（feishu_client / calibration / portfolio / config）
agents/     AI 角色提示词（quality_review.md）
templates/  研究/风险/决策模板
docs/       开发约定 + 任务卡(tasks/)
tests/      单元测试
cache/      本地行情缓存（gitignore）
```

## 现状
P0 脚手架。`core/calibration.py`、`core/portfolio.py` 已有可用纯逻辑；`core/feishu_client.py` 为接口桩，待实现（见 `docs/tasks/T0-3.md`）。
