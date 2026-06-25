# K 线图表组件 · 实现计划

> **面向 AI 代理的工作者：** 使用 subagent-driven-development 或 executing-plans 逐任务实现。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 重构 KlineChart 为多图层架构，叠加 MA/成交量/MACD/KDJ，个股搜索展示近 2 年日线。

**架构：** 单文件前端修改（`web/index.html`），新增 JS 指标计算函数 + Chart.js 多图层插件，后端无改动。

**技术栈：** React 18 (CDN) + Chart.js 4.4 + Babel Standalone

---

### 任务 1：新增技术指标计算函数

**文件：**
- 修改：`web/index.html` — 在 `<script type="text/babel">` 顶部（React 组件之前）插入

插入位置：`const { useState, useEffect, useRef, useCallback, useMemo } = React;` 之后，第一个组件定义之前。

- [ ] **步骤 1：插入指标计算函数**

```javascript
// ═══ 技术指标计算（纯函数，无副作用） ═══

function calcMA(data, period) {
  // 简单移动平均，返回与 data 等长的数组，前 period-1 位为 null
  const result = new Array(data.length).fill(null);
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += data[j].close;
    result[i] = sum / period;
  }
  return result;
}

function calcEMA(data, period) {
  // 指数移动平均：EMA = price * α + EMA_prev * (1-α)，α = 2/(period+1)
  const result = new Array(data.length).fill(null);
  const alpha = 2 / (period + 1);
  // 初始值用第一个 SMA
  let sum = 0;
  for (let i = 0; i < period; i++) sum += data[i].close;
  let ema = sum / period;
  result[period - 1] = ema;
  for (let i = period; i < data.length; i++) {
    ema = data[i].close * alpha + ema * (1 - alpha);
    result[i] = ema;
  }
  return result;
}

function calcMACD(data) {
  const ema12 = calcEMA(data, 12);
  const ema26 = calcEMA(data, 26);
  const dif = new Array(data.length).fill(null);
  const dea = new Array(data.length).fill(null);
  const macd = new Array(data.length).fill(null);
  for (let i = 25; i < data.length; i++) {
    if (ema12[i] != null && ema26[i] != null) dif[i] = ema12[i] - ema26[i];
  }
  // DEA = EMA(dif, 9)，从第 33 位开始
  const alpha = 2 / (9 + 1);
  let deaVal = 0;
  let count = 0;
  for (let i = 25; i < data.length; i++) {
    if (dif[i] != null) {
      if (count < 9) { deaVal += dif[i]; count++; }
      else deaVal = dif[i] * alpha + deaVal * (1 - alpha);
      if (count === 9) { dea[i] = deaVal / 9; count++; } // SMA 作为种子
      else if (count > 9) dea[i] = deaVal;
    }
  }
  for (let i = 0; i < data.length; i++) {
    if (dif[i] != null && dea[i] != null) macd[i] = (dif[i] - dea[i]) * 2;
  }
  return { dif, dea, macd };
}

function calcKDJ(data, n = 9) {
  const k = new Array(data.length).fill(null);
  const d = new Array(data.length).fill(null);
  const j = new Array(data.length).fill(null);
  let kPrev = 50, dPrev = 50;
  for (let i = n - 1; i < data.length; i++) {
    let hh = -Infinity, ll = Infinity;
    for (let t = i - n + 1; t <= i; t++) {
      if (data[t].high > hh) hh = data[t].high;
      if (data[t].low < ll) ll = data[t].low;
    }
    const rsv = hh !== ll ? ((data[i].close - ll) / (hh - ll)) * 100 : 50;
    const kVal = 2/3 * kPrev + 1/3 * rsv;
    const dVal = 2/3 * dPrev + 1/3 * kVal;
    k[i] = kVal; d[i] = dVal; j[i] = 3 * kVal - 2 * dVal;
    kPrev = kVal; dPrev = dVal;
  }
  return { k, d, j };
}
```

- [ ] **步骤 2：验证函数可用（浏览器 console 快速测试）**

启动后端 `uvicorn api.main:app --port 8000`，然后浏览器打开 `http://localhost:3000`，在 console 里：

```javascript
fetch('http://localhost:8000/api/stock/kline/600519?days=500')
  .then(r => r.json()).then(d => {
    const ma5 = calcMA(d.data, 5);
    const { dif, dea, macd } = calcMACD(d.data);
    console.log('MA5 last:', ma5[ma5.length-1]);
    console.log('DIF last:', dif[dif.length-1]);
  });
```

预期：MA5 和 DIF 输出有效数字，非 null。

- [ ] **步骤 3：Commit**

```bash
git add web/index.html
git commit -m "feat: add JS technical indicators (MA/EMA/MACD/KDJ)"
```

---

### 任务 2：重构 KlineChart 为多图层架构

**文件：**
- 修改：`web/index.html` — KlineChart 函数体

- [ ] **步骤 1：替换 KlineChart 组件**

找到 `function KlineChart({ data })`（约第 1146 行），完整替换为：

```javascript
function KlineChart({ data, maPeriods = [5, 10, 20, 60], layers = ['candlestick'], subIndicator = 'macd', height = 400 }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const labels = (data || []).map(d => d.date?.slice(5) || '');
  const closes = (data || []).map(d => d.close);

  // 预计算指标
  const maLines = useMemo(() => {
    const result = {};
    for (const p of maPeriods) result[p] = calcMA(data, p);
    return result;
  }, [data, maPeriods]);

  const macdData = useMemo(() => data && data.length > 33 ? calcMACD(data) : null, [data]);
  const kdjData  = useMemo(() => data && data.length > 9  ? calcKDJ(data, 9) : null, [data]);

  // MA 颜色映射
  const maColors = { 5: '#9CA3AF', 10: '#F59E0B', 20: '#3B82F6', 60: '#8B5CF6' };

  // ── Chart.js 插件集 ──

  const candlePlugin = useMemo(() => ({
    id: 'candlestick',
    afterDraw(chart) {
      const { ctx, chartArea: { left, right, top, bottom }, scales: { x, y } } = chart;
      if (!data || !data.length) return;
      const barWidth = Math.max(2, Math.min(8, (right - left) / data.length * 0.6));
      data.forEach((d, i) => {
        const xPos = x.getPixelForValue(labels[i]);
        if (xPos < left || xPos > right) return;
        const openY = y.getPixelForValue(d.open);
        const closeY = y.getPixelForValue(d.close);
        const highY = y.getPixelForValue(d.high);
        const lowY = y.getPixelForValue(d.low);
        const isUp = d.close >= d.open;
        ctx.strokeStyle = isUp ? '#10B981' : '#EF4444';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(xPos, highY); ctx.lineTo(xPos, lowY); ctx.stroke();
        const bodyH = Math.max(1, Math.abs(closeY - openY));
        ctx.fillStyle = isUp ? '#10B981' : '#EF4444';
        ctx.fillRect(xPos - barWidth / 2, Math.min(openY, closeY), barWidth, bodyH);
      });
    },
  }), [data, labels]);

  const maPlugin = useMemo(() => ({
    id: 'maOverlay',
    afterDraw(chart) {
      const { ctx, chartArea: { left, right }, scales: { x, y } } = chart;
      for (const period of maPeriods) {
        const line = maLines[period];
        if (!line) continue;
        ctx.strokeStyle = maColors[period];
        ctx.lineWidth = 1.2;
        ctx.setLineDash(period === 60 ? [4, 2] : []);
        ctx.beginPath();
        let started = false;
        for (let i = 0; i < line.length; i++) {
          if (line[i] == null) continue;
          const xPos = x.getPixelForValue(labels[i]);
          if (xPos < left || xPos > right) continue;
          const yPos = y.getPixelForValue(line[i]);
          if (!started) { ctx.moveTo(xPos, yPos); started = true; }
          else ctx.lineTo(xPos, yPos);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }
    },
  }), [maPeriods, maLines, maColors, labels]);

  const volumePlugin = useMemo(() => ({
    id: 'volumeBars',
    afterDraw(chart) {
      const { ctx, chartArea: { left, right, bottom }, scales: { x } } = chart;
      if (!data || !data.length) return;
      const volMax = Math.max(...data.map(d => d.volume || 0));
      const volHeight = 60; // 成交量区域高度
      const volBase = bottom + 30;
      const barWidth = Math.max(1, Math.min(6, (right - left) / data.length * 0.5));
      data.forEach((d, i) => {
        const xPos = x.getPixelForValue(labels[i]);
        if (xPos < left || xPos > right) return;
        const h = volMax > 0 ? ((d.volume || 0) / volMax) * volHeight : 0;
        const isUp = d.close >= d.open;
        ctx.fillStyle = isUp ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)';
        ctx.fillRect(xPos - barWidth / 2, volBase - h, barWidth, h);
      });
      // 量比参考线
      const avgVol = data.reduce((s, d) => s + (d.volume || 0), 0) / data.length;
      const avgH = volMax > 0 ? (avgVol / volMax) * volHeight : 0;
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.setLineDash([2, 4]);
      ctx.beginPath(); ctx.moveTo(left, volBase - avgH); ctx.lineTo(right, volBase - avgH); ctx.stroke();
      ctx.setLineDash([]);
    },
  }), [data, labels]);

  const subPlugin = useMemo(() => {
    const sub = subIndicator === 'macd' ? macdData : kdjData;
    if (!sub) return { id: 'subEmpty', afterDraw() {} };
    return {
      id: 'subIndicator',
      afterDraw(chart) {
        const { ctx, chartArea: { left, right, top, bottom }, scales: { x } } = chart;
        const pad = 10;
        const subTop = bottom + 65;
        const subBottom = bottom + 150;
        const subH = subBottom - subTop;
        const mid = subTop + subH / 2;

        // 背景
        ctx.fillStyle = 'rgba(0,0,0,0.15)';
        ctx.fillRect(left, subTop, right - left, subH);

        if (subIndicator === 'macd') {
          const { dif, dea, macd } = sub;
          const allVals = [...dif.filter(v => v!=null), ...dea.filter(v => v!=null), ...macd.filter(v => v!=null)];
          const vMin = Math.min(...allVals), vMax = Math.max(...allVals);
          const vRange = vMax - vMin || 1;
          const yFromVal = v => subBottom - ((v - vMin) / vRange) * subH;

          // MACD 柱
          data.forEach((d, i) => {
            if (macd[i] == null) return;
            const xPos = x.getPixelForValue(labels[i]);
            if (xPos < left || xPos > right) return;
            const bw = Math.max(1, (right - left) / data.length * 0.5);
            const y0 = yFromVal(0), yV = yFromVal(macd[i]);
            ctx.fillStyle = macd[i] >= 0 ? 'rgba(16,185,129,0.6)' : 'rgba(239,68,68,0.6)';
            ctx.fillRect(xPos - bw / 2, Math.min(y0, yV), bw, Math.abs(yV - y0));
          });

          // DIF / DEA 线
          [{line: dif, color: '#3B82F6'}, {line: dea, color: '#F59E0B'}].forEach(({line, color}) => {
            ctx.strokeStyle = color; ctx.lineWidth = 1;
            ctx.beginPath(); let started = false;
            for (let i = 0; i < line.length; i++) {
              if (line[i] == null) continue;
              const xPos = x.getPixelForValue(labels[i]);
              if (xPos < left || xPos > right) continue;
              if (!started) { ctx.moveTo(xPos, yFromVal(line[i])); started = true; }
              else ctx.lineTo(xPos, yFromVal(line[i]));
            }
            ctx.stroke();
          });
        } else {
          // KDJ
          const { k, d, j } = sub;
          const allVals = [...k.filter(v=>v!=null), ...d.filter(v=>v!=null), ...j.filter(v=>v!=null)];
          const vMin = Math.min(...allVals), vMax = Math.max(...allVals, 100);
          const vRange = vMax - vMin || 1;
          const yFromVal = v => subBottom - ((v - vMin) / vRange) * subH;

          [{line: k, color: '#3B82F6'}, {line: d, color: '#F59E0B'}, {line: j, color: '#8B5CF6'}].forEach(({line, color}) => {
            ctx.strokeStyle = color; ctx.lineWidth = 1;
            ctx.beginPath(); let started = false;
            for (let i = 0; i < line.length; i++) {
              if (line[i] == null) continue;
              const xPos = x.getPixelForValue(labels[i]);
              if (xPos < left || xPos > right) continue;
              if (!started) { ctx.moveTo(xPos, yFromVal(line[i])); started = true; }
              else ctx.lineTo(xPos, yFromVal(line[i]));
            }
            ctx.stroke();
          });
        }
      },
    };
  }, [subIndicator, macdData, kdjData, data, labels]);

  // ── Chart 实例 ──
  useEffect(() => {
    if (!canvasRef.current || !data || !data.length) return;
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    const yMin = Math.min(...data.map(d => d.low)) * 0.995;
    const yMax = Math.max(...data.map(d => d.high)) * 1.005;
    const plugins = [candlePlugin, maPlugin, volumePlugin, subPlugin];

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ data: closes, borderColor: 'transparent', pointRadius: 0 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: {
            callbacks: {
              title: ctx => data[ctx[0].dataIndex]?.date || '',
              label: ctx => {
                const d = data[ctx.dataIndex];
                return d ? [`开: ${d.open}  高: ${d.high}`, `低: ${d.low}  收: ${d.close}`, `量: ${d.volume?.toLocaleString()}`] : [];
              },
            },
          },
        },
        scales: {
          x: { grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 10 }, maxTicksLimit: 8 } },
          y: { min: yMin, max: yMax, grid: { color: 'rgba(99,130,255,0.04)' }, ticks: { color: '#8892A8', font: { size: 11, family: 'JetBrains Mono' } } },
        },
      },
      plugins,
    });
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [data, labels, closes, candlePlugin, maPlugin, volumePlugin, subPlugin]);
  return <canvas ref={canvasRef} />;
}
```

- [ ] **步骤 2：验证编译无错误**

浏览器打开 `http://localhost:3000`，检查 console 无 React/JS 错误。

- [ ] **步骤 3：Commit**

```bash
git add web/index.html
git commit -m "refactor: KlineChart 多图层架构 (candlestick+MA+volume+MACD/KDJ)"
```

---

### 任务 3：ResearchPage 接入新 KlineChart

**文件：**
- 修改：`web/index.html` — ResearchPage 组件

- [ ] **步骤 1：修改 days 和 KlineChart 调用**

找到 ResearchPage 中 `apiFetch('/api/stock/kline/' + code + '?days=180')`（约第 988 行），将 `180` 改为 `500`。

找到 `<KlineChart data={filteredKline} />`（约第 1054 行），替换为：

```javascript
<KlineChart
  data={filteredKline}
  layers={['candlestick', 'ma', 'volume', 'macd']}
  subIndicator={subIndicator}
  height={500}
/>
```

在 ResearchPage 的 useState 区添加：
```javascript
const [subIndicator, setSubIndicator] = useState('macd');
```

- [ ] **步骤 2：添加副图切换按钮**

在 `{filteredKline ? <KlineChart ... /> : ` 之后、KlineChart 组件之前，添加：

```javascript
<div style={{display:'flex',gap:6,marginBottom:8}}>
  <button className={`btn btn-sm ${subIndicator==='macd'?'btn-primary':'btn-ghost'}`}
    onClick={()=>setSubIndicator('macd')} style={{fontSize:11,padding:'2px 10px'}}>MACD</button>
  <button className={`btn btn-sm ${subIndicator==='kdj'?'btn-primary':'btn-ghost'}`}
    onClick={()=>setSubIndicator('kdj')} style={{fontSize:11,padding:'2px 10px'}}>KDJ</button>
</div>
```

- [ ] **步骤 3：删除旧的客户端指标近似计算**

找到 ResearchPage 中计算 `ma5/ma20/ma60/macd/rsv` 的代码块（约第 994-1012 行），这段已被 KlineChart 内部的精确计算替代。删除以下代码：

```javascript
// 删除 start
const closes = kData.map(d => d.close);
const highs = kData.map(d => d.high);
const lows = kData.map(d => d.low);
const volumes = kData.map(d => d.volume);
const ma5 = closes.slice(-5).reduce((a,b)=>a+b,0)/5;
const ma20 = closes.slice(-20).reduce((a,b)=>a+b,0)/20;
// ... 到 setIndicators({...})
// 删除 end
```

同时删除 `indicators` 状态和对应的显示卡片，因为图表已可视化呈现。

- [ ] **步骤 4：验证完整流程**

浏览器打开 `http://localhost:3000`：
1. 进入「个股分析」页
2. 输入 `600519` 回车
3. 确认显示蜡烛图 + MA 四线 + 成交量柱 + MACD 副图
4. 点击 KDJ 按钮切换到 KDJ 副图
5. 悬停查看 tooltip
6. 确认 console 无错误

- [ ] **步骤 5：Commit**

```bash
git add web/index.html
git commit -m "feat: ResearchPage 接入新 KlineChart (days=500 + MACD/KDJ切换)"
```

---

### 任务 4：启动后端并端到端验证

- [ ] **步骤 1：启动后端**

```bash
cd C:\Users\Jeffery\私人文件\Agent\JefferyFinanceExpert
.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

- [ ] **步骤 2：端到端测试**

1. 浏览器 `http://localhost:3000` → 个股分析
2. 输入 `000858` 回车 → 五粮液 K 线
3. 输入 `300750` 回车 → 宁德时代 K 线
4. 切换到 KDJ 副图
5. 切换周线/月线

- [ ] **步骤 3：Commit 如有微调**

```bash
git add web/index.html && git commit -m "chore: e2e验证微调" && git push
```
（如无微调则跳过）

---

### 自检

1. **规格覆盖度**：所有设计规格需求均有对应任务 ✅
2. **占位符扫描**：无 TODO/待定 ✅
3. **类型一致性**：layer 名称 `candlestick/ma/volume/macd` 跨任务一致 ✅
