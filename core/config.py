"""配置加载：从 .env 读取飞书凭证与各表 token。"""
from __future__ import annotations
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv 未安装时不致命
    pass


@dataclass(frozen=True)
class Config:
    app_id: str = os.getenv("FEISHU_APP_ID", "")
    app_secret: str = os.getenv("FEISHU_APP_SECRET", "")
    bitable_app_token: str = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
    table_judgments: str = os.getenv("TABLE_JUDGMENTS", "")
    table_portfolio: str = os.getenv("TABLE_PORTFOLIO", "")
    table_tasks: str = os.getenv("TABLE_TASKS", "")
    table_decisions: str = os.getenv("TABLE_DECISIONS", "")
    table_risk_reviews: str = os.getenv("TABLE_RISK_REVIEWS", "")
    table_intel: str = os.getenv("TABLE_INTEL", "")

    # LLM（复盘用，OpenAI 兼容 API）
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    def is_ready(self) -> bool:
        return bool(self.app_id and self.app_secret and self.bitable_app_token)

    def llm_ready(self) -> bool:
        """LLM 是否已配置（排除占位符值）。"""
        key = self.llm_api_key.strip()
        if not key:
            return False
        # 排除占位符：含中文 / 尖括号 / 纯星号
        if any('\u4e00' <= c <= '\u9fff' for c in key):
            return False
        if '<' in key or key.startswith('xxx'):
            return False
        return True


config = Config()
