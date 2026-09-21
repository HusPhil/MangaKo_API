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

IMAGE_PROXY_WORKER_URL = "https://mangabuddy-image-proxy.REDACTED.workers.dev/"
DIMENSION_WORKER_URL = "https://mangabuddy-image-dimension.REDACTED.workers.dev/"

DEFAULT_HEADERS = {
    "Referer": "https://mangahere.cc/manga/one_piece/v98/c1071/2.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
}

SOURCE_NAME = "mangakakalot"
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class MangakakalotScraper(BaseScraper):
    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://manhuato.com/manhua/magic-emperor/magic-emperor-chapter-576-ch341494",
                headers=DEFAULT_HEADERS,
            )

        return {"source": SOURCE_NAME, "message": "this is the mangakakalot scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)

            tree = HTMLParser(response.text)

            latest_manga: list[Manga] = []

            # 1. Select the items using MangaBuddy's grid layout classes
            story_items = tree.css(".book-item .book-detailed-item")

            for item in story_items:
                thumb_link_tag = item.css_first(".thumb a")
                title_tag = item.css_first(".meta .title h3 a")
                img_tag = item.css_first(".thumb img")

                if not thumb_link_tag or not title_tag or not img_tag:
                    continue

                # Title extraction: Fallback to the text content if the title attribute is missing
                manga_title = thumb_link_tag.attributes.get("title") or title_tag.text(
                    strip=True
                )

                raw_url = thumb_link_tag.attributes.get("href")
                # Format relative paths into absolute URLs
                manga_url = (
                    f"https://mangabuddy.com{raw_url}"
                    if raw_url and raw_url.startswith("/")
                    else raw_url
                )

                # Cover image extraction: MangaBuddy uses lazy loading
                original_cover_url = img_tag.attributes.get(
                    "data-src"
                ) or img_tag.attributes.get("src")

                if not manga_url or not original_cover_url:
                    continue

                manga_cover = (
                    f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"
                )
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

            # 2. Extract "Next Page" URL from the select dropdown
            next_url = None
            options = tree.css(".paginator select option")

            for i, opt in enumerate(options):
                # Locate the currently selected page option
                if "selected" in opt.attributes:
                    # Check if there is a subsequent option available
                    if i + 1 < len(options):
                        raw_next = options[i + 1].attributes.get("value")
                        if raw_next:
                            next_url = (
                                f"https://mangabuddy.com{raw_next}"
                                if raw_next.startswith("/")
                                else raw_next
                            )
                    break

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)

            popular_manga: List[Manga] = []

            # 1. Target the correct grid layout for the MangaBuddy popular list
            story_items = tree.css(".book-item .book-detailed-item")

            for item in story_items:
                thumb_link_tag = item.css_first(".thumb a")
                title_tag = item.css_first(".meta .title h3 a")
                img_tag = item.css_first(".thumb img")

                if not thumb_link_tag or not title_tag or not img_tag:
                    continue

                # Extract title, prioritizing the attribute to avoid inner HTML tags
                manga_title = thumb_link_tag.attributes.get("title") or title_tag.text(
                    strip=True
                )

                raw_url = thumb_link_tag.attributes.get("href")
                # Ensure the URL is absolute
                manga_url = (
                    f"https://mangabuddy.com{raw_url}"
                    if raw_url and raw_url.startswith("/")
                    else raw_url
                )

                # Extract the real image source from 'data-src' due to lazy loading
                original_cover_url = img_tag.attributes.get(
                    "data-src"
                ) or img_tag.attributes.get("src")

                if not manga_url or not original_cover_url:
                    continue

                manga_cover = (
                    f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"
                )
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

            # 2. Extract "Next Page" URL from the pagination dropdown
            next_url = None
            options = tree.css(".paginator select option")

            for i, opt in enumerate(options):
                if "selected" in opt.attributes:
                    # Retrieve the value of the subsequent option if it exists
                    if i + 1 < len(options):
                        raw_next = options[i + 1].attributes.get("value")
                        if raw_next:
                            next_url = (
                                f"https://mangabuddy.com{raw_next}"
                                if raw_next.startswith("/")
                                else raw_next
                            )
                    break

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with httpx.AsyncClient() as client:
            search_url = (
                f"https://mangabuddy.com/search?q={self._to_mangakakalot_slug(keyword)}"
            )
            response = await client.get(search_url, headers=DEFAULT_HEADERS)

            tree = HTMLParser(response.text)

            # MangaBuddy uses .book-item for its grid list
            story_items = tree.css(".list.manga-list .book-item .book-detailed-item")
            results: list[Manga] = []

            for item in story_items:
                thumb_link_tag = item.css_first(".thumb a")
                title_tag = item.css_first(".meta .title h3 a")
                img_tag = item.css_first(".thumb img")

                if not thumb_link_tag or not title_tag or not img_tag:
                    continue

                # The title inside the <a> tag contains HTML spans for highlights.
                # We use the title attribute from the thumb link for a clean string.
                manga_title = thumb_link_tag.attributes.get("title") or title_tag.text(
                    strip=True
                )

                raw_url = thumb_link_tag.attributes.get("href")

                # Convert relative paths to absolute URLs
                manga_url = (
                    f"https://mangabuddy.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # MangaBuddy uses lazy loading, so the actual cover is in 'data-src'
                original_cover_url = img_tag.attributes.get(
                    "data-src"
                ) or img_tag.attributes.get("src")

                if not manga_url or not original_cover_url:
                    continue

                manga_cover = (
                    f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"
                )
                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                results.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga_id,
                        mangaTitle=manga_title,
                        mangaUrl=manga_url,
                        mangaCover=manga_cover,
                    )
                )

            return MangaSearchResponse(source=SOURCE_NAME, results=results)

    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with httpx.AsyncClient() as client:
            # 1. Fetch main page HTML
            resp = await client.get(url, headers=DEFAULT_HEADERS)
            html = HTMLParser(resp.text)

            # --- Extract Manga Details ---
            desc_tag = html.css_first(".summary .content")
            manga_description = (
                desc_tag.text(strip=True) if desc_tag else "No description available."
            )

            alt_names_tag = html.css_first(".detail .name h2")
            if alt_names_tag:
                manga_alternative_names = [
                    name.strip()
                    for name in alt_names_tag.text().split(",")
                    if name.strip()
                ]
            else:
                manga_alternative_names = []

            manga_author = "Unknown"
            manga_status = "Unknown"
            manga_tags = []

            meta_paragraphs = html.css(".detail .meta.box p")
            for p in meta_paragraphs:
                strong_tag = p.css_first("strong")
                if not strong_tag:
                    continue

                label = strong_tag.text(strip=True).lower()

                if "authors" in label:
                    authors = [
                        a.text(strip=True).replace(",", "").strip() for a in p.css("a")
                    ]
                    manga_author = ", ".join(authors) if authors else "Unknown"
                elif "status" in label:
                    status_tag = p.css_first("a")
                    manga_status = (
                        status_tag.text(strip=True) if status_tag else "Unknown"
                    )
                elif "genres" in label:
                    manga_tags = [
                        a.text(strip=True).replace(",", "").strip() for a in p.css("a")
                    ]

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            # --- Extract Chapters via API ---
            chapters: list[MangaChapter] = []

            # Use regex to find bookId
            match = re.search(r"var\s+bookId\s*=\s*(\d+)", resp.text)

            if match:
                book_id = match.group(1)

                # Fetch the chapters HTML payload
                chapters_resp = await client.get(
                    f"https://mangabuddy.com/api/manga/{book_id}/chapters?source=detail",
                    headers=DEFAULT_HEADERS,
                )

                # Parse the returned HTML chunk
                chapters_html = HTMLParser(chapters_resp.text)

                # The API returns the <ul id="chapter-list"> directly
                chapter_items = chapters_html.css("li a")

                for item in chapter_items:
                    raw_url = item.attributes.get("href")
                    if not raw_url:
                        continue

                    # Convert relative paths to absolute URLs
                    chapter_url = (
                        f"https://mangabuddy.com{raw_url}"
                        if raw_url.startswith("/")
                        else raw_url
                    )
                    chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()

                    title_tag = item.css_first(".chapter-title")
                    chapter_name = (
                        title_tag.text(strip=True) if title_tag else "Unknown Chapter"
                    )

                    time_tag = item.css_first(".chapter-update")
                    chapter_time = (
                        time_tag.text(strip=True) if time_tag else "Unknown Time"
                    )

                    chapters.append(
                        MangaChapter(
                            chapterId=chapter_id,
                            chapterTitle=chapter_name,
                            chapterUrl=chapter_url,
                            chapterTimeUploaded=chapter_time,
                        )
                    )

            # Build navigation map
            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map,
            )

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with httpx.AsyncClient() as client:
            # 1. Fetch the chapter page HTML
            response = await client.get(url, headers=DEFAULT_HEADERS)

            match = re.search(r"var\s+chapImages\s*=\s*'(.*?)'", response.text)
            pages: list[MangaChapterPage] = []

            if not match:
                return pages

            raw_images_str = match.group(1)
            raw_urls = [img.strip() for img in raw_images_str.split(",") if img.strip()]

            if not raw_urls:
                return pages

            # 2. Transform volatile URLs to the stable CDN
            stable_urls = []
            for img_url in raw_urls:
                stable_url = re.sub(
                    r"https://s\d+\.mbcdns[a-z]+\.org/res/",
                    "https://sb.mbbcdn.com/",
                    img_url,
                )
                stable_urls.append(stable_url)

            # 3. Fetch dimensions via Cloudflare Worker using Chunking
            dimensions_map = {}
            chunk_size = 40  # Safely below Cloudflare's 50 subrequest limit

            for i in range(0, len(stable_urls), chunk_size):
                chunk = stable_urls[i : i + chunk_size]

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

                # Delay between batches to prevent rate limiting from the target CDN
                if i + chunk_size < len(stable_urls):
                    await asyncio.sleep(0.5)

            # 4. Iterate through the stable URLs and build the response schema
            for img_url in stable_urls:
                page_id = hashlib.md5(img_url.encode()).hexdigest()
                proxied_url = f"{IMAGE_PROXY_WORKER_URL}?url={quote(img_url)}"

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

    def _to_mangakakalot_slug(self, query: str) -> str:
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
