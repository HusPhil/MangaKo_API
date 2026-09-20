from fastapi import APIRouter, HTTPException, Query
from app.services.scraper.factory import get_scraper
from app.schemas.manga_schema import (
    LatestMangaListResponse,
    MangaInfoResponse,
    PopularMangaListResponse,
    MangaChapterPage,
    MangaSearchResponse,
)

router = APIRouter()
source = "manhuaplus"


@router.get("/")
async def test_manhuaplus():
    try:
        scraper = get_scraper(source)
        return await scraper.scrape()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manga/latest/{page}")
async def get_latest_manga(page: int) -> LatestMangaListResponse:
    url = f"https://manhuaplus.top/all-manga/{page}/?sort=last_update&status=0"
    try:
        scraper = get_scraper(source)
        latest_manga = await scraper.scrape_latest_manga(url)
        return latest_manga
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manga/popular")
async def get_popular_manga() -> PopularMangaListResponse:
    url = f"https://manhuaplus.top/all-manga/?sort=views_week"
    try:
        scraper = get_scraper(source)
        popular_manga = await scraper.scrape_popular_manga(url)
        return popular_manga
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manga/info")
async def get_manga_info(url: str) -> MangaInfoResponse:
    try:
        scraper = get_scraper(source)
        manga_info = await scraper.scrape_manga_info(url)
        return manga_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manga/chapter/pages", response_model=list[MangaChapterPage])
async def get_chapter_pages(url: str = Query(..., description="Full chapter URL")):
    try:
        scraper = get_scraper(source)
        return await scraper.scrape_chapter_pages(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manga/search", response_model=MangaSearchResponse)
async def search_manga(keyword: str = Query(..., description="Search query")):
    try:
        scraper = get_scraper(source)
        return await scraper.scrape_manga_search(keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
