import hashlib
import httpx
from curl_cffi import AsyncSession
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

from urllib.parse import quote


IMAGE_PROXY_WORKER_URL = "https://comick-image-proxy.REDACTED.workers.dev/"
IMAGE_METADATA_PROXY_WORKER_URL = (
    "https://mangako-image-metadata-worker.REDACTED.workers.dev/"
)
DEFAULT_HEADERS = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=1, i",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-arch": '""',
    "sec-ch-ua-bitness": "64",
    "sec-ch-ua-full-version": "137.0.7151.56",
    "sec-ch-ua-full-version-list": (
        '"Google Chrome";v="137.0.7151.56", "Chromium";v="137.0.7151.56", "Not/A)Brand";v="24.0.0.0"'
    ),
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-model": "Nexus 5",
    "sec-ch-ua-platform": "Android",
    "sec-ch-ua-platform-version": "6.0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
}

cookies = {}

status_map = {1: "Ongoing", 2: "Completed", 3: "Cancelled", 4: "Hiatus", 5: "Unknown"}

SOURCE_NAME = "comick"
MAX_CONCURRENT_REQUESTS = 10
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class ComickioScrapper(BaseScraper):

    def __init__(self):
        self.AsyncClient = AsyncSession(
            impersonate="chrome_android", headers=DEFAULT_HEADERS, cookies=cookies
        )

    async def scrape(self) -> dict:
        url = "https://api.comick.fun/v1.0/comic/genius-corpse-collecting-warrior"

        async with self.AsyncClient:
            response = await self.fetch_with_scraper(url)
            response.raise_for_status()

        return {
            "res": "Comick source is working without hiccups!",
            "source": SOURCE_NAME,
        }

    async def scrape_latest_manga(self, url: str):
        async with self.AsyncClient as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            manga_entries = data.get("data", [])

            latest_manga = []
            seen_ids = set()

            for manga in manga_entries:
                m_id = str(manga["id"])

                # Skip if we've already seen this ID
                if m_id in seen_ids:
                    continue

                # Safety check: Ensure the English translation keys exist
                lang_data = manga.get("chapter_latest_by_langs", {}).get("en")
                if not lang_data:
                    continue

                latest_manga.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=m_id,
                        mangaTitle=str(manga["title"]),
                        mangaCover=f"{IMAGE_PROXY_WORKER_URL}?url={manga['default_thumbnail']}",
                        mangaUrl=f"https://comick.live/api/comics/{manga['slug']}/{lang_data['hid']}-chapter-{lang_data['chapter_number_slug']}-en",
                    )
                )
                seen_ids.add(m_id)

            return LatestMangaListResponse(
                source=SOURCE_NAME,
                latest_manga=latest_manga,
                next_url=f"{url}&cursor={data.get('next_cursor')}",
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.AsyncClient as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json().get("data", [])

            popular_manga = []
            seen_ids = set()  # Track unique IDs here

            for manga in data:
                m_id = str(manga["id"])
                if m_id not in seen_ids:
                    popular_manga.append(
                        Manga(
                            mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                            mangaId=m_id,
                            mangaTitle=str(manga["title"]),
                            mangaCover=f"{IMAGE_PROXY_WORKER_URL}?url={manga['default_thumbnail']}",
                            mangaUrl=f"https://comick.live/api/comics/{manga['slug']}/{manga['chapter_latest_by_langs']['en']['hid']}-chapter-{manga['chapter_latest_by_langs']['en']['chapter_number_slug']}-en",
                        )
                    )
                    seen_ids.add(m_id)

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME,
                popular_manga=popular_manga,
                next_url=f"{url}&cursor={response.json().get('next_cursor')}",
            )

    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with self.AsyncClient as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            chapter_data = data.get("chapter", {})
            comic_data = chapter_data.get("comic", {})
            chapter_list_data = data.get("chapterList", [])

            # Status Mapping: 1/Ongoing 2/Completed 3/Cancelled 4/Hiatus
            # Looking at the JSON, status is null, so we use a fallback
            status_map = {1: "Ongoing", 2: "Completed", 3: "Cancelled", 4: "Hiatus"}
            raw_status = chapter_data.get("status")

            manga_details = MangaDetails(
                mangaDescription=comic_data.get(
                    "description", "No description available."
                ),
                # Using group_name as author since that's what was in your snippet
                mangaAuthor=chapter_data.get("group_name", "Unknown Author"),
                mangaStatus=status_map.get(raw_status, "Unknown"),
                mangaTags=[],  # You can map comic_data.get("genres") here if needed
                mangaAlternativeNames=[],
            )

            manga_chapters: list[MangaChapter] = []
            seen_titles = set()

            for chapter in chapter_list_data:
                chap_num = chapter.get("chap")

                # Build a consistent title for deduplication
                # Logic: If 'title' is a string, use it. Otherwise, use 'Chapter X'
                raw_title = chapter.get("title")
                if raw_title and str(raw_title).strip():
                    display_title = raw_title
                else:
                    display_title = (
                        f"Chapter {chap_num}" if chap_num else "Unknown Chapter"
                    )

                # Deduplication Check
                if display_title in seen_titles:
                    continue

                res_chapter = MangaChapter(
                    chapterId=chapter["hid"],
                    chapterTitle=display_title,
                    # Dynamically building the slug URL using the comic slug and chapter data
                    chapterUrl=(
                        f"https://comick.live/api/comics/{comic_data.get('slug')}/"
                        f"{chapter['hid']}-chapter-{chap_num}-{chapter['lang']}"
                    ),
                    chapterTimeUploaded=chapter.get("created_at"),
                )

                manga_chapters.append(res_chapter)
                seen_titles.add(display_title)

            chapterNavigationMap = self._build_chapters_navigation_map(manga_chapters)

            return MangaInfoResponse(
                mangaDetails=manga_details,
                mangaChapters=manga_chapters,
                chaptersNavigationMap=chapterNavigationMap,
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.AsyncClient:
            search_url = f"https://api.comick.fun/v1.0/search/?page=1&limit=300&sort=user_follow_count&showall=false&q={self._to_comickio_slug(keyword)}"
            response = await self.fetch_with_scraper(search_url)
            response.raise_for_status()
            results = []

            for manga in response.json():
                if (
                    not manga.get("slug")
                    or not manga.get("md_covers")
                    or not isinstance(manga["md_covers"], list)
                    or not manga["md_covers"][0].get("b2key")
                ):
                    continue  # Skip if essential data is missing

                results.append(
                    Manga(
                        mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                        mangaId=manga["hid"],
                        mangaTitle=manga.get("title", "Unknown Title"),
                        mangaCover=f"https://meo.comick.pictures/{manga['md_covers'][0]['b2key']}",
                        mangaUrl=f"https://api.comick.fun/v1.0/comic/{manga['slug']}",
                    )
                )

            return MangaSearchResponse(source=SOURCE_NAME, results=results)

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with self.AsyncClient as client:
            response = await client.get(url)
            response.raise_for_status()

            pages_data = response.json().get("chapter").get("images")

            pages = []
            for page_data in pages_data:
                pages.append(
                    MangaChapterPage(
                        pageId=hashlib.md5(
                            page_data["url"].encode("utf-8")
                        ).hexdigest(),
                        pageUrl=url,
                        pageImageUrl=f"{IMAGE_PROXY_WORKER_URL}?url={quote(page_data['url'])}",
                        pageWidth=page_data["w"],
                        pageHeight=page_data["h"],
                        pageBlurhash="",
                    )
                )

            return pages

    async def get_blurhash(
        self, client: httpx.AsyncClient, endpoint: str, image_url: str
    ) -> str | None:
        print("[DEBUG] OVERRIDEN Fetching blurhash for image URL:", image_url)
        try:
            async with self.AsyncClient:
                res = await client.get(f"{endpoint}?url={quote(image_url)}", timeout=5)
                res.raise_for_status()
                return res.json().get("blurhash")
        except Exception:
            return None

    def _to_comickio_slug(self, query: str) -> str:
        """
        Convert a search query to ComickIO's expected slug format.
        - Lowercase
        - Remove non-word characters
        - Replace spaces with underscores
        """
        import re

        query = query.strip().lower()
        query = re.sub(r"[^\w\s]", "", query)  # Remove special characters
        query = re.sub(r"\s+", "_", query)  # Replace spaces with underscores
        return query
