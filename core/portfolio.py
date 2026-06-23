"""持仓与绩效归因。

compute_position_metrics / concentration 已实现；attribution 待 P1（需关联判断质量）。
"""
from __future__ import annotations


def compute_position_metrics(positions: list[dict], prices: dict[str, float]) -> list[dict]:
    """计算每个持仓的市值、盈亏%、仓位占比。

    positions: 每条含 code, qty, cost。
    prices: {code: 现价}；缺失则用 cost 兜底。
    返回在原 dict 基础上补充 market_value / pnl_pct / weight 的新列表。
    """
    enriched = []
    for p in positions:
        price = prices.get(p["code"], p["cost"])
        mv = price * p["qty"]
        pnl = (price - p["cost"]) / p["cost"] if p["cost"] else 0.0
        enriched.append({**p, "price": price, "market_value": round(mv, 2),
                         "pnl_pct": round(pnl * 100, 2)})
    total = sum(e["market_value"] for e in enriched) or 1.0
    for e in enriched:
        e["weight"] = round(e["market_value"] / total * 100, 2)
    return enriched


def concentration(positions_with_metrics: list[dict]) -> dict:
    """组合集中度：单标最大占比 + 行业占比。用于风险提示。"""
    if not positions_with_metrics:
        return {"max_single_weight": 0.0, "by_industry": {}}
    max_single = max(e.get("weight", 0) for e in positions_with_metrics)
    by_industry: dict[str, float] = {}
    for e in positions_with_metrics:
        ind = e.get("industry", "未分类")
        by_industry[ind] = round(by_industry.get(ind, 0) + e.get("weight", 0), 2)
    return {"max_single_weight": max_single, "by_industry": by_industry}


def attribution(position: dict, linked_judgment: dict | None) -> dict:
    """绩效归因：把盈亏拆成「判断对不对」与「执行对不对」。

    Args:
        position: 持仓记录（含 pnl_pct, linked_judgment_id 等）。
        linked_judgment: 关联的判断记录（含 direction/confidence/actual_result/brier_score）。
                         为 None 时表示无关联判断。

    Returns:
        {"judgment_score": float|None,    # Brier 分数（越低越好）
         "judgment_correct": bool|None,   # 判断方向对不对（None=无关联）
         "execution_quality": str,        # 好/幸运/执行问题/一致/无关联
         "pnl_pct": float,                # 盈亏%
         "note": str}                     # 归因说明
    """
    pnl = position.get("pnl_pct", 0.0)

    # 无关联判断
    if linked_judgment is None:
        return {
            "judgment_score": None,
            "judgment_correct": None,
            "execution_quality": "无关联",
            "pnl_pct": pnl,
            "note": "该持仓未关联判断，无法做归因分析。建议在录入持仓时关联对应的判断ID。",
        }

    # 判断质量
    direction = linked_judgment.get("direction", "")
    actual = linked_judgment.get("actual_result", "")
    confidence = linked_judgment.get("confidence")
    brier = linked_judgment.get("brier_score")

    # 判断是否正确（actual_result 为"正确"或"部分"=方向对）
    correct = actual in ("正确", "部分")

    # Brier 分数（如有）
    from .calibration import brier_score as _brier
    js = None
    if confidence is not None and actual in ("正确", "部分", "错误"):
        try:
            js = _brier(int(confidence), actual)
        except (ValueError, TypeError):
            pass

    # 执行质量
    if correct and pnl > 0:
        eq = "好"
        note = "判断方向准确且盈利，判断与执行一致。"
    elif correct and pnl <= 0:
        eq = "执行问题"
        note = "判断方向准确但未盈利（可能择时/仓位/止损问题）。"
    elif not correct and pnl > 0:
        eq = "幸运"
        note = "判断方向错误但因其他因素盈利，不具可持续性。"
    else:
        eq = "一致"
        note = "判断方向错误且亏损，判断与执行一致。"

    return {
        "judgment_score": js,
        "judgment_correct": correct,
        "execution_quality": eq,
        "pnl_pct": pnl,
        "note": note,
    }


def portfolio_attribution(positions: list[dict], judgments: dict[str, dict]) -> dict:
    """组合级绩效归因汇总。

    Args:
        positions: 含 pnl_pct / linked_judgment_id 的持仓列表。
        judgments: {judgment_id: judgment_dict} 的查找表。

    Returns:
        {"total_positions": int, "with_link": int, "without_link": int,
         "execution_summary": {quality: count, ...},
         "avg_judgment_score": float|None}
    """
    results = []
    for p in positions:
        jid = p.get("linked_judgment_id", "")
        j = judgments.get(jid) if jid else None
        results.append(attribution(p, j))

    total = len(results)
    with_link = sum(1 for r in results if r["judgment_correct"] is not None)
    without_link = total - with_link

    exec_summary: dict[str, int] = {}
    for r in results:
        eq = r["execution_quality"]
        exec_summary[eq] = exec_summary.get(eq, 0) + 1

    scores = [r["judgment_score"] for r in results if r["judgment_score"] is not None]
    avg_score = round(sum(scores) / len(scores), 4) if scores else None

    return {
        "total_positions": total,
        "with_link": with_link,
        "without_link": without_link,
        "execution_summary": exec_summary,
        "avg_judgment_score": avg_score,
    }
