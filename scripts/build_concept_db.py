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
import re
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"

# ── 表 DDL ─────────────────────────────────────────────────────────

CONCEPT_DDL = """
CREATE TABLE IF NOT EXISTS stock_concept (
    code          TEXT NOT NULL,    -- 股票代码
    concept_code  TEXT NOT NULL,    -- 概念代码（同花顺6位）
    concept_name  TEXT NOT NULL,    -- 概念名称
    PRIMARY KEY (code, concept_code)
);
CREATE INDEX IF NOT EXISTS idx_stock_concept_code ON stock_concept(code);
CREATE INDEX IF NOT EXISTS idx_stock_concept_ccode ON stock_concept(concept_code);

CREATE TABLE IF NOT EXISTS concept_kline (
    code   TEXT NOT NULL,           -- 概念代码
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
    code       TEXT NOT NULL,       -- 概念代码
    date       TEXT NOT NULL,       -- 日期
    name       TEXT,                -- 概念名称
    inflow     REAL,                -- 流入资金（亿）
    outflow    REAL,                -- 流出资金（亿）
    net        REAL,                -- 净流入（亿）
    pct_change REAL,                -- 涨跌幅
    stock_count INT,                -- 成分股数量
    PRIMARY KEY (code, date)
);
CREATE INDEX IF NOT EXISTS idx_concept_ff_code ON concept_fund_flow(code);
"""


def _ensure_tables():
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    # 从 HTML 中提取概念链接: /gn/detail/code/NNNNNN/
    seen = set()
    concepts = []
    for m in re.finditer(r'/gn/detail/code/(\d{6})/"', r.text):
        code = m.group(1)
        if code in seen:
            continue
        seen.add(code)
        # 提取名称：链接后面的文本
        name_match = re.search(
            rf'/gn/detail/code/{code}/"[^>]*>([^<]+)<', r.text
        )
        name = name_match.group(1).strip() if name_match else code
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
        股票代码列表，如 ['600519', '000858', ...]
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"http://q.10jqka.com.cn/gn/detail/code/{concept_code}/",
    }
    all_codes = []
    for page in range(1, 50):  # 最多 50 页
        url = (
            f"http://q.10jqka.com.cn/gn/detail/order/desc/page/{page}"
            f"/ajax/1/code/{concept_code}/"
        )
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            break
        rows = table.find_all("tr")[1:]  # 跳过表头
        page_codes = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                c = cells[1].get_text().strip()
                if c.isdigit() and len(c) == 6:
                    page_codes.append(c)
        if not page_codes:
            break
        all_codes.extend(page_codes)
        if len(page_codes) < 10:
            break
    return all_codes


# ═══════════════════════════════════════════════════════════════════
# 步骤 3：概念板块日K线
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_kline(concept_name: str, years: int = 2) -> int:
    """用 akshare 同花顺接口获取概念板块日K线，写入 SQLite。

    Returns:
        写入行数
    """
    import akshare as ak

    today = date.today()
    start = today.replace(year=today.year - years)

    try:
        df = ak.stock_board_concept_index_ths(
            symbol=concept_name,
            start_date=start.strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return 0
    except Exception:
        return -1

    # ak 返回列名可能是中文
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
                """INSERT OR REPLACE INTO concept_kline VALUES (?,?,?,?,?,?,?,?)""",
                (
                    concept_name,
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
        return count
    except Exception:
        return -1
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# 步骤 4：概念资金流向
# ═══════════════════════════════════════════════════════════════════

def fetch_concept_fund_flow(today_str: str = "") -> int:
    """用 akshare 获取概念板块资金流向（当天），写入 SQLite。

    Returns:
        写入行数
    """
    import akshare as ak

    if not today_str:
        today_str = date.today().isoformat()

    try:
        df = ak.stock_fund_flow_concept()
    except Exception:
        # 10jqka 页面偶有变动，降级
        return -1

    if df is None or df.empty:
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        count = 0
        for _, row in df.iterrows():
            name = str(row.get("行业", ""))
            net = float(row.get("净额", 0) or 0)
            inflow = float(row.get("流入资金", 0) or 0)
            outflow_val = float(row.get("流出资金", 0) or 0)
            pct = float(row.get("行业-涨跌幅", 0) or 0)
            cnt = int(row.get("公司家数", 0) or 0)
            conn.execute(
                """INSERT OR REPLACE INTO concept_fund_flow VALUES (?,?,?,?,?,?,?,?)""",
                (name, today_str, name, inflow, outflow_val, net, pct, cnt),
            )
            count += 1
        conn.commit()
        return count
    except Exception:
        return -1
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

def build(years: int = 2):
    _ensure_tables()
    t_start = time.time()

    # ── 步骤 1: 概念列表 ──────────────────────────────────────────
    print("① 获取概念列表...")
    concepts = fetch_concept_list()
    print(f"   共 {len(concepts)} 个概念")

    # ── 步骤 2: 概念成分股 + 反查索引 ─────────────────────────────
    print("② 拉取概念成分股...")
    stock_to_concepts: dict[str, list[tuple[str, str]]] = {}
    total_stocks_in_concepts = 0
    failed_concepts = 0

    conn = sqlite3.connect(str(DB_PATH))
    for i, c in enumerate(concepts):
        stocks = fetch_concept_stocks(c["code"])
        if stocks:
            total_stocks_in_concepts += len(stocks)
            conn.execute("BEGIN")
            for s in stocks:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_concept VALUES (?,?,?)",
                    (s, c["code"], c["name"]),
                )
                stock_to_concepts.setdefault(s, []).append((c["code"], c["name"]))
            conn.commit()
        else:
            failed_concepts += 1

        if (i + 1) % 50 == 0:
            print(f"   [{i+1}/{len(concepts)}] {c['name']}: {len(stocks)} 只")
    conn.close()

    stock_count = len(stock_to_concepts)
    print(f"   完成：{total_stocks_in_concepts} 条映射，{stock_count} 只股票有概念归属，{failed_concepts} 个概念无成分股")

    # ── 步骤 3: 概念 K 线 ─────────────────────────────────────────
    print(f"③ 拉取概念板块日K线（{years}年）...")
    kline_total = 0
    kline_failed = 0

    for i, c in enumerate(concepts):
        n = fetch_concept_kline(c["name"], years)
        if n > 0:
            kline_total += n
        elif n < 0:
            kline_failed += 1

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t_start
            print(f"   [{i+1}/{len(concepts)}] {c['name']}: {n} 条  "
                  f"({elapsed/60:.1f}min)")

    print(f"   完成：{kline_total} 条 K 线，{kline_failed} 个概念失败")

    # ── 步骤 4: 概念资金流 ────────────────────────────────────────
    print("④ 拉取概念资金流向...")
    ff_count = fetch_concept_fund_flow()
    print(f"   完成：{ff_count} 条资金流数据" if ff_count > 0
          else f"   ⚠️ 资金流获取失败（10jqka 页面可能变动）")

    # ── 总结 ──────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"全部完成！总耗时 {elapsed/60:.1f} 分钟")
    print(f"  概念板块:    {len(concepts)} 个")
    print(f"  成分股映射:  {total_stocks_in_concepts} 条（{stock_count} 只股票）")
    print(f"  概念 K 线:   {kline_total} 条")
    print(f"  概念资金流:  {ff_count} 条")
    print(f"  数据库:      {DB_PATH} "
          f"({DB_PATH.stat().st_size/1024/1024:.0f} MB)" if DB_PATH.exists() else "")


def main():
    parser = argparse.ArgumentParser(description="构建概念板块数据库")
    parser.add_argument("--years", type=int, default=2, help="拉取最近 N 年 K 线")
    args = parser.parse_args()
    build(args.years)


if __name__ == "__main__":
    main()
