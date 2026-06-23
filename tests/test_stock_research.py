"""core/stock_research.py 单测：纯辅助函数（不触发 LLM/网络）。

含对 _build_data_summary 的回归测试——曾因未定义变量 `days` 在 kline 非空时崩溃。
"""
from core import stock_research as sr


def test_pipeline_structure():
    assert isinstance(sr.STOCK_RESEARCH_PIPELINE, list) and sr.STOCK_RESEARCH_PIPELINE
    for step in sr.STOCK_RESEARCH_PIPELINE:
        assert "agent" in step and "task" in step and "max_tokens" in step


def test_build_data_summary_with_kline_does_not_crash():
    """回归：kline 非空时不得抛 NameError(days 未定义)。"""
    price = {"price": 10.5, "pe": 8, "pb": 1.2, "name": "测试股"}
    kline = [{"close": 10 + i * 0.1, "high": 11, "low": 9} for i in range(20)]
    fundamentals = {"indicators": {"ROE": "12%"}}
    out = sr._build_data_summary("000001", "测试股", price, kline, fundamentals)
    assert "测试股" in out
    assert "K线" in out  # 走到了 kline 分支且未崩溃


def test_build_data_summary_empty_kline():
    out = sr._build_data_summary("000001", "x", {"price": 1}, [], {"indicators": {}})
    assert "000001" in out


def test_extract_section():
    text = "## 业务概览\n这是业务内容\n## 财务健康度\n这是财务"
    assert "业务内容" in sr._extract_section(text, "业务概览")
    assert sr._extract_section(text, "不存在的小节") == ""
    assert sr._extract_section("", "任意") == ""


def test_build_step_prompt_tasks():
    ctx = {"data_summary": "DS", "code": "000001", "name": "测试股",
           "draft": "草稿", "devil_advocate": "反方", "risk_control": "风险"}
    for task in ("draft", "devil_advocate", "technical_analysis", "risk_control", "summary"):
        p = sr._build_step_prompt(task, ctx)
        assert isinstance(p, str) and len(p) > 0


def test_build_memo_keys():
    ctx = {"draft": "## 业务概览\nA\n## 数据来源\n年报", "devil_advocate": "反方",
           "risk_control": "风险", "summary": "## 综合结论\n结论"}
    memo = sr._build_memo("000001", "测试股", "2026-06-23", ctx)
    for key in ("code", "name", "date", "business", "reverse_view", "risks", "conclusion", "confidence"):
        assert key in memo
    assert memo["code"] == "000001"
