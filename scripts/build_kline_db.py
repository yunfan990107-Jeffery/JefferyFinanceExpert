#!/usr/bin/env python
"""一次性构建本地 K 线数据库（通达信 pytdx → SQLite）。

直连通达信行情服务器（TCP socket，不走 HTTP），速度快、不受东方财富/Baostock 封禁影响。

用法：
    python scripts/build_kline_db.py                          # 全量，8线程
    python scripts/build_kline_db.py --years 2                # 最近 N 年
    python scripts/build_kline_db.py --codes 600519,000001    # 指定股票
    python scripts/build_kline_db.py --years 2 --workers 4    # 4 线程
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"

# ── 通达信服务器列表（按优先级）───────────────────────────────────
TDX_SERVERS = [
    ("218.75.126.9", 7709),
    ("119.147.212.81", 7709),
    ("120.76.152.2", 7709),
    ("47.103.48.45", 7709),
    ("113.105.73.88", 7709),
]

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

# ── 真正的 A 股代码前缀 ──────────────────────────────────────────
A_SHARE_PREFIXES = ("600", "601", "603", "605", "688",  # 上海
                    "000", "001", "002", "003", "300", "301")  # 深圳


def _ensure_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(TABLE_DDL)
    conn.commit()
    conn.close()


# ── 线程局部通达信连接 ────────────────────────────────────────────
import threading as _threading

_tdx_local = _threading.local()


def _tdx_connect(server_ip: str = ""):
    """建立当前线程的通达信连接（复用）。"""
    if not hasattr(_tdx_local, "api"):
        from pytdx.hq import TdxHq_API
        api = TdxHq_API()
        # 尝试指定服务器或遍历列表
        if server_ip:
            ok = api.connect(server_ip, 7709, time_out=5)
            if not ok:
                raise ConnectionError(f"通达信 {server_ip}:7709 连接失败")
        else:
            ok = False
            for ip, port in TDX_SERVERS:
                try:
                    ok = api.connect(ip, port, time_out=5)
                    if ok:
                        break
                except Exception:
                    continue
            if not ok:
                raise ConnectionError("所有通达信服务器连接失败")
        _tdx_local.api = api
    return _tdx_local.api


def _tdx_disconnect_all():
    if hasattr(_tdx_local, "api"):
        try:
            _tdx_local.api.disconnect()
        except Exception:
            pass
        del _tdx_local.api


# ── 代码列表 ──────────────────────────────────────────────────────

def _get_all_codes(server_ip: str = "") -> list[str]:
    """从通达信获取全市场 A 股代码。"""
    api = _tdx_connect(server_ip)
    codes = []
    for market, skip_until in [(0, 0), (1, 20000)]:  # 沪市A股从 25000 开始
        total = api.get_security_count(market)
        for start in range(skip_until, total, 1000):
            batch = api.get_security_list(market, start)
            if not batch:
                continue
            for item in batch:
                c = item.get("code", "")
                if c.startswith(A_SHARE_PREFIXES) and len(c) == 6:
                    codes.append(c)
    return sorted(set(codes))


# ── 单只下载 ──────────────────────────────────────────────────────

def download_one(code: str, years: int = 0, server_ip: str = "") -> int:
    """用通达信下载单只股票日线，写入 SQLite。返回写入条数。

    years=0 表示全量，years=N 表示最近 N 年（按自然年算）。
    """
    try:
        api = _tdx_connect(server_ip)
    except Exception as e:
        print(f"  [{code}] 连接失败: {e}", file=sys.stderr, flush=True)
        return -1

    # 确定市场
    if code.startswith(("6", "68")):
        market = 1   # 上海
    else:
        market = 0   # 深圳

    # 请求足够多的 K 线（全量 8000 条覆盖 1990 至今）
    if years > 0:
        # 每年约 250 个交易日
        count = years * 260
    else:
        count = 8000

    try:
        bars = api.get_security_bars(9, market, code, 0, count)
    except Exception as e:
        print(f"  [{code}] 请求失败: {e}", file=sys.stderr, flush=True)
        return -1

    if not bars:
        return 0

    # 按年份过滤（如果需要）
    if years > 0:
        cutoff_year = 2026 - years + 1  # 针对 2026 年
        bars = [b for b in bars if b["year"] >= cutoff_year]

    if not bars:
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN")
        count = 0
        for b in bars:
            d = f"{b['year']}-{b['month']:02d}-{b['day']:02d}"
            o = float(b["open"])
            h = float(b["high"])
            l = float(b["low"])
            c = float(b["close"])
            vol = float(b.get("vol", 0))
            amt = float(b.get("amount", 0))
            conn.execute(
                "INSERT OR REPLACE INTO daily_k VALUES (?,?,?,?,?,?,?,?,?,?)",
                (code, d, o, h, l, c, vol, amt, None, None),
            )
            count += 1
        conn.commit()
        return count
    except Exception as e:
        print(f"  [{code}] 写入失败: {e}", file=sys.stderr, flush=True)
        return -1
    finally:
        conn.close()


# ── 主流程 ────────────────────────────────────────────────────────

def build(codes: list[str], workers: int = 8, years: int = 0, server_ip: str = ""):
    _ensure_table()
    total = len(codes)
    done = 0
    rows = 0
    failed = 0
    t0 = time.time()

    info = f"最近 {years} 年" if years > 0 else "全量"
    print(f"数据源：通达信 pytdx")
    print(f"开始构建本地 K 线数据库 · {total} 只股票 · {workers} 线程 · {info}")
    print(f"数据库: {DB_PATH}")
    print()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, c, years, server_ip): c for c in codes}
        for f in as_completed(futures):
            code = futures[f]
            done += 1
            try:
                n = f.result()
                if n > 0:
                    rows += n
                elif n == 0:
                    pass
                else:
                    failed += 1
            except Exception:
                failed += 1

            if done % 200 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(
                    f"[{done}/{total}] {done / total * 100:.0f}% | "
                    f"{rows} 条 | {failed} 失败 | "
                    f"{rate:.1f} 只/s | 预计剩余 {eta / 60:.0f} 分钟"
                )

    _tdx_disconnect_all()
    elapsed = time.time() - t0
    print()
    print(f"完成！{rows} 条 K 线，{failed} 只失败，总耗时 {elapsed / 60:.1f} 分钟")
    if DB_PATH.exists():
        print(f"数据库大小: {DB_PATH.stat().st_size / 1024 / 1024:.0f} MB")


def main():
    parser = argparse.ArgumentParser(description="构建本地 K 线数据库（通达信 pytdx）")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码(如 600519,000001)")
    parser.add_argument("--years", type=int, default=0, help="拉取最近 N 年（0=全量）")
    parser.add_argument("--server", type=str, default="", help="通达信服务器 IP（可选）")
    args = parser.parse_args()

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    else:
        print("获取全市场 A 股代码（通达信）...")
        codes = _get_all_codes(args.server)
        print(f"共 {len(codes)} 只股票")

    build(codes, args.workers, args.years, args.server)


if __name__ == "__main__":
    main()
