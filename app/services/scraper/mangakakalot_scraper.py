import hashlib
import re
import asyncio
from typing import List

from curl_cffi import AsyncSession
import httpx
from urllib.parse import quote
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
        from urllib.parse import quote

        account_id = "REDACTED"
        api_token = "REDACTED"
        target_url = (
            "https://comick.live/api/comics/the-great-mage-returns-after-4/chapter-list"
        )
        selectors = ["div"]
        wait_until = "networkidle"

        endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/content"

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        # Construct Payload
        payload = {
            "url": target_url,
            # "gotoOptions" controls how long the browser waits before returning
            "gotoOptions": {"waitUntil": wait_until},
        }

        url = "https://comick-source-api.notaspider.dev/api/search"
        payload = {"query": "Solo Leveling", "source": "mangapark"}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Python-Requests/2.x",  # optional, but good practice
        }

        async with httpx.AsyncClient() as client:
            try:
                # Increase timeout because rendering JS takes time
                response = await client.post(url=url, json=payload, headers=headers)

                # Check for errors
                if response.status_code != 200:
                    return ""

                # The API returns the raw HTML directly in the body
                return response.json()

            except Exception as e:
                return ""

        # return {"source": SOURCE_NAME, "message": "this is the mangakakalot scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
            )

            # 1. Parse the HTML tree
            tree = HTMLParser(response.text)

            latest_manga: List[Manga] = []

            # 2. Update selector: The provided HTML uses 'div.manga-list-1 ul.manga-list-1-list li'
            for item in tree.css("div.manga-list-1 ul.manga-list-1-list li"):
                # The title and link are inside a paragraph with class 'manga-list-1-item-title'
                title_tag = item.css_first("p.manga-list-1-item-title a")
                img_tag = item.css_first("img.manga-list-1-cover")

                if not title_tag or not img_tag:
                    continue

                manga_url = title_tag.attributes.get("href")
                manga_title = title_tag.attributes.get("title")

                # 3. Handle relative URLs if necessary
                if manga_url and manga_url.startswith("/"):
                    # You might want to prepend the base domain here if your app requires absolute URLs
                    # manga_url = f"https://www.mangahere.cc{manga_url}"
                    pass

                # 4. Get cover image (MangaHere uses 'src' for these covers)
                original_cover_url = img_tag.attributes.get("src")

                # Handle potential protocol-relative URLs (e.g., //static...)
                if original_cover_url and original_cover_url.startswith("//"):
                    original_cover_url = f"https:{original_cover_url}"

                manga_cover = (
                    f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"
                    if original_cover_url
                    else ""
                )

                # 5. Generate ID
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

            # 6. Extract "Next Page" URL from the pager
            # Pager structure: <div class="pager-list-left"> ... <a href="/directory/2.htm?latest=1">&gt;</a>
            next_tag = tree.css_first("div.pager-list-left a:last-child")
            next_url = None
            if next_tag and next_tag.text() == ">":
                next_url = next_tag.attributes.get("href")

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)

            popular_manga: List[Manga] = []

            for item in tree.css("div.owl-carousel div.item"):
                title_tag = item.css_first("div.slide-caption h3 a")
                img_tag = item.css_first("img")

                if not title_tag or not img_tag:
                    continue

                manga_title = title_tag.text(strip=True)
                manga_url = title_tag.attributes.get("href")
                original_cover_url = img_tag.attributes.get("src")
                manga_cover = (
                    f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"
                )

                if not manga_url:
                    continue

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

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga
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
            resp = await client.get(url, headers=DEFAULT_HEADERS)
            html = HTMLParser(resp.text)

            # Extract Description
            desc_tag = html.css_first(".summary .content")
            manga_description = (
                desc_tag.text(strip=True) if desc_tag else "No description available."
            )

            # Extract Alternative Names
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

            # Extract Meta details (Author, Status, Genres)
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

            chapters: list[MangaChapter] = []
            chapter_items = html.css("#chapter-list li a")

            # Extract Chapters
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
                chapter_time = time_tag.text(strip=True) if time_tag else "Unknown Time"

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
            response = await client.get(url, headers=DEFAULT_HEADERS)

            # 1. Extract the chapImages string using regex
            match = re.search(r"var\s+chapImages\s*=\s*'(.*?)'", response.text)
            pages: list[MangaChapterPage] = []

            if not match:
                return pages

            raw_images_str = match.group(1)

            # 2. Clean and split into a list of URLs
            image_urls = [
                img.strip() for img in raw_images_str.split(",") if img.strip()
            ]

            if not image_urls:
                return pages

            # --- DIMENSION WORKER LOGIC ---

            # 3. Batch URLs (Max 40 per batch to stay safely under Cloudflare's 50 limit)
            batch_size = 40
            url_batches = [
                image_urls[i : i + batch_size]
                for i in range(0, len(image_urls), batch_size)
            ]

            dimension_map = (
                {}
            )  # Dictionary to store { "url": {"width": w, "height": h} }

            # Helper function to request dimensions for a single batch
            async def fetch_dimensions_batch(batch: list[str]):
                try:
                    worker_resp = await client.post(
                        DIMENSION_WORKER_URL,
                        json={"urls": batch},
                        timeout=15.0,  # Give the worker time to fetch the headers
                    )

                    worker_resp.raise_for_status()
                    return worker_resp.json()
                except Exception as e:
                    return []

            # 4. Run all batch requests concurrently
            batch_results = await asyncio.gather(
                *(fetch_dimensions_batch(b) for b in url_batches)
            )

            # 5. Flatten the results and map them by URL for easy lookup
            for batch_result in batch_results:
                for item in batch_result:
                    dimension_map[item.get("url")] = {
                        "width": item.get("width", 0),
                        "height": item.get("height", 0),
                    }

            # ------------------------------

            # 6. Iterate through the original URLs and build the response schema
            for img_url in image_urls:
                # Generate a unique ID based on the original URL
                page_id = hashlib.md5(img_url.encode()).hexdigest()

                # Append proxy URL
                proxied_url = f"{IMAGE_PROXY_WORKER_URL}?url={quote(img_url)}"

                # Lookup dimensions (fallback to 0 if the worker failed for this specific image)
                dims = dimension_map.get(img_url, {"width": 0, "height": 0})

                pages.append(
                    MangaChapterPage(
                        pageId=page_id,
                        pageUrl=url,
                        pageImageUrl=proxied_url,
                        pageWidth=dims["width"],
                        pageHeight=dims["height"],
                        pageBlurhash="",
                    )
                )

            return pages

    async def get_image_dimensions(
        self, client: httpx.AsyncClient, image_url: str
    ) -> tuple[int, int]:
        try:
            res = await client.get(
                f"{IMAGE_METADATA_PROXY_WORKER_URL}?url={quote(image_url)}",
                headers=DEFAULT_HEADERS,
                timeout=5,
            )
            data = res.json()
            return int(data.get("width", 0)), int(data.get("height", 0))
        except Exception as e:
            print(e)
            return 0, 0

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
