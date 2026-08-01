from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints import (
    asura_scans_router,
    auth_router,
    comick_router,
    image_router,
    mangafox_router,
    manhuato_router,
    scrape_router,
    mangakakalot_router,
    weebcentral_router,
)
from app.api.v1.errors import raise_scraper_error

limiter = Limiter(key_func=get_remote_address)


def get_limiter(request: Request):
    return limiter


router = APIRouter()
router.include_router(
    scrape_router.router,
    prefix="/scrape",
    tags=["Scrape"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    mangakakalot_router.router,
    prefix="/mangakakalot",
    tags=["Mangakakalot"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    comick_router.router,
    prefix="/comick",
    tags=["Comick"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    asura_scans_router.router,
    prefix="/asura_scans",
    tags=["Asura Scans"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    manhuato_router.router,
    prefix="/manhuato",
    tags=["Manhuato"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    mangafox_router.router,
    prefix="/mangafox",
    tags=["Mangafox"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    image_router.router,
    prefix="/image_service",
    tags=["Image Service"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    weebcentral_router.router,
    prefix="/weeb_central",
    tags=["WeebCentral"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
router.include_router(
    auth_router.router,
    prefix="/auth",
    tags=["Auth"],
    dependencies=[Depends(limiter.limit("60/minute"))],
)
