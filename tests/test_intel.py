"""core/intel.py 单测：新闻分级/摘要解析（monkeypatch 掉 LLM 调用，不触发网络）。"""
from core import intel


def test_classify_news_must_read(monkeypatch):
    monkeypatch.setattr(intel, "chat",
                        lambda *a, **k: "重要性：必读\n摘要：【公司营收同比+20%】")
    importance, summary = intel._classify_news({"title": "某公司财报", "source": "财联社", "time": "2026-06-23"})
    assert importance == "必读"
    assert "营收" in summary


def test_classify_news_ignore(monkeypatch):
    monkeypatch.setattr(intel, "chat",
                        lambda *a, **k: "重要性：忽略\n摘要：【无关紧要】")
    importance, _ = intel._classify_news({"title": "八卦", "source": "x", "time": ""})
    assert importance == "忽略"


def test_classify_news_default_readable(monkeypatch):
    # 无法解析时降级为"可读"
    monkeypatch.setattr(intel, "chat", lambda *a, **k: "无格式输出")
    importance, summary = intel._classify_news({"title": "标题XYZ", "source": "x", "time": ""})
    assert importance == "可读"
    assert summary  # 用标题兜底
