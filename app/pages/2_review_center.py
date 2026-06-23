"""页面②：复盘中心。对应 FR-J-3/J-4 / FR-U-2。

闭环：列出到期判断 → 填实际结果 → 算 Brier → LLM 质量审查 → 写回飞书。
原始判断字段（content/confidence/direction/basis/falsify_cond 等）不可改写。
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from core import calibration  # noqa: E402
from core.feishu_client import FeishuClient  # noqa: E402
from core.llm_client import generate_review  # noqa: E402
from core.config import config  # noqa: E402

st.title("🔁 复盘中心")
st.caption("对到期判断对答案，AI 给校准反馈。原始判断不可改写。")

fc = FeishuClient()

# ── 加载到期待验证的判断 ──────────────────────────────────────
try:
    due = fc.get_due_judgments(date.today())
except Exception as e:
    due = []
    st.error(f"读取到期判断失败：{e}")

if not due:
    st.info("🎉 暂无待复盘的到期判断。")
    st.stop()

st.write(f"共 **{len(due)}** 条到期待验证的判断：")

# ── 逐条复盘 ──────────────────────────────────────────────────
ORIGINAL_FIELDS = {"content", "confidence", "direction", "basis",
                   "falsify_cond", "horizon", "target", "date", "verify_date"}

for j in due:
    rid = j.get("record_id", "")
    with st.expander(
        f"{j.get('date', '?')} · {j.get('target', '?')} · "
        f"{j.get('direction', '?')} · 置信度 {j.get('confidence', '?')}/100"
    ):
        st.markdown(f"**判断内容**：{j.get('content', '')}")
        st.caption(
            f"时间范围：{j.get('horizon', '')} ｜ "
            f"依据：{j.get('basis', '')} ｜ "
            f"反证条件：{j.get('falsify_cond', '')}"
        )

        col1, col2 = st.columns(2)
        result = col1.selectbox(
            "实际结果", ["", "正确", "部分", "错误"],
            key=f"result_{rid}"
        )
        note = col2.text_area(
            "实际发生了什么", key=f"note_{rid}",
            placeholder="简述实际走势与判断的异同"
        )

        if st.button("生成复盘并写回飞书", key=f"btn_{rid}"):
            if not result or result not in calibration.RESULT_HIT:
                st.error("请选择实际结果（正确/部分/错误）。")
            else:
                # ① 计算 Brier 分数
                bs = calibration.brier_score(j["confidence"], result)
                st.metric("Brier 分数（越低越准）", f"{bs:.4f}")

                # ② 调用 LLM 质量审查
                with st.spinner("AI 正在生成复盘分析…"):
                    ai_review = generate_review(j, note)
                st.text_area("AI 复盘分析", ai_review, height=200, key=f"review_{rid}")

                # ③ 写回飞书（仅写 actual_result / brier_score / ai_review）
                try:
                    fc.update_record(config.table_judgments, rid, {
                        "actual_result": result,
                        "brier_score": bs,
                        "ai_review": ai_review,
                    })
                    st.success(f"✅ 已写回飞书 · record_id: `{rid}`")
                    st.caption("原始判断字段（content/confidence/direction 等）未被修改。")
                    st.rerun()
                except Exception as e:
                    st.error(f"写回失败：{e}")

# ── 校准汇总 ──────────────────────────────────────────────────
st.divider()
st.subheader("📊 校准统计")

try:
    all_judgments = fc.list_records(config.table_judgments)
    summary = calibration.calibration_summary(all_judgments)
    if summary["count"] == 0:
        st.write("暂无已复盘记录可统计。")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("已复盘数", summary["count"])
        col2.metric("平均 Brier", f"{summary['avg_brier']:.4f}" if summary["avg_brier"] else "N/A")
        if summary["overconfident"]:
            col3.warning("⚠️ 过度自信")
        else:
            col3.success("校准正常")

        if summary.get("buckets"):
            st.write("**按置信度分桶命中率**：")
            bucket_data = []
            for label, info in summary["buckets"].items():
                bucket_data.append({
                    "置信区间": f"{label}%",
                    "数量": info["count"],
                    "命中率": f"{info['hit_rate']:.1%}",
                })
            st.dataframe(bucket_data, use_container_width=True)
except Exception as e:
    st.error(f"校准统计加载失败：{e}")
