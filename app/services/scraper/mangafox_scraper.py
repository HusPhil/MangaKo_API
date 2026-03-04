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
            url = f"https://fanfox.net/manga/onepunch_man/v01/c001/3.html"

            print(url)

            response = await client.get(url)
            response.raise_for_status()

            with open("test_files/mangafox.html", "w", encoding="utf-8") as f:
                f.write(response.text)

            resp = await client.get(
                "https://fanfox.net//manga/onepunch_man/v01/c001/chapterfun.ashx?cid=184674&page=3  &key=a13632162dfa2df0",
                headers={"Referer": url},
            )

            with open("test_files/kineme.html", "w", encoding="utf-8") as f:
                f.write(resp.text)

        return {"source": SOURCE_NAME, "message": "this is the mangafox scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            latest_manga: List[Manga] = []

            # 1. Target the list items inside the main container
            for item in tree.css(".list_wrap ul li"):
                # Extract Title and URL from the .visual .manga-cover link
                link_tag = item.css_first(".visual .manga-cover a")
                img_tag = item.css_first(".visual .manga-cover img")

                if not link_tag or not img_tag:
                    continue

                manga_title = img_tag.attributes.get("alt", "").strip()
                raw_url = link_tag.attributes.get("href")

                if not raw_url:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://manhuato.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # Handle cover image with lazy-loading fallback
                manga_cover = img_tag.attributes.get(
                    "data-original"
                ) or img_tag.attributes.get("src")

                if not manga_cover:
                    continue

                # Generate deterministic ID
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
            # Targeting the link with the right arrow icon
            next_tag = tree.css_first(".pagination li a[aria-label='Next']")

            if next_tag:
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    if raw_next.startswith("/"):
                        next_url = f"https://manhuato.com{raw_next}"
                    else:
                        next_url = raw_next

            return LatestMangaListResponse(
                source=SOURCE_NAME, latest_manga=latest_manga, next_url=next_url
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            # 1. Fetch the HTML
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            popular_manga: List[Manga] = []

            # 2. Select items using the ManhuaTo list structure
            # Items are inside .list_wrap > ul > li
            for item in tree.css(".list_wrap ul li"):
                link_tag = item.css_first(".visual .manga-cover a")
                img_tag = item.css_first(".visual .manga-cover img")

                if not link_tag or not img_tag:
                    continue

                # Extract Title from img alt and URL from the link
                manga_title = img_tag.attributes.get("alt", "").strip()
                raw_url = link_tag.attributes.get("href")

                if not raw_url:
                    continue

                # Ensure the URL is absolute
                manga_url = (
                    f"https://manhuato.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # Handle cover image: use data-original for the actual high-quality thumbnail
                manga_cover = img_tag.attributes.get(
                    "data-original"
                ) or img_tag.attributes.get("src")

                if not manga_cover:
                    continue

                # Generate deterministic ID
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

            # 3. Extract "Next Page" URL from the pagination element
            next_url = None
            next_tag = tree.css_first(".pagination li a[aria-label='Next']")

            if next_tag:
                raw_next = next_tag.attributes.get("href")
                if raw_next:
                    if raw_next.startswith("/"):
                        next_url = f"https://manhuato.com{raw_next}"
                    else:
                        next_url = raw_next

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME, popular_manga=popular_manga, next_url=next_url
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            # ManhuaTo standard search URL structure
            # Note: ManhuaTo uses spaces in the URL for search keywords based on the HTML metadata
            search_url = f"https://manhuato.com/{quote(keyword)}"

            response = await client.get(search_url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            tree = HTMLParser(response.text)
            results = []

            # Target the list items inside the main results container
            # The provided HTML structure: .section_todayup > .list_wrap > ul > li
            for item in tree.css(".list_wrap ul li"):
                # 1. Extract Title and URL from the .main_text h3 link
                title_tag = item.css_first(".main_text h3.title a")
                # 2. Extract Image from the .visual .manga-cover container
                img_tag = item.css_first(".visual .manga-cover img")

                if not title_tag or not img_tag:
                    continue

                manga_title = title_tag.text(strip=True)
                raw_url = title_tag.attributes.get("href")

                # 3. Normalize absolute URL
                manga_url = (
                    f"https://manhuato.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                # 4. Handle cover image (prefer data-original for lazy-loaded images)
                manga_cover = img_tag.attributes.get(
                    "data-original"
                ) or img_tag.attributes.get("src")

                if not manga_cover:
                    continue

                # 5. Generate deterministic ID
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
            # 1. Fetch the HTML
            response = await client.get(
                url, headers=DEFAULT_HEADERS, allow_redirects=True
            )
            response.raise_for_status()

            tree = HTMLParser(response.text)

            # 2. Extract Manga Details
            # Description is inside .desc tags (there are two, the first usually contains the synopsis)
            desc_tag = tree.css_first(".desc")
            manga_description = (
                desc_tag.text(strip=True) if desc_tag else "No description available."
            )

            # Alternative names are in the h2 class "alternative"
            alt_names_tag = tree.css_first("h2.alternative")
            manga_alternative_names = []
            if alt_names_tag:
                # Splits by comma and cleans whitespace
                manga_alternative_names = [
                    name.strip() for name in alt_names_tag.text().split(",")
                ]

            # Extract Tags/Genres from the .hentai-info section
            manga_tags = []
            for tag in tree.css(".hentai-info .item-tag"):
                # Filtering out tags that might be authors or artists by checking the parent text
                parent_text = (
                    tag.parent.parent.text() if tag.parent and tag.parent.parent else ""
                )
                if "Genres" in parent_text:
                    manga_tags.append(tag.text(strip=True))

            # Extract Author and Status
            manga_author = "Unknown"
            manga_status = "Ongoing"

            for line in tree.css(".hentai-info .line"):
                line_text = line.text()
                if "Authors:" in line_text:
                    author_tag = line.css_first(".item-tag")
                    if author_tag:
                        manga_author = author_tag.text(strip=True)
                elif "Status:" in line_text:
                    status_content = line.css_first(".line-content")
                    if status_content:
                        manga_status = status_content.text(strip=True)

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            # 3. Extract Chapters
            chapters: List[MangaChapter] = []
            # Chapters are in <li class="citem"> inside <ul id="chapter-list">
            for item in tree.css("#chapter-list li.citem"):
                link_tag = item.css_first("a")
                if not link_tag:
                    continue

                raw_url = link_tag.attributes.get("href")
                if not raw_url:
                    continue

                chapter_url = (
                    f"https://manhuato.com{raw_url}"
                    if raw_url.startswith("/")
                    else raw_url
                )

                chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()
                chapter_name = link_tag.text(strip=True)

                time_tag = item.css_first(".time")
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
