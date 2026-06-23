"""信息筛选 —— 抓取行业/市场信息，去重、分级、关联资产，写入飞书 intel 表。

流程：取新闻 → AI 分级/摘要 → 去重 → 写 intel 表。
"""
from __future__ import annotations
from datetime import date

from . import data_fetcher
from .feishu_client import FeishuClient
from .config import config
from .llm_client import chat, load_role


def fetch_and_process(keyword: str, limit: int = 10) -> list[dict]:
    """抓取并处理新闻：去重→分级→入库。

    Returns:
        已入库的新闻列表 [{title, source, time, importance, summary, record_id}, ...]
    """
    # 1. 取原始新闻
    raw_news = data_fetcher.get_news(keyword, limit=limit)
    if not raw_news:
        return []

    # 2. 去重（按标题相似度简单去重）
    seen_titles = set()
    deduped = []
    for n in raw_news:
        t = n.get("title", "")
        # 简单去重：前 30 字符
        key = t[:30]
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(n)

    # 3. AI 分级 + 摘要
    processed = []
    for n in deduped[:limit]:
        importance, summary = _classify_news(n)
        n["importance"] = importance
        n["summary"] = summary
        processed.append(n)

    # 4. 写入 intel 表
    fc = FeishuClient()
    today = date.today().isoformat()
    results = []
    for n in processed:
        fields = {
            "intel_id": f"INTEL-{today}-{n.get('time','')[:10]}",
            "date": today,
            "source": n.get("source", ""),
            "title": n.get("title", "")[:200],
            "content": f"[{n.get('importance','')}] {n.get('summary','')}"[:500],
        }
        try:
            rid = fc.add_record(config.table_intel, fields)
            n["record_id"] = rid
        except Exception:
            n["record_id"] = ""
        results.append(n)

    return results


def _classify_news(news: dict) -> tuple[str, str]:
    """用 AI 对新闻做重要性分级和摘要。

    Returns:
        (importance: 必读/可读/忽略, summary: str)
    """
    title = news.get("title", "")
    source = news.get("source", "")
    time_str = news.get("time", "")

    prompt = (
        f"请对以下财经新闻做分级和摘要（非买卖建议）：\n\n"
        f"标题：{title}\n来源：{source}\n时间：{time_str}\n\n"
        f"请按以下格式输出（只输出这两行）：\n"
        f"重要性：【必读/可读/忽略】\n"
        f"摘要：【一句话摘要，含关键数字】"
    )

    response = chat(
        load_role("quality_review.md"),
        prompt,
        max_tokens=200,
    )

    # 解析
    importance = "可读"
    summary = title[:100]
    for line in response.split("\n"):
        if "必读" in line:
            importance = "必读"
        elif "忽略" in line:
            importance = "忽略"
        elif "摘要" in line and "【" in line:
            summary = line.split("】")[-1].strip()[:200] if "】" in line else line.strip()[:200]

    return importance, summary
