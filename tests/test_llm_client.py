"""core/llm_client.py 单测：load_role + 未配置时的降级路径（不触发网络）。"""
from core import llm_client
from core.config import config


def test_load_role_existing():
    txt = llm_client.load_role("quality_review.md")
    assert isinstance(txt, str) and len(txt) > 0


def test_load_role_missing_fallback():
    txt = llm_client.load_role("__no_such_role__.md")
    assert isinstance(txt, str) and len(txt) > 0  # 返回兜底文本，不报错


def test_chat_degrades_without_key(monkeypatch):
    # 模拟未配置 LLM：chat 应返回带提示词的降级文本，而非发网络请求
    monkeypatch.setattr(type(config), "llm_ready", lambda self: False)
    out = llm_client.chat("系统提示", "用户提示词内容")
    assert "未配置" in out
    assert "用户提示词内容" in out


def test_chat_with_tools_degrades_without_key(monkeypatch):
    monkeypatch.setattr(type(config), "llm_ready", lambda self: False)
    out = llm_client.chat_with_tools("系统", "问题内容", ["get_price"])
    assert isinstance(out, str) and len(out) > 0
