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
    """绩效归因：把盈亏拆成'判断对不对'与'执行对不对'。

    TODO(P1): 结合 linked_judgment 的方向/置信度与实际盈亏，区分判断质量与执行质量。
    """
    raise NotImplementedError("绩效归因在 P1 实现，见 docs/tasks (P1)")
