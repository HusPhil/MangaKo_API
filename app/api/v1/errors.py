import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def raise_scraper_error(e: Exception) -> JSONResponse:
    logger.exception("Scraper error: %s", e)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit exceeded for %s", request.client.host)
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )