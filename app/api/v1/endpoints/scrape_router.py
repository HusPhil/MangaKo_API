from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.core.sources import SUPPORTED_SOURCES
from app.services.scraper.factory import get_scraper
from app.schemas.sources_schema import Source
from typing import List
import hashlib, httpx, json

router = APIRouter()


@router.get("/")
async def test_scrape():

    acc_id = "REDACTED"
    api_key = "REDACTED"

    # return {'message': 'scrape route working!', 'supported_sources': supported_sources}
    base_url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + acc_id
        + "/browser-rendering/content"
    )
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {"url": "https://fto.to/apo/"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(base_url, headers=headers, data=json.dumps(payload))
        return {"message": "scrape route working!", "response": resp.json()}
    return {
        "message": "scrape route working!",
    }
    pass


@router.get("/sources")
def get_supported_sources() -> List[Source]:
    return list(SUPPORTED_SOURCES.values())
