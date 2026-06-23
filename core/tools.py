"""工具注册表 + OpenAI function-calling schema。

"装 skill" 只需 TOOL_REGISTRY[name] = fn。
TOOL_REGISTRY 的 key 对应 agent frontmatter 的 tools 字段。
"""
from __future__ import annotations
from typing import Callable

TOOL_REGISTRY: dict[str, Callable] = {}

# 工具 schema（OpenAI function-calling 格式）
_SCHEMAS: dict[str, dict] = {}


def register(name: str, fn: Callable, description: str, parameters: dict) -> None:
    """注册一个工具。

    Args:
        name: 工具名（对应 agent frontmatter 的 tools 列表项）。
        fn: 可调用对象。
        description: 工具描述（给 LLM 看的）。
        parameters: JSON Schema 格式的参数定义。
    """
    TOOL_REGISTRY[name] = fn
    _SCHEMAS[name] = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": list(parameters.keys()),
            },
        },
    }


def get_schemas(names: list[str]) -> list[dict]:
    """取指定工具的 OpenAI function schema 列表。"""
    return [_SCHEMAS[n] for n in names if n in _SCHEMAS]


# ── 预注册 data_fetcher 工具 ──────────────────────────────────

try:
    from . import data_fetcher

    register(
        "get_price",
        data_fetcher.get_price,
        "获取 A 股最新价、PE、PB",
        {"code": {"type": "string", "description": "6 位股票代码，如 000001"}},
    )
    register(
        "get_kline",
        lambda code, days=300: data_fetcher.get_kline(code, days),
        "获取日 K 线数据，含 date/open/high/low/close/volume",
        {
            "code": {"type": "string", "description": "6 位股票代码"},
            "days": {"type": "integer", "description": "天数，默认 300"},
        },
    )
    register(
        "get_fundamentals",
        data_fetcher.get_fundamentals,
        "获取关键财务指标（ROE/净利率/负债率等）",
        {"code": {"type": "string", "description": "6 位股票代码"}},
    )
    register(
        "get_news",
        lambda keyword, limit=20: data_fetcher.get_news(keyword, limit),
        "获取相关新闻",
        {
            "keyword": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回条数，默认 20"},
        },
    )
except ImportError:
    pass


# ── 技术指标工具（T2-1 验证用）────────────────────────────────

def calc_indicators(kline: list[dict]) -> dict:
    """计算 MA/MACD/KDJ。

    Args:
        kline: [{date, open, high, low, close, volume}, ...]

    Returns:
        {"ma5": ..., "ma20": ..., "macd": ..., "kdj_k": ..., "kdj_d": ...}
    """
    if len(kline) < 26:
        return {"error": f"K 线数据不足（需要≥26条，当前{len(kline)}条）"}

    closes = [k["close"] for k in kline]

    def _sma(data, n):
        if len(data) < n:
            return None
        return round(sum(data[-n:]) / n, 2)

    # MA
    ma5 = _sma(closes, 5)
    ma20 = _sma(closes, 20)

    # MACD (12, 26, 9)
    def _ema(data, n):
        if len(data) < n:
            return None
        k = 2 / (n + 1)
        ema = sum(data[:n]) / n
        for x in data[n:]:
            ema = x * k + ema * (1 - k)
        return round(ema, 2)

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = round(ema12 - ema26, 2) if ema12 and ema26 else None
    # 简化 MACD（不计算完整 DEA 序列，只取当前近似）
    macd = dif

    # KDJ (9, 3, 3)
    n = min(9, len(kline))
    highs = [k["high"] for k in kline[-n:]]
    lows = [k["low"] for k in kline[-n:]]
    hh = max(highs)
    ll = min(lows)
    rsv = round((closes[-1] - ll) / (hh - ll) * 100, 2) if hh != ll else 50.0
    k = rsv  # 简化 K=RSV
    d = k  # 简化 D=K
    j = round(3 * k - 2 * d, 2)

    return {
        "ma5": ma5, "ma20": ma20,
        "macd_dif": macd,
        "kdj_k": k, "kdj_d": d, "kdj_j": j,
        "latest_close": closes[-1] if closes else None,
    }


register(
    "calc_indicators",
    calc_indicators,
    "计算 MA/MACD/KDJ 技术指标。输入 K 线列表，返回各指标当前值。",
    {
        "kline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "open": {"type": "number"},
                    "high": {"type": "number"},
                    "low": {"type": "number"},
                    "close": {"type": "number"},
                    "volume": {"type": "number"},
                },
            },
            "description": "K 线数据列表",
        },
    },
)
