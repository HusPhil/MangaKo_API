from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.core.sources import SUPPORTED_SOURCES
from app.services.scraper.factory import get_scraper
from app.schemas.sources_schema import Source
from typing import List
import hashlib

router = APIRouter()

@router.get("/")
def test_scrape():
    supported_sources = list(SUPPORTED_SOURCES.keys())
    print(supported_sources)

    return {'message': 'scrape route working!', 'supported_sources': supported_sources}


@router.get("/sources")
def get_supported_sources() -> List[Source]:
    return [
        Source(
            sourceId=hashlib.md5(f"{source}".encode()).hexdigest()
, 
            sourceName=source, 
            sourceUrl=url
        ) 
        for source, url in SUPPORTED_SOURCES.items()
    ]
