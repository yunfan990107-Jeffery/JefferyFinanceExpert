""""""
import sqlite3
from pathlib import Path
DB = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"
def _conn(): return sqlite3.connect(str(DB))
def init_tables():
    c=_conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, name TEXT NOT NULL,
            type TEXT NOT NULL, category TEXT NOT NULL,
            cost REAL, quantity REAL, unit TEXT DEFAULT '股',
            created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS portfolio_targets (
            category TEXT PRIMARY KEY, target_pct REAL);
        INSERT OR IGNORE INTO portfolio_targets VALUES ('进攻',50),('黄金',30),('现金',20);
    """)
    c.commit();c.close()
def _latest_close(code):
    if not code: return None
    c=_conn()
    r=c.execute("SELECT close FROM daily_k WHERE code=? ORDER BY date DESC LIMIT 1",(code,)).fetchone()
    c.close()
    return r[0] if r else None
def get_portfolio():
    c=_conn()
    pos=[]
    for row in c.execute("SELECT * FROM portfolio_positions ORDER BY category, code").fetchall():
        pid,code,name,typ,cat,cost,qty,unit,_,_=row
        close=_latest_close(code) if code else (cost or 0)
        mkt=qty*close if close else qty*(cost or 0)
        pnl_pct=(close-cost)/cost*100 if cost and cost>0 and close else 0
        pos.append(dict(id=pid,code=code,name=name,type=typ,category=cat,cost=cost,quantity=qty,unit=unit,close=close,market_value=round(mkt,2),pnl_pct=round(pnl_pct,2)))
    tv=sum(p['market_value'] for p in pos)
    tc=sum((p['quantity']or 0)*(p['cost']or 0) for p in pos)
    tgts={r[0]:r[1] for r in c.execute("SELECT * FROM portfolio_targets").fetchall()}
    dev=[]
    for cat,tgt in tgts.items():
        cv=sum(p['market_value'] for p in pos if p['category']==cat)
        ap=round(cv/tv*100,1) if tv else 0
        dev.append(dict(category=cat,target_pct=tgt,actual_pct=ap,diff=round(ap-tgt,1)))
    c.close()
    return dict(positions=pos,targets=dev,summary=dict(total_value=round(tv,2),total_cost=round(tc,2),total_pnl=round(tv-tc,2),total_pnl_pct=round((tv-tc)/tc*100,2) if tc else 0))
