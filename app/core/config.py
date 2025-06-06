from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv


load_dotenv()

class Settings(BaseSettings):
    COMICK_COOKIE: str = os.getenv("COMICK_COOKIE")


    class Config:
        extra = "allow"
        env_file = ".env"  # Load environment variables
        

settings = Settings()
