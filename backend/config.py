"""
Social Media Manager - Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Social Media Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8765

    # Database
    DATABASE_URL: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'manager.db'}"

    # Security
    SECRET_KEY: str = "smm-secret-key-change-in-production-2024"
    ENCRYPTION_KEY: str = "smm-encryption-key-change-in-production-2024!!"

    # Scheduler
    SCHEDULER_POLL_INTERVAL: int = 30  # seconds

    # Max accounts per platform - configurable
    MAX_ACCOUNTS_PER_PLATFORM: int = 20
    TOTAL_ACCOUNTS_LIMIT: int = 100

    # Supported platforms
    PLATFORMS: list[str] = ["weibo", "wechat", "douyin", "xiaohongshu", "bilibili"]

    # Platform display names
    PLATFORM_NAMES: dict[str, str] = {
        "weibo": "微博",
        "wechat": "微信",
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "bilibili": "B站",
    }

    # Platform capabilities
    PLATFORM_CAPABILITIES: dict[str, list[str]] = {
        "weibo": ["text", "image", "video", "poll"],
        "wechat": ["text", "image", "video", "article"],
        "douyin": ["video", "image"],
        "xiaohongshu": ["text", "image", "video"],
        "bilibili": ["video", "text", "image"],
    }

    class Config:
        env_file = ".env"
        env_prefix = "SMM_"


settings = Settings()
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CONTENT_DIR = BASE_DIR / "content"

for d in [DATA_DIR, LOGS_DIR, CONTENT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
