from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.sources_schema import SourceStatus

SUPPORTED_SOURCES = {
    "mangakakalot": {
        "url": "https://mangakakalot.com",
        "status": SourceStatus.ACTIVE
    },
    "manganelo": {
        "url": "https://manganelo.com",
        "status": SourceStatus.ACTIVE   
    },
    "asurascans": {
        "url": "https://asurascans.com",
        "status": SourceStatus.ACTIVE
    },
    "comickio": {
        "url": "https://comick.io/",
        "status": SourceStatus.ACTIVE
    }
}
