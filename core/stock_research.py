"""个股深度研究流程编排。

流程：数据采集 → 草稿 → 反方论证 → 风险评估 → 质量汇总 → 入库。
全程通过 core/llm_client 调用 AI，不自行写 requests。
"""
from __future__ import annotations
from datetime import date

from . import data_fetcher
from .feishu_client import FeishuClient
from .config import config
from .llm_client import chat, load_role


def research_stock(code: str) -> dict:
    """对单只 A 股执行完整研究流程，写入飞书研究库，返回 memo dict。

    Args:
        code: 6 位股票代码，如 '000001'。

    Returns:
        {"code": ..., "memo": {...}, "record_id": ...}
    """
    today = date.today().isoformat()

    # ── 1. 数据采集 ──────────────────────────────────────────
    price_info = data_fetcher.get_price(code)
    kline = data_fetcher.get_kline(code, days=300)
    fundamentals = data_fetcher.get_fundamentals(code)

    name = price_info.get("name", code)
    price = price_info.get("price")
    pe = price_info.get("pe")
    pb = price_info.get("pb")

    # 构建数据摘要
    data_summary = _build_data_summary(code, name, price, pe, pb, kline, fundamentals)

    # ── 2. 研究草稿 ──────────────────────────────────────────
    draft = chat(
        load_role("quality_review.md"),
        f"""请对以下 A 股标的数据做初步研究分析（非买卖建议）。

{data_summary}

请按以下结构输出：
## 公司与业务概览
## 财务健康度
## 估值分析
## 核心优势与护城河
## 关键假设与不确定性
## 数据来源

注意：关键事实必须标注来源；结论是研究判断+条件，非买卖指令。""",
        max_tokens=1500,
    )

    # ── 3. 反方论证 ──────────────────────────────────────────
    reverse_view = chat(
        load_role("devil_advocate.md"),
        f"标的：{name}（{code}）\n\n研究草稿如下：\n\n{draft}\n\n"
        f"补充数据：当前价 {price}，PE {pe}，PB {pb}",
        max_tokens=1000,
    )

    # ── 4. 风险评估 ──────────────────────────────────────────
    risk_assessment = chat(
        load_role("risk_control.md"),
        f"标的：{name}（{code}）\n当前价 {price}，PE {pe}，PB {pb}\n\n"
        f"研究草稿：\n{draft}\n\n反方观点：\n{reverse_view}",
        max_tokens=1000,
    )

    # ── 5. 质量汇总 ──────────────────────────────────────────
    final_memo = chat(
        load_role("quality_review.md"),
        f"请将以下各部分整合为一份完整的研究备忘录（非买卖建议）：\n\n"
        f"--- 研究草稿 ---\n{draft}\n\n"
        f"--- 反方观点 ---\n{reverse_view}\n\n"
        f"--- 风险评估 ---\n{risk_assessment}\n\n"
        f"整合后按研究备忘录格式输出，确保：关键事实带来源、含反方观点、"
        f"含风险与证伪条件、标注不确定性、结论非买卖指令。",
        max_tokens=2000,
    )

    # ── 6. 写入飞书研究库 ────────────────────────────────────
    def _trunc(s, n=500):
        return (s or "")[:n]

    memo = {
        "code": code, "name": name, "date": today,
        "business": _trunc(_extract_section(draft, "公司与业务概览") or draft[:500]),
        "financials": _trunc(_extract_section(draft, "财务健康度")),
        "valuation": _trunc(_extract_section(draft, "估值分析")),
        "moat": _trunc(_extract_section(draft, "核心优势")),
        "assumptions": _trunc(_extract_section(draft, "关键假设")),
        "reverse_view": _trunc(reverse_view),
        "risks": _trunc(risk_assessment),
        "falsify": _trunc(_extract_section(risk_assessment, "证伪条件") or _extract_section(reverse_view, "证伪条件")),
        "conclusion": _trunc(_extract_section(final_memo, "综合结论") or final_memo[:500]),
        "sources": _trunc(_extract_section(draft, "数据来源")),
        "confidence": "中",
    }

    try:
        rid = FeishuClient().add_record(config.table_research, memo)
    except Exception as e:
        rid = f"(写入失败: {e})"

    return {"code": code, "memo": memo, "record_id": rid, "final_memo": final_memo}


def _build_data_summary(
    code: str, name: str, price, pe, pb, kline: list, fundamentals: dict
) -> str:
    """构建供 LLM 使用的数据摘要文本。"""
    lines = [
        f"标的：{name}（{code}）",
        f"最新价：{price}　PE：{pe}　PB：{pb}",
    ]
    indicators = fundamentals.get("indicators", {})
    if indicators:
        lines.append("财务指标：" + "、".join(f"{k}={v}" for k, v in indicators.items()))
    if kline:
        recent = kline[-5:]
        lines.append("近5日K线：")
        for k in recent:
            lines.append(
                f"  {k['date']} O{k['open']} H{k['high']} L{k['low']} C{k['close']} V{k['volume']}"
            )
        # 简单统计
        closes = [k["close"] for k in kline]
        lines.append(
            f"近{days}日：最高 {max(closes):.2f} 最低 {min(closes):.2f} "
            f"均值 {sum(closes)/len(closes):.2f}"
        )
    return "\n".join(lines)


def _extract_section(text: str, keyword: str) -> str:
    """从 LLM 输出中提取指定小节内容（取 ## 标题后的段落）。"""
    if not text:
        return ""
    for line in text.split("\n"):
        if keyword in line and line.strip().startswith("#"):
            idx = text.index(line)
            rest = text[idx + len(line):]
            # 取到下一个 ## 标题或 500 字符
            next_idx = rest.find("\n##")
            if next_idx > 0:
                return rest[:next_idx].strip()[:500]
            return rest.strip()[:500]
    return ""
