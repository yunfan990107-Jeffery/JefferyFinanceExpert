"""判断校准 / Brier 评分。

系统的灵魂：衡量"你说 80% 把握时，是否真有 80% 兑现"，并识别认知偏差。
纯函数，已实现，可直接用并被测试覆盖。
"""
from __future__ import annotations
from datetime import date, timedelta

HORIZON_DAYS = {"次日": 1, "一周": 7, "一月": 30, "半年": 182}
# 实际结果 -> 命中度（用于 Brier；部分正确记 0.5）
RESULT_HIT = {"正确": 1.0, "部分": 0.5, "错误": 0.0}


def make_verify_date(start: date, horizon: str) -> date:
    """根据时间范围推算验证日期。horizon 取 HORIZON_DAYS 的键。"""
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"未知时间范围: {horizon}")
    return start + timedelta(days=HORIZON_DAYS[horizon])


def brier_score(confidence_0_100: int, result: str) -> float:
    """Brier 分数：((置信度/100) - 命中度)^2，越低越准。

    confidence_0_100: 0-100 的整数置信度。
    result: '正确' / '部分' / '错误'。
    """
    if not 0 <= confidence_0_100 <= 100:
        raise ValueError("置信度必须在 0-100")
    if result not in RESULT_HIT:
        raise ValueError(f"未知结果: {result}")
    p = confidence_0_100 / 100.0
    hit = RESULT_HIT[result]
    return round((p - hit) ** 2, 4)


def calibration_summary(judgments: list[dict]) -> dict:
    """对一批已验证判断做汇总：平均 Brier、按置信度分桶的命中率、过度自信标记。

    judgments: 每条含 'confidence'(int) 与 'actual_result'(str)，仅统计已验证的。
    """
    verified = [j for j in judgments
                if j.get("actual_result") in RESULT_HIT and j.get("confidence") is not None]
    n = len(verified)
    if n == 0:
        return {"count": 0, "avg_brier": None, "buckets": {}, "overconfident": False}

    avg_brier = round(sum(brier_score(j["confidence"], j["actual_result"]) for j in verified) / n, 4)

    buckets: dict[str, dict] = {}
    for lo in (0, 20, 40, 60, 80):
        label = f"{lo}-{lo + 20}"
        grp = [j for j in verified if lo <= j["confidence"] < lo + 20 or (lo == 80 and j["confidence"] == 100)]
        if grp:
            hit_rate = round(sum(RESULT_HIT[j["actual_result"]] for j in grp) / len(grp), 3)
            buckets[label] = {"count": len(grp), "hit_rate": hit_rate}

    # 过度自信：高置信桶(>=60)的平均命中率显著低于其平均置信度
    high = [j for j in verified if j["confidence"] >= 60]
    overconfident = False
    if high:
        avg_conf = sum(j["confidence"] for j in high) / len(high) / 100.0
        avg_hit = sum(RESULT_HIT[j["actual_result"]] for j in high) / len(high)
        overconfident = (avg_conf - avg_hit) > 0.15
    return {"count": n, "avg_brier": avg_brier, "buckets": buckets, "overconfident": overconfident}


def build_review_prompt(judgment: dict, actual_note: str) -> str:
    """构造喂给"质量审查"AI 角色的复盘提示词。"""
    return (
        "请对以下到期判断做复盘（只分析、不给买卖建议）：\n"
        f"- 判断对象: {judgment.get('target', '')}\n"
        f"- 原始判断: {judgment.get('content', '')}\n"
        f"- 方向: {judgment.get('direction', '')}  置信度: {judgment.get('confidence', '')}/100\n"
        f"- 当时依据: {judgment.get('basis', '')}\n"
        f"- 反证条件: {judgment.get('falsify_cond', '')}\n"
        f"- 实际发生: {actual_note}\n\n"
        "输出：①对/错/部分 ②置信度是否校准（过度自信？）"
        "③证据是否充分、时间范围是否合理 ④是否有情绪/认知偏差 ⑤下次改进一条。"
    )


# ── P1 新增函数（不改既有签名）─────────────────────────────────

def monthly_calibration_report(judgments: list[dict]) -> dict:
    """生成月度校准报告：高置信准确率、平均 Brier、趋势。

    Args:
        judgments: 已验证的判断列表（含 confidence / actual_result / date）。

    Returns:
        {"period": str, "avg_brier": float, "overconfident": bool,
         "bias_types": str, "strength_areas": str, "sample_count": int}
    """
    summary = calibration_summary(judgments)
    n = summary["count"]
    if n == 0:
        return {
            "period": "", "avg_brier": 0.0, "overconfident": False,
            "bias_types": "", "strength_areas": "", "sample_count": 0,
        }

    # 偏差类型识别
    biases = []
    verified = [j for j in judgments
                if j.get("actual_result") in RESULT_HIT and j.get("confidence") is not None]

    # 过度自信（高置信低命中）
    if summary["overconfident"]:
        biases.append("过度自信")

    # 按方向偏差检测
    dir_stats: dict[str, list] = {}
    for j in verified:
        d = j.get("direction", "未知")
        dir_stats.setdefault(d, []).append(
            brier_score(j["confidence"], j["actual_result"])
        )
    for d, scores in dir_stats.items():
        if len(scores) >= 3 and sum(scores) / len(scores) > 0.4:
            biases.append(f"{d}方向偏差(Brier>{0.4:.2f})")

    # 擅长领域（Brier < 0.1）
    strengths = []
    target_stats: dict[str, list] = {}
    for j in verified:
        t = j.get("target", "未知")
        target_stats.setdefault(t, []).append(
            brier_score(j["confidence"], j["actual_result"])
        )
    for t, scores in target_stats.items():
        if len(scores) >= 2:
            avg = sum(scores) / len(scores)
            if avg < 0.1:
                strengths.append(t)

    # 月度区间
    dates = [j.get("date", "") for j in verified if j.get("date")]
    period = f"{min(dates)} ~ {max(dates)}" if dates else ""

    return {
        "period": period,
        "avg_brier": summary["avg_brier"] or 0.0,
        "overconfident": summary["overconfident"],
        "bias_types": "、".join(biases) if biases else "无明显偏差",
        "strength_areas": "、".join(strengths) if strengths else "暂无足够数据",
        "sample_count": n,
    }


def detect_bias_by_target(judgments: list[dict]) -> dict:
    """按标的类型检测系统性偏差。

    Returns:
        {target: {"count": int, "avg_brier": float, "hit_rate": float}, ...}
    """
    verified = [j for j in judgments
                if j.get("actual_result") in RESULT_HIT and j.get("confidence") is not None]
    result: dict[str, dict] = {}
    for j in verified:
        t = j.get("target", "未知")
        if t not in result:
            result[t] = {"count": 0, "brier_sum": 0.0, "hit_sum": 0.0}
        result[t]["count"] += 1
        result[t]["brier_sum"] += brier_score(j["confidence"], j["actual_result"])
        result[t]["hit_sum"] += RESULT_HIT[j["actual_result"]]

    output = {}
    for t, stats in result.items():
        n = stats["count"]
        output[t] = {
            "count": n,
            "avg_brier": round(stats["brier_sum"] / n, 4),
            "hit_rate": round(stats["hit_sum"] / n, 3),
        }
    return output
