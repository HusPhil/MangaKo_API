import hashlib
import re
import asyncio
from typing import List

from curl_cffi import AsyncSession
import httpx
from urllib.parse import quote, urlparse, urlunparse
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
    ChaptersNavigationMap,
    ChapterNavigation,
)

DIMENSION_WORKER_URL = "https://mangabuddy-image-dimension.REDACTED.workers.dev/"

DEFAULT_HEADERS = {
    "Referer": "https://asurascanz.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
}

SOURCE_NAME = "asura scans"
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class AsuraScansScraper(BaseScraper):
    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:

        async with self.AsyncClient as client:
            # Standard search query parameter for WordPress-based sites like Asura Scans
            url = f"https://asurascanz.com/manga/?page=2&status=&type=&order=latest"

            response = await client.get(url)
            response.raise_for_status()

        return {"source": SOURCE_NAME, "message": "this is the asura scans scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            latest_manga: List[Manga] = []

            # 1. Select the items using the MangaReader grid layout classes
            for item in tree.css(".listupd .bsx a"):
                manga_url = item.attributes.get("href")
                manga_title = item.attributes.get("title")
                img_tag = item.css_first("img")

                if not manga_url or not manga_title or not img_tag:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://asurascanz.com{manga_url}"
                    if manga_url.startswith("/")
                    else manga_url
                )

                original_cover_url = img_tag.attributes.get("src")
                if not original_cover_url:
                    continue

                manga_cover = original_cover_url

                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                latest_manga.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga_id,
                        mangaTitle=manga_title,
                        mangaUrl=manga_url,
                        mangaCover=manga_cover,
                    )
                )

            # 2. Extract "Next Page" URL from the pagination element
            next_url = None
            next_tag = tree.css_first(".hpage a.r")

            if next_tag:
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    if raw_next.startswith("?"):
                        # Extract the base URL without existing query parameters
                        base_url = url.split("?")[0]
                        next_url = f"{base_url}{raw_next}"
                    elif raw_next.startswith("/"):
                        next_url = f"https://asurascanz.com{raw_next}"
                    else:
                        next_url = raw_next

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            popular_manga: List[Manga] = []

            # 1. Select the items using the MangaReader grid layout classes
            for item in tree.css(".listupd .bsx a"):
                manga_url = item.attributes.get("href")
                manga_title = item.attributes.get("title")
                img_tag = item.css_first("img")

                if not manga_url or not manga_title or not img_tag:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://asurascanz.com{manga_url}"
                    if manga_url.startswith("/")
                    else manga_url
                )

                original_cover_url = img_tag.attributes.get("src")
                if not original_cover_url:
                    continue

                manga_cover = original_cover_url

                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                popular_manga.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga_id,
                        mangaTitle=manga_title,
                        mangaUrl=manga_url,
                        mangaCover=manga_cover,
                    )
                )

            # 2. Extract "Next Page" URL from the pagination element
            next_url = None
            next_tag = tree.css_first(".hpage a.r")

            if next_tag:
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    if raw_next.startswith("?"):
                        # Extract the base URL without existing query parameters
                        base_url = url.split("?")[0]
                        next_url = f"{base_url}{raw_next}"
                    elif raw_next.startswith("/"):
                        next_url = f"https://asurascanz.com{raw_next}"
                    else:
                        next_url = raw_next

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            # Standard search query parameter for WordPress-based sites like Asura Scans
            search_url = f"https://asurascanz.com/?s={quote(keyword)}"

            response = await client.get(search_url)
            response.raise_for_status()

            # 1. Parse the HTML tree instead of JSON
            tree = HTMLParser(response.text)
            results = []

            # 2. Extract Manga entries from the grid layout
            # Asura Scans search results wrap the manga card in an <a> tag inside .bsx
            for item in tree.css(".listupd .bsx a"):
                manga_url = item.attributes.get("href")
                manga_title = item.attributes.get("title")
                img_tag = item.css_first("img")

                # Validate extracted fields
                if not manga_url or not manga_title or not img_tag:
                    continue

                original_cover_url = img_tag.attributes.get("src")
                if not original_cover_url:
                    continue

                # Proxy the image URL as per previous structure
                manga_cover = original_cover_url

                # Generate deterministic ID
                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                print(
                    f"ID: {manga_id}, Title: {manga_title}, URL: {manga_url}, Cover: {manga_cover}"
                )

                results.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga_id,
                        mangaTitle=manga_title,
                        mangaUrl=manga_url,
                        mangaCover=manga_cover,
                    )
                )

            print(results)

            return MangaSearchResponse(source=SOURCE_NAME, results=results)

    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(
                url, headers=DEFAULT_HEADERS, allow_redirects=True
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)

            # 2. Extract Manga Details
            # Description is usually contained within a <p> tag inside the .entry-content div
            desc_tag = tree.css_first(".entry-content[itemprop='description'] p")
            manga_description = (
                desc_tag.text(strip=True) if desc_tag else "No description available."
            )

            # Extract Tags/Genres
            manga_tags = [a.text(strip=True) for a in tree.css(".mgen a")]

            # Extract Status from the info box
            manga_status = "Unknown"
            for item in tree.css(".tsinfo .imptdt"):
                if "Status" in item.text():
                    status_tag = item.css_first("i")
                    if status_tag:
                        manga_status = status_tag.text(strip=True)
                    break

            # Asura Scans often does not display alternative names or author prominently in this view
            # We default them to match the schema constraints
            manga_alternative_names = []
            manga_author = "Unknown"

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            # 3. Extract Chapters
            chapters: List[MangaChapter] = []
            chapter_items = tree.css("#chapterlist ul li")

            for item in chapter_items:
                link_tag = item.css_first(".eph-num a")
                if not link_tag:
                    continue

                raw_url = link_tag.attributes.get("href")
                if not raw_url:
                    continue

                # Ensure URL is absolute (Asura Scans usually provides absolute URLs by default)
                chapter_url = (
                    f"https://asurascanz.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()

                title_tag = item.css_first(".chapternum")
                chapter_name = (
                    title_tag.text(strip=True).replace("\n", " ")
                    if title_tag
                    else "Unknown Chapter"
                )

                time_tag = item.css_first(".chapterdate")
                chapter_time = time_tag.text(strip=True) if time_tag else "Unknown Time"

                chapters.append(
                    MangaChapter(
                        chapterId=chapter_id,
                        chapterTitle=chapter_name,
                        chapterUrl=chapter_url,
                        chapterTimeUploaded=chapter_time,
                    )
                )

            # 4. Build navigation map
            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map,
            )

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with self.AsyncClient as client:
            # 1. Fetch the chapter page HTML
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
            )
            response.raise_for_status()

            # 2. Parse the HTML tree
            tree = HTMLParser(response.text)
            pages: list[MangaChapterPage] = []
            raw_urls = []

            # Asura Scans stores chapter images inside the #readerarea container
            for img_tag in tree.css("#readerarea img"):
                # Prioritize data-src for lazy-loaded images, falling back to src
                img_url = img_tag.attributes.get("data-src") or img_tag.attributes.get(
                    "src"
                )

                if img_url:
                    img_url = img_url.strip()
                    # Normalize protocol-relative URLs
                    if img_url.startswith("//"):
                        img_url = f"https:{img_url}"
                    raw_urls.append(img_url)

            if not raw_urls:
                return pages

            # Note: The MangaBuddy-specific stable CDN transformation (mbcdns -> mbbcdn)
            # has been removed here because Asura Scans images are hosted differently.

            # 3. Fetch dimensions via Cloudflare Worker using Chunking
            dimensions_map = {}
            chunk_size = 40  # Safely below Cloudflare's 50 subrequest limit

            for i in range(0, len(raw_urls), chunk_size):
                chunk = raw_urls[i : i + chunk_size]

                try:
                    dim_response = await client.post(
                        DIMENSION_WORKER_URL, json={"urls": chunk}, timeout=30.0
                    )

                    if dim_response.status_code == 200:
                        dimensions_data = dim_response.json()
                        for item in dimensions_data:
                            dimensions_map[item.get("url")] = item
                    else:
                        print(
                            f"Dimension Worker batch {i} returned status {dim_response.status_code}"
                        )

                except Exception as e:
                    print(
                        f"Failed to communicate with dimension worker on batch {i}: {e}"
                    )

                # Delay between batches to prevent rate limiting
                if i + chunk_size < len(raw_urls):
                    await asyncio.sleep(0.5)

            # 4. Iterate through the URLs and build the response schema
            for img_url in raw_urls:
                page_id = hashlib.md5(img_url.encode()).hexdigest()
                proxied_url = img_url

                # Retrieve dimensions from the map
                dim_info = dimensions_map.get(img_url, {})
                width = dim_info.get("width", 0)
                height = dim_info.get("height", 0)

                pages.append(
                    MangaChapterPage(
                        pageId=page_id,
                        pageUrl=url,
                        pageImageUrl=proxied_url,
                        pageWidth=width,
                        pageHeight=height,
                        pageBlurhash="",
                    )
                )

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
