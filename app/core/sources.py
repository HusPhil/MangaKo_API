from app.schemas.sources_schema import SourceStatus, Source


SUPPORTED_SOURCES: dict[str, Source] = {
    "mangakakalot": Source(
        sourceId="mangakakalot",
        sourceName="MangaKakalot",
        sourceUrl="https://mangabuddy.com",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "manganelo": Source(
        sourceId="manganelo",
        sourceName="MangaNelo",
        sourceUrl="https://manganelo.com",
        sourceStatus=SourceStatus.DEPRECATED,
    ),
    "comick": Source(
        sourceId="comick",
        sourceName="Comick",
        sourceUrl="https://comick.live/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
}
