# MangaKo API

FastAPI manga-scraping API. Platform-agnostic. Python 3.12. All direct dependencies are pinned in `requirements.txt`.

## Commands

- Run locally: `uvicorn app.main:app --reload` (from repo root)
- Deploy: any ASGI-compatible hosting — serve `app.main:app`.

## Configuration

All secrets and infrastructure endpoints live in `app/core/config.py`, loaded from env vars prefixed `MANGAKO_` (see `.env.example`). Copy `.env.example` to `.env` to configure.

## Endpoints

- `GET /` — health check
- `GET /api/v1/mangakakalot/latest/{page}` — latest manga
- `GET /api/v1/mangakakalot/popular/{page}` — popular manga
- `GET /api/v1/mangakakalot/search?keyword={keyword}` — search
- `GET /api/v1/mangakakalot/info?mangaId={mangaId}` — manga details
- `GET /api/v1/mangakakalot/chapters?mangaId={mangaId}` — chapter list
- `GET /api/v1/mangakakalot/pages?chapterId={chapterId}` — chapter pages
- `GET /api/v1/comick/...` — Comick source
- `GET /api/v1/asura_scans/...` — Asura Scans source
- `GET /api/v1/weeb_central/...` — WeebCentral source
- `GET /api/v1/mangafox/...` — MangaFox source
- `GET /api/v1/manhuato/...` — Manhuato source
- `GET /api/v1/image_service/...` — image proxy
- `GET /api/v1/auth/...` — authentication
- `GET /api/v1/scrape/...` — debug scrape route (dev only)

## Adding a new source

A source must be registered in all three places or `get_scraper()` / routing breaks:

1. `app/core/sources.py` → add entry to `SUPPORTED_SOURCES`
2. `app/services/scraper/factory.py` → add class to `SCRAPER_MAP`
3. `app/api/v1/router.py` → import and include the new `endpoints/<source>_router.py`

The dict key in `SUPPORTED_SOURCES`, the `sourceId`, the factory key, the router `source` string, and the scraper's `SOURCE_NAME` must ALL be identical.

## Rate Limiting

The API is protected by slowapi rate limiting (60 requests/minute per IP). The root endpoint is limited to 10 requests/minute.

## License

MIT