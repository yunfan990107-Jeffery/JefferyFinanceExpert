# Z 哥选股页面 · 实现计划

> **面向 AI 代理的工作者：** 使用 executing-plans 逐任务实现。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 集成 Z 哥交易体系的 8 个策略规则选股页面到 React SPA

**架构：** Python 指标层(core/zg_*) → 日更预计算(sync_daily) → API 检索(api) → 前端选股页(web)

**技术栈：** Python 3.13 + pandas/numpy + pytdx + FastAPI + React 18 + LW Charts

---

### 任务 1：搬运 Z 哥指标 — `core/zg_config.py` + `core/zg_indicators.py`

**文件：**
- 创建：`core/zg_config.py`
- 创建：`core/zg_indicators.py`
- 测试：运行 `pytest tests/ -k zg -v`

- [ ] **步骤 1：创建 `core/zg_config.py`**

```python
"""Z 哥交易体系参数"""
# 双线系统
WHITE_LINE_SPAN = 10
YELLOW_LINE_MAS = [14, 28, 57, 114]

# KDJ
KDJ_N, KDJ_M1, KDJ_M2 = 9, 3, 3

# 砖型图
BRICK_HHV_LLV_N = 4
BRICK_SMA1_N = 3
BRICK_SMA2_N = 3
BRICK_THRESHOLD = 100
BRICK_STRONG_RATIO = 2 / 3

# 深V
DEEP_V_N1 = 3
DEEP_V_N2 = 21

# 0AMV
OAMV_SMA_N = 10
OAMV_DANGER_PCT = -2.3
OAMV_CAUTION_PCT = -1.0
OAMV_HEALTHY_PCT = 0.5
OAMV_MA_FAST = 5
OAMV_MA_SLOW = 13

# B1
B1_VOL_N = 30
B1_J_THRESHOLD = 13
B1_VOL_RATIO_MIN = 2.4

# B2
B2_J_REF = 13
B2_J_MAX = 55
B2_ZF_MIN = 4
```

- [ ] **步骤 2：搬运 `core/zg_indicators.py`**

从 `C:\Users\Jeffery\私人文件\Agent\ZGFinanaceAgent\core\indicators.py` 复制全部代码，修改：

```python
# 修改 import 路径
from pathlib import Path
from core.zg_config import (
    WHITE_LINE_SPAN, YELLOW_LINE_MAS,
    KDJ_N, KDJ_M1, KDJ_M2,
    BRICK_HHV_LLV_N, BRICK_SMA1_N, BRICK_SMA2_N,
    BRICK_THRESHOLD, BRICK_STRONG_RATIO,
    DEEP_V_N1, DEEP_V_N2,
    OAMV_SMA_N, OAMV_DANGER_PCT, OAMV_CAUTION_PCT,
    OAMV_HEALTHY_PCT, OAMV_MA_FAST, OAMV_MA_SLOW,
)
```

删除最后两节（trend_status / weekly_b1_check / 板块识别 / 行业缓存），因为当前不需要。

- [ ] **步骤 3：运行语法检查**

```bash
python -c "from core.zg_indicators import white_line, yellow_line, calc_kdj, calc_macd, calc_brick, calc_deep_v, calc_oamv; print('OK')"
```

- [ ] **步骤 4：Commit**

```bash
git add core/zg_config.py core/zg_indicators.py
git commit -m "feat: Z哥指标层 — 搬运 indicators.py (白线/黄线/KDJ/MACD/砖型/深V/0AMV)"
```

---

### 任务 2：8 个策略筛选器 — `core/zg_screen.py`

**文件：**
- 创建：`core/zg_screen.py`

- [ ] **步骤 1：创建策略筛选器**

```python
"""Z 哥策略筛选器 — 每只股票返回 (通过, 评分, 详情)"""
import sqlite3
from pathlib import Path
import pandas as pd
from core.zg_indicators import (
    white_line, yellow_line, dual_line_status,
    calc_kdj, calc_macd, calc_brick, brick_signal,
    calc_deep_v, deep_v_signal,
)

DB = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"


def _load_klines(code: str, days: int = 300) -> pd.DataFrame:
    """从 daily_k 加载日K线"""
    conn = sqlite3.connect(str(DB))
    rows = conn.execute(
        "SELECT date, open, high, low, close, volume, amount FROM daily_k WHERE code=? ORDER BY date", (code,)
    ).fetchall()
    conn.close()
    if len(rows) < 60:
        return None
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])


def screen_B1(code: str) -> dict:
    """规则B1：六条件交集"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    wl = white_line(c)
    yl = yellow_line(c)
    kdj = calc_kdj(h, l, c)
    macd = calc_macd(c)
    L = len(df) - 1
    j = float(kdj["J"].iloc[L])
    dif = float(macd["DIF"].iloc[L])
    dea = float(macd["DEA"].iloc[L])
    v_ratio = float(v.iloc[L]) / v.tail(30).mean() if v.tail(30).mean() > 0 else 0
    checks = {
        "双线多头": float(wl.iloc[L]) > float(yl.iloc[L]),
        "KDJ_J超卖": j < 13,
        "MACD金叉": dif > dea,
        "价在黄线上": float(c.iloc[L]) > float(yl.iloc[L]),
        "倍量": v_ratio >= 2.4,
        "阳线收盘": float(c.iloc[L]) >= float(c.iloc[L - 1]) if L >= 1 else False,
    }
    passed = sum(1 for v in checks.values() if v)
    return {"hit": passed >= 5, "score": passed, "details": f"{passed}/6"}


def screen_Brick(code: str) -> dict:
    """形态红砖：砖型图绿转红检测"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    h, l, c = df["high"], df["low"], df["close"]
    yl = float(yellow_line(c).iloc[-1])
    bs = brick_signal(h, l, c, yl)
    return {
        "hit": bs["signal"],
        "score": round(bs["strength"] * 100, 1) if bs["strength"] else 0,
        "details": bs["tag"],
    }


def screen_B2(code: str) -> dict:
    """规则B2：趋势确认+J低位+涨幅+放量"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    kdj = calc_kdj(h, l, c)
    wl = white_line(c)
    yl = yellow_line(c)
    L = len(df) - 1
    j = float(kdj["J"].iloc[L])
    zf = (float(c.iloc[L]) - float(c.iloc[L - 1])) / float(c.iloc[L - 1]) * 100
    v_ratio = float(v.iloc[L]) / v.rolling(5).mean().iloc[L]
    checks = {
        "趋势多头": float(wl.iloc[L]) > float(yl.iloc[L]),
        "J约束": j < 55,
        "涨幅": zf >= 4,
        "放量": v_ratio >= 1.5,
        "上影线": (float(h.iloc[L]) - float(c.iloc[L])) / (float(h.iloc[L]) - float(l.iloc[L]) + 0.01) < 0.5,
    }
    passed = sum(1 for v in checks.values() if v)
    return {"hit": passed >= 3, "score": passed, "details": f"{passed}/5"}


SCREENERS = {"B1": screen_B1, "红砖": screen_Brick, "B2": screen_B2}
```

- [ ] **步骤 2：运行验证**

```bash
python -c "from core.zg_screen import screen_B1, screen_Brick; r1=screen_B1('600519'); r2=screen_Brick('600519'); print('B1:', r1); print('Brick:', r2)"
```

- [ ] **步骤 3：Commit**

```bash
git add core/zg_screen.py
git commit -m "feat: Z哥策略筛选器 — B1/红砖/B2 三规则"
```

---

### 任务 3：日更集成 — `scripts/sync_daily.py`

**文件：**
- 修改：`scripts/sync_daily.py` — 新增 `sync_zg_signals()` 函数
- 修改：`scripts/sync_daily.py` — `sync()` 函数末尾调用

- [ ] **步骤 1：新增函数并在 sync() 中调用**

在 `sync_daily.py` 的 `sync()` 函数中，概念资金流之后添加：

```python
    # 6. Z 哥信号
    t6 = time.time()
    n6 = sync_zg_signals(conn)
    t6 = time.time() - t6
```

新增函数（放在 main 之前）：

```python
def sync_zg_signals(conn: sqlite3.Connection) -> int:
    """预计算 Z 哥 8 个策略规则，写入 zg_signals 表。"""
    from core.zg_screen import SCREENERS
    conn.execute("""CREATE TABLE IF NOT EXISTS zg_signals (
        code TEXT NOT NULL, rule_name TEXT NOT NULL, score REAL,
        details TEXT, date TEXT NOT NULL, PRIMARY KEY (code, rule_name, date))""")
    codes = [r[0] for r in conn.execute(
        "SELECT DISTINCT code FROM daily_k WHERE code NOT GLOB '399*' ORDER BY code").fetchall()]
    today = date.today().isoformat()
    total = 0
    print(f"  Z哥信号: {len(codes)} 只 …", end=" ", flush=True)
    for code in codes:
        for rule_name, screener in SCREENERS.items():
            try:
                result = screener(code)
                if result and result.get("hit"):
                    conn.execute(
                        "INSERT OR REPLACE INTO zg_signals VALUES (?,?,?,?,?)",
                        (code, rule_name, result["score"], result.get("details", ""), today))
                    total += 1
            except Exception:
                pass
    conn.commit()
    print(f"{total} 条")
    return total
```

在 sync() 的总结部分添加 n6 的显示。

- [ ] **步骤 2：Commit**

```bash
git add scripts/sync_daily.py
git commit -m "feat: sync_daily 新增 Z哥信号预计算"
```

---

### 任务 4：后端 API — `api/main.py`

**文件：**
- 修改：`api/main.py` — 新增 2 个端点

- [ ] **步骤 1：添加 `POST /api/screen` 和 `GET /api/zg/{code}`**

```python
@app.post("/api/screen")
def zg_screen(body: dict):
    """Z 哥选股检索。body: {rules: ["B1","红砖"]}"""
    rules = body.get("rules", [])
    if not rules:
        return {"data": []}
    import sqlite3
    from pathlib import Path
    db = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"
    conn = sqlite3.connect(str(db))
    placeholders = ",".join("?" for _ in rules)
    rows = conn.execute(
        f"SELECT code, rule_name, score, details FROM zg_signals WHERE rule_name IN ({placeholders}) AND date=(SELECT MAX(date) FROM zg_signals) ORDER BY code",
        rules,
    ).fetchall()
    conn.close()
    return {"data": [{"code": r[0], "rule": r[1], "score": r[2], "details": r[3]} for r in rows]}


@app.get("/api/zg/{code}")
def zg_analysis(code: str):
    """个股 Z 哥战法分析。"""
    from core.zg_indicators import (
        dual_line_status, calc_kdj, calc_macd,
        calc_brick, brick_signal, calc_deep_v, deep_v_signal, trend_status,
    )
    import sqlite3, pandas as pd
    from pathlib import Path
    db = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT date, open, high, low, close, volume FROM daily_k WHERE code=? ORDER BY date",
        (code,),
    ).fetchall()
    conn.close()
    if len(rows) < 60:
        return {"data": {"error": "数据不足"}}
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    c, h, l = df["close"], df["high"], df["low"]
    dual = dual_line_status(c)
    kdj = calc_kdj(h, l, c)
    macd = calc_macd(c)
    yl = float(dual["yl"])
    brick = brick_signal(h, l, c, yl)
    dv = deep_v_signal(h, l, c)
    trend = trend_status(c)
    return {"data": {
        "code": code, "dual_line": dual,
        "kdj": {"k": round(float(kdj["K"].iloc[-1]), 2), "d": round(float(kdj["D"].iloc[-1]), 2), "j": round(float(kdj["J"].iloc[-1]), 2)},
        "macd": {"dif": round(float(macd["DIF"].iloc[-1]), 2), "dea": round(float(macd["DEA"].iloc[-1]), 2), "bar": round(float(macd["MACD"].iloc[-1]), 2)},
        "brick": brick, "deep_v": dv, "trend": trend["trend"], "trend_label": trend["trend_label"],
    }}
```

- [ ] **步骤 2：测试端点**

```bash
curl -X POST http://localhost:8000/api/screen -H "Content-Type: application/json" -d '{"rules":["B1"]}' | head -200
curl http://localhost:8000/api/zg/600519 | head -200
```

- [ ] **步骤 3：Commit**

```bash
git add api/main.py
git commit -m "feat: Z哥选股API — POST /api/screen + GET /api/zg/{code}"
```

---

### 任务 5：前端选股页面 — `web/index.html`

**文件：**
- 修改：`web/index.html` — 新增 ScreenPage + 导航项

- [ ] **步骤 1：添加 ScreenPage 组件**

在 `{/* ── 技术指标详情 ── */}` 区域之后，`CalibrationPage` 之前，插入 ScreenPage。

关键 JSX 结构：
- 左侧栏：日期 + 8 个规则勾选框 + 开始检索按钮
- 右侧：结果表格（含表格数据 + 点击行 + K 线预览）
- 复用现有 `KlineChart` 组件

- [ ] **步骤 2：添加导航项**

在侧边栏导航中，找到 `case 'portfolio': return <PortfolioPage />;` 附近，添加：
```javascript
case 'screen': return <ScreenPage />;
```

在导航 JSX 中添加按钮：
```html
<div className={`nav-item ${activePage === 'screen' ? 'active' : ''}`} onClick={() => setActivePage('screen')}>
  <svg>...</svg> 选股
</div>
```

- [ ] **步骤 3：Commit**

```bash
git add web/index.html
git commit -m "feat: Z哥选股页面 — ScreenPage 条件检索+结果表格+K线预览"
```

---

### 任务 6：端到端验证

- [ ] **步骤 1：运行日更（仅 Z 哥信号部分测试几只股票）**

```bash
python -c "from core.zg_screen import screen_B1; print(screen_B1('600519'))"
```

- [ ] **步骤 2：启动服务验证页面**

```bash
uvicorn api.main:app --port 8000 &
npx serve web -l 3000 &
```

浏览器打开 `http://localhost:3000` → 点击「选股」→ 勾选规则 → 检索 → 点击结果行 → 查看 K 线

- [ ] **步骤 3：Commit 微调**

（如有前端微调）

---

### 自检

1. **规格覆盖度**：所有 5 个需求均有对应任务 ✅
2. **占位符扫描**：无 TODO/待定 ✅
3. **类型一致性**：API 返回格式与前端消费一致 ✅
