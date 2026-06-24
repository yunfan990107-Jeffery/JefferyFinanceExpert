#!/usr/bin/env python
"""一次性构建本地 K 线数据库（Baostock → SQLite）。

首次运行下载全市场 A 股历史日 K 线（1990年至今），约 4000+ 只股票。
数据量约 1.3GB，8线程预计 1-3 小时。

用法：
    python scripts/build_kline_db.py                          # 全量
    python scripts/build_kline_db.py --workers 12             # 12线程
    python scripts/build_kline_db.py --codes 600519,000001   # 只指定股票
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent / "cache" / "market_data.sqlite"

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS daily_k (
    code  TEXT NOT NULL,
    date  TEXT NOT NULL,
    open  REAL,
    high  REAL,
    low   REAL,
    close REAL,
    volume   REAL,
    amount   REAL,
    pct_chg  REAL,
    turnover REAL,
    PRIMARY KEY (code, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_k_code ON daily_k(code);
CREATE INDEX IF NOT EXISTS idx_daily_k_date ON daily_k(date);
"""


def _ensure_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(TABLE_DDL)
    conn.commit()
    conn.close()


def _get_all_codes() -> list[str]:
    """从 Baostock 获取全市场 A 股代码。"""
    import baostock as bs
    bs.login()
    rs = bs.query_all_stock()
    codes = []
    while (rs.error_code == '0') & rs.next():
        row = rs.get_row_data()
        code = row[0]  # sh.600519
        # 只取沪深 A 股（sh.6 / sz.0 / sz.3 / sz.002）
        if code.startswith(('sh.6', 'sz.0', 'sz.3', 'sz.002')):
            codes.append(code)
    bs.logout()
    return codes


def _to_plain_code(bs_code: str) -> str:
    """sh.600519 → 600519"""
    return bs_code.split(".")[-1] if "." in bs_code else bs_code


def download_one(bs_code: str) -> int:
    """下载单只股票全量日线（分年批次），写入 SQLite。返回写入条数。"""
    import baostock as bs
    total_rows = 0
    year_start = 1990
    year_end = 2027

    try:
        bs.login()
        for y in range(year_start, year_end):
            start = f"{y}-01-01"
            end = f"{y}-12-31"
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,volume,amount,pctChg,turn",
                    start_date=start, end_date=end,
                    frequency="d", adjustflag="2",
                )
                if rs.error_code != '0':
                    continue
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())
                if rows:
                    plain_code = _to_plain_code(bs_code)
                    conn = sqlite3.connect(str(DB_PATH))
                    conn.execute("BEGIN")
                    for r in rows:
                        conn.execute(
                            "INSERT OR REPLACE INTO daily_k VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [plain_code] + r,
                        )
                    conn.commit()
                    conn.close()
                    total_rows += len(rows)
            except Exception:
                continue  # 单年失败不阻塞
        bs.logout()
        return total_rows
    except Exception:
        return -1


def build(codes: list[str], workers: int = 8):
    _ensure_table()
    total = len(codes)
    done = 0
    rows = 0
    failed = 0
    t0 = time.time()

    print(f"开始构建本地 K 线数据库 · {total} 只股票 · {workers} 线程")
    print(f"数据库: {DB_PATH}")
    print()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, c): c for c in codes}
        for f in as_completed(futures):
            code = futures[f]
            done += 1
            try:
                n = f.result()
                if n > 0:
                    rows += n
                elif n == 0:
                    pass  # 无数据（如退市）
                else:
                    failed += 1
            except Exception:
                failed += 1

            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(
                    f"[{done}/{total}] {done/total*100:.0f}% | "
                    f"{rows}条 | {failed}失败 | "
                    f"{rate:.1f}只/s | 预计剩余 {eta/60:.0f}min"
                )

    elapsed = time.time() - t0
    print()
    print(f"完成！{rows} 条 K 线，{failed} 只失败，总耗时 {elapsed/60:.1f} 分钟")
    print(f"数据库大小: {DB_PATH.stat().st_size / 1024 / 1024:.0f} MB")


def main():
    parser = argparse.ArgumentParser(description="构建本地 K 线数据库")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码(如 600519,000001)")
    args = parser.parse_args()

    if args.codes:
        codes = [f"sh.{c}" if c.startswith("6") else f"sz.{c}" for c in args.codes.split(",")]
    else:
        print("获取全市场 A 股代码...")
        codes = _get_all_codes()
        print(f"共 {len(codes)} 只股票")

    build(codes, args.workers)


if __name__ == "__main__":
    main()
