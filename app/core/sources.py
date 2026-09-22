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
        sourceStatus=SourceStatus.DEPRECATED,
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
    "weeb_central": Source(
        sourceId="weeb_central",
        sourceName="Weeb Central",
        sourceUrl="https://weebcentral.com/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
    "manhuaplus": Source(
        sourceId="manhuaplus",
        sourceName="Manhua Plus",
        sourceUrl="https://manhuaplus.top/",
        sourceStatus=SourceStatus.READY_TO_USE,
    ),
}
