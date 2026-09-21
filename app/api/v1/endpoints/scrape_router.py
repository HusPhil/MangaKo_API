from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.core.sources import SUPPORTED_SOURCES
from app.services.scraper.factory import get_scraper
from app.schemas.sources_schema import Source
from typing import List
import hashlib, httpx, json

router = APIRouter()


@router.get("/sources")
def get_supported_sources() -> List[Source]:
    return list(SUPPORTED_SOURCES.values())
