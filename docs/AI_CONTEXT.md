# AI Agent 项目上下文

> **新 AI 第一读此文件。** 了解项目状态、架构、当前任务和坑，5 分钟即可上手。

## 我是谁

PrivateFinanceExpert — 个人 A 股 AI 投资分析系统。不自动下单，只做研究支持。

## 当前状态（2026-06-27 晚间）

### ✅ 已完成（7 大模块）

| 模块 | 说明 |
|------|------|
| K 线数据库 | 5202 只 A 股 + 6 指数，182 万行日线，通达信 pytdx TCP 直连 |
| 概念板块 | 361 概念 + 成分股 + K 线 + 资金流，同花顺 10jqka 源 |
| K 线图表 | LW Charts 原生渲染，蜡烛图+MA+成交量+MACD/KDJ，十字光标+缩放平移 |
| 指数行情 | 6 大指数实时K线（上证/深证/创业板/科创50/沪深300/上证50） |
| Z 哥选股 | 7 个策略筛选器 + 预计算信号 + ScreenPage 条件检索页面 |
| 持仓看板 | 收益概览+持仓表格+目标偏离+新增/调整/删除，SQLite 存储 |
| 日更系统 | `sync_daily.py` 增量同步个股/指数/概念/资金流/Z哥信号 |

### ⚠️ 已知问题

| 问题 | 详情 |
|------|------|
| 概念成分股偏少 | 每只股票平均 2.2 个概念，10jqka 分页限制待排查 |
| Portfolio 飞书集成 | 旧飞书版 portfolio 端点已删，现在是纯 SQLite 版本 |
| 搜索代码前缀 | stock_list 表有 sh/sz 前缀，部分 JOIN 需手动去前缀 |
| Babel 兼容 | `let` 顶层变量 + 函数默认数组参数会触发 Babel bug，避免即可 |

## 架构速览

```
web/index.html      ← React SPA（单文件 ~1900 行，CDN 加载）
  ├─ <script>         纯 JS：renderKlineChart (LW Charts)
  └─ <script babel>   React：Dashboard/Research/Screen/Portfolio/...
api/main.py          ← FastAPI（20+ 端点）
core/                ← 业务逻辑
  ├─ data_fetcher.py    ← K线/价格/概念查询
  ├─ portfolio.py      ← 持仓计算（收益+目标偏离）
  ├─ zg_indicators.py  ← Z哥指标（白线/黄线/砖型/KDJ/MACD）
  ├─ zg_screen.py      ← 7 个策略筛选器
  └─ zg_config.py      ← Z哥参数
scripts/
  ├─ build_kline_db.py    ← 通达信 pytdx → SQLite（--years 2, 3分钟）
  ├─ build_concept_db.py  ← 同花顺 10jqka → SQLite（--years 2, 7分钟）
  └─ sync_daily.py        ← 每日增量同步（--days 1, ~90秒）
data/market_data.sqlite ← 不入 Git（daily_k/stock_concept/concept_kline/zg_signals/portfolio_*）
```

## 快速启动

```bash
cd C:\Users\Jeffery\私人文件\Agent\JefferyFinanceExpert
source .venv/Scripts/activate

# 后端（守护进程，不会被杀）
python -c "import subprocess;subprocess.Popen(['.venv\\Scripts\\python.exe','-m','uvicorn','api.main:app','--port','8000'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,close_fds=True)"

# 前端（3000 端口）
cmd //c "taskkill /F /IM node.exe 2>nul" 2>&1
npx serve web -l 3000 --no-clipboard
```

## 数据源策略

| 用途 | 首选 | 备选 | 状态 |
|------|------|------|:--:|
| 个股K线 | 通达信 pytdx (TCP) | — | ✅ |
| 指数K线 | 通达信 get_index_bars | — | ✅ |
| 概念板块 | 同花顺 10jqka | — | ✅ |
| 实时价 | 通达信 + daily_k | Sina | ✅ |
| 板块资金流 | 同花顺 data.10jqka.com.cn | — | ✅ |

## Git 注意

- **SSH remote**：`git@github.com:yunfan990107-Jeffery/JefferyFinanceExpert.git`
- 密钥：`~/.ssh/id_ed25519`
- 本机 HTTPS 不通（443 被墙）
- `data/` `.env` `.claude/` `.superpowers/` 不入 Git
- Windows 11, Git Bash, Python 3.13 (Miniconda3)

## 红线

- 不要改 `core/` 已定义的函数签名
- 不写任何真实下单/交易执行代码
- 不提交 `.env` 或密钥
- 新增功能按 brainstorming → writing-plans → TDD → verify 流程
- 遇到 BUG 先用 systematic-debugging，不要猜
- KlineChart 用 `var` 不用 `const`（Babel 兼容）
- 不要在顶层用 `let`（Babel 兼容）
- 不要用默认数组参数（Babel 兼容）
