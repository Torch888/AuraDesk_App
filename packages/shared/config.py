"""共享配置模块"""
from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AuraDesk 智能提醒助手"
    version: str = "1.0.0"
    debug: bool = True

    # 数据库
    db_path: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "auradesk.db")

    # OpenAI API (用于 LLM 自然语言解析)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "sk-xxx")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # 邮件
    email_imap_host: str = os.getenv("EMAIL_IMAP_HOST", "")
    email_imap_port: int = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    email_address: str = os.getenv("EMAIL_ADDRESS", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")

    # 飞书
    feishu_app_id: str = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret: str = os.getenv("FEISHU_APP_SECRET", "")

    # 默认用户偏好
    default_parcel_time: str = "18:30"
    default_remind_offsets: list[int] = [-1800, -600, 0]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()