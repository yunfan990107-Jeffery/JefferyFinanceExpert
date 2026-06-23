"""页面①：记今日判断。对应 FR-J-1 / FR-U-1。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from core import calibration  # noqa: E402
from core.feishu_client import FeishuClient  # noqa: E402
from core.config import config  # noqa: E402

st.title("📝 记今日判断")

with st.form("judgment"):
    target = st.text_input("判断对象", placeholder="如 沪深300 / 宁德时代 / 新能源板块")
    content = st.text_area("判断内容（提交后不可改写）", placeholder="你认为会发生什么")
    col1, col2 = st.columns(2)
    direction = col1.selectbox("方向", ["看多", "看空", "中性", "不确定"])
    horizon = col2.selectbox("时间范围", list(calibration.HORIZON_DAYS.keys()))
    confidence = st.slider("置信度（0-100）", 0, 100, 60)
    basis = st.text_area("依据", placeholder="当时的事实/数据/逻辑")
    falsify = st.text_area("反证条件", placeholder="什么情况发生说明我错了")
    submitted = st.form_submit_button("提交判断")

if submitted:
    if not content or not target:
        st.error("判断对象与内容必填。")
    else:
        verify_date = calibration.make_verify_date(date.today(), horizon)
        fields = {
            "date": date.today().isoformat(), "target": target, "content": content,
            "direction": direction, "horizon": horizon, "confidence": confidence,
            "basis": basis, "falsify_cond": falsify,
            "verify_date": verify_date.isoformat(), "actual_result": "待验证",
        }
        try:
            rid = FeishuClient().add_record(config.table_judgments, fields)
            st.success(f"✅ 已记录到飞书 · 验证日期 {verify_date} · record_id: `{rid}`")
            st.caption("可在飞书多维表格或复盘中心查看。")
        except Exception as e:
            st.error(f"写入飞书失败：{e}")
