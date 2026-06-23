"""Streamlit 入口 —— 统一导航 + 暗色主题 + 仪表盘首页。

运行：streamlit run app/main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="PrivateFinanceExpert",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局暗色主题 CSS ──────────────────────────────────────────
st.markdown("""
<style>
  /* ── 全局底色 ── */
  .stApp, .main, [data-testid="stAppViewContainer"] {
    background: #0B0E14;
    color: #E6E8EC;
  }
  .stMain, section[data-testid="stSidebar"] {
    background: #141820;
  }
  section[data-testid="stSidebar"] > div:first-child {
    background: #141820;
    border-right: 1px solid #252A36;
  }

  /* ── 侧边栏 ── */
  [data-testid="stSidebarNav"] a {
    color: #7A8290 !important;
    font-size: 13px !important;
    border-radius: 6px !important;
    padding: 10px 12px !important;
    margin-bottom: 2px !important;
    transition: background 150ms !important;
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: #1A1F2A !important;
    color: #E8A840 !important;
    font-weight: 600 !important;
  }
  [data-testid="stSidebarNav"] a:hover {
    background: #1A1F2A !important;
    color: #E6E8EC !important;
  }
  [data-testid="stSidebarNavLinkText"] {
    font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif !important;
  }

  /* ── 卡片 ── */
  .metric-card {
    background: #141820;
    border: 1px solid #252A36;
    border-radius: 6px;
    padding: 16px 20px;
    margin-bottom: 8px;
    transition: transform 150ms, box-shadow 150ms;
  }
  .metric-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }

  /* ── 按钮 ── */
  .stButton > button {
    background: #1A1F2A !important;
    border: 1px solid #E8A840 !important;
    color: #E8A840 !important;
    border-radius: 4px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 14px !important;
  }
  .stButton > button:hover {
    background: #252A36 !important;
    color: #E8A840 !important;
  }

  /* ── 表格/DataFrame ── */
  [data-testid="stDataFrame"] {
    background: #141820 !important;
    border: 1px solid #252A36 !important;
    border-radius: 6px !important;
  }
  .stDataFrame th {
    background: #1A1F2A !important;
    color: #7A8290 !important;
    font-size: 12px !important;
  }
  .stDataFrame td {
    background: #141820 !important;
    color: #E6E8EC !important;
    font-size: 13px !important;
  }

  /* ── 输入框 ── */
  .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
    background: #1A1F2A !important;
    border: 1px solid #252A36 !important;
    color: #E6E8EC !important;
    border-radius: 4px !important;
  }
  .stSlider [data-baseweb="slider"] {
    background: #E8A840 !important;
  }

  /* ── 标题 ── */
  h1 { color: #E6E8EC !important; font-size: 22px !important; font-weight: 600 !important; }
  h2 { color: #E6E8EC !important; font-size: 15px !important; font-weight: 600 !important; }
  h3 { color: #E6E8EC !important; font-size: 13px !important; }
  p, label, .stCaption { color: #7A8290 !important; font-size: 12px !important; }

  /* ── 展开器(expander) ── */
  .stExpander {
    background: #141820 !important;
    border: 1px solid #252A36 !important;
    border-radius: 6px !important;
  }
  .stExpander [data-testid="stExpanderDetails"] {
    background: #141820 !important;
  }

  /* ── Metric ── */
  [data-testid="stMetricValue"] {
    color: #E8A840 !important;
    font-family: "JetBrains Mono", monospace !important;
  }
  [data-testid="stMetricLabel"] {
    color: #7A8290 !important;
  }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏标题 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 16px; border-bottom: 1px solid #252A36; margin-bottom: 8px;">
      <div style="font-size:13px; font-weight:600; color:#E8A840; letter-spacing:0.5px;">
        PrivateFinanceExpert
      </div>
      <div style="font-size:11px; color:#7A8290; margin-top:2px;">
        个人 AI 投资分析系统
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("今日 2026-06-23")

# ── 页面路由 ───────────────────────────────────────────────────
pages = {
    "仪表盘": [
        st.Page("pages/dashboard.py", title="仪表盘", icon="📊"),
    ],
    "操作": [
        st.Page("pages/1_record_judgment.py", title="记判断", icon="📝"),
        st.Page("pages/2_review_center.py", title="复盘中心", icon="🔁"),
        st.Page("pages/3_portfolio.py", title="持仓看板", icon="💼"),
    ],
}

pg = st.navigation(pages, position="sidebar")
pg.run()
