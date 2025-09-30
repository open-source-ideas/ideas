from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    database_path: Path


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Create a .env file or export the variable beforehand.")
    db_path = os.getenv("DATABASE_PATH", "telegram_bot.db")
    return Settings(bot_token=token, database_path=Path(db_path))
