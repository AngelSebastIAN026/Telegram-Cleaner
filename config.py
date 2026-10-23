import os

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class TelegramConfig(BaseModel):

    api_id: int
    api_hash: str
    session_name: str

    bot_token: str
    bot_session_name: str


def load_config() -> TelegramConfig:

    return TelegramConfig(

        api_id=int(
            os.getenv("TELEGRAM_API_ID")
        ),

        api_hash=os.getenv(
            "TELEGRAM_API_HASH"
        ),

        session_name=os.getenv(
            "TELEGRAM_SESSION_NAME",
            "telegram_cleaner",
        ),

        bot_token=os.getenv(
            "TELEGRAM_BOT_TOKEN"
        ),

        bot_session_name=os.getenv(
            "TELEGRAM_BOT_SESSION_NAME",
            "telegram_movie_bot",
        ),

    )

