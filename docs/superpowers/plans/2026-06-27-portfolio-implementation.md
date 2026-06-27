# 持仓看板 · 实现计划

> **面向 AI 代理的工作者：** 使用 executing-plans 逐任务实现。步骤使用复选框语法跟踪进度。

**目标：** 重构持仓看板：收益概览 + 持仓表格（新增/调整/删除）+ 目标偏离图

**架构：** Python 计算层(core/portfolio.py) → API(5端点) → React 前端(PortfolioPage重写) → SQLite 两张新表

**技术栈：** Python 3.13 + FastAPI + React 18 + SQLite

---

### 任务 1：数据库表 + 计算层

**文件：**
- 创建：`core/portfolio.py`
- 创建：`tests/test_portfolio.py`

**步骤 1：创建 portfolio_positions 和 portfolio_targets 表**

```python
# core/portfolio.py
"""持仓计算模块"""
import sqlite3
from pathlib import Path
from datetime import date

DB = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"

def _conn():
    return sqlite3.connect(str(DB))

def init_tables():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL,
            type TEXT NOT NULL, category TEXT NOT NULL,
            cost REAL, quantity REAL, unit TEXT DEFAULT '股',
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS portfolio_targets (
            category TEXT PRIMARY KEY, target_pct REAL
        );
        INSERT OR IGNORE INTO portfolio_targets VALUES ('进攻',50),('黄金',30),('现金',20);
    """)
    c.commit()
    c.close()
```

**步骤 2：编写计算函数**

```python
def get_portfolio():
    """返回持仓+目标+收益汇总"""
    c = _conn()
    today = date.today().isoformat()
    positions = []
    for row in c.execute("SELECT * FROM portfolio_positions ORDER BY category, code").fetchall():
        qty, cost = row[6], row[5]
        close = _latest_close(row[1]) if row[1] else (cost or 0)
        mkt_val = qty * close if close else qty * (cost or 0)
        pnl_pct = (close - cost) / cost * 100 if cost and cost > 0 and close else 0
        positions.append({"id":row[0],"code":row[1],"name":row[2],"type":row[3],"category":row[4],"cost":cost,"quantity":qty,"unit":row[7],"close":close,"market_value":round(mkt_val,2),"pnl_pct":round(pnl_pct,2)})
    total_val = sum(p["market_value"] for p in positions)
    total_cost = sum((p["quantity"] or 0) * (p["cost"] or 0) for p in positions)
    # 目标偏离
    targets = {r[0]:r[1] for r in c.execute("SELECT * FROM portfolio_targets").fetchall()}
    dev = []
    for cat, tgt in targets.items():
        cat_val = sum(p["market_value"] for p in positions if p["category"]==cat)
        actual_pct = round(cat_val/total_val*100,1) if total_val else 0
        dev.append({"category":cat,"target_pct":tgt,"actual_pct":actual_pct,"diff":round(actual_pct-tgt,1)})
    c.close()
    return {"positions":positions,"targets":dev,"summary":{"total_value":round(total_val,2),"total_cost":round(total_cost,2),"total_pnl":round(total_val-total_cost,2),"total_pnl_pct":round((total_val-total_cost)/total_cost*100,2) if total_cost else 0}}

def _latest_close(code):
    if not code: return None
    c = _conn()
    r = c.execute("SELECT close FROM daily_k WHERE code=? ORDER BY date DESC LIMIT 1",(code,)).fetchone()
    c.close()
    return r[0] if r else None
```

**步骤 3：运行验证**

```bash
python -c "from core.portfolio import init_tables, get_portfolio; init_tables(); print(get_portfolio())"
```

预期：`{'positions': [], 'targets': [...], 'summary': {...}}`

**步骤 4：Commit**

```bash
git add core/portfolio.py tests/test_portfolio.py
git commit -m "feat(task1): 持仓计算层 + 数据库表"
```

---

### 任务 2：API 端点

**文件：** 修改 `api/main.py`

**步骤 1：添加 5 个端点**

在 `# 健康检查` 之前插入：

```python
from core.portfolio import init_tables as _init_pt, get_portfolio as _get_pt, _conn

_init_pt()

@app.get("/api/portfolio")
def portfolio_get():
    return {"data": _get_pt()}

@app.post("/api/portfolio/add")
def portfolio_add(body: dict):
    c = _conn()
    c.execute("INSERT INTO portfolio_positions (code,name,type,category,cost,quantity,unit,created_at,updated_at) VALUES (?,?,?,?,?,?,?,date('now'),date('now'))",(body.get("code",""),body.get("name"),body.get("type"),body.get("category"),body.get("cost"),body.get("quantity"),body.get("unit","股")))
    c.commit(); c.close()
    return {"ok": True}

@app.post("/api/portfolio/adjust/{pid}")
def portfolio_adjust(pid: int, body: dict):
    action, qty, price = body.get("action"), body.get("quantity",0), body.get("price",0)
    c = _conn()
    row = c.execute("SELECT quantity, cost FROM portfolio_positions WHERE id=?",(pid,)).fetchone()
    if not row: c.close(); return {"ok": False, "error": "not found"}
    old_qty, old_cost = row
    if action == "buy": new_qty = old_qty + qty; new_cost = (old_cost*old_qty + price*qty)/new_qty if new_qty else old_cost
    else: new_qty = max(0, old_qty - qty); new_cost = old_cost
    c.execute("UPDATE portfolio_positions SET quantity=?, cost=?, updated_at=date('now') WHERE id=?",(new_qty,new_cost,pid))
    c.commit(); c.close()
    return {"ok": True}

@app.delete("/api/portfolio/{pid}")
def portfolio_delete(pid: int):
    c = _conn()
    c.execute("DELETE FROM portfolio_positions WHERE id=?",(pid,))
    c.commit(); c.close()
    return {"ok": True}

@app.put("/api/portfolio/targets")
def portfolio_targets(body: dict):
    c = _conn()
    for cat, pct in body.items():
        c.execute("INSERT OR REPLACE INTO portfolio_targets VALUES (?,?)",(cat,pct))
    c.commit(); c.close()
    return {"ok": True}
```

**步骤 2：测试端点**

```bash
curl -X POST http://localhost:8000/api/portfolio/add -H 'Content-Type: application/json' -d '{"code":"600519","name":"茅台","type":"股票","category":"进攻","cost":1680,"quantity":200}'
curl http://localhost:8000/api/portfolio
```

**步骤 3：Commit**

```bash
git add api/main.py
git commit -m "feat(task2): 持仓API — 5端点 (get/add/adjust/delete/targets)"
```

---

### 任务 3：前端 PortfolioPage 重写

**文件：** 修改 `web/index.html` — 替换 `function PortfolioPage()` (行 1569-1700)

**步骤 1：完整替换 PortfolioPage 组件**

```javascript
function PortfolioPage() {
  const [data, setData] = useState(null);
  const [adjust, setAdjust] = useState(null);

  useEffect(() => { load(); }, []);
  const load = async () => { const r = await apiFetch('/api/portfolio'); if (r) setData(r); };

  const doAdd = async (e) => { e.preventDefault(); const f = new FormData(e.target); await apiFetch('/api/portfolio/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:f.get('code'),name:f.get('name'),type:f.get('type'),category:f.get('cat'),cost:parseFloat(f.get('cost')),quantity:parseFloat(f.get('qty'))})}); load(); e.target.reset(); };
  const doAdjust = async () => { if (!adjust) return; await apiFetch('/api/portfolio/adjust/'+adjust.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(adjust)}); setAdjust(null); load(); };
  const doDelete = async (id) => { if (!confirm('确认删除？')) return; await apiFetch('/api/portfolio/'+id,{method:'DELETE'}); load(); };

  if (!data) return <div>加载中...</div>;
  const s = data.summary || {};

  return (
    <div>
      <h2>持仓看板</h2>
      {/* 收益概览 */}
      <div className="card" style={{marginBottom:12}}>
        <div style={{fontSize:10,color:'var(--muted)',marginBottom:8}}>收益概览</div>
        <div style={{display:'flex',gap:24}}>
          <Stat label="累计收益率" val={(s.total_pnl_pct||0).toFixed(2)+'%'} color={s.total_pnl_pct>=0?'var(--up)':'var(--down)'} />
          <Stat label="总市值" val={'¥'+((s.total_value||0)/10000).toFixed(1)+'万'} />
          <Stat label="总成本" val={'¥'+((s.total_cost||0)/10000).toFixed(1)+'万'} />
          <Stat label="累计盈亏" val={(s.total_pnl>=0?'+':'')+'¥'+Math.abs(s.total_pnl||0).toLocaleString()} color={s.total_pnl>=0?'var(--up)':'var(--down)'} />
        </div>
      </div>
      {/* 持仓表格 */}
      <div className="card" style={{marginBottom:12}}>
        <div style={{fontSize:10,color:'var(--muted)',marginBottom:8}}>当前持仓</div>
        <table style={{width:'100%',fontSize:12}}>
          <thead><tr style={{color:'var(--muted)',textAlign:'left'}}><th style={{padding:'4px 8px'}}>类型</th><th style={{padding:'4px 8px'}}>标的</th><th style={{padding:'4px 8px'}}>成本</th><th style={{padding:'4px 8px'}}>持仓</th><th style={{padding:'4px 8px'}}>现价</th><th style={{padding:'4px 8px'}}>市值</th><th style={{padding:'4px 8px'}}>盈亏</th><th></th></tr></thead>
          <tbody>
            {(data.positions||[]).map(p => (
              <tr key={p.id} style={{borderBottom:'1px solid rgba(37,42,54,0.5)'}}>
                <td style={{padding:'4px 8px'}}><Tag cat={p.category} /></td>
                <td style={{padding:'4px 8px'}}><span style={{color:'var(--amber)'}}>{p.code||p.name}</span> <span style={{fontSize:10,color:'var(--muted)'}}>{p.code?p.name:''}</span></td>
                <td style={{padding:'4px 8px',fontFamily:'var(--font-mono)',fontSize:11}}>{p.cost?p.cost.toFixed(2):'—'}</td>
                <td style={{padding:'4px 8px',fontFamily:'var(--font-mono)',fontSize:11}}>{p.quantity}{p.unit}</td>
                <td style={{padding:'4px 8px',fontFamily:'var(--font-mono)',fontSize:11}}>{p.close?p.close.toFixed(2):'—'}</td>
                <td style={{padding:'4px 8px',fontFamily:'var(--font-mono)',fontSize:11}}>{p.market_value?p.market_value.toLocaleString():'—'}</td>
                <td style={{padding:'4px 8px',fontFamily:'var(--font-mono)',fontSize:11,color:p.pnl_pct>=0?'var(--up)':'var(--down)'}}>{p.pnl_pct>=0?'+':''}{p.pnl_pct?.toFixed(1)}%</td>
                <td style={{padding:'4px 8px'}}>
                  <button onClick={()=>setAdjust({id:p.id,name:p.name,action:'buy',quantity:0,price:0})} style={{...btnSm,border:'none',background:'var(--primary)',color:'#fff',borderRadius:3,marginRight:3}}>+</button>
                  <button onClick={()=>setAdjust({id:p.id,name:p.name,action:'sell',quantity:0,price:0})} style={{...btnSm,border:'1px solid rgba(239,68,68,0.3)',color:'var(--down)',background:'transparent',borderRadius:3,marginRight:3}}>-</button>
                  <button onClick={()=>doDelete(p.id)} style={{border:'none',background:'transparent',color:'#444',cursor:'pointer',fontSize:12}}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
        {/* 目标偏离 */}
        <div className="card">
          <div style={{fontSize:10,color:'var(--muted)',marginBottom:8}}>目标 vs 实际</div>
          {(data.targets||[]).map(t => (
            <div key={t.category} style={{marginBottom:10}}>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:11,marginBottom:2}}>
                <span><Tag cat={t.category} /> <span>{t.category}</span></span>
                <span style={{fontFamily:'var(--font-mono)',fontSize:10}}>{t.actual_pct}% / {t.target_pct}% <span style={{color:Math.abs(t.diff)>10?'var(--down)':'var(--muted)'}}>{t.diff>=0?'+':''}{t.diff}%</span></span>
              </div>
              <div style={{height:6,borderRadius:3,background:'var(--border)',position:'relative'}}>
                <div style={{height:6,borderRadius:3,background:'var(--primary)',width:t.actual_pct+'%',position:'absolute'}}></div>
                <div style={{position:'absolute',left:t.target_pct+'%',top:-2,width:2,height:10,background:'var(--amber)',borderRadius:1}}></div>
              </div>
            </div>
          ))}
        </div>
        {/* 新增持仓 */}
        <div className="card">
          <div style={{fontSize:10,color:'var(--muted)',marginBottom:8}}>新增持仓</div>
          <form onSubmit={doAdd} style={{display:'flex',flexDirection:'column',gap:8}}>
            <div style={{display:'flex',gap:8}}>
              <select name="type" style={inputStyle}><option>股票</option><option>ETF</option><option>黄金</option><option>债券</option><option>现金</option></select>
              <input name="code" placeholder="代码" style={{...inputStyle,flex:1}} />
              <input name="name" placeholder="名称" style={{...inputStyle,flex:1}} />
            </div>
            <div style={{display:'flex',gap:8}}>
              <select name="cat" style={inputStyle}><option>进攻</option><option>黄金</option><option>红利低波</option><option>现金</option></select>
              <input name="cost" placeholder="成本价" style={{...inputStyle,flex:1}} />
              <input name="qty" placeholder="数量" style={{...inputStyle,flex:1}} />
              <button type="submit" style={{...btnStyle,flex:0.6}}>新增</button>
            </div>
          </form>
        </div>
      </div>
      {/* 调整弹窗 */}
      {adjust && (
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:100}} onClick={()=>setAdjust(null)}>
          <div style={{background:'var(--surface)',border:'1px solid var(--border)',borderRadius:8,padding:16,minWidth:300}} onClick={e=>e.stopPropagation()}>
            <div style={{marginBottom:10}}>调整 {adjust.name}</div>
            <div style={{display:'flex',gap:8,marginBottom:10}}>
              <select value={adjust.action} onChange={e=>setAdjust({...adjust,action:e.target.value})} style={inputStyle}>
                <option value="buy">买入</option><option value="sell">卖出</option>
              </select>
              <input type="number" placeholder="数量" value={adjust.quantity||''} onChange={e=>setAdjust({...adjust,quantity:parseFloat(e.target.value)||0})} style={{...inputStyle,flex:1}} />
              <input type="number" placeholder="价格" value={adjust.price||''} onChange={e=>setAdjust({...adjust,price:parseFloat(e.target.value)||0})} style={{...inputStyle,flex:1}} />
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button onClick={()=>setAdjust(null)} style={{...btnStyle,background:'transparent',border:'1px solid var(--border)',color:'var(--muted)'}}>取消</button>
              <button onClick={doAdjust} style={btnStyle}>确认</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
// 辅助组件
function Stat({label,val,color}) { return <div style={{flex:1}}><div style={{fontFamily:'var(--font-mono)',fontSize:16,fontWeight:700,color:color||'var(--text)'}}>{val}</div><div style={{fontSize:10,color:'var(--muted)'}}>{label}</div></div>; }
function Tag({cat}) { const m={进攻:'attack',黄金:'gold',红利低波:'dividend',现金:'cash'}; const c=m[cat]||'attack'; return <span className={'tag tag-'+c} style={{display:'inline-block',padding:'1px 6px',borderRadius:3,fontSize:9}}>{cat}</span>; }
const inputStyle = {background:'#0B0E14',border:'1px solid var(--border)',color:'var(--text)',padding:'5px 8px',borderRadius:4,fontSize:11};
const btnStyle = {background:'var(--primary)',color:'#fff',border:'none',padding:'6px 14px',borderRadius:4,fontSize:11,cursor:'pointer'};
const btnSm = {padding:'3px 7px',fontSize:10,cursor:'pointer'};
```

**步骤 2：验证**

重启前端，浏览器打开 → 持仓看板 → 确认四个分区正常渲染

**步骤 3：Commit**

```bash
git add web/index.html
git commit -m "feat(task3): 持仓看板重写 — 收益概览+持仓表格+目标偏离+新增+调整弹窗"
```

---

### 任务 4：端到端验证

**步骤 1：重启后端 + 前端**

```bash
uvicorn api.main:app --port 8000 &
npx serve web -l 3000 &
```

**步骤 2：测试流程**

1. 打开 localhost:3000 → 持仓看板
2. 新增持仓：类型=股票，代码=600519，名称=茅台，成本=1680，数量=200
3. 确认表格显示
4. 点击 + 调整：买入 100 股 @1700
5. 确认数量变为 300
6. 点击 ✕ 删除

**步骤 3：Commit 微调**

```bash
# 如有微调
git add web/index.html && git commit -m "chore: e2e验证微调"
```

---

### 自检

1. 规格覆盖度：所有 4 个验收标准均有对应任务 ✅
2. 占位符扫描：无 TODO/待定 ✅
3. 类型一致性：API 字段与前端消费一致 ✅
