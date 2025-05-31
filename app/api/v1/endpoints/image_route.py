from fastapi import APIRouter, Response
from app.services.scraper.factory import get_scraper
import httpx

router = APIRouter()


@router.get("/image-proxy")
async def proxy_image(url: str):
    headers = {
        #"Referer": "https://www.mangakakalot.gg/",
        "Referer": "https://comick.io/home2",
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return Response(content=response.content, media_type="image/jpeg")
