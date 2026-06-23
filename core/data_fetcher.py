"""行情与财务数据获取 —— AkShare + SQLite 本地缓存。

缓存策略：按日缓存；当日已有则走缓存（不重复请求外部 API）。
未安装 akshare 或网络不可用时降级返回空/缓存。
"""
from __future__ import annotations
import json
import sqlite3
import warnings
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import config

# ── 缓存路径 ────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_DB = CACHE_DIR / "market_data.sqlite"

# 抑制 akshare 的 FutureWarning / 网络异常噪音
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    _ensure_cache_dir()
    conn = sqlite3.connect(str(CACHE_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _init_cache_tables() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS price_cache (
            code TEXT PRIMARY KEY,
            price REAL,
            pe REAL,
            pb REAL,
            name TEXT,
            updated TEXT
        );
        CREATE TABLE IF NOT EXISTS kline_cache (
            code TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (code, date)
        );
        CREATE TABLE IF NOT EXISTS fundamentals_cache (
            code TEXT,
            indicator TEXT,
            value TEXT,
            updated TEXT,
            PRIMARY KEY (code, indicator)
        );
        CREATE TABLE IF NOT EXISTS news_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            title TEXT,
            source TEXT,
            time TEXT,
            url TEXT,
            fetched TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── AkShare 延迟导入 ────────────────────────────────────────────

_ak = None


def _get_ak():
    global _ak
    if _ak is None:
        try:
            import akshare as ak_mod
            _ak = ak_mod
        except ImportError:
            pass
    return _ak


# ── 公开接口 ────────────────────────────────────────────────────

def get_price(code: str) -> dict:
    """获取股票最新价与估值。

    Returns:
        {"code": str, "price": float, "pe": float|None, "pb": float|None, "name": str}
        失败返回 {"code": code, "price": None, "error": str}
    """
    today_str = date.today().isoformat()

    # 1. 查缓存（当日）
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM price_cache WHERE code = ? AND updated = ?",
        (code, today_str),
    ).fetchone()
    if row:
        conn.close()
        return {"code": code, "price": row["price"], "pe": row["pe"],
                "pb": row["pb"], "name": row["name"]}

    # 2. 调 AkShare
    ak = _get_ak()
    if ak is None:
        conn.close()
        return {"code": code, "price": None, "error": "akshare 未安装"}

    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            conn.close()
            return {"code": code, "price": None, "error": f"未找到代码 {code}"}
        r = row.iloc[0]
        price = float(r["最新价"]) if pd.notna(r.get("最新价")) else None
        pe = float(r["市盈率-动态"]) if pd.notna(r.get("市盈率-动态")) else None
        pb = float(r["市净率"]) if pd.notna(r.get("市净率")) else None
        name = str(r["名称"]) if pd.notna(r.get("名称")) else ""

        # 写入缓存
        conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?,?,?,?)",
            (code, price, pe, pb, name, today_str),
        )
        conn.commit()
        conn.close()
        return {"code": code, "price": price, "pe": pe, "pb": pb, "name": name}
    except Exception as e:
        conn.close()
        return {"code": code, "price": None, "error": str(e)}


def get_kline(code: str, days: int = 300) -> list[dict]:
    """获取日K线数据。

    Returns:
        [{date, open, high, low, close, volume}, ...]  按日期升序。
    """
    today = date.today()
    start = today - timedelta(days=days + 10)  # 多取几天容错

    # 1. 查缓存
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM kline_cache WHERE code = ? AND date >= ? ORDER BY date",
        (code, start.isoformat()),
    ).fetchall()
    if len(rows) >= min(days, 200):  # 缓存够用
        conn.close()
        return [_kline_row_to_dict(r) for r in rows[-days:]]

    # 2. 调 AkShare
    ak = _get_ak()
    if ak is None:
        conn.close()
        return [_kline_row_to_dict(r) for r in rows]  # 返缓存兜底

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
            adjust="qfq",
        )
        for _, r in df.iterrows():
            d = str(r["日期"])[:10]
            conn.execute(
                "INSERT OR REPLACE INTO kline_cache VALUES (?,?,?,?,?,?,?)",
                (code, d, float(r["开盘"]), float(r["最高"]),
                 float(r["最低"]), float(r["收盘"]), float(r["成交量"])),
            )
        conn.commit()
    except Exception:
        pass  # 网络异常，用缓存兜底
    finally:
        conn.close()

    # 重新读缓存（含刚写入的）
    conn2 = _get_conn()
    rows2 = conn2.execute(
        "SELECT * FROM kline_cache WHERE code = ? AND date >= ? ORDER BY date",
        (code, start.isoformat()),
    ).fetchall()
    conn2.close()
    return [_kline_row_to_dict(r) for r in rows2[-days:]]


def _kline_row_to_dict(row) -> dict:
    return {
        "date": row["date"], "open": row["open"], "high": row["high"],
        "low": row["low"], "close": row["close"], "volume": row["volume"],
    }


def get_fundamentals(code: str) -> dict:
    """获取关键财务指标。

    Returns:
        {"code": str, "indicators": {指标名: 值, ...}}
    """
    today_str = date.today().isoformat()

    # 1. 查缓存
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM fundamentals_cache WHERE code = ? AND updated = ?",
        (code, today_str),
    ).fetchall()
    if rows:
        conn.close()
        return {"code": code, "indicators": {r["indicator"]: r["value"] for r in rows}}

    # 2. 调 AkShare
    ak = _get_ak()
    if ak is None:
        conn.close()
        return {"code": code, "indicators": {}}

    try:
        df = ak.stock_financial_indicators_ths(symbol=code)
        # 取最新一期数据
        latest = df.iloc[-1] if not df.empty else None
        if latest is not None:
            key_map = {
                "净资产收益率": "ROE", "净利润率": "net_margin",
                "资产负债率": "debt_ratio", "营业总收入": "revenue",
                "归母净利润": "net_profit",
            }
            for cn_name, en_key in key_map.items():
                if cn_name in df.columns and pd.notna(latest.get(cn_name)):
                    val = str(latest[cn_name])
                    conn.execute(
                        "INSERT OR REPLACE INTO fundamentals_cache VALUES (?,?,?,?)",
                        (code, en_key, val, today_str),
                    )
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

    conn2 = _get_conn()
    rows2 = conn2.execute(
        "SELECT * FROM fundamentals_cache WHERE code = ? AND updated = ?",
        (code, today_str),
    ).fetchall()
    conn2.close()
    return {"code": code, "indicators": {r["indicator"]: r["value"] for r in rows2}}


def get_news(keyword: str, limit: int = 20) -> list[dict]:
    """获取相关新闻（调用 AkShare stock_news_em）。

    Returns:
        [{title, source, time, url}, ...]
    """
    today_str = date.today().isoformat()

    # 1. 查缓存
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM news_cache WHERE keyword = ? AND fetched = ? ORDER BY id DESC LIMIT ?",
        (keyword, today_str, limit),
    ).fetchall()
    if len(rows) >= min(limit, 5):
        conn.close()
        return [{"title": r["title"], "source": r["source"],
                 "time": r["time"], "url": r["url"]} for r in rows]

    # 2. 调 AkShare
    ak = _get_ak()
    if ak is None:
        conn.close()
        return []

    try:
        df = ak.stock_news_em(stock=keyword)
        for _, r in df.head(limit).iterrows():
            conn.execute(
                "INSERT INTO news_cache (keyword, title, source, time, url, fetched) VALUES (?,?,?,?,?,?)",
                (keyword, str(r.get("标题", "")), str(r.get("来源", "")),
                 str(r.get("发布时间", "")), str(r.get("新闻链接", "")), today_str),
            )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

    conn2 = _get_conn()
    rows2 = conn2.execute(
        "SELECT * FROM news_cache WHERE keyword = ? AND fetched = ? ORDER BY id DESC LIMIT ?",
        (keyword, today_str, limit),
    ).fetchall()
    conn2.close()
    return [{"title": r["title"], "source": r["source"],
             "time": r["time"], "url": r["url"]} for r in rows2]


# ── 初始化 ──────────────────────────────────────────────────────


# ── P2 兜底源：Baostock ────────────────────────────────────────

_bs = None


def _get_bs():
    global _bs
    if _bs is None:
        try:
            import baostock as bs
            bs.login()
            _bs = bs
        except Exception:
            pass
    return _bs


def _bs_get_price(code: str) -> dict | None:
    """Baostock 兜底取价。"""
    bs = _get_bs()
    if bs is None:
        return None
    try:
        # 补齐交易所前缀：sz=000001, sh=600519
        full_code = f"sz.{code}" if code.startswith(("0", "3")) else f"sh.{code}"
        rs = bs.query_history_k_data_plus(
            full_code, "date,close", start_date=(date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
            end_date=date.today().strftime("%Y-%m-%d"), frequency="d", adjustflag="2",
        )
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        bs.logout()
        if rows and rows[-1][1]:
            return {"code": code, "price": float(rows[-1][1]), "pe": None, "pb": None, "name": code}
    except Exception:
        pass
    return None


def _bs_get_kline(code: str, days: int = 300) -> list[dict] | None:
    """Baostock 兜底取 K 线。"""
    bs = _get_bs()
    if bs is None:
        return None
    try:
        full_code = f"sz.{code}" if code.startswith(("0", "3")) else f"sh.{code}"
        start = (date.today() - timedelta(days=days + 10)).strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(
            full_code, "date,open,high,low,close,volume",
            start_date=start, end_date=date.today().strftime("%Y-%m-%d"),
            frequency="d", adjustflag="2",
        )
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        bs.logout()
        return [
            {"date": r[0], "open": float(r[1]), "high": float(r[2]),
             "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])}
            for r in rows if r[4]
        ]
    except Exception:
        return None


# ── P2 数据质量校验 ────────────────────────────────────────────

def _validate_price_result(result: dict) -> dict:
    """校验 get_price 返回值，坏数据标 _stale。"""
    price = result.get("price")
    if price is not None:
        if not isinstance(price, (int, float)) or price <= 0:
            result["price"] = None
            result["_stale"] = True
            result["_warning"] = f"价格异常({price})，已标记为无效"
    return result


def _validate_kline_result(rows: list[dict]) -> list[dict]:
    """校验 K 线数据：过滤掉 close <= 0 的行。"""
    return [r for r in rows if isinstance(r.get("close"), (int, float)) and r["close"] > 0]


# ── P2 缓存健壮：取 stale 缓存兜底 ─────────────────────────────

def _get_stale_price_cache(code: str) -> dict | None:
    """取最近一次缓存（不要求当日）。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM price_cache WHERE code = ? ORDER BY updated DESC LIMIT 1", (code,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "code": code, "price": row["price"], "pe": row["pe"],
            "pb": row["pb"], "name": row["name"], "_stale": True,
        }
    return None


# ── 重连 Baostock（每次调用后 bs.logout() 会断开） ──────────────

_bs_logged_in = False


def _bs_ensure_login():
    global _bs_logged_in
    if not _bs_logged_in:
        try:
            import baostock as bs_mod
            bs_mod.login()
            _bs_logged_in = True
        except Exception:
            pass


# ── 更新 get_price 接入兜底 ────────────────────────────────────

# 保存原始实现的引用
_get_price_original = get_price


def get_price(code: str) -> dict:  # noqa: F811 (redefine intentionally)
    """获取股票最新价（AkShare → Baostock → stale cache 三级兜底）。"""
    result = _get_price_original(code)

    # 校验
    result = _validate_price_result(result)

    # 如果 AkShare 失败，试 Baostock
    if result.get("price") is None and "error" in result:
        bs_result = _bs_get_price(code)
        if bs_result and bs_result.get("price"):
            return _validate_price_result(bs_result)

        # 取 stale 缓存兜底
        stale = _get_stale_price_cache(code)
        if stale:
            return stale

    return result


# 保存原始 get_kline
_get_kline_original = get_kline


def get_kline(code: str, days: int = 300) -> list[dict]:  # noqa: F811
    """获取 K 线（AkShare → Baostock → stale cache 三级兜底）。"""
    result = _get_kline_original(code, days)
    result = _validate_kline_result(result)

    if len(result) < 5:
        bs_result = _bs_get_kline(code, days)
        if bs_result and len(bs_result) >= 5:
            return _validate_kline_result(bs_result[-days:])

    return result


_init_cache_tables()
