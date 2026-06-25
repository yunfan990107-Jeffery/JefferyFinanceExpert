#!/usr/bin/env python
"""一次性构建概念板块数据库（同花顺 10jqka → SQLite）。

拉取内容：
  1. 概念列表（361 个概念）
  2. 概念成分股（每个概念的股票列表）
  3. 股票→概念反向映射
  4. 概念板块日K线（最近 2 年）
  5. 概念资金流向（日频）

数据源：同花顺（q.10jqka.com.cn + data.10jqka.com.cn），不依赖东方财富。
结果写入 data/market_data.sqlite，与股票 K 线库同一文件。

用法：
    python scripts/build_concept_db.py
    python scripts/build_concept_db.py --years 2
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"

# ── 表 DDL ─────────────────────────────────────────────────────────

CONCEPT_DDL = """
CREATE TABLE IF NOT EXISTS stock_concept (
    code          TEXT NOT NULL,
    concept_code  TEXT NOT NULL,
    concept_name  TEXT NOT NULL,
    PRIMARY KEY (code, concept_code)
);
CREATE INDEX IF NOT EXISTS idx_stock_concept_code ON stock_concept(code);
CREATE INDEX IF NOT EXISTS idx_stock_concept_ccode ON stock_concept(concept_code);

CREATE TABLE IF NOT EXISTS concept_kline (
    code   TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    volume REAL,
    amount REAL,
    PRIMARY KEY (code, date)
);
CREATE INDEX IF NOT EXISTS idx_concept_kline_code ON concept_kline(code);

CREATE TABLE IF NOT EXISTS concept_fund_flow (
    code       TEXT NOT NULL,
    date       TEXT NOT NULL,
    name       TEXT,
    inflow     REAL,
    outflow    REAL,
    net        REAL,
    pct_change REAL,
    stock_count INT,
    PRIMARY KEY (code, date)
);
CREATE INDEX IF NOT EXISTS idx_concept_ff_code ON concept_fund_flow(code);
"""

# 共享的 HTTP Session（连接复用）
_SESSION: requests.Session | None = None


def _session() -> requests.Session:
    """获取共享的 HTTP Session（User-Agent 预设）。"""
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        })
    return _SESSION


def _ensure_tables() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(CONCEPT_DDL)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# 步骤 1：获取概念列表
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_list() -> list[dict]:
    """从 10jqka 概念列表页获取所有概念名称和代码。

    Returns:
        [{code: '300008', name: '新能源'}, ...]
    """
    url = "http://q.10jqka.com.cn/gn/"
    r = _session().get(url, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    concepts = []
    seen = set()

    # 概念链接格式: <a href="/gn/detail/code/NNNNNN/">概念名</a>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/gn/detail/code/" not in href:
            continue
        code = href.rsplit("/", 2)[-2]  # 提取 6 位数字
        if not code.isdigit() or len(code) != 6 or code in seen:
            continue
        seen.add(code)
        name = a.get_text().strip() or code
        concepts.append({"code": code, "name": name})
    return concepts


# ═══════════════════════════════════════════════════════════════════
# 步骤 2：获取概念成分股
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_stocks(concept_code: str) -> list[str]:
    """获取指定概念的所有成分股代码（自动分页）。

    Args:
        concept_code: 同花顺概念代码，如 '300008'

    Returns:
        股票代码列表
    """
    referer = f"http://q.10jqka.com.cn/gn/detail/code/{concept_code}/"
    all_codes = []

    for page in range(1, 50):
        url = (
            f"http://q.10jqka.com.cn/gn/detail/order/desc"
            f"/page/{page}/ajax/1/code/{concept_code}/"
        )
        r = _session().get(url, headers={"Referer": referer}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            break

        page_codes = []
        for tr in table.find_all("tr")[1:]:  # 跳过表头
            tds = tr.find_all("td")
            if len(tds) >= 3:
                c = tds[1].get_text().strip()
                if c.isdigit() and len(c) == 6:
                    page_codes.append(c)

        if not page_codes:
            break
        all_codes.extend(page_codes)
        if len(page_codes) < 10:
            break  # 最后一页
    return all_codes


# ═══════════════════════════════════════════════════════════════════
# 步骤 3：概念板块日K线
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_klines(
    concepts: list[dict], years: int
) -> tuple[int, int, list[str]]:
    """批量拉取概念 K 线，遍历 concepts 列表。

    Returns:
        (总行数, 失败数, 失败概念名列表)
    """
    import akshare as ak

    today = date.today()
    start = today.replace(year=today.year - years)

    total = 0
    failed = 0
    failed_names: list[str] = []

    for i, c in enumerate(concepts):
        try:
            df = ak.stock_board_concept_index_ths(
                symbol=c["name"],
                start_date=start.strftime("%Y%m%d"),
                end_date=today.strftime("%Y%m%d"),
            )
            if df is None or df.empty:
                continue
        except Exception:
            failed += 1
            failed_names.append(c["name"])
            continue

        # 列名可能为中文
        col_map = {
            "日期": "date", "开盘价": "open", "最高价": "high",
            "最低价": "low", "收盘价": "close",
            "成交量": "volume", "成交额": "amount",
        }
        df = df.rename(columns=col_map)

        conn = sqlite3.connect(str(DB_PATH))
        try:
            count = 0
            for _, row in df.iterrows():
                d = str(row.get("date", ""))[:10]
                if not d:
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO concept_kline VALUES (?,?,?,?,?,?,?,?)",
                    (
                        c["name"],
                        d,
                        float(row.get("open", 0) or 0),
                        float(row.get("high", 0) or 0),
                        float(row.get("low", 0) or 0),
                        float(row.get("close", 0) or 0),
                        float(row.get("volume", 0) or 0),
                        float(row.get("amount", 0) or 0),
                    ),
                )
                count += 1
            conn.commit()
            total += count
        except Exception:
            failed += 1
            failed_names.append(c["name"])
        finally:
            conn.close()

        if (i + 1) % 50 == 0:
            elapsed = time.time() - _t0
            print(f"   [{i+1}/{len(concepts)}] {c['name']}: {count} 条  "
                  f"({elapsed/60:.1f}min)")

    return total, failed, failed_names


# ═══════════════════════════════════════════════════════════════════
# 步骤 4：概念资金流向
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_fund_flows(today_str: str = "") -> tuple[int, list[str]]:
    """拉取概念板块资金流向（当天），写入 SQLite。

    Returns:
        (写入行数, 失败概念名列表)
    """
    import akshare as ak

    if not today_str:
        today_str = date.today().isoformat()

    try:
        df = ak.stock_fund_flow_concept()
    except Exception:
        return -1, ["ak.stock_fund_flow_concept() 调用失败"]

    if df is None or df.empty:
        return 0, []

    conn = sqlite3.connect(str(DB_PATH))
    try:
        count = 0
        for _, row in df.iterrows():
            name = str(row.get("行业", ""))
            conn.execute(
                "INSERT OR REPLACE INTO concept_fund_flow VALUES (?,?,?,?,?,?,?,?)",
                (
                    name, today_str, name,
                    float(row.get("流入资金", 0) or 0),
                    float(row.get("流出资金", 0) or 0),
                    float(row.get("净额", 0) or 0),
                    float(row.get("行业-涨跌幅", 0) or 0),
                    int(row.get("公司家数", 0) or 0),
                ),
            )
            count += 1
        conn.commit()
        return count, []
    except Exception:
        return -1, ["数据库写入失败"]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

_t0 = 0.0  # 全局计时器，供 fetch_concept_klines 使用


def _step1_concept_list() -> list[dict]:
    print("① 获取概念列表...")
    concepts = fetch_concept_list()
    print(f"   共 {len(concepts)} 个概念")
    return concepts


def _step2_stocks(concepts: list[dict]) -> tuple[int, int, list[str]]:
    print("② 拉取概念成分股...")
    total_mappings = 0
    failed_names: list[str] = []
    stocks_with_concepts: set[str] = set()

    conn = sqlite3.connect(str(DB_PATH))
    for i, c in enumerate(concepts):
        stocks = fetch_concept_stocks(c["code"])
        if stocks:
            total_mappings += len(stocks)
            stocks_with_concepts.update(stocks)
            conn.execute("BEGIN")
            for s in stocks:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_concept VALUES (?,?,?)",
                    (s, c["code"], c["name"]),
                )
            conn.commit()
        else:
            failed_names.append(c["name"])

        if (i + 1) % 50 == 0:
            print(f"   [{i+1}/{len(concepts)}] {c['name']}: {len(stocks)} 只")
    conn.close()

    print(f"   完成：{total_mappings} 条映射，{len(stocks_with_concepts)} 只股票有概念归属"
          f"{'，' + str(len(failed_names)) + ' 个概念无成分股' if failed_names else ''}")
    if failed_names and len(failed_names) <= 10:
        print(f"   无成分股的概念: {', '.join(failed_names[:10])}")
    return total_mappings, len(stocks_with_concepts), failed_names


def _step3_klines(concepts: list[dict], years: int) -> tuple[int, int]:
    print(f"③ 拉取概念板块日K线（{years}年）...")
    global _t0
    _t0 = time.time()
    total, failed, failed_names = fetch_concept_klines(concepts, years)
    print(f"   完成：{total} 条 K 线，{failed} 个概念失败"
          f"{' (' + ', '.join(failed_names[:5]) + '...)' if failed_names else ''}")
    return total, failed


def _step4_fund_flow() -> int:
    print("④ 拉取概念资金流向...")
    count, errs = fetch_concept_fund_flows()
    if count > 0:
        print(f"   完成：{count} 条资金流数据")
    else:
        print(f"   ⚠️ 资金流获取失败"
              f"{' (' + '; '.join(errs[:3]) + ')' if errs else ''}")
    return count


def _print_summary(
    concept_count: int, mappings: int, stock_count: int,
    kline_count: int, fund_flow_count: int, elapsed: float,
) -> None:
    print(f"\n{'='*50}")
    print(f"全部完成！总耗时 {elapsed/60:.1f} 分钟")
    print(f"  概念板块:    {concept_count} 个")
    print(f"  成分股映射:  {mappings} 条（{stock_count} 只股票）")
    print(f"  概念 K 线:   {kline_count} 条")
    print(f"  概念资金流:  {fund_flow_count} 条")
    if DB_PATH.exists():
        print(f"  数据库:      {DB_PATH} "
              f"({DB_PATH.stat().st_size/1024/1024:.0f} MB)")


def build(years: int = 2) -> None:
    _ensure_tables()
    t_start = time.time()

    concepts = _step1_concept_list()
    mappings, stock_count, _ = _step2_stocks(concepts)
    kline_count, _ = _step3_klines(concepts, years)
    ff_count = _step4_fund_flow()

    elapsed = time.time() - t_start
    _print_summary(len(concepts), mappings, stock_count, kline_count, ff_count, elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="构建概念板块数据库")
    parser.add_argument("--years", type=int, default=2, help="拉取最近 N 年 K 线")
    args = parser.parse_args()
    build(args.years)


if __name__ == "__main__":
    main()
