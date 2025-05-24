from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.sources import SUPPORTED_SOURCES
from app.services.scraper.factory import get_scraper

# from app.services.scraper import scrape_website
# from app.core.security import oauth2_scheme

router = APIRouter()

@router.get("/")
def test_scrape():
    supported_sources = list(SUPPORTED_SOURCES.keys())
    print(supported_sources)

    return {'message': 'scrape route working!', 'supported_sources': supported_sources}


@router.get("/scrape")
async def scrape(
    source: str = Query(..., description="Name of the source"),
    url: str = Query(..., description="URL to scrape")
):
    if source not in SUPPORTED_SOURCES:
        raise HTTPException(status_code=400, detail="Unsupported source")

    try:
        scraper = get_scraper(source)
        data = await scraper.scrape(url)
        return {"source": source, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))