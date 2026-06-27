"""
指标计算层 (indicators.py)
===========================
所有技术指标的唯一实现。零重复、纯函数、只依赖 pandas/numpy + config。
通达信公式 → Python 的精确转化全部在此。

模块索引：
  通达信函数  : sma_tdx, hhv, llv
  双线系统    : white_line, yellow_line, dual_line_status
  KDJ        : calc_kdj
  MACD       : calc_macd
  砖型图     : calc_brick, brick_signal
  深V战法    : calc_deep_v, deep_v_signal
  0AMV活跃市值: calc_oamv, oamv_status
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.zg_config import (
    WHITE_LINE_SPAN, YELLOW_LINE_MAS,
    KDJ_N, KDJ_M1, KDJ_M2,
    BRICK_HHV_LLV_N, BRICK_SMA1_N, BRICK_SMA2_N,
    BRICK_THRESHOLD, BRICK_STRONG_RATIO,
    DEEP_V_N1, DEEP_V_N2,
    OAMV_SMA_N, OAMV_DANGER_PCT, OAMV_CAUTION_PCT,
    OAMV_HEALTHY_PCT, OAMV_MA_FAST, OAMV_MA_SLOW,
)


# ====================================================================
# 1. 通达信基础函数
# ====================================================================

def sma_tdx(s: pd.Series, n: int, m: int) -> pd.Series:
    """通达信SMA(X,N,M) = (M*X + (N-M)*Y') / N"""
    out = np.empty(len(s), dtype=float)
    first = s.first_valid_index()
    if first is None:
        return pd.Series(np.nan, index=s.index)
    p = s.index.get_loc(first)
    out[:p] = np.nan
    out[p] = float(s.iloc[p])
    vals = s.to_numpy(dtype=float, na_value=0.0)
    for i in range(p + 1, len(s)):
        out[i] = (m * vals[i] + (n - m) * out[i - 1]) / n
    return pd.Series(out, index=s.index)


def hhv(s: pd.Series, n: int) -> pd.Series:
    """N周期最高值"""
    return s.rolling(n, min_periods=1).max()


def llv(s: pd.Series, n: int) -> pd.Series:
    """N周期最低值"""
    return s.rolling(n, min_periods=1).min()


# ====================================================================
# 2. 双线系统
# ====================================================================

def white_line(close: pd.Series) -> pd.Series:
    """白线 = EMA(EMA(C, span), span)"""
    s = WHITE_LINE_SPAN
    e1 = close.ewm(span=s, adjust=False).mean()
    return e1.ewm(span=s, adjust=False).mean()


def yellow_line(close: pd.Series) -> pd.Series:
    """黄线 = (MA14+MA28+MA57+MA114)/4"""
    mas = [close.rolling(p, min_periods=1).mean() for p in YELLOW_LINE_MAS]
    return sum(mas) / len(mas)


def dual_line_status(close: pd.Series) -> dict:
    """双线状态快照"""
    wl, yl = float(white_line(close).iloc[-1]), float(yellow_line(close).iloc[-1])
    c = float(close.iloc[-1])
    return {
        "wl": round(wl, 2), "yl": round(yl, 2),
        "bull": wl > yl,
        "c_vs_yl": round((c - yl) / yl * 100, 2),
        "c_vs_wl": round((c - wl) / wl * 100, 2),
    }


# ====================================================================
# 3. KDJ
# ====================================================================

def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series,
             n=KDJ_N, m1=KDJ_M1, m2=KDJ_M2) -> pd.DataFrame:
    lo = low.rolling(n, min_periods=1).min()
    hi = high.rolling(n, min_periods=1).max()
    rsv = ((close - lo) / (hi - lo).replace(0, np.nan) * 100).fillna(50)

    k = np.empty(len(close)); d = np.empty(len(close))
    k[0] = d[0] = 50.0
    rv = rsv.to_numpy(dtype=float)
    for i in range(1, len(close)):
        k[i] = (m1 - 1) / m1 * k[i-1] + rv[i] / m1
        d[i] = (m2 - 1) / m2 * d[i-1] + k[i] / m2
    j = 3 * k - 2 * d
    return pd.DataFrame({"K": k, "D": d, "J": j}, index=close.index)


# ====================================================================
# 4. MACD
# ====================================================================

def calc_macd(close: pd.Series, fast=12, slow=26, sig=9) -> pd.DataFrame:
    ef = close.ewm(span=fast, adjust=False).mean()
    es = close.ewm(span=slow, adjust=False).mean()
    dif = ef - es
    dea = dif.ewm(span=sig, adjust=False).mean()
    bar = 2 * (dif - dea)
    return pd.DataFrame({"DIF": dif, "DEA": dea, "MACD": bar}, index=close.index)


# ====================================================================
# 5. 砖型图 — Z哥原版公式精确复刻
# ====================================================================

def calc_brick(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    """
    返回: brick_val, is_red, green_to_red, red_to_green,
          red_count, green_count, strength
    """
    h, l, c = high.astype(float), low.astype(float), close.astype(float)
    hh4 = hhv(h, BRICK_HHV_LLV_N)
    ll4 = llv(l, BRICK_HHV_LLV_N)
    den = (hh4 - ll4).replace(0, np.nan)

    var1a = ((hh4 - c) / den * 100 - 90).fillna(0)
    var2a = sma_tdx(var1a, BRICK_SMA1_N, 1) + 100
    var3a = ((c - ll4) / den * 100).fillna(0)
    var4a = sma_tdx(var3a, BRICK_SMA2_N, 1)
    var5a = sma_tdx(var4a, BRICK_SMA2_N, 1) + 100
    var6a = var5a - var2a

    bv = pd.Series(np.where(var6a > BRICK_THRESHOLD, var6a - BRICK_THRESHOLD, 0),
                   index=close.index, dtype=float)
    bp = bv.shift(1).fillna(0)

    is_red = bp < bv
    is_red_prev = is_red.shift(1).fillna(False)
    g2r = (~is_red_prev) & is_red
    r2g = is_red_prev & (~is_red)

    # 连续计数 + 强度
    # strength = 当前柱高 / 前一根柱高  (通达信STICKLINE可视柱体比)
    # 红柱高 = bv - bp,  绿柱高 = bp - bv
    # 绿转红时: strength = 红柱高/前绿柱高 → >2/3为强红
    rc = np.zeros(len(bv), dtype=int)
    gc = np.zeros(len(bv), dtype=int)
    st = np.zeros(len(bv), dtype=float)
    r, g = 0, 0
    bv_arr = bv.to_numpy(); bp_arr = bp.to_numpy(); ir_arr = is_red.to_numpy()
    for i in range(len(bv)):
        if ir_arr[i]:
            r += 1; g = 0
        else:
            g += 1; r = 0
        rc[i], gc[i] = r, g
        cur_bar = abs(bv_arr[i] - bp_arr[i])
        prev_bar = abs(bv_arr[i-1] - bv_arr[i-2]) if i > 1 else 0
        st[i] = cur_bar / prev_bar if prev_bar > 0 else 0

    return pd.DataFrame({
        "brick_val": bv, "is_red": is_red,
        "green_to_red": g2r, "red_to_green": r2g,
        "red_count": rc, "green_count": gc, "strength": st,
    }, index=close.index)


def brick_signal(high, low, close, yl_val: float) -> dict:
    """砖型图买入信号（六要素检测）"""
    bc = calc_brick(high, low, close)
    L = bc.iloc[-1]
    bv, s = float(L["brick_val"]), float(L["strength"])
    g2r, red = bool(L["green_to_red"]), bool(L["is_red"])
    strong = s > BRICK_STRONG_RATIO
    above_yl = float(close.iloc[-1]) > yl_val

    if g2r:
        tag = f"绿转{'强' if strong else '弱'}红({s:.0%}){'🔥' if strong else '⚠️'}"
    elif L["red_to_green"]:
        tag = "红转绿❌"
    elif red:
        tag = f"红砖×{int(L['red_count'])}{'🔥' if int(L['red_count'])>=3 else ''}"
    else:
        tag = f"绿砖×{int(L['green_count'])}"

    return {
        "signal": g2r and above_yl,
        "strong": g2r and above_yl and strong,
        "g2r": g2r, "red": red, "strong_red": strong,
        "above_yl": above_yl,
        "val": round(bv, 2), "strength": round(s, 4),
        "red_n": int(L["red_count"]), "green_n": int(L["green_count"]),
        "tag": tag,
    }


# ====================================================================
# 6. 深V战法
# ====================================================================

def calc_deep_v(high, low, close, n1=DEEP_V_N1, n2=DEEP_V_N2) -> pd.DataFrame:
    c, h, l = close.astype(float), high.astype(float), low.astype(float)
    def _s(cc, hh, ll, nn):
        lo = llv(ll, nn); hi = hhv(hh, nn)
        return ((cc - lo) / (hi - lo).replace(0, np.nan) * 100).fillna(50)
    return pd.DataFrame({
        "short": _s(c,h,l,n1), "mid": _s(c,h,l,10),
        "mid_long": _s(c,h,l,20), "long": _s(c,h,l,n2),
    }, index=close.index)


def deep_v_signal(high, low, close) -> dict:
    dv = calc_deep_v(high, low, close)
    s, m, ml, lg = [float(dv[c].iloc[-1]) for c in ("short","mid","mid_long","long")]
    sigs = []
    if s<=6 and m<=6 and ml<=6 and lg<=6: sigs.append("四线归零买")
    if s<=20 and lg>=60: sigs.append("白线下20买")
    if len(dv)>=2:
        sp,lgp = float(dv["short"].iloc[-2]), float(dv["long"].iloc[-2])
        mp = float(dv["mid"].iloc[-2])
        if s>lg and sp<=lgp and lg<20: sigs.append("白穿红线买")
        if s>m and sp<=mp and m<30: sigs.append("白穿黄线买")
    return {"signals": sigs, "short": round(s,1), "mid": round(m,1),
            "mid_long": round(ml,1), "long": round(lg,1)}


# ====================================================================
# 7. 0AMV活跃市值
# ====================================================================

def calc_oamv(amount: pd.Series) -> pd.DataFrame:
    sm = sma_tdx(amount, OAMV_SMA_N, 1)
    prev = sm.shift(1)
    pct = ((sm - prev) / prev * 100).fillna(0)
    ma5 = sm.rolling(OAMV_MA_FAST, min_periods=1).mean()
    ma13 = sm.rolling(OAMV_MA_SLOW, min_periods=1).mean()
    return pd.DataFrame({"oamv": sm, "prev": prev, "pct": pct,
                         "red": sm > prev, "ma5": ma5, "ma13": ma13},
                        index=amount.index)


def oamv_status(amount: pd.Series, close: Optional[pd.Series] = None) -> dict:
    """大盘0AMV择时状态"""
    df = calc_oamv(amount)
    pct = float(df["pct"].iloc[-1])
    pct3 = float(df["pct"].tail(3).mean())
    is_red = bool(df["red"].iloc[-1])
    o, m5, m13 = float(df["oamv"].iloc[-1]), float(df["ma5"].iloc[-1]), float(df["ma13"].iloc[-1])

    # 连续红/绿计数
    rd, gd = 0, 0
    for i in range(len(df)-1, -1, -1):
        r = df["red"].iloc[i]
        if pd.isna(r): break
        if r:
            if gd: break
            rd += 1
        else:
            if rd: break
            gd += 1

    # 背离
    div = None
    if close is not None and len(close)>=10:
        ic = (float(close.iloc[-1])-float(close.iloc[-10]))/float(close.iloc[-10])*100
        oc = (o - float(df["oamv"].iloc[-10]))/float(df["oamv"].iloc[-10])*100 if float(df["oamv"].iloc[-10])>0 else 0
        if ic>2 and oc<-2: div="bear_div"
        elif ic<-2 and oc>2: div="bull_div"

    # 区域
    if o>m5 and m5>m13: zone="bull"
    elif o<m5 and m5<m13: zone="bear"
    else: zone="neutral"

    # 状态
    if pct<=OAMV_DANGER_PCT or pct3<=OAMV_DANGER_PCT:
        st, ok, cap = "DANGER", False, 0.0
    elif pct<=OAMV_CAUTION_PCT or zone=="bear":
        st, ok, cap = "CAUTION", True, 0.3
    elif zone=="bull" and pct>=OAMV_HEALTHY_PCT:
        st, ok, cap = "HEALTHY", True, 1.0
    else:
        st, ok, cap = "NEUTRAL", True, 0.6

    if div=="bear_div" and st in ("HEALTHY","NEUTRAL"):
        st, cap = "CAUTION", min(cap, 0.3)

    labels = {"DANGER": "🔴 活跃市值跌破-2.3%生死线，禁止买入",
              "CAUTION": f"🟡 活跃市值{pct:+.2f}%，仓位≤{cap*100:.0f}%",
              "HEALTHY": f"🟢 活跃市值{pct:+.2f}%，可正常操作",
              "NEUTRAL": f"⚪ 活跃市值{pct:+.2f}%，仓位≤{cap*100:.0f}%"}

    return {"status": st, "pct": round(pct,2), "pct3": round(pct3,2),
            "zone": zone, "red_days": rd, "green_days": gd,
            "divergence": div, "allow": ok, "cap": cap,
            "summary": labels[st]}


# ====================================================================
# 8. 多空趋势判断（日线+周线双级别）
# ====================================================================

def trend_status(daily_close: pd.Series, weekly_df: pd.DataFrame = None) -> dict:
    """多空趋势综合判断

    规则来源（Z哥体系）：
      - 日线白>黄 = 日线多头
      - 周线白>黄 = 周线多头（权重更高）
      - 短周期绝对服从长周期：日周矛盾时以周线为准
      - 周线空头排列 = 绝对不碰

    返回: {
      daily_bull, weekly_bull, trend, trend_label, trend_color,
      daily_wl, daily_yl, weekly_wl, weekly_yl, weekly_j
    }
    """
    # 日线
    d_wl = float(white_line(daily_close).iloc[-1])
    d_yl = float(yellow_line(daily_close).iloc[-1])
    d_cl = float(daily_close.iloc[-1])
    d_bull = d_wl > d_yl and d_cl > d_yl

    # 周线
    w_bull = None
    w_wl = w_yl = w_j = None
    if weekly_df is not None and len(weekly_df) >= 20:
        wc = weekly_df["close"]
        w_wl = float(white_line(wc).iloc[-1])
        w_yl = float(yellow_line(wc).iloc[-1])
        w_cl = float(wc.iloc[-1])
        w_bull = w_wl > w_yl and w_cl > w_yl
        # 周线KDJ
        wkdj = calc_kdj(weekly_df["high"], weekly_df["low"], wc)
        w_j = float(wkdj["J"].iloc[-1])

    # 综合判断
    if w_bull is not None:
        if w_bull and d_bull:
            trend, label, color = "strong_bull", "强多头", "green"
        elif w_bull and not d_bull:
            trend, label, color = "pullback", "周多日调", "blue"
        elif not w_bull and d_bull:
            trend, label, color = "bounce", "反弹", "orange"
        else:
            trend, label, color = "bear", "空头", "red"
    else:
        trend = "bull" if d_bull else "bear"
        label = "日线多头" if d_bull else "日线空头"
        color = "green" if d_bull else "red"

    return {
        "daily_bull": d_bull, "weekly_bull": w_bull,
        "trend": trend, "trend_label": label, "trend_color": color,
        "daily_wl": round(d_wl, 2), "daily_yl": round(d_yl, 2),
        "weekly_wl": round(w_wl, 2) if w_wl else None,
        "weekly_yl": round(w_yl, 2) if w_yl else None,
        "weekly_j": round(w_j, 1) if w_j is not None else None,
    }


# ====================================================================
# 9. 周线B1检测（千亿以上大市值）
# ====================================================================

def weekly_b1_check(weekly_df: pd.DataFrame) -> dict:
    """周线级别B1检测

    规则来源（Z哥体系）：
      - 主线股等周线B1（仓位管理01: "主题等日线B1、主线等周B1"）
      - 周线白>黄 + 价在黄线上 + J<16
      - 周线B1适合中长线投资者（仓位管理03）
      - 周线MACD配合判断

    返回: {signal, j, wl, yl, macd_cross, details}
    """
    if weekly_df is None or len(weekly_df) < 30:
        return {"signal": False, "j": None, "reason": "周线数据不足"}

    c = weekly_df["close"]
    wl = float(white_line(c).iloc[-1])
    yl = float(yellow_line(c).iloc[-1])
    cl = float(c.iloc[-1])

    kdj = calc_kdj(weekly_df["high"], weekly_df["low"], c)
    j = float(kdj["J"].iloc[-1])
    k = float(kdj["K"].iloc[-1])

    # 周线MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_cross = "金叉" if float(dif.iloc[-1]) > float(dea.iloc[-1]) else "死叉"

    # 检查条件
    bull = wl > yl
    above_yl = cl > yl
    j_oversold = j < 16

    signal = bull and above_yl and j_oversold
    near_b1 = bull and above_yl and j < 30  # 接近B1区域

    details = {
        "周线白>黄": bull,
        "价在周黄线上": above_yl,
        "周J<16超卖": j_oversold,
        "周MACD": macd_cross,
    }

    return {
        "signal": signal, "near_b1": near_b1,
        "j": round(j, 1), "k": round(k, 1),
        "wl": round(wl, 2), "yl": round(yl, 2),
        "macd_cross": macd_cross,
        "details": details,
    }


# ====================================================================
# 10. 板块识别
# ====================================================================

# 通达信 get_finance_info.industry 行业编码映射
# ⚠️ 修复说明（2026-04-20）：
# 原版编码表为错误的自创映射，已通过实盘验证校正。
# 验证方法：对已知行业股票批量调用 get_finance_info，对照真实分类归纳。
# 编码范围实测为 0-51，未覆盖到的编码统一兜底为"综合"。
TDX_INDUSTRY = {
    0:  "指数/板块",
    1:  "银行",
    2:  "非银金融",       # 券商/保险/多元金融
    3:  "建筑材料",
    4:  "建筑装饰",
    5:  "化工",
    6:  "交通运输",
    7:  "汽车",
    8:  "交通运输",       # 港口/铁路/公路
    9:  "医疗服务",
    10: "旅游酒店",
    11: "房地产",
    12: "商贸零售",
    13: "综合",
    14: "农林牧渔",
    15: "纺织服装",
    16: "公用事业",       # 电力/水务/燃气
    17: "农林牧渔",
    18: "传媒",
    19: "钢铁",
    20: "煤炭",
    21: "基础化工",
    22: "建筑装饰",
    23: "家用电器",
    24: "电子",           # 通信设备/光模块/电子元器件（实测：中兴/新易盛/天孚/亨通/烽火均为24）
    25: "计算机",
    26: "机械设备",
    27: "基础化工",
    28: "有色金属",
    29: "电力设备",       # 电气设备/新能源
    30: "环保",
    31: "仪器仪表",
    32: "传媒",
    33: "国防军工",
    34: "医药生物",
    35: "半导体",         # 实测：中芯国际/中微公司/立讯精密均为35
    36: "有色金属",       # 实测：紫金矿业为36
    37: "食品饮料",       # 实测：贵州茅台为37
    38: "纺织服装",
    39: "环保",
    40: "软件开发",
    41: "综合",
    42: "公用事业",
    43: "电力设备",       # 实测：宁德时代为43
    44: "光伏",
    45: "风电",
    46: "传媒",
    47: "教育",
    48: "建筑材料",       # 实测：南玻A为48
    49: "物流",
    50: "纺织",
    51: "电子",           # 实测：海康威视/汇川技术均为51（安防/工控归入电子大类）
}

# 行业缓存: code -> industry_name
_industry_cache: dict[str, str] = {}


def get_tdx_industry(api, mkt: int, code: str) -> str:
    """从通达信 finance_info 提取行业名称（带缓存）
    
    修复说明（2026-04-20）：
    - 字段名确认为 'industry'（pytdx实测确认，非'hy'）
    - 编码表已校正为实测映射（见 TDX_INDUSTRY）
    - 兜底值从 "综合" 统一保留，无匹配时返回 "综合"
    """
    if code in _industry_cache:
        return _industry_cache[code]
    try:
        fi = api.get_finance_info(mkt, code)
        # 字段名为 'industry'，值为整数编码
        ind_code = int(fi.get("industry", -1)) if fi else -1
        name = TDX_INDUSTRY.get(ind_code, "综合")
    except Exception:
        name = "综合"
    _industry_cache[code] = name
    return name


def batch_load_industries(api, stocks: list[tuple[int, str]]):
    """批量预加载行业 (mkt, code) -> cache, 减少逐个查询"""
    for mkt, code in stocks:
        if code not in _industry_cache:
            get_tdx_industry(api, mkt, code)


def lookup_sector(code: str, tdx_industry: str = "") -> dict:
    """根据股票代码查找所属板块/热度/阵容位置

    三层优先级：
      1. SECTOR_MAP  手动维护的高热度主题板块（含热度分加成）
      2. BlockReader 通达信本地文件行业数据（5500+只，真实行业名）
      3. API编码兜底  get_finance_info industry字段 + TDX_INDUSTRY表
    """
    from config import SECTOR_MAP, SECTOR_HEAT_BONUS
    code = code.strip()

    # ── 第一层：精准主题板块 ──
    for name, info in SECTOR_MAP.items():
        if code in info["codes"]:
            return {
                "sector": name,
                "tier":   info["tier"],
                "heat":   info["heat"],
                "bonus":  SECTOR_HEAT_BONUS.get(info["heat"], 0),
                "note":   info["note"],
            }

    # ── 第二层：BlockReader 本地 TDX 行业数据 ──
    try:
        from core.block_reader import get_block_reader
        reader = get_block_reader()
        t_name = reader.get_primary_industry(code)
        if t_name and t_name not in ("综合", ""):
            return {"sector": t_name, "tier": "未分类", "heat": 0, "bonus": 0, "note": "TDX本地行业"}
    except Exception:
        pass

    # ── 第三层：API 编码兜底 ──
    fallback = tdx_industry or _industry_cache.get(code, "综合")
    return {"sector": fallback, "tier": "未分类", "heat": 0, "bonus": 0, "note": "API兜底"}
