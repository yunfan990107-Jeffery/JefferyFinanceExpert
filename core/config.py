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

    def is_ready(self) -> bool:
        return bool(self.app_id and self.app_secret and self.bitable_app_token)


config = Config()
