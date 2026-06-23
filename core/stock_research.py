"""个股深度研究流程编排（可配置流水线）。

加专员 = 清单加一行 + 配置加一项，不改 runner 主体。
"""
from __future__ import annotations
from datetime import date

from . import data_fetcher
from .feishu_client import FeishuClient
from .config import config
from .llm_client import chat, load_role
from agents.registry import get_agent

# ── 流水线定义 ─────────────────────────────────────────────────
# 每个步骤：{agent: 角色名, task: 任务标签, max_tokens: int}
STOCK_RESEARCH_PIPELINE = [
    {"agent": "quality_review", "task": "draft", "max_tokens": 1500},
    {"agent": "technical_analysis", "task": "technical_analysis", "max_tokens": 600},
    {"agent": "devil_advocate", "task": "devil_advocate", "max_tokens": 1000},
    {"agent": "risk_control", "task": "risk_control", "max_tokens": 1000},
    {"agent": "quality_review", "task": "summary", "max_tokens": 2000},
]


def research_stock(code: str) -> dict:
    """对单只 A 股执行完整研究流程，写入飞书研究库。

    Args:
        code: 6 位股票代码。

    Returns:
        {"code": ..., "memo": {...}, "record_id": ..., "final_memo": ...}
    """
    today = date.today().isoformat()

    # ── 数据采集（一次性取数进缓存）────────────────────────────
    price_info = data_fetcher.get_price(code)
    kline = data_fetcher.get_kline(code, days=300)
    fundamentals = data_fetcher.get_fundamentals(code)
    name = price_info.get("name", code)

    data_summary = _build_data_summary(code, name, price_info, kline, fundamentals)

    # ── 流水线执行 ─────────────────────────────────────────────
    context: dict[str, str] = {"data_summary": data_summary, "code": code, "name": name}

    for step in STOCK_RESEARCH_PIPELINE:
        agent_spec = get_agent(step["agent"])
        system_prompt = agent_spec.prompt if agent_spec else load_role(f"{step['agent']}.md")
        user_prompt = _build_step_prompt(step["task"], context)
        result = chat(system_prompt, user_prompt, max_tokens=step["max_tokens"])
        context[step["task"]] = result

    # ── 写入飞书研究库 ─────────────────────────────────────────
    memo = _build_memo(code, name, today, context)
    try:
        rid = FeishuClient().add_record(config.table_research, memo)
    except Exception as e:
        rid = f"(写入失败: {e})"

    return {
        "code": code,
        "memo": memo,
        "record_id": rid,
        "final_memo": context.get("summary", ""),
    }


def _build_step_prompt(task: str, ctx: dict) -> str:
    """根据任务标签构建 user prompt。"""
    ds = ctx.get("data_summary", "")
    code = ctx.get("code", "")
    name = ctx.get("name", "")

    if task == "draft":
        return (
            f"请对以下 A 股标的数据做初步研究分析（非买卖建议）。\n\n{ds}\n\n"
            "按结构输出：## 公司与业务概览\n## 财务健康度\n## 估值分析\n"
            "## 核心优势与护城河\n## 关键假设与不确定性\n## 数据来源\n"
            "注意：关键事实标注来源；结论非买卖指令。"
        )
    elif task == "devil_advocate":
        draft = ctx.get("draft", "")
        return (
            f"标的：{name}（{code}）\n\n研究草稿：\n{draft}\n\n{ds[:300]}"
        )
    elif task == "technical_analysis":
        draft = ctx.get("draft", "")
        return (
            f"标的：{name}（{code}）\n\n研究草稿摘要：\n{draft[:500]}\n\n"
            f"K线数据（近5日）：\n{ds.split('近')[0] if '近' in ds else ds[:300]}"
        )
    elif task == "risk_control":
        return (
            f"标的：{name}（{code}）\n"
            f"研究草稿：\n{ctx.get('draft','')}\n"
            f"反方观点：\n{ctx.get('devil_advocate','')}"
        )
    elif task == "summary":
        return (
            f"请整合以下各部分为完整研究备忘录（非买卖建议）：\n\n"
            f"--- 研究草稿 ---\n{ctx.get('draft','')}\n\n"
            f"--- 反方观点 ---\n{ctx.get('devil_advocate','')}\n\n"
            f"--- 风险评估 ---\n{ctx.get('risk_control','')}\n\n"
            f"确保：关键事实带来源、含反方、含风险与证伪条件、标注不确定性、结论非买卖指令。"
        )
    return f"标的：{name}（{code}）\n\n{ds}"


def _build_memo(code: str, name: str, today: str, ctx: dict) -> dict:
    def _trunc(s, n=500):
        return (s or "")[:n]
    return {
        "code": code, "name": name, "date": today,
        "business": _trunc(_extract_section(ctx.get("draft",""), "业务概览") or ctx.get("draft","")[:500]),
        "financials": _trunc(_extract_section(ctx.get("draft",""), "财务健康度")),
        "valuation": _trunc(_extract_section(ctx.get("draft",""), "估值分析")),
        "moat": _trunc(_extract_section(ctx.get("draft",""), "核心优势")),
        "assumptions": _trunc(_extract_section(ctx.get("draft",""), "关键假设")),
        "reverse_view": _trunc(ctx.get("devil_advocate","")),
        "risks": _trunc(ctx.get("risk_control","")),
        "falsify": _trunc(_extract_section(ctx.get("risk_control",""), "证伪条件") or _extract_section(ctx.get("devil_advocate",""), "证伪条件")),
        "conclusion": _trunc(_extract_section(ctx.get("summary",""), "综合结论") or ctx.get("summary","")[:500]),
        "sources": _trunc(_extract_section(ctx.get("draft",""), "数据来源")),
        "confidence": "中",
    }


def _build_data_summary(code, name, price_info, kline, fundamentals):
    lines = [
        f"标的：{name}（{code}）",
        f"最新价：{price_info.get('price')} PE：{price_info.get('pe')} PB：{price_info.get('pb')}",
    ]
    indicators = fundamentals.get("indicators", {})
    if indicators:
        lines.append("财务指标：" + "、".join(f"{k}={v}" for k, v in indicators.items()))
    if kline:
        closes = [k["close"] for k in kline]
        lines.append(f"近{len(kline)}日K线：最高{max(closes):.2f} 最低{min(closes):.2f} 均值{sum(closes)/len(closes):.2f}")
    return "\n".join(lines)


def _extract_section(text: str, keyword: str) -> str:
    if not text:
        return ""
    for line in text.split("\n"):
        if keyword in line and line.strip().startswith("#"):
            idx = text.index(line)
            rest = text[idx + len(line):]
            next_idx = rest.find("\n##")
            if next_idx > 0:
                return rest[:next_idx].strip()[:500]
            return rest.strip()[:500]
    return ""
