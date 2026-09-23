from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DEV_ENVIRONMENT: bool = os.getenv("DEV_ENVIRONMENT", True) == "true"

    WEEB_CENTRAL_IMAGE_PROXY_WORKER_URL: str = os.getenv(
        "WEEB_CENTRAL_IMAGE_PROXY_WORKER_URL", ""
    )

    MANHUAPLUS_IMAGE_PROXY_WORKER_URL: str = os.getenv(
        "MANHUAPLUS_IMAGE_PROXY_WORKER_URL", ""
    )

    class Config:
        extra = "allow"
        env_file = ".env"  # Load environment variables


settings = Settings()
