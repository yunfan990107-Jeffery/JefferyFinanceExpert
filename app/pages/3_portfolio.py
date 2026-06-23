"""页面③：持仓看板。对应 FR-P-1/P-2 / FR-U-3。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
import pandas as pd  # noqa: E402
from core import portfolio  # noqa: E402
from core.feishu_client import FeishuClient  # noqa: E402
from core.config import config  # noqa: E402

st.title("💼 持仓看板")

with st.expander("➕ 录入持仓"):
    with st.form("add_pos"):
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("标的代码")
        name = c2.text_input("名称")
        industry = c3.text_input("所属行业")
        c4, c5, c6 = st.columns(3)
        qty = c4.number_input("数量", min_value=0.0, step=100.0)
        cost = c5.number_input("成本价", min_value=0.0, step=0.01)
        linked = c6.text_input("关联判断/决策ID（可选）")
        reason = st.text_area("买入理由")
        if st.form_submit_button("保存"):
            fields = {"code": code, "name": name, "industry": industry, "qty": qty,
                      "cost": cost, "buy_date": date.today().isoformat(),
                      "linked_judgment_id": linked, "reason": reason}
            try:
                rid = FeishuClient().add_record(config.table_portfolio, fields)
                st.success(f"✅ 已保存到飞书 · record_id: `{rid}`")
            except Exception as e:
                st.error(f"保存失败：{e}")

st.subheader("当前组合")
try:
    positions = FeishuClient().list_records(config.table_portfolio)
except Exception as e:
    positions = []
    st.error(f"读取持仓失败：{e}")

if positions:
    prices = {p["code"]: p.get("cost", 0) for p in positions}  # TODO(P1): AkShare 取现价
    metrics = portfolio.compute_position_metrics(positions, prices)
    st.dataframe(pd.DataFrame(metrics))
    conc = portfolio.concentration(metrics)
    if conc["max_single_weight"] > 30:
        st.warning(f"单一标的集中度偏高：{conc['max_single_weight']}%")
    st.write("行业分布：", conc["by_industry"])
