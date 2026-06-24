# Web 前端架构说明

> 供后续 AI Agent 理解和修改前端代码使用。

---

## 技术栈

| 层 | 选型 | 版本 |
|---|---|---|
| UI 框架 | React (CDN, 非 Node 构建) | 18.2.0 |
| JSX 转译 | Babel Standalone | 7.23.6 |
| 图表 | Chart.js | 4.4.0 |
| 样式 | 纯 CSS (custom properties + glassmorphism) | — |
| 字体 | Inter + JetBrains Mono (Google Fonts) | — |
| 后端 | FastAPI | ≥0.110 |
| 数据源 | AkShare (行情) + 飞书多维表格 (持仓/判断) | — |

**关键约束**: 这是一个单文件 SPA (`web/index.html`)，所有 React 组件写在一个 `<script type="text/babel">` 块中。没有 npm/webpack/vite，不需要 `npm install`。

---

## 文件结构

```
web/
└── index.html          # 完整 SPA (HTML + CSS + React 组件，~1500行)

api/
├── __init__.py
└── main.py             # FastAPI 薄接口层 (12 个端点)

core/                   # 业务逻辑层 (前端不直接调用)
├── data_fetcher.py     # AkShare + SQLite 缓存
├── intel.py            # AI 新闻分级
├── portfolio.py        # 持仓计算
├── calibration.py      # 校准统计
├── stock_research.py   # 个股深度研究
└── feishu_client.py    # 飞书数据库读写

.claude/launch.json     # 开发服务器配置 (web:3000, api:8000)
```

---

## 启动方式

```bash
# 前端静态服务 (端口 3000)
npx serve web -l 3000

# 后端 API (端口 8000)
python -m uvicorn api.main:app --reload --port 8000
```

或使用 `.claude/launch.json` 中的 preview 配置。

---

## 设计系统 (Design Tokens)

全部通过 CSS custom properties 定义在 `:root` 中：

```
背景色        --bg: #F0F3F8 (浅蓝灰)
表面          --surface: rgba(255,255,255,0.72) (毛玻璃)
主色          --primary: #4F6BFF (蓝紫)
渐变          --gradient-start → --gradient-end (#4F6BFF → #06B6D4)
涨            --up: #10B981 (绿)
跌            --down: #EF4444 (红)
警告          --warning: #F59E0B (橙)
圆角          --radius-sm/md/lg/xl: 6/10/14/20px
阴影          --shadow-sm/md/lg + --shadow-glow
```

**视觉风格**: 浅色科技感 glassmorphism (backdrop-filter: blur)，蓝紫渐变作为品牌色。

---

## 页面结构 (7 页)

| 页面 | 组件函数名 | 路由 key | 功能 |
|------|-----------|---------|------|
| 仪表盘 | `DashboardPage` | `dashboard` | 指数 + 涨跌 + 新闻 + 持仓摘要 + 校准条 |
| 个股分析 | `ResearchPage` | `research` | 输入代码 → 基本面 + 技术面 + AI报告 + K线 |
| 信息总览 | `NewsPage` | `news` | 关键词搜索 + AI分级/原始 + 重要性筛选 |
| 记判断 | `RecordPage` | `record` | 表单提交判断 (POST) |
| 复盘中心 | `ReviewPage` | `review` | 到期判断列表 + Brier 图 + 总结 |
| 持仓看板 | `PortfolioPage` | `portfolio` | 持仓表 + 集中度预警 + 绩效归因 |
| 校准报告 | `CalibrationPage` | `calibration` | Brier Score + 按标的偏差 + 建议 |

**路由机制**: `App` 组件中 `useState('dashboard')` + `switch` 渲染，侧边栏 `.nav-item` 的 `onClick` 切换 `activePage`。

---

## API 集成模式

### 核心工具函数

```javascript
const API_BASE = 'http://localhost:8000';

async function apiFetch(path) {
  try {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) throw new Error(resp.statusText);
    const json = await resp.json();
    return json.data ?? json;
  } catch (e) {
    console.warn('[API]', path, e.message);
    return null;
  }
}
```

### 每个页面的数据流模式

```
1. useState(mockData)          ← 硬编码兜底数据作为初始值
2. useEffect / useCallback     ← 组件挂载或用户触发时请求 API
3. apiFetch('/api/xxx')        ← 请求后端
4. if (data) setState(data)    ← 有数据则更新，否则保持 mock
```

**设计原则**: API 不可用时页面仍完整展示 mock 数据，不会白屏或报错。

### POST 请求 (仅 RecordPage)

```javascript
fetch(API_BASE + '/api/judgments', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ target, direction, confidence, horizon, basis, falsify }),
});
```

---

## API 端点清单

| 方法 | 路径 | 用途 | 返回格式 |
|------|------|------|---------|
| GET | `/api/market/indices` | 三大指数 | `{data: [{name,code,price,change_pct,volume}]}` |
| GET | `/api/market/overview` | 涨跌家数 | `{data: {up_count,down_count,flat_count,total}}` |
| GET | `/api/news?keyword=&limit=` | AI分级新闻 | `{data: [{title,summary,importance,source,time}]}` |
| GET | `/api/news/raw?keyword=&limit=` | 原始新闻 | 同上 (无 importance) |
| GET | `/api/portfolio` | 持仓全量 | `{data: {positions:[...],total_value,total_pnl,total_pnl_pct,concentration}}` |
| GET | `/api/judgments?status=` | 判断列表 | `{data: [{target,direction,confidence,...}]}` |
| GET | `/api/judgments/due` | 到期判断 | `{data: [...]}` |
| POST | `/api/judgments` | 创建判断 | `{record_id: "..."}` |
| GET | `/api/calibration/summary` | 校准统计 | `{data: {avg_brier,count,accuracy,bias_by_target}}` |
| GET | `/api/research/{code}` | 深度研究 | `{data: {technicals,report,...}}` |
| GET | `/api/stock/price/{code}` | 最新价 | `{data: {price,change_pct,...}}` |
| GET | `/api/stock/kline/{code}?days=60` | K线 | `{data: {dates:[],closes:[],...}}` |
| GET | `/api/stock/fundamentals/{code}` | 基本面 | `{data: {pe,pb,roe,...}}` |
| GET | `/api/health` | 健康检查 | `{status:"ok",llm_ready,feishu_ready}` |

---

## 图表组件

| 组件 | 类型 | 位置 |
|------|------|------|
| `IndexChart` | line (带面积填充) | Dashboard - 指数60日 |
| `SentimentChart` | doughnut | Dashboard - 市场情绪 |
| `PriceChart` | line (带面积填充) | Research - K线60日 |
| `BrierChart` | bar (条件着色) | Review - Brier趋势 |

所有图表使用 `useRef` + `useEffect` 管理 Chart.js 实例，组件卸载时 `destroy()`。`PriceChart` 接受 `data` prop（`{dates:[], closes:[]}`），无数据时使用内置 mock。

---

## 修改指南

### 调整样式
直接修改 `<style>` 块中的 CSS custom properties 或组件 class。

### 添加新页面
1. 在 `<script type="text/babel">` 中新增 `function XxxPage() {...}`
2. 在 `App` 的 `switch` 中添加 `case 'xxx': return <XxxPage />;`
3. 在侧边栏导航 JSX 中添加对应 `.nav-item`

### 修改 API 对接
- 调整 `apiFetch` 路径或参数
- 后端端点定义在 `api/main.py`，修改响应格式需同步调整前端 state 解构

### 注意事项
- **不要使用 `const styles = {...}`** — 全局命名冲突
- **不要使用 `scrollIntoView`** — iframe 预览环境兼容问题
- **不要使用 ES Module import** — Babel standalone 不支持
- 所有组件共享同一个 `<script>` 作用域，React hooks (`useState`, `useEffect`, `useRef`, `useCallback`, `useMemo`) 在顶部通过解构获取：
  ```javascript
  const { useState, useEffect, useRef, useCallback, useMemo } = React;
  ```

---

## 当前状态 (2026-06-24)

- ✅ 7 页全部搭建完成，API 骨架已接通
- ✅ 无 console 错误，页面完整渲染
- ⚠️ API 依赖网络 (AkShare) 和飞书连接，不可用时自动降级到 mock 数据
- 🔲 待完善: 各页面的交互细节、loading 骨架屏、错误状态 UI、响应式适配
- 🔲 待完善: 复盘中心的"复盘"按钮逻辑、持仓看板的"添加持仓"流程
- 🔲 待完善: 校准报告的动态建议生成 (目前为静态文案)
