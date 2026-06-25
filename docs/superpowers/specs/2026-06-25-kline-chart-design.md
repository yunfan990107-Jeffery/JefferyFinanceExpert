# K 线图表组件 · 设计规格

> 2026-06-25 | 方案 B：专业看盘级别 K 线 | brainstorming → writing-plans

## 目标

在个股分析页（ResearchPage）输入股票代码后，展示近 2 年日 K 线图，包含：
- 蜡烛图（candlestick，涨绿跌红）
- MA 均线叠加（MA5 灰 / MA10 黄 / MA20 蓝 / MA60 紫）
- 成交量副图（涨绿跌红柱）
- MACD / KDJ 副图（可切换）

## 架构

```
KlineChart（容器组件）
  ├─ chart layers（插件式注册）
  │   ├─ candlestick     — 蜡烛图
  │   ├─ maOverlay       — 均线叠加
  │   ├─ volumeBars      — 成交量副图
  │   ├─ macdChart       — MACD 副图（DIF/DEA/柱）
  │   └─ kdjChart        — KDJ 副图（K/D/J 线）
  ├─ periodSelector      — 日线/周线/月线
  └─ subIndicatorToggle  — 副图切换按钮（MACD / KDJ）
```

## 核心接口设计

```javascript
// KlineChart 对外接口
<KlineChart
  data={klines}           // [{date, open, high, low, close, volume}, ...]
  maPeriods={[5,10,20,60]}  // 均线周期
  maColors={{5:'#9CA3AF', 10:'#F59E0B', 20:'#3B82F6', 60:'#8B5CF6'}}
  layers={['candlestick','ma','volume','macd']}  // 渲染图层列表
  height={500}
  subIndicator="macd"     // 当前选中的副图 'macd' | 'kdj'
  onSubIndicatorChange={fn}
/>

// 新图层只需实现注册：
// chartPlugins.register('rsi', { render(ctx, chart, data, params) })
```

### 扩展方式

后续新增指标（如 RSI、BOLL、WR），只需：
1. 实现一个 `render` 函数，签名同现有图层
2. 加入 `layers` 数组
3. 在 `subIndicatorToggle` 加一个按钮

不修改 KlineChart 主体代码。

## 数据流

```
ResearchPage
  │ 用户输入 600519 → doResearch()
  │
  ├─ GET /api/stock/kline/600519?days=500
  │   └─ data_fetcher.get_kline() → daily_k 表
  │   └─ 返回 [{date, open, high, low, close, volume}, ...]
  │
  ├─ GET /api/stock/price/600519
  │   └─ data_fetcher.get_price() → price_cache / AkShare fallback
  │
  └─ setKlineData → KlineChart 渲染
```

## 视觉设计

### 配色

| 元素 | 颜色 | 色值 |
|------|------|------|
| 涨（阳线） | 绿 | `#10B981` |
| 跌（阴线） | 红 | `#EF4444` |
| MA5 | 灰 | `#9CA3AF` |
| MA10 | 黄 | `#F59E0B` |
| MA20 | 蓝 | `#3B82F6` |
| MA60 | 紫 | `#8B5CF6` |
| MACD DIF | 蓝 | `#3B82F6` |
| MACD DEA | 橙 | `#F59E0B` |
| MACD 柱(正) | 绿 | `#10B981` |
| MACD 柱(负) | 红 | `#EF4444` |
| KDJ K | 蓝 | `#3B82F6` |
| KDJ D | 橙 | `#F59E0B` |
| KDJ J | 紫 | `#8B5CF6` |
| 成交量涨 | 绿 | `rgba(16,185,129,0.5)` |
| 成交量跌 | 红 | `rgba(239,68,68,0.5)` |

### 布局比例

```
┌────────────────────────────┐
│  periodSelector            │  日线 | 周线 | 月线                    35px
├────────────────────────────┤
│                            │
│  candlestick + MA          │  主图区                             60%
│                            │
├────────────────────────────┤
│  volume                    │  成交量副图                          15%
├────────────────────────────┤
│  subIndicator (MACD/K线)    │  副图指标区                          25%
│  + toggle 按钮             │                                      50px
└────────────────────────────┘
```

## 前后端改动清单

### 前端 (`web/index.html`)

1. **ResearchPage**：`days=180` → `days=500`
2. **KlineChart 组件**：从单一 `candlePlugin` 重构为多图层架构
3. **新增图层函数**：`maOverlay` / `volumeBars` / `macdChart` / `kdjChart`
4. **新增 `subIndicatorToggle`**：MACD / KDJ 切换按钮
5. **技术指标计算**：从客户端简单近似 → 精确计算（EMA 需要递归）

### 后端

无改动。现有 API 已就绪：
- `GET /api/stock/kline/{code}?days=500` 直接返回 `daily_k` 表数据
- `GET /api/stock/price/{code}` 返回最新价

## 验收标准

- [ ] 输入 600519，展示近 2 年日 K 线蜡烛图
- [ ] MA5/10/20/60 四线清晰可见，颜色正确
- [ ] 成交量柱状图涨绿跌红
- [ ] MACD 副图：DIF 线、DEA 线、柱状图
- [ ] KDJ 副图：K/D/J 三线
- [ ] MACD/KDJ 切换按钮功能正常
- [ ] 日线/周线/月线周期切换正常
- [ ] Tooltip 悬停显示 OHLCV 数据
- [ ] 无 console 错误
- [ ] 后续新增指标只需注册 layer + 按钮，不改 KlineChart 主体

## 技术指标计算

### EMA (指数移动平均)
```
EMA(period) = price * α + EMA_prev * (1 - α)
α = 2 / (period + 1)
```

### MACD
```
EMA12, EMA26 = EMA(close, 12), EMA(close, 26)
DIF = EMA12 - EMA26
DEA = EMA(DIF, 9)
柱 = (DIF - DEA) * 2
```

### KDJ
```
RSV(n) = (close - low_n) / (high_n - low_n) * 100
K = 2/3 * K_prev + 1/3 * RSV
D = 2/3 * D_prev + 1/3 * K
J = 3 * K - 2 * D
```

### MA (简单移动平均)
```
MA(n) = sum(close[-n:]) / n
```

## 已知约束

- 周线/月线：前端对日线降采样（Chart.js 只渲染日线，周月按钮过滤数据）
- 数据和指标计算完全客户端（不调 LLM，保证离线可用）
- Chart.js 4.4 已加载，不新增依赖
