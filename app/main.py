from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from dotenv import load_dotenv

from app.core.config import settings
from app.api.v1.errors import rate_limit_handler

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="MangaKo API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://REDACTED:8081",
        "http://REDACTED:8081",
        "http://REDACTED:8081",
        "http://REDACTED:8081",
        "http://REDACTED:5173",
        "http://REDACTED:5173",
        "http://REDACTED:5173",
        "http://REDACTED:5173",
        "http://REDACTED:5173",
        "http://REDACTED:5173",
        "http://REDACTED:8081",
        "http://REDACTED:8081",
        "exp://REDACTED:8081",
        "exp://REDACTED:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.router import router as api_router

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
@limiter.limit("10/minute")
def index(request):
    return {"message": "mangako server is working!"}
