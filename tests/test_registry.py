"""agents/registry.py 单测：frontmatter 解析、agent 查找。"""
from agents import registry


def test_parse_frontmatter_with_meta():
    text = (
        "---\n"
        "name: foo\n"
        "team: research\n"
        "tools: [get_price, get_kline]\n"
        "---\n"
        "正文提示词。"
    )
    meta, prompt = registry._parse_frontmatter(text)
    assert meta["name"] == "foo"
    assert meta["team"] == "research"
    assert meta["tools"] == ["get_price", "get_kline"]
    assert prompt.strip() == "正文提示词。"


def test_parse_frontmatter_without_meta():
    meta, prompt = registry._parse_frontmatter("没有 frontmatter 的纯文本")
    assert meta == {}
    assert "纯文本" in prompt


def test_get_agent_real_file():
    spec = registry.get_agent("devil_advocate")
    assert spec is not None
    assert spec.name == "devil_advocate"
    assert spec.prompt  # 非空提示词


def test_get_agent_unknown():
    assert registry.get_agent("__no_such_agent__") is None


def test_list_agents_nonempty():
    agents = registry.list_agents()
    assert len(agents) >= 3
    assert all(a.name for a in agents)


def test_list_agents_team_filter_empty():
    assert registry.list_agents(team="__no_such_team__") == []
