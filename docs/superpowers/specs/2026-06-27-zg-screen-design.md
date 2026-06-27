# Z 哥选股页面 · 设计规格

> 2026-06-27 | 基于 ZG 条件检索页的选股系统集成

## 目标

将 Z 哥交易体系的 8 个策略规则集成到 React SPA，提供条件检索选股页面：
- 多规则勾选筛选
- 全市场预计算 + 秒级检索
- K 线预览联动
- 每只股票的完整 Z 哥战法分析

## 数据流

```
日更 sync_daily.py（收盘后）
  ├─ 更新 K 线（已有）
  ├─ 更新股票列表（已有）
  ├─ 更新指数（已有）
  └─ 【新增】sync_zg_signals()
       ├─ 遍历全市场 5200+ 只股票
       ├─ 对每只股票计算 8 个策略规则
       ├─ 满足条件的写入 zg_signals 表
       └─ 约 3-5 分钟（与 K 线同步并行）

检索时 POST /api/screen
  → SELECT FROM zg_signals WHERE rule IN (...) AND date=today
  → 秒级返回

选中结果行 GET /api/zg/{code}
  → 返回完整 Z 哥分析 JSON
  → 前端渲染 K 线 + 指标面板
```

## 数据库

### 新增表：zg_signals

```sql
CREATE TABLE IF NOT EXISTS zg_signals (
    code       TEXT NOT NULL,
    rule_name  TEXT NOT NULL,   -- B1/红砖/暴力K/B2/Tepu/单针/B1宽松/周线B1
    score      REAL,            -- 规则评分（B1为 X/12，红砖为强度%）
    details    TEXT,            -- JSON 详情
    date       TEXT NOT NULL,   -- 计算日期
    PRIMARY KEY (code, rule_name, date)
);
```

## 后端 API

### POST /api/screen

请求：
```json
{ "rules": ["B1", "红砖", "B2"] }
```

响应：
```json
{
  "data": [
    {"code":"600519","name":"贵州茅台","sector":"食品饮料","concepts":["白酒","超级品牌"],"rules":["B1","B2"],"b1_score":"10/12","brick_strength":"78%","close":1168.63,"pct_change":-3.2,"amount":45.2}
  ]
}
```

### GET /api/zg/{code}

返回该股完整 Z 哥战法分析：
```json
{
  "data": {
    "code":"600519",
    "dual_line":{"wl":1205.3,"yl":1180.5,"bull":true,"c_vs_yl":-1.0},
    "kdj":{"k":45.2,"d":52.1,"j":31.4},
    "macd":{"dif":-12.3,"dea":-8.1,"bar":-8.4},
    "brick":{"signal":false,"tag":"绿砖×5","val":0,"strength":0,"red_n":0,"green_n":5},
    "deep_v":{"signals":[],"short":68.1,"long":72.3},
    "trend":"pullback","trend_label":"周多日调",
    "risk":{"level":"SAFE","flags":0}
  }
}
```

## 前端页面

### 路由：新增 ScreenPage

侧边栏加导航项「选股」，路由 key `screen`。

### 布局（方案 A）

```
┌─ 左侧栏 200px ─┬─ 主内容区 ──────────────────────────┐
│ 参数检索        │ 条件检索  已选3规则  结果148条      │
│ 日期 [...]     │ [搜索▾] [全部板块▾] [导出]         │
│                │ ┌────────────────────────────────┐ │
│ 过滤规则        ││ 股票 │板块│概念│B1│红砖│成交额   │ │
│ ☑ 规则B1       ││ ... 结果表格（可点击选中行）      │ │
│ ☑ 形态红砖     │└────────────────────────────────┘ │
│ ☑ 规则B2       │                                    │
│ ☐ 底部暴力K    │ K线预览 [日K][周K][月K]             │
│ ☐ 周线B1       │ ┌────────────────────────────────┐ │
│ ☐ 规则B1宽松   │ │ 复用 KlineChart(LW Charts)      │ │
│ ☐ 规则Tepu     │ │ 叠加 Z 哥多空线（白线+黄线）     │ │
│ ☐ 单针         │ │ 副图: VOL + MACD                │ │
│                │ └────────────────────────────────┘ │
│ [开始检索]     │                                    │
└────────────────┴────────────────────────────────────┘
```

### 结果表格列

| 列 | 来源 | 说明 |
|---|---|---|
| 股票（代码+名称）| stock_list | 可点击选中 |
| 所属行业 | zg_signals | 从 TDX 行业编码获得 |
| 所属概念 | stock_concept | 主要概念 |
| B1 评分 | zg_signals | X/12 |
| 红砖强度 | zg_signals | % |
| 匹配规则 | zg_signals | 标签 |
| 最新价 | daily_k | |
| 涨跌幅 | 计算 | |
| 成交额 | daily_k | |

### 交互

1. 勾选规则 → 点击"开始检索" → 表格显示结果
2. 点击表格行 → 右侧 K 线预览区加载该股 K 线（含白线/黄线叠加）
3. K 线切换日/周/月
4. 搜索框支持代码/名称过滤

## 改动文件

| 文件 | 操作 |
|------|------|
| `core/zg_indicators.py` | 新 — 从 ZG 项目搬运指标函数 |
| `core/zg_screen.py` | 新 — 8 个策略筛选器 + 日更集成 |
| `core/zg_config.py` | 新 — Z 哥指标参数常量 |
| `scripts/sync_daily.py` | 改 — 新增 sync_zg_signals() |
| `api/main.py` | 改 — +2 端点 |
| `web/index.html` | 改 — +ScreenPage + 导航 |

## 验收标准

- [ ] sync_daily.py 运行后 zg_signals 表有今日数据
- [ ] POST /api/screen 返回正确筛选结果
- [ ] GET /api/zg/{code} 返回完整 Z 哥分析
- [ ] ScreenPage 可勾选规则并检索
- [ ] 结果表格显示正确列
- [ ] 点击行加载 K 线预览（含白线/黄线叠加）
- [ ] 日/周/月 K 线切换正常
- [ ] 不破坏现有页面功能
