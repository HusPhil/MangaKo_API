from fastapi import FastAPI
from app.api.v1.router import router as api_router
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv


load_dotenv()

app = FastAPI(title="MangaKo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",  # ✅ Allow local frontend during development
        "http://REDACTED:8081",  # ✅ Allow local frontend during development
        "http://REDACTED:8081",  # ✅ Allow local frontend during development
        "http://REDACTED:8081",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",  # ✅ Allow local frontend during development
        "http://REDACTED:5173",
    ],
    # allow_origins=["http://REDACTED:5173"],
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allow all headers
)

app.include_router(api_router, prefix="/api/v1")

@app.get('/')
def index():
    return {'message': 'mangako server is working!'}
