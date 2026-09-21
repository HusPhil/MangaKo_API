from fastapi import APIRouter

from app.api.v1.endpoints import (
    asura_scans_router,
    comick_router,
    image_router,
    mangafox_router,
    manhuaplus_router,
    manhuato_router,
    mangakakalot_router,
    scrape_router,
    weebcentral_router,
)

router = APIRouter()

router.include_router(scrape_router.router, prefix="/scrape", tags=["Scrape"])

router.include_router(
    mangakakalot_router.router,
    prefix="/mangakakalot",
    tags=["Mangakakalot"],
)
router.include_router(
    comick_router.router,
    prefix="/comick",
    tags=["Comick"],
)
router.include_router(
    asura_scans_router.router,
    prefix="/asura_scans",
    tags=["Asura Scans"],
)
router.include_router(
    manhuato_router.router,
    prefix="/manhuato",
    tags=["Manhuato"],
)
router.include_router(
    mangafox_router.router,
    prefix="/mangafox",
    tags=["Mangafox"],
)
router.include_router(
    image_router.router,
    prefix="/image_service",
    tags=["Image Service"],
)
router.include_router(
    weebcentral_router.router,
    prefix="/weeb_central",
    tags=["WeebCentral"],
)

router.include_router(
    manhuaplus_router.router,
    prefix="/manhuaplus",
    tags=["manhuaplus"],
)
