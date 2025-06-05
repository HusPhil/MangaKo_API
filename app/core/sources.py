from app.schemas.sources_schema import SourceStatus, Source


SUPPORTED_SOURCES: dict[str, Source] = {
    "mangakakalot": Source(
        sourceId="mangakakalot",
        sourceName="MangaKakalot",
        sourceUrl="https://mangakakalot.com",
        sourceStatus=SourceStatus.READY_TO_USE
    ),
    "manganelo": Source(
        sourceId="manganelo",
        sourceName="MangaNelo",
        sourceUrl="https://manganelo.com",
        sourceStatus=SourceStatus.DEPRECATED
    ),
    "asurascans": Source(
        sourceId="asurascans",
        sourceName="Asura Scans",
        sourceUrl="https://asurascans.com",
        sourceStatus=SourceStatus.IN_DEVELOPMENT
    ),
    "comick": Source(
        sourceId="comick",
        sourceName="Comick",
        sourceUrl="https://comick.io/",
        sourceStatus=SourceStatus.READY_TO_USE
    ),
}
