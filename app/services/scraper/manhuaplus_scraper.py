import hashlib
from typing import List

from curl_cffi import AsyncSession
from selectolax.parser import HTMLParser
from .base import BaseScraper
from app.schemas.manga_schema import (
    Manga,
    MangaInfoResponse,
    MangaDetails,
    MangaChapter,
    LatestMangaListResponse,
    PopularMangaListResponse,
    MangaChapterPage,
    MangaSearchResponse,
)

DEFAULT_HEADERS = {
    "Referer": "https://manhuaplus.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
}

SOURCE_NAME = "manhua_plus"


class ManhuaPlusScraper(BaseScraper):
    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:

        async with self.AsyncClient as client:
            url = f"https://manhuaplus.top/manga/demon-magic-emperor/chapter-898"

            response = await client.get(url)
            response.raise_for_status()

            with open("test_files/manhuaplus_test.html", "w", encoding="utf-8") as f:
                f.write(response.text)

        return {"source": SOURCE_NAME, "message": "this is the asura scans scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            latest_manga: List[Manga] = []
            next_url = None

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            popular_manga: List[Manga] = []
            next_url = None

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            search_url = f"https://manhuaplus.top/search?keyword={quote(keyword)}"

            response = await client.get(search_url)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            results = []

            return MangaSearchResponse(source=SOURCE_NAME, results=results)

    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with self.AsyncClient as client:

            response = await client.get(
                url, headers=DEFAULT_HEADERS, allow_redirects=True
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)
            manga_description = "No description available."
            manga_tags = []
            manga_status = "Unknown"
            manga_alternative_names = []
            manga_author = "Unknown"

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            chapters: List[MangaChapter] = []
            chapter_items = []

            for item in chapter_items:
                chapter_url = ""
                chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()
                chapter_name = ""
                chapter_time = ""
                chapters.append(
                    MangaChapter(
                        chapterId=chapter_id,
                        chapterTitle=chapter_name,
                        chapterUrl=chapter_url,
                        chapterTimeUploaded=chapter_time,
                    )
                )

            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map,
            )

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with self.AsyncClient as client:
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)
            pages: list[MangaChapterPage] = []

            return pages

    def _to_asura_scans_slug(self, query: str) -> str:
        """
        Convert a search query to Mangakakalot's expected slug format.
        - Lowercase
        - Remove non-word characters
        - Replace spaces with underscores
        """
        import re

        query = query.strip().lower()
        query = re.sub(r"[^\w\s]", "", query)  # Remove special characters
        query = re.sub(r"\s+", "+", query)  # Replace spaces with underscores
        return query
