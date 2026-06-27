"""Z 哥策略筛选器 — 每只股票返回 (通过, 评分, 详情标签)

所有筛选器接收 6 位股票代码，返回 dict:
  {"hit": bool, "score": number, "details": str}

集成到 sync_daily.py 做预计算，或 API 层做实时查询。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, Optional

from core.zg_indicators import (
    white_line, yellow_line, calc_kdj, calc_macd,
    calc_brick, brick_signal, calc_deep_v, deep_v_signal,
    trend_status, calc_oamv, oamv_status,
)
from core.zg_config import (
    B1_J_THRESHOLD, B1_LOOKBACK,
    BRICK_STRONG_RATIO,
)

DB = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"


def _load_klines(code: str, days: int = 300) -> Optional[pd.DataFrame]:
    """从 daily_k 加载日K线"""
    conn = sqlite3.connect(str(DB))
    try:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume, amount "
            "FROM daily_k WHERE code=? ORDER BY date", (code,)
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 60:
        return None
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])


# ═══════════════════════════════════════════════════════════════════
# 8 个策略筛选器
# ═══════════════════════════════════════════════════════════════════

def screen_B1(code: str) -> Dict:
    """规则B1 少妇战法 — 12维模型（精简6维版，保留核心条件）"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, o, h, l, v = df["close"], df["open"], df["high"], df["low"], df["volume"]
    L = len(df) - 1
    wl = white_line(c)
    yl = yellow_line(c)
    kdj = calc_kdj(h, l, c)
    macd = calc_macd(c)
    j = float(kdj["J"].iloc[L])
    k = float(kdj["K"].iloc[L])
    d = float(kdj["D"].iloc[L])
    dif = float(macd["DIF"].iloc[L])
    dea = float(macd["DEA"].iloc[L])
    avg30 = v.rolling(30, min_periods=1).mean()
    v_ratio = float(v.iloc[L]) / float(avg30.iloc[L]) if float(avg30.iloc[L]) > 0 else 0
    yl_v = float(yl.iloc[L])
    wl_v = float(wl.iloc[L])
    close_v = float(c.iloc[L])

    checks = {
        "双线多头(白>黄)": wl_v > yl_v,
        "KDJ超卖(J<13)": j < 13,
        "MACD金叉(DIF>DEA)": dif > dea,
        "价在黄线上方": close_v > yl_v,
        "倍量(>2.4x)": v_ratio >= 2.4,
        "阳线收盘": close_v >= float(c.iloc[L - 1]) if L >= 1 else False,
    }
    passed = sum(1 for v in checks.values() if v)
    return {"hit": passed >= 5, "score": passed, "details": f"{passed}/6"}


def screen_Brick(code: str) -> Dict:
    """形态红砖 瑜伽裤 — 砖型图绿转红 + 站上黄线"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    h, l, c = df["high"], df["low"], df["close"]
    yl_v = float(yellow_line(c).iloc[-1])
    bs = brick_signal(h, l, c, yl_v)
    return {
        "hit": bs.get("signal", False),
        "score": round(bs.get("strength", 0) * 100, 1),
        "details": bs.get("tag", ""),
    }


def screen_B1_Loose(code: str) -> Dict:
    """规则B1宽松版 — J<20 + 双线多头"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, h, l = df["close"], df["high"], df["low"]
    L = len(df) - 1
    wl = white_line(c)
    yl = yellow_line(c)
    kdj = calc_kdj(h, l, c)
    j = float(kdj["J"].iloc[L])
    checks = {
        "双线多头": float(wl.iloc[L]) > float(yl.iloc[L]),
        "J<20": j < 20,
        "价在黄线上": float(c.iloc[L]) > float(yl.iloc[L]),
    }
    p = sum(1 for v in checks.values() if v)
    return {"hit": p >= 2, "score": p, "details": f"{p}/3"}


def screen_WeeklyB1(code: str) -> Dict:
    """周线B1 — 周K线 J<13 + 价在黄线上方"""
    df = _load_klines(code, 500)
    if df is None or len(df) < 100:
        return {"hit": False, "score": 0, "details": "数据不足"}
    # 从日K降采样到周K
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    weekly = df.resample("W").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    if len(weekly) < 30:
        return {"hit": False, "score": 0, "details": "数据不足"}
    h, l, c = weekly["high"], weekly["low"], weekly["close"]
    wl = white_line(c)
    yl = yellow_line(c)
    kdj = calc_kdj(h, l, c)
    L = len(weekly) - 1
    j = float(kdj["J"].iloc[L])
    checks = {
        "周J<13": j < 13,
        "价在周黄线上": float(c.iloc[L]) > float(yl.iloc[L]),
        "白线在黄线上": float(wl.iloc[L]) > float(yl.iloc[L]),
    }
    p = sum(1 for v in checks.values() if v)
    return {"hit": p >= 2, "score": p, "details": f"{p}/3"}


def screen_B2(code: str) -> Dict:
    """规则B2 — 趋势确认机 + 涨幅 + J<55"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    L = len(df) - 1
    wl = white_line(c)
    yl = yellow_line(c)
    kdj = calc_kdj(h, l, c)
    j = float(kdj["J"].iloc[L])
    zf = (float(c.iloc[L]) - float(c.iloc[L - 1])) / float(c.iloc[L - 1]) * 100
    v_ratio = float(v.iloc[L]) / v.rolling(5).mean().iloc[L] if v.rolling(5).mean().iloc[L] > 0 else 0
    checks = {
        "趋势多头": float(wl.iloc[L]) > float(yl.iloc[L]),
        "J<55": j < 55,
        "涨幅≥4%": zf >= 4,
        "放量(>1.5x)": v_ratio >= 1.5,
        "上影线可控": (float(h.iloc[L]) - float(c.iloc[L])) / max(float(h.iloc[L]) - float(l.iloc[L]), 0.01) < 0.5,
    }
    p = sum(1 for v in checks.values() if v)
    return {"hit": p >= 3, "score": p, "details": f"{p}/5"}


def screen_Tepu(code: str) -> Dict:
    """规则Tepu 平台突破 — 65日平台整理 + 突破确认 + 趋势"""
    df = _load_klines(code, 400)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    L = len(df) - 1
    c, h, l = df["close"], df["high"], df["low"]
    wl = white_line(c)
    yl = yellow_line(c)
    close_v = float(c.iloc[L])
    # 近65日最高价和最低价
    hh_65 = h.tail(65).max()
    ll_65 = l.tail(65).min()
    platform_range = (hh_65 - ll_65) / ll_65 * 100 if ll_65 > 0 else 100
    # 是否是平台整理（<15%振幅）
    is_platform = platform_range < 15
    # 突破：收盘价接近65日最高价（<3%距离）
    near_high = (hh_65 - close_v) / hh_65 * 100 < 3 if hh_65 > 0 else False
    # 趋势确认
    trend_ok = float(wl.iloc[L]) > float(yl.iloc[L])
    checks = {
        "平台整理(65日<15%振幅)": is_platform,
        "突破65日高点(3%距离)": near_high,
        "趋势多头": trend_ok,
    }
    p = sum(1 for v in checks.values() if v)
    return {"hit": p >= 2, "score": p, "details": f"{p}/3"}


def screen_PinBar(code: str) -> Dict:
    """单针 探底 — 随机指标 + 下影线 > 3 * (上影线+实体)"""
    df = _load_klines(code)
    if df is None:
        return {"hit": False, "score": 0, "details": "数据不足"}
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    L = len(df) - 1
    close_v = float(c.iloc[L])
    open_v = float(o.iloc[L])
    high_v = float(h.iloc[L])
    low_v = float(l.iloc[L])
    body = abs(close_v - open_v)
    upper_wick = high_v - max(close_v, open_v)
    lower_wick = min(close_v, open_v) - low_v
    # 下影线条件
    is_pin = lower_wick > 3 * max(upper_wick, body, 0.01)
    # KDJ低位
    kdj = calc_kdj(h, l, c)
    j = float(kdj["J"].iloc[L])
    j_low = j < 20
    checks = {
        "下影线(>3倍上影线+实体)": is_pin,
        "KDJ低位(J<20)": j_low,
    }
    p = sum(1 for v in checks.values() if v)
    return {"hit": p >= 2, "score": p, "details": f"{p}/2"}


# ═══════════════════════════════════════════════════════════════════
# 注册表
# ═══════════════════════════════════════════════════════════════════

SCREENERS: Dict[str, callable] = {
    "B1": screen_B1,
    "红砖": screen_Brick,
    "B1宽松": screen_B1_Loose,
    "周线B1": screen_WeeklyB1,
    "B2": screen_B2,
    "Tepu": screen_Tepu,
    "单针": screen_PinBar,
}
