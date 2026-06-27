# 持仓看板 · 设计规格

> 2026-06-27 | brainstorming 确认

## 目标

重构持仓看板，支持：
1. 每日轻松登记持仓变化
2. 今日 vs 昨日持仓对比
3. 实际 vs 目标持仓比例偏离
4. 总收益一目了然

## 布局（全宽上下分区）

```
┌─ 收益概览 ──────────────────────────────────────┐
│ +9.01% │ ¥523,266 │ ¥480,000 │ +¥43,266 │ ...  │
├─ 当前持仓 ──────────────────────────────────────┤
│ 类型 │标的│成本│持仓│现价│市值│[+][-]│[✕]      │
│ …                                             │
├──────────────────┬──────────────────────────────┤
│ 目标 vs 实际     │ 新增持仓                     │
│ 黄金 6.5%/30%   │ [类型▾][代码][投资类型▾]      │
│ 进攻 64.8%/50%  │ [成本价][数量]  [新增]        │
│ 现金 28.7%/20%  │                              │
│ 目标配置        │                              │
│ 黄金[30]% …     │                              │
└──────────────────┴──────────────────────────────┘
```

## 数据模型

### 后端表：portfolio_positions

```sql
CREATE TABLE portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,              -- 股票代码（非股票可为空）
    name TEXT NOT NULL,     -- 标的名称
    type TEXT NOT NULL,     -- 股票/ETF/黄金/债券/现金
    category TEXT NOT NULL, -- 投资类型: 进攻/黄金/红利低波/现金
    cost REAL,              -- 成本价
    quantity REAL,          -- 持仓数量
    unit TEXT,              -- 单位: 股/克/元
    created_at TEXT,
    updated_at TEXT
);
```

### 后端表：portfolio_targets

```sql
CREATE TABLE portfolio_targets (
    category TEXT PRIMARY KEY,  -- 投资类型
    target_pct REAL             -- 目标仓位比例（0-100）
);
```

### 后端 API

| 端点 | 用途 |
|------|------|
| `GET /api/portfolio` | 获取当前持仓+目标+收益汇总 |
| `POST /api/portfolio/add` | 新增持仓 |
| `POST /api/portfolio/adjust` | 调整仓位（买/卖+数量+价格） |
| `DELETE /api/portfolio/{id}` | 删除持仓 |
| `PUT /api/portfolio/targets` | 更新目标配置 |

### 操作逻辑

- **新增**：表单提交 code/name/type/category/cost/quantity → INSERT
- **调整**：点击行 +/- → 弹出小窗选买/卖+数量+价格 → 更新 quantity 和 cost
- **删除**：点击 ✕ → 确认 → DELETE
- **实时价**：股票/ETF 从 daily_k 取最新 close，黄金手动更新，现金不变

### 收益计算

```
总市值 = SUM(quantity × current_price)
总成本 = SUM(quantity × cost_price)
累计盈亏 = 总市值 - 总成本
累计收益率 = 累计盈亏 / 总成本 × 100
今日盈亏 = SUM(quantity × (today_close - yesterday_close))
```

## 前端组件

### PortfolioPage 状态

```javascript
positions: [{id, code, name, type, category, cost, quantity, unit, current_price, market_value, pnl}]
targets: [{category, target_pct, actual_pct, diff}]
summary: {total_value, total_cost, total_pnl, total_pnl_pct, today_pnl}
adjustModal: {id, name, action, quantity, price} | null
```

## 验收标准

- [ ] 收益概览显示 6 个数字卡片
- [ ] 持仓表格支持 +/- 调整和 ✕ 删除
- [ ] 新增表单支持 5 种投资类型
- [ ] 目标偏离条形图显示实际 vs 目标
- [ ] 目标配置可修改
- [ ] 所有操作同步到 SQLite
- [ ] 不破坏现有页面功能
