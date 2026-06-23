"""Streamlit 入口。多页应用：记今日判断 / 复盘中心 / 持仓看板。

运行： streamlit run app/main.py
页面文件在 app/pages/，Streamlit 自动加载到侧边栏。
"""
import sys
from pathlib import Path

# 让 app/ 下的页面能 import core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from core.config import config  # noqa: E402

st.set_page_config(page_title="AI 投资分析系统", page_icon="📈", layout="wide")

st.title("📈 个人 AI 投资分析系统")
st.caption("永不自动下单 · 只产出研究与认知支持 · 决策由你做")

if not config.is_ready():
    st.warning("尚未配置飞书凭证：请复制 .env.example 为 .env 并填入。当前为脚手架演示模式。")

st.markdown(
    """
    ### 从左侧选择功能
    - **记今日判断** — 写下判断、置信度(0-100)、反证条件
    - **复盘中心** — 到期判断对答案，AI 给校准反馈
    - **持仓看板** — 录入/查看持仓与集中度

    > 数据写入飞书云端数据库；本页仅导航。
    """
)
