"""仪表盘首页 —— 全局概览，数据来自飞书 + calibration。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from core.feishu_client import FeishuClient
from core.config import config
from core import calibration

fc = FeishuClient()
today = date.today()

st.title("仪表盘")

# ── 加载数据 ───────────────────────────────────────────────────
try:
    due = fc.get_due_judgments(today)
except Exception:
    due = []

try:
    all_j = fc.list_records(config.table_judgments)
    summary = calibration.calibration_summary(all_j)
except Exception:
    all_j, summary = [], {"count": 0}

try:
    positions = fc.list_records(config.table_portfolio)
    from core import portfolio as pf
    prices = {p.get("code", ""): p.get("cost", 0) for p in positions}
    metrics = pf.compute_position_metrics(positions, prices)
    conc = pf.concentration(metrics)
    has_positions = len(metrics) > 0
except Exception:
    metrics, conc, has_positions = [], {}, False

# ── 指标行 ─────────────────────────────────────────────────────
st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("待复盘判断", len(due), delta=f"最早到期 {due[0].get('verify_date','?')}" if due else None)
c2.metric("累计判断", summary.get("count", 0))
c3.metric(
    "平均 Brier",
    f"{summary.get('avg_brier',0):.3f}" if summary.get("avg_brier") else "N/A",
)
over = summary.get("overconfident", False)
c4.metric("校准状态", "⚠️ 过度自信" if over else "✅ 正常")

st.divider()

# ── 双栏 ───────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("近期待复盘")
    if due:
        for j in due[:5]:
            with st.container():
                st.markdown(f"""
                <div class="metric-card">
                  <span style="color:#7A8290;font-size:12px">{j.get('date','?')}</span>
                  <b>{j.get('target','?')}</b>
                  <span style="color:{'#2ECC71' if j.get('direction')=='看多' else '#E74C3C' if j.get('direction')=='看空' else '#7A8290'};margin-left:8px;font-size:12px">
                    {j.get('direction','?')}
                  </span>
                  <br><span style="color:#7A8290;font-size:12px">
                    置信度 {j.get('confidence','?')}/100 · 到期 {j.get('verify_date','?')}
                  </span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("暂无到期待复盘的判断。去「记判断」页创建第一条吧。")

with col_right:
    st.subheader("持仓摘要")
    if has_positions:
        for m in metrics:
            pnl_color = "#2ECC71" if m.get("pnl_pct", 0) >= 0 else "#E74C3C"
            w = max(m.get("weight", 0), 2)
            st.markdown(f"""
            <div class="metric-card" style="display:flex;justify-content:space-between;align-items:center">
              <span>{m.get('name', m.get('code','?'))}</span>
              <div style="display:flex;gap:12px;align-items:center">
                <div style="width:{w}px;height:6px;background:{pnl_color if w>30 else '#E8A840'};border-radius:3px;min-width:20px"></div>
                <span style="font-family:JetBrains Mono,monospace;font-size:12px;color:#7A8290;width:48px;text-align:right">{m.get('weight',0)}%</span>
                <span style="font-family:JetBrains Mono,monospace;font-size:12px;color:{pnl_color};width:56px;text-align:right">{m.get('pnl_pct',0):+.1f}%</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
        if conc.get("max_single_weight", 0) > 30:
            st.warning(f"⚠️ 单标集中度偏高：{conc['max_single_weight']}%")
    else:
        st.info("暂无持仓数据。去「持仓看板」页录入。")

# ── 校准快照 ───────────────────────────────────────────────────
st.divider()
st.subheader("校准快照")

if summary.get("count", 0) > 0 and summary.get("buckets"):
    bucket_data = []
    for label, info in summary["buckets"].items():
        bucket_data.append({
            "置信区间": f"{label}%",
            "数量": info["count"],
            "命中率": f"{info['hit_rate']:.1%}",
        })
    st.dataframe(bucket_data, use_container_width=True, hide_index=True)
else:
    st.info("暂无足够已复盘数据生成校准快照。完成一些复盘后这里会显示你的判断准确率分布。")
