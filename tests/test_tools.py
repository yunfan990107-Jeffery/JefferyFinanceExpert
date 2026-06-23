"""core/tools.py 单测：工具注册、schema、技术指标计算。"""
from core import tools


def test_register_and_get_schema():
    tools.register(
        "_dummy_tool", lambda x: x * 2, "测试工具",
        {"x": {"type": "integer", "description": "输入"}},
    )
    assert "_dummy_tool" in tools.TOOL_REGISTRY
    assert tools.TOOL_REGISTRY["_dummy_tool"](3) == 6
    schemas = tools.get_schemas(["_dummy_tool"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "_dummy_tool"
    assert "x" in schemas[0]["function"]["parameters"]["properties"]


def test_get_schemas_skips_unknown():
    assert tools.get_schemas(["__nonexistent__"]) == []


def test_data_fetcher_tools_preregistered():
    for name in ("get_price", "get_kline", "get_fundamentals", "get_news"):
        assert name in tools.TOOL_REGISTRY


def test_calc_indicators_insufficient_data():
    out = tools.calc_indicators([{"close": 10, "high": 10, "low": 9}] * 5)
    assert "error" in out


def test_calc_indicators_normal():
    kline = [
        {"date": f"d{i}", "open": 10, "high": 10 + (i % 3),
         "low": 9, "close": 10 + (i % 5), "volume": 100}
        for i in range(30)
    ]
    out = tools.calc_indicators(kline)
    assert "error" not in out
    for key in ("ma5", "ma20", "macd_dif", "kdj_k", "kdj_j", "latest_close"):
        assert key in out
    assert out["ma5"] is not None
