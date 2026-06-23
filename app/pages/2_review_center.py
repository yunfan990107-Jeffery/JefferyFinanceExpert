"""页面②：复盘中心。对应 FR-J-3/J-4 / FR-U-2。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from core import calibration  # noqa: E402
from core.feishu_client import FeishuClient  # noqa: E402

st.title("🔁 复盘中心")
st.caption("对到期判断对答案，AI 给校准反馈。原始判断不可改写。")

try:
    due = FeishuClient().get_due_judgments(date.today())
except NotImplementedError:
    due = []
    st.info("⚙️ 待实现：feishu_client.get_due_judgments（见 docs/tasks/T0-3.md）。下方为交互占位。")

if not due:
    st.write("（暂无到期判断，或飞书读取未实现）")

for j in due:
    with st.expander(f"{j.get('date','')} · {j.get('target','')} · 置信度 {j.get('confidence','')}"):
        st.write(j.get("content", ""))
        result = st.selectbox("实际结果", ["待验证", "正确", "部分", "错误"], key=j.get("record_id"))
        note = st.text_area("实际发生了什么", key="note_" + str(j.get("record_id")))
        if st.button("生成复盘", key="btn_" + str(j.get("record_id"))):
            if result in calibration.RESULT_HIT:
                bs = calibration.brier_score(j["confidence"], result)
                prompt = calibration.build_review_prompt(j, note)
                st.metric("Brier 分数（越低越准）", bs)
                st.text_area("喂给质量审查角色的提示词", prompt, height=180)
                st.caption("TODO: 调用 agents/quality_review.md 角色生成复盘，并 update_record 写回飞书。")
