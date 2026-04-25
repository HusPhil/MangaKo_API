import hashlib
from http import cookies
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
)

DIMENSION_WORKER_URL = "https://mangabuddy-image-dimension.REDACTED.workers.dev/"

DEFAULT_HEADERS = {
    "Referer": "https://fanfox.net/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
}

SOURCE_NAME = "weeb_central"
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class WeebCentralScraper(BaseScraper):
    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:

        async with self.AsyncClient as client:
            # Standard search query parameter for WordPress-based sites like Asura Scans
            url = f"https://weebcentral.com/search/data?author=&text=murim&sort=Best%20Match&order=Descending&official=Any&anime=Any&adult=Any&display_mode=Full%20Display"

            print(url)

            response = await client.get(url)
            response.raise_for_status()

        return {"source": SOURCE_NAME, "message": "this is the weebcentral scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            latest_manga: List[Manga] = []

            # 2. Iterate through each manga article
        for item in tree.css("article.bg-base-300"):
            # A. The Link/URL: Look for the anchor that goes to /series/
            # This exists in both the mobile and desktop sections.
            link_tag = item.css_first("a[href*='/series/']")

            # B. The Image: Look for the <img> tag that contains 'cover' in its URL
            # We skip the SVG icons by looking specifically for the cover domain/path
            img_tag = item.css_first("img[src*='cover']")

            # C. The Title:
            # In your HTML, the most reliable clean text is in the img 'alt'
            # or the link text in the second section. Let's try both.
            manga_title = None

            # Strategy 1: The 'alt' attribute usually has "Title cover"
            if img_tag:
                alt_text = img_tag.attributes.get("alt", "")
                manga_title = alt_text.replace(" cover", "").strip()

            # Strategy 2: If alt is missing, get the first link text inside the second section
            if not manga_title:
                title_node = item.css_first("section.lg\\:block a.link-hover")
                if title_node:
                    manga_title = title_node.text(strip=True)

            print(
                f"Found manga - Title: {manga_title}, Link: {link_tag.attributes.get('href') if link_tag else 'N/A'}, Image: {img_tag.attributes.get('src') if img_tag else 'N/A'}"
            )

            # Debug: check what we found
            if not link_tag or not img_tag or not manga_title:
                # Log specifically what is missing to troubleshoot
                print(
                    f"Skipping: link={bool(link_tag)}, img={bool(img_tag)}, title={bool(manga_title)}"
                )
                continue

            raw_url = link_tag.attributes.get("href")
            manga_cover = img_tag.attributes.get("src")

            # Ensure the URL is absolute
            manga_url = (
                f"https://weebcentral.com{raw_url}"
                if raw_url.startswith("/")
                else raw_url
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

        # 3. Extract "Next Page" URL from HTMX button
        next_url = None
        next_tag = tree.css_first("button[hx-get]")
        if next_tag:
            raw_next = next_tag.attributes.get("hx-get")
            if raw_next:
                next_url = (
                    f"https://weebcentral.com{raw_next}"
                    if raw_next.startswith("/")
                    else raw_next
                )

        return LatestMangaListResponse(
            source=SOURCE_NAME, latest_manga=latest_manga, next_url=None
        )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            popular_manga: List[Manga] = []

            # 2. Iterate through each manga article
            for item in tree.css("article.bg-base-300"):
                # A. The Link/URL: Look for the anchor that goes to /series/
                link_tag = item.css_first("a[href*='/series/']")

                # B. The Image: Look for the <img> tag that contains 'cover' in its URL
                img_tag = item.css_first("img[src*='cover']")

                # C. The Title: Strategy 1 (Alt text) then Strategy 2 (Link text)
                manga_title = None

                if img_tag:
                    alt_text = img_tag.attributes.get("alt", "")
                    # Clean up "Title cover" or "Title (Color) cover"
                    manga_title = alt_text.replace(" cover", "").strip()

                if not manga_title:
                    title_node = item.css_first("section.lg\\:block a.link-hover")
                    if title_node:
                        manga_title = title_node.text(strip=True)

                # Validation
                if not link_tag or not img_tag or not manga_title:
                    continue

                raw_url = link_tag.attributes.get("href")
                manga_cover = img_tag.attributes.get("src")

                # Ensure the URL is absolute
                manga_url = (
                    f"https://weebcentral.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
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

            # 3. Extract "Next Page" URL from HTMX button
            next_url = None
            next_tag = tree.css_first("button[hx-get]")
            if next_tag:
                raw_next = next_tag.attributes.get("hx-get")
                if raw_next:
                    next_url = (
                        f"https://weebcentral.com{raw_next}"
                        if raw_next.startswith("/")
                        else raw_next
                    )

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            # WeebCentral search data endpoint with 'Full Display' to get all metadata
            search_url = f"https://weebcentral.com/search/data?author=&text={quote(keyword)}&sort=Best%20Match&order=Descending&official=Any&anime=Any&adult=Any&display_mode=Full%20Display"

            response = await client.get(
                search_url, headers=DEFAULT_HEADERS, cookies={"isAdult": "1"}
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)
            results: List[Manga] = []

            # Each result is wrapped in an <article> tag
            for article in tree.css("article.bg-base-300"):
                # 1. Extract URL and Title from the link in the sidebar or heading
                link_node = article.css_first("a[href*='/series/']")
                if not link_node:
                    continue

                manga_url = link_node.attributes.get("href", "")

                # The title is usually in the alt text of the img or inside a hidden-on-mobile div
                # We'll grab it from the alt attribute of the image for reliability
                img_node = article.css_first("img")
                manga_title = "Unknown"
                if img_node:
                    manga_title = (
                        img_node.attributes.get("alt", "").replace(" cover", "").strip()
                    )

                # 2. Extract Cover Image
                # We check for the webp source first for better quality/compression
                source_node = article.css_first("picture source")
                if source_node:
                    manga_cover = source_node.attributes.get("srcset", "")
                elif img_node:
                    manga_cover = img_node.attributes.get("src", "")
                else:
                    manga_cover = ""

                # 3. Extract ID from URL
                # Format: https://weebcentral.com/series/01J76XYE0NQJN87JW5VZNAQG70/Murim-Login
                manga_id = manga_url.split("/series/")[1].split("/")[0]

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
        async with self.AsyncClient as client:
            # 1. Fetch main page for Metadata
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
                cookies={"isAdult": "1"},
                allow_redirects=True,
            )
            response.raise_for_status()
            main_tree = HTMLParser(response.text)

            # Extract Details
            manga_description = ""
            desc_node = main_tree.css_first("ul.flex.flex-col.gap-4 li p")
            if desc_node:
                manga_description = desc_node.text(strip=True)

            manga_author = "Unknown"
            author_node = main_tree.css_first("a[href*='search?author=']")
            if author_node:
                manga_author = author_node.text(strip=True)

            manga_status = "Unknown"
            status_node = main_tree.css_first("a[href*='included_status=']")
            if status_node:
                manga_status = status_node.text(strip=True)

            manga_tags = [
                tag.text(strip=True)
                for tag in main_tree.css("a[href*='included_tag=']")
            ]

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=[],
            )

            # 2. Build and Fetch the Full Chapter List URL
            # Logic: https://weebcentral.com/series/[ID]/[SLUG] -> https://weebcentral.com/series/[ID]/full-chapter-list
            url_parts = url.split("/")
            if "series" in url_parts:
                series_idx = url_parts.index("series")
                full_list_url = (
                    "/".join(url_parts[: series_idx + 2]) + "/full-chapter-list"
                )
            else:
                full_list_url = url.rstrip("/") + "/full-chapter-list"

            list_response = await client.get(
                full_list_url,
                headers=DEFAULT_HEADERS,
                cookies={"isAdult": "1"},
            )
            list_response.raise_for_status()
            list_tree = HTMLParser(list_response.text)

            # 3. Extract All Chapters
            chapters: List[MangaChapter] = []

            # We target each row container
            for row in list_tree.css("div.flex.items-center"):
                link_node = row.css_first("a[href*='/chapters/']")
                if not link_node:
                    continue

                chapter_url = link_node.attributes.get("href", "")

                # --- CLEAN TITLE EXTRACTION ---
                # The structure is: <span class="grow"><span class="">Text</span><span x-show="...">SVG</span></span>
                # We specifically target the span INSIDE 'grow' that DOES NOT have the 'x-show' attribute.
                title_node = link_node.css_first("span.grow span:not([x-show])")

                if title_node:
                    chapter_title = title_node.text(strip=True)
                else:
                    # Fallback: Get text from the grow container but don't go into children (deep=False)
                    grow_node = link_node.css_first("span.grow")
                    chapter_title = (
                        grow_node.text(deep=False, strip=True)
                        if grow_node
                        else "Unknown Chapter"
                    )

                # 4. Extract Time
                time_node = row.css_first("time")
                chapter_time = (
                    time_node.attributes.get("datetime", "") if time_node else ""
                )

                chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()

                chapters.append(
                    MangaChapter(
                        chapterId=chapter_id,
                        chapterTitle=chapter_title,
                        chapterUrl=chapter_url,
                        chapterTimeUploaded=chapter_time,
                    )
                )

            # 3. Build navigation map
            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map,
            )

    async def scrape_chapter_pages(self, url: str) -> List[MangaChapterPage]:
        # 1. Transform the URL to the images endpoint
        # input:  https://weebcentral.com/chapters/[ID]/
        # output: https://weebcentral.com/chapters/[ID]/images?is_prev=False&current_page=1&reading_style=long_strip
        base_url = url.rstrip("/")
        images_endpoint = (
            f"{base_url}/images?is_prev=False&current_page=1&reading_style=long_strip"
        )

        async with self.AsyncClient as client:
            # 2. Fetch the HTML containing the <img> tags
            response = await client.get(
                images_endpoint, headers=DEFAULT_HEADERS, cookies={"isAdult": "1"}
            )
            response.raise_for_status()

            # 3. Parse the HTML partial
            tree = HTMLParser(response.text)
            pages: List[MangaChapterPage] = []

            # 4. Iterate through all <img> tags inside the section
            # The example HTML shows <img> tags directly under the <section>
            for img in tree.css("img"):
                img_url = img.attributes.get("src", "")
                if not img_url or "broken_image.jpg" in img_url:
                    continue

                # 5. Extract dimensions from attributes
                # WeebCentral provides width and height directly in the HTML attributes
                width = int(img.attributes.get("width", 0))
                height = int(img.attributes.get("height", 0))

                pages.append(
                    MangaChapterPage(
                        pageId=hashlib.md5(img_url.encode()).hexdigest(),
                        pageUrl=url,  # Original chapter URL
                        pageImageUrl=img_url,
                        pageWidth=width,
                        pageHeight=height,
                        pageBlurhash="",  # Blurhash usually requires processing the image itself
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
