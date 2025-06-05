from app.schemas.sources_schema import SourceStatus


SUPPORTED_SOURCES = {
    "mangakakalot": {
        "url": "https://mangakakalot.com",
        "status": SourceStatus.READY_TO_USE
    },
    "manganelo": {
        "url": "https://manganelo.com",
        "status": SourceStatus.DEPRECATED   
    },
    "asurascans": {
        "url": "https://asurascans.com",
        "status": SourceStatus.IN_DEVELOPMENT
    },
    "comick": {
        "url": "https://comick.io/",
        "status": SourceStatus.READY_TO_USE
    }
}
