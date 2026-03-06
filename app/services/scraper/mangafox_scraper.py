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
    ChaptersNavigationMap,
    ChapterNavigation,
)

DIMENSION_WORKER_URL = "https://mangabuddy-image-dimension.REDACTED.workers.dev/"

DEFAULT_HEADERS = {
    "Referer": "https://fanfox.net/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
}

SOURCE_NAME = "mangafox"
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class MangafoxScraper(BaseScraper):
    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:

        async with self.AsyncClient as client:
            # Standard search query parameter for WordPress-based sites like Asura Scans
            url = f"https://fanfox.net/manga/re_monster/"

            print(url)

            response = await client.get(url)
            response.raise_for_status()

            with open("test_files/mangafox.html", "w", encoding="utf-8") as f:
                f.write(response.text)

        return {"source": SOURCE_NAME, "message": "this is the mangafox scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            latest_manga: List[Manga] = []

            # 2. Target the list items inside the manga-list-4 container
            for item in tree.css(".manga-list-4-list li"):
                # Extract Title and URL from the title paragraph link
                title_tag = item.css_first(".manga-list-4-item-title a")
                img_tag = item.css_first("img.manga-list-4-cover")

                if not title_tag or not img_tag:
                    continue

                manga_title = title_tag.text(strip=True)
                raw_url = title_tag.attributes.get("href")

                if not raw_url:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://fanfox.net{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # 3. Handle cover image and apply domain replacement
                original_cover = img_tag.attributes.get("src")
                if not original_cover:
                    continue

                # Normalize protocol-relative URLs
                if original_cover.startswith("//"):
                    original_cover = f"https:{original_cover}"

                # Replace the mfcdn.net domain with fanfox.net
                manga_cover = original_cover.replace("mfcdn.net", "fanfox.net")

                # 4. Generate deterministic ID
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

            # 5. Extract "Next Page" URL from the pager-list element
            next_url = None
            # Targeting the link with the ">" character
            next_tag = tree.css_first(".pager-list-left a:last-child")

            if next_tag and next_tag.text() == ">":
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    next_url = (
                        f"https://fanfox.net{raw_next}"
                        if raw_next.startswith("/")
                        else raw_next
                    )

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(
                url, headers=DEFAULT_HEADERS, cookies={"isAdult": "1"}
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)
            popular_manga: List[Manga] = []

            # 2. Select items using the Manga Fox leaderboard structure
            # Items are found in ul.manga-list-1-list > li
            for item in tree.css(".manga-list-1-list li"):
                link_tag = item.css_first("a")
                title_tag = item.css_first(".manga-list-1-item-title a")
                img_tag = item.css_first("img.manga-list-1-cover")

                if not link_tag or not img_tag:
                    continue

                # Extract Title and URL
                # Fallback to img alt if title_tag text is empty
                manga_title = (
                    title_tag.text(strip=True)
                    if title_tag
                    else img_tag.attributes.get("alt", "")
                ).strip()
                raw_url = link_tag.attributes.get("href")

                if not raw_url:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://fanfox.net{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # 3. Handle cover image and apply domain replacement
                original_cover = img_tag.attributes.get("src")
                if not original_cover:
                    continue

                # Normalize protocol-relative URLs
                if original_cover.startswith("//"):
                    original_cover = f"https:{original_cover}"

                # Replace the mfcdn.net domain with fanfox.net
                manga_cover = original_cover.replace("mfcdn.net", "fanfox.net")

                # 4. Generate deterministic ID
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

            # 5. Extract "Next Page" URL
            # Manga Fox leaderboard usually handles pagination via separate tabs or page numbers
            next_url = None
            next_tag = tree.css_first(
                ".pager-list-left a.btn:last-child"
            ) or tree.css_first("a.next")

            if next_tag and "Next" in next_tag.text():
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    next_url = (
                        f"https://fanfox.net{raw_next}"
                        if raw_next.startswith("/")
                        else raw_next
                    )

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            # Manga Fox search URL structure
            search_url = f"https://fanfox.net/search?title={quote(keyword)}"

            response = await client.get(search_url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            results = []

            # 1. Target the list items in the search results grid
            for item in tree.css(".manga-list-4-list li"):
                # 2. Extract Title and URL from the title paragraph link
                title_tag = item.css_first(".manga-list-4-item-title a")
                # 3. Extract Image from the cover image tag
                img_tag = item.css_first("img.manga-list-4-cover")

                if not title_tag or not img_tag:
                    continue

                manga_title = title_tag.text(strip=True)
                raw_url = title_tag.attributes.get("href")

                if not raw_url:
                    continue

                # 4. Normalize absolute URL for the manga page
                manga_url = (
                    f"https://fanfox.net{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # 5. Handle cover image and apply domain replacement
                original_cover = img_tag.attributes.get("src")
                if not original_cover:
                    continue

                # Normalize protocol-relative URLs
                if original_cover.startswith("//"):
                    original_cover = f"https:{original_cover}"

                # Replace the mfcdn.net domain with fanfox.net as requested
                manga_cover = original_cover.replace("mfcdn.net", "fanfox.net")

                # 6. Generate deterministic ID
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
        async with self.AsyncClient as client:
            # 1. Fetch the HTML with the adult cookie to avoid blocks
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
                cookies={"isAdult": "1"},
                allow_redirects=True,
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)

            # 2. Extract Manga Details
            # Priority on .fullcontent to avoid truncated text
            desc_tag = tree.css_first(".fullcontent") or tree.css_first(
                ".detail-info-right-content"
            )
            manga_description = (
                desc_tag.text(strip=True) if desc_tag else "No description available."
            )

            manga_alternative_names = []
            # Genres are inside the tag list container
            manga_tags = [
                a.text(strip=True) for a in tree.css(".detail-info-right-tag-list a")
            ]

            manga_author = "Unknown"
            author_tag = tree.css_first(".detail-info-right-say a")
            if author_tag:
                manga_author = author_tag.text(strip=True)

            manga_status = "Ongoing"
            status_tag = tree.css_first(".detail-info-right-title-tip")
            if status_tag:
                manga_status = status_tag.text(strip=True)

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            # 3. Choose the more complete chapter list
            list_1 = tree.css_first("#list-1")
            list_2 = tree.css_first("#list-2")

            count_1 = len(list_1.css("ul.detail-main-list li")) if list_1 else 0
            count_2 = len(list_2.css("ul.detail-main-list li")) if list_2 else 0

            # Choose larger container
            target_container = list_1 if count_1 >= count_2 else list_2

            chapters: List[MangaChapter] = []
            if target_container:
                for item in target_container.css("ul.detail-main-list li"):
                    link_tag = item.css_first("a")
                    if not link_tag:
                        continue

                    raw_url = link_tag.attributes.get("href")
                    if not raw_url:
                        continue

                    chapter_url = (
                        f"https://fanfox.net{raw_url}"
                        if raw_url.startswith("/")
                        else raw_url
                    )
                    chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()

                    # Manga Fox specific structure for chapter titles and dates
                    title_p = item.css_first("p.title3")
                    time_p = item.css_first("p.title2")

                    chapters.append(
                        MangaChapter(
                            chapterId=chapter_id,
                            chapterTitle=(
                                title_p.text(strip=True)
                                if title_p
                                else "Unknown Chapter"
                            ),
                            chapterUrl=chapter_url,
                            chapterTimeUploaded=(
                                time_p.text(strip=True) if time_p else "Unknown Time"
                            ),
                        )
                    )

            # 4. Build navigation map
            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map,
            )

    async def scrape_chapter_pages(self, url: str) -> List[MangaChapterPage]:
        # Use the async context manager to keep the session open for all requests
        async with self.AsyncClient as client:
            # 1. Fetch initial HTML and extract metadata
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            html_content = response.text

            # Extract imagecount and chapterid
            image_count_match = re.search(r"var imagecount\s*=\s*(\d+);", html_content)
            chapter_id_match = re.search(r"var chapterid\s*=\s*(\d+);", html_content)

            # Extract the guid_key dynamically
            key_match = re.search(r"guidkey\s*=\s*\'([^\']+)\'", html_content)
            if not key_match:
                key_match = re.search(r"7=\'\'\+\'([^\']+)\'", html_content)

            guid_key = (
                key_match.group(1).replace("'", "").replace("+", "")
                if key_match
                else "a13632162dfa2df0"
            )

            if not image_count_match or not chapter_id_match:
                return []

            image_count = int(image_count_match.group(1))
            chapter_id = chapter_id_match.group(1)

            # 2. Construct the dynamic ashx base URL
            # Changes .../c001/1.html to .../c001/chapterfun.ashx
            base_ashx = re.sub(r"\d+\.html$", "chapterfun.ashx", url)
            if not base_ashx.endswith("chapterfun.ashx"):
                base_ashx = url.rstrip("/") + "/chapterfun.ashx"

            raw_urls = []

            # 3. Iterate through batches (2 images per request)
            for page_idx in range(1, image_count + 1, 2):
                ashx_url = (
                    f"{base_ashx}?cid={chapter_id}&page={page_idx}&key={guid_key}"
                )

                try:
                    resp = await client.get(ashx_url, headers={"Referer": url})
                    if resp.status_code != 200:
                        continue

                    # Extract components of the packer
                    packed_match = re.search(
                        r"}\('(.*)',\s*(\d+),\s*(\d+),\s*'(.*)'\.split\('\|'\)",
                        resp.text,
                    )

                    if packed_match:
                        p, a, c, k_raw = packed_match.groups()
                        words = k_raw.split("|")
                        a_int, c_int = int(a), int(c)

                        # Decoder for the base-36 packer
                        def baseN(num, b):
                            return ((num == 0) and "0") or (
                                baseN(num // b, b).lstrip("0")
                                + "0123456789abcdefghijklmnopqrstuvwxyz"[num % b]
                            )

                        unpacked_js = p
                        for i in range(c_int - 1, -1, -1):
                            if words[i]:
                                unpacked_js = re.sub(
                                    r"\b" + baseN(i, a_int) + r"\b",
                                    words[i],
                                    unpacked_js,
                                )

                        # 4. Extract URLs and fix the Domain to fanfox.net
                        pix_match = re.search(r'pix\s*=\s*"([^"]+)"', unpacked_js)
                        pvalue_match = re.search(r"pvalue\s*=\s*\[(.*?)\]", unpacked_js)

                        if pix_match and pvalue_match:
                            base_pix = pix_match.group(1)
                            if base_pix.startswith("//"):
                                base_pix = f"https:{base_pix}"

                            # Standardize domain to zjcdn.fanfox.net
                            base_pix = base_pix.replace("mangafox.me", "fanfox.net")

                            files = pvalue_match.group(1).replace('"', "").split(",")
                            for f in files:
                                f = f.strip()
                                img_url = (
                                    f if f.startswith("http") else f"{base_pix}{f}"
                                )
                                if img_url not in raw_urls:
                                    raw_urls.append(img_url)

                except Exception as e:
                    print(f"Error fetching batch at page {page_idx}: {e}")

            # 5. Fetch dimensions (MUST be inside the 'async with' block)
            dimensions_map = {}
            for i in range(0, len(raw_urls), 40):
                chunk = raw_urls[i : i + 40]
                try:
                    # Use the same 'client' instance while the session is open
                    dim_res = await client.post(
                        DIMENSION_WORKER_URL, json={"urls": chunk}, timeout=30.0
                    )
                    if dim_res.status_code == 200:
                        for item in dim_res.json():
                            dimensions_map[item.get("url")] = item
                except Exception as e:
                    print("Error fetching dimensions:", e)

            # 6. Build final schema response
            pages: List[MangaChapterPage] = []
            for img_url in raw_urls:
                pages.append(
                    MangaChapterPage(
                        pageId=hashlib.md5(img_url.encode()).hexdigest(),
                        pageUrl=url,
                        pageImageUrl=img_url,
                        pageWidth=dimensions_map.get(img_url, {}).get("width", 0),
                        pageHeight=dimensions_map.get(img_url, {}).get("height", 0),
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
