from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str


def load_settings() -> Settings:
    load_dotenv()

    bot_token = getenv("BOT_TOKEN")
    database_url = getenv("DATABASE_URL")

    missing = [
        name
        for name, value in {
            "BOT_TOKEN": bot_token,
            "DATABASE_URL": database_url,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Settings(bot_token=bot_token, database_url=database_url)
