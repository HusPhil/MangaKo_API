from fastapi import APIRouter
from app.api.v1.endpoints import auth_router, scrape_router, mangakakalot_router, image_route

router = APIRouter()
router.include_router(scrape_router.router, prefix="/scrape", tags=["Scrape"])
router.include_router(mangakakalot_router.router, prefix="/mangakakalot", tags=["Mangakakalot"])
router.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
router.include_router(image_route.router, prefix="/image_service", tags=["Image Service"])
