from app.schemas.sources_schema import SourceStatus, Source

# to be changed or add new source for managabuddy
SUPPORTED_SOURCES: dict[str, Source] = {
    "mangakakalot": Source(
        sourceId="mangakakalot",
        sourceName="MangaKakalot",
        sourceUrl="https://mangabuddy.com",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "comick": Source(
        sourceId="comick",
        sourceName="Comick",
        sourceUrl="https://comick.live/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "asura scans": Source(
        sourceId="asura_scans",
        sourceName="Asura Scans",
        sourceUrl="https://asurascanz.com/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "manhuato": Source(
        sourceId="manhuato",
        sourceName="Manhuato",
        sourceUrl="http://manhuato.com/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "mangafox": Source(
        sourceId="mangafox",
        sourceName="Mangafox",
        sourceUrl="https://fanfox.net/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
}
