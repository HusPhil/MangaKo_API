import hashlib
from typing import List

from curl_cffi import AsyncSession
from urllib.parse import quote, urljoin

from selectolax.parser import HTMLParser

from app.core.sources import SUPPORTED_SOURCES
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

SOURCE_NAME = "manhuaplus"


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
            seen_ids = set()

            for item in tree.css("div.items div.item"):
                link = item.css_first("figure div.image a")
                if not link:
                    continue

                href = link.attributes.get("href")
                if not href:
                    continue

                manga_url = urljoin(url, href.strip())
                manga_id = manga_url.rstrip("/").split("/")[-1]

                title_node = item.css_first("figcaption h3 a")
                manga_title = (
                    link.attributes.get("title")
                    or (title_node.text(strip=True) if title_node else "")
                    or ""
                ).strip()

                img = item.css_first("figure div.image img")
                manga_cover = ""
                if img:
                    cover_src = (
                        img.attributes.get("data-original")
                        or img.attributes.get("data-src")
                        or img.attributes.get("src")
                        or ""
                    )
                    manga_cover = urljoin(url, cover_src.strip())

                # skip broken or duplicate entries
                if not manga_id or not manga_title or manga_id in seen_ids:
                    continue
                seen_ids.add(manga_id)

                latest_manga.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga_id,
                        mangaTitle=manga_title,
                        mangaUrl=manga_url,
                        mangaCover=manga_cover,
                    )
                )

            # next page: the <li> right after the active page in the pagination
            next_node = tree.css_first("ul.pagination li.active + li a")
            next_href = next_node.attributes.get("href") if next_node else None

            # fallback to <link rel="next"> in the head
            if not next_href:
                rel_next = tree.css_first("link[rel='next']")
                next_href = rel_next.attributes.get("href") if rel_next else None

            if next_href:
                next_url = urljoin(url, next_href)

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
