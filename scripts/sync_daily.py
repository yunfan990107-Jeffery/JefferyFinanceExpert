#!/usr/bin/env python
"""每日增量同步脚本 — 只拉最近数据，INSERT OR REPLACE 自动去重。

覆盖：个股K线 / 指数K线 / 股票列表 / 概念K线 / 概念资金流

用法：
    python scripts/sync_daily.py           # 增量同步（默认2天）
    python scripts/sync_daily.py --days 5  # 补最近5天（防假期断更）
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed
import akshare as ak
from pytdx.hq import TdxHq_API

import threading as _th

_tdx_pool = _th.local()  # 线程局部 TDX 连接

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"
TDX_IP = "218.75.126.9"
TDX_PORT = 7709

# ── 指数定义 ──────────────────────────────────────────────────────
INDICES = [
    ("000001", 1),   # 上证指数
    ("399001", 0),   # 深证成指
    ("399006", 0),   # 创业板指
    ("000688", 1),   # 科创50
    ("000300", 1),   # 沪深300
    ("000016", 1),   # 上证50
]


def _db_conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))


def _latest_date(conn: sqlite3.Connection) -> str:
    """daily_k 中最新的日期。"""
    row = conn.execute("SELECT MAX(date) FROM daily_k").fetchone()
    return row[0] if row and row[0] else "2000-01-01"


def _all_stock_codes(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """返回所有个股代码及市场（排除399开头的指数）。"""
    rows = conn.execute(
        "SELECT DISTINCT code FROM daily_k WHERE code NOT GLOB '399*' ORDER BY code"
    ).fetchall()
    result = []
    for (code,) in rows:
        market = 1 if code.startswith(("6", "68")) else 0
        result.append((code, market))
    return result


# ═══════════════════════════════════════════════════════════════════
# 1. 个股 K 线
# ═══════════════════════════════════════════════════════════════════

def _tdx_connect() -> TdxHq_API:
    """获取线程局部的 TDX 连接。"""
    if not hasattr(_tdx_pool, "api"):
        api = TdxHq_API()
        api.connect(TDX_IP, TDX_PORT, time_out=10)
        _tdx_pool.api = api
    return _tdx_pool.api


def _download_one_stock(code: str, market: int, days: int) -> list[tuple]:
    """下载单只股票最近 days 条 K 线，返回 [(code, date, open, high, low, close, vol, amount), ...]"""
    api = _tdx_connect()
    try:
        bars = api.get_security_bars(9, market, code, 0, days + 1)
    except Exception:
        return []
    if not bars:
        return []
    result = []
    for b in bars:
        if b["year"] < 2024:
            continue
        d = f"{b['year']}-{b['month']:02d}-{b['day']:02d}"
        result.append((code, d, float(b["open"]), float(b["high"]), float(b["low"]),
                       float(b["close"]), float(b.get("vol", 0)), float(b.get("amount", 0))))
    return result


def sync_stock_kline(conn: sqlite3.Connection, api: TdxHq_API, days: int, workers: int = 8) -> int:
    """增量同步个股日K线（多线程）。"""
    codes = _all_stock_codes(conn)
    total = 0
    failed = 0
    print(f"  个股 K 线: {len(codes)} 只 ({workers}线程) …", end=" ", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_one_stock, c, m, days): c for c, m in codes}
        for f in as_completed(futures):
            code = futures[f]
            try:
                rows = f.result()
                if rows:
                    for r in rows:
                        conn.execute(
                            "INSERT OR REPLACE INTO daily_k VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], None, None),
                        )
                        total += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
    conn.commit()
    print(f"{total} 条" + (f", {failed} 失败" if failed else ""))
    return total


# ═══════════════════════════════════════════════════════════════════
# 2. 指数 K 线
# ═══════════════════════════════════════════════════════════════════

def sync_index_kline(conn: sqlite3.Connection, api: TdxHq_API, days: int) -> int:
    """增量同步指数日K线。"""
    total = 0
    print(f"  指数 K 线: {len(INDICES)} 只 …", end=" ", flush=True)

    for code, market in INDICES:
        try:
            bars = api.get_index_bars(9, market, code, 0, days + 1)
        except Exception:
            continue
        if not bars:
            continue
        for b in bars:
            if b["year"] < 2024 or b["year"] > 2027:
                continue
            d = f"{b['year']}-{b['month']:02d}-{b['day']:02d}"
            conn.execute(
                "INSERT OR REPLACE INTO daily_k VALUES (?,?,?,?,?,?,?,?,?,?)",
                (code, d, float(b["open"]), float(b["high"]), float(b["low"]),
                 float(b["close"]), float(b.get("vol", 0)), float(b.get("amount", 0)), None, None),
            )
            total += 1
    conn.commit()
    print(f"{total} 条")
    return total


# ═══════════════════════════════════════════════════════════════════
# 3. 股票列表
# ═══════════════════════════════════════════════════════════════════

def sync_stock_list(conn: sqlite3.Connection) -> int:
    """更新股票代码-名称映射（全量覆盖，15 秒）。"""
    print("  股票列表 …", end=" ", flush=True)
    try:
        df = ak.stock_zh_a_spot()
    except Exception:
        print("失败")
        return 0

    conn.execute("CREATE TABLE IF NOT EXISTS stock_list (code TEXT PRIMARY KEY, name TEXT)")
    conn.execute("DELETE FROM stock_list")
    for _, row in df.iterrows():
        conn.execute("INSERT OR REPLACE INTO stock_list VALUES (?,?)", (row["代码"], row["名称"]))
    conn.commit()
    print(f"{len(df)} 只")
    return len(df)


# ═══════════════════════════════════════════════════════════════════
# 4. 概念 K 线（最近 30 天）
# ═══════════════════════════════════════════════════════════════════

def sync_concept_kline(conn: sqlite3.Connection, workers: int = 8) -> int:
    """增量同步概念板块日K线（多线程）。"""
    today = date.today()
    start = (today - timedelta(days=30)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    try:
        names = ak.stock_board_concept_name_ths()
    except Exception:
        print("  概念 K 线: 列表获取失败")
        return 0

    concepts = names["name"].tolist()
    total = 0
    failed = 0
    print(f"  概念 K 线: {len(concepts)} 个 ({workers}线程) …", end=" ", flush=True)

    def _fetch_one(name: str) -> list[tuple]:
        try:
            df = ak.stock_board_concept_index_ths(symbol=name, start_date=start, end_date=end)
        except Exception:
            return []
        if df is None or df.empty:
            return []
        col_map = {"日期": "date", "开盘价": "open", "最高价": "high",
                   "最低价": "low", "收盘价": "close", "成交量": "volume", "成交额": "amount"}
        df = df.rename(columns=col_map)
        rows = []
        for _, row in df.iterrows():
            d = str(row.get("date", ""))[:10]
            if not d:
                continue
            rows.append((name, d,
                         float(row.get("open", 0) or 0), float(row.get("high", 0) or 0),
                         float(row.get("low", 0) or 0), float(row.get("close", 0) or 0),
                         float(row.get("volume", 0) or 0), float(row.get("amount", 0) or 0)))
        return rows

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, c): c for c in concepts}
        for f in as_completed(futures):
            try:
                rows = f.result()
                if rows:
                    for r in rows:
                        conn.execute(
                            "INSERT OR REPLACE INTO concept_kline VALUES (?,?,?,?,?,?,?,?)", r)
                        total += 1
            except Exception:
                failed += 1
    conn.commit()
    print(f"{total} 条" + (f", {failed} 失败" if failed else ""))
    return total


# ═══════════════════════════════════════════════════════════════════
# 5. 概念资金流
# ═══════════════════════════════════════════════════════════════════

def sync_concept_fund_flow(conn: sqlite3.Connection) -> int:
    """同步当日概念资金流向。"""
    print("  概念资金流 …", end=" ", flush=True)
    today_str = date.today().isoformat()
    try:
        df = ak.stock_fund_flow_concept()
    except Exception:
        print("失败")
        return 0
    if df is None or df.empty:
        print("无数据")
        return 0

    count = 0
    for _, row in df.iterrows():
        name = str(row.get("行业", ""))
        conn.execute(
            "INSERT OR REPLACE INTO concept_fund_flow VALUES (?,?,?,?,?,?,?,?)",
            (name, today_str, name,
             float(row.get("流入资金", 0) or 0), float(row.get("流出资金", 0) or 0),
             float(row.get("净额", 0) or 0), float(row.get("行业-涨跌幅", 0) or 0),
             int(row.get("公司家数", 0) or 0)),
        )
        count += 1
    conn.commit()
    print(f"{count} 条")
    return count


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

def sync(days: int = 2) -> None:
    t_start = time.time()
    conn = _db_conn()

    latest = _latest_date(conn)
    today = date.today().isoformat()
    print(f"每日增量同步 · {today}")
    print(f"  最新数据: {latest}" + (" (已是最新，仍强制拉取)" if latest >= today else ""))
    print()

    # 连 TDX
    api = TdxHq_API()
    if not api.connect(TDX_IP, TDX_PORT, time_out=10):
        print("❌ 通达信连接失败！")
        return

    # 1. 个股 K 线（多线程）
    t1 = time.time()
    n1 = sync_stock_kline(conn, api, days)
    t1 = time.time() - t1

    # 2. 指数 K 线
    t2 = time.time()
    n2 = sync_index_kline(conn, api, days)
    t2 = time.time() - t2

    api.disconnect()

    # 3. 股票列表
    t3 = time.time()
    n3 = sync_stock_list(conn)
    t3 = time.time() - t3

    # 4. 概念 K 线
    t4 = time.time()
    n4 = sync_concept_kline(conn, 8)
    t4 = time.time() - t4

    # 5. 概念资金流
    t5 = time.time()
    n5 = sync_concept_fund_flow(conn)
    t5 = time.time() - t5

    # 6. Z哥信号预计算
    t6 = time.time()
    n6 = sync_zg_signals(conn)
    t6 = time.time() - t6

    conn.close()

    elapsed = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"同步完成 · 总耗时 {elapsed:.0f}s")
    print(f"  个股K线:  {n1:>6} 条  ({t1:.0f}s)")
    print(f"  指数K线:  {n2:>6} 条  ({t2:.0f}s)")
    print(f"  股票列表: {n3:>6} 只  ({t3:.0f}s)")
    print(f"  概念K线:  {n4:>6} 条  ({t4:.0f}s)")
    print(f"  概念资金: {n5:>6} 条  ({t5:.0f}s)")
    print(f"  Z哥信号:  {n6:>6} 条  ({t6:.0f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="每日增量同步")
    parser.add_argument("--days", type=int, default=2, help="同步最近 N 天（默认2，覆盖周末+假期）")
    args = parser.parse_args()
    sync(args.days)


def sync_zg_signals(conn: sqlite3.Connection) -> int:
    """预计算 Z 哥 7 个策略规则，写入 zg_signals 表。"""
    from core.zg_screen import SCREENERS
    conn.execute("""CREATE TABLE IF NOT EXISTS zg_signals (
        code TEXT NOT NULL, rule_name TEXT NOT NULL, score REAL,
        details TEXT, date TEXT NOT NULL,
        PRIMARY KEY (code, rule_name, date))""")
    codes = [r[0] for r in conn.execute(
        "SELECT DISTINCT code FROM daily_k WHERE code NOT GLOB '399*' ORDER BY code").fetchall()]
    today = date.today().isoformat()
    total = 0
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
    return total


if __name__ == "__main__":
    main()
