# AI Agent 项目上下文

> **新 AI 第一读此文件。** 了解项目状态、架构、当前任务和坑，5 分钟即可上手。

## 我是谁

PrivateFinanceExpert — 个人 A 股 AI 投资分析系统。不自动下单，只做研究支持。

## 当前状态（2026-06-25 上午）

### ✅ 已完成

- **K 线数据库**：`data/market_data.sqlite`，5202 只 A 股，182 万行日线（2025-01 ~ 今），通过通达信 pytdx 拉取
- **概念板块数据库**：361 个概念板块 + 成分股 + K 线 + 资金流
- **K 线图表**：React SPA 多图层架构（蜡烛图 + MA5/10/20/60 + 成交量 + MACD/KDJ 切换）
- **后端 API**：FastAPI 12+ 个端点，含概念板块查询

### ⚠️ 已知问题

| 问题 | 详情 |
|------|------|
| K 线图间距不均 | Chart.js category scale 按日期当标签，周末留空。方案：改线性索引 + `chartjs-plugin-zoom` |
| K 线图无缩放/平移 | 用户要滚轮缩放 + 拖拽平移。方案 C（Lightweight Charts）已推荐，待用户确认 |
| 概念成分股偏少 | 平均每只股 2.2 个概念，10jqka 分页限制待排查 |
| 后端进程不稳定 | uvicorn background task 超时被杀，需手动 `python -m uvicorn api.main:app --port 8000` |

### 🔲 待确认

- K 线图交互方案（方案 A: chartjs-plugin-zoom / C: Lightweight Charts）

## 架构速览

```
web/index.html      ← React SPA（单文件，CDN 加载，约 1700 行）
api/main.py          ← FastAPI 薄接口层（12+ 端点，CORS 开）
core/                ← 业务逻辑（data_fetcher / feishu_client / calibration / portfolio / llm_client）
scripts/             ← 建库脚本
  build_kline_db.py      ← 通达信 pytdx → SQLite（--years 2 --workers 4，约 3 分钟）
  build_concept_db.py    ← 同花顺 10jqka → SQLite（--years 2，约 7 分钟）
data/                ← SQLite 数据库（不入 Git）
  market_data.sqlite     ← daily_k / stock_concept / concept_kline / concept_fund_flow
docs/
  AI_CONTEXT.md          ← 本文件（新 AI 先读）
  DEVLOG.md              ← 人类可读开发日志
  CHANGELOG.md           ← 面向 AI 的详细变更日志
```

## 快速启动

```bash
cd C:\Users\Jeffery\私人文件\Agent\JefferyFinanceExpert

# 激活虚拟环境
source .venv/Scripts/activate   # Git Bash

# 构建 K 线数据库（如已构建则跳过）
python scripts/build_kline_db.py --years 2 --workers 4

# 构建概念板块数据库（如已构建则跳过）
python scripts/build_concept_db.py --years 2

# 启动后端
python -m uvicorn api.main:app --port 8000

# 启动前端（另一个终端）
npx serve web -l 3000 --no-clipboard
```

## 数据源策略

| 用途 | 首选 | 备选 | 状态 |
|------|------|------|:--:|
| 股票 K 线 | 通达信 pytdx (TCP) | Baostock（被封） | ✅ |
| 概念板块 | 同花顺 10jqka | 东方财富（被封） | ✅ |
| 股票实时价 | Sina spot | AkShare（不稳定） | ✅ |
| 板块资金流 | 同花顺 data.10jqka.com.cn | — | ✅ |

## Git 注意

- **Remote 是 SSH**：`git@github.com:yunfan990107-Jeffery/JefferyFinanceExpert.git`
- 本机 HTTPS 不通（443 被墙），SSH 密钥在 `~/.ssh/id_ed25519`
- `data/`、`.env`、`cache/` 不入 Git
- 开发环境：Windows 11, Git Bash, Python 3.13 (Miniconda3), Node via npx

## 代码约定

- Python：`core/` 层纯函数优先，不依赖 UI
- 前端：React 18 CDN + Chart.js 4.4 + Babel Standalone，单文件 `web/index.html`
- 新增功能按 `brainstorming → writing-plans → implementing` 流程
- 日志：变更记录写入 `CHANGELOG.md`，简要写入 `docs/DEVLOG.md`
- 扩展 K 线指标：实现 `render` 函数 + 加入 `layers` 数组 + 加切换按钮，不改 KlineChart 主体

## 红线

- **不要改 `core/` 已定义的函数签名与 `FeishuClient` 方法签名**
- 不写任何真实下单/交易执行代码
- 不提交 `.env` 或任何密钥
- LLM 调用统一走 `core/llm_client.chat()`，不要自己写 requests

## LLM 调用

```
llm_client.chat(system_prompt, user_prompt) → str     # 通用调用
llm_client.load_role("devil_advocate.md") → str       # 加载角色提示词
```
DeepSeek（OpenAI 兼容），配置在 `.env`。未配置 key 时自动降级，不报错。

## 飞书资源

所有文档与多维表格挂入知识库 `space_id=7652969095092014047`，不在个人空间。
数据表位置：https://qcnsl9sevuhc.feishu.cn/wiki/QLDOw8ehRiypsRkemrVcNIFQnvd
