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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://comick.live/",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Priority": "u=1, i",
    "Cookie": "REDACTED",
}

cookies = {}

status_map = {1: "Ongoing", 2: "Completed", 3: "Cancelled", 4: "Hiatus", 5: "Unknown"}

SOURCE_NAME = "comick"
MAX_CONCURRENT_REQUESTS = 10
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class ComickioScrapper(BaseScraper):

    def __init__(self):
        self.AsyncClient = AsyncSession(impersonate="chrome", headers=DEFAULT_HEADERS)

    async def scrape(self) -> dict:

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

    async def scrape_manga_search(
        self, keyword: str, cookie: str = None
    ) -> MangaSearchResponse:
        async with self.AsyncClient as client:
            # Note: Using the .dev API which is generally more permissive
            search_url = (
                f"https://comick.live/api/search?q={self._to_comickio_slug(keyword)}"
            )
            search_url = f"https://comick.live/api/search?q=one&__cf_chl_tk=REDACTED"

            # We keep the header structure, but the cookie is now optional/None
            headers = {**DEFAULT_HEADERS}
            if cookie:
                headers["Cookie"] = cookie

            response = await client.get(search_url, headers=headers)
            response.raise_for_status()

            # The new API returns the list directly or inside a data key
            search_results = response.json()

            # Based on your provided schema, it's a list of objects
            results = []

            for manga in search_results:
                if not manga:
                    continue

                # --- Field Extraction ---
                m_id = manga.get("id")
                m_hid = manga.get("hid")  # New field from this API
                m_slug = manga.get("slug")
                m_title = manga.get("title", "Unknown Title")

                # This API uses 'md_covers' array for images
                # We try to get the first cover b2key
                covers = manga.get("md_covers", [])
                m_thumb = ""
                if covers:
                    # Comick image CDN usually follows this pattern
                    b2key = covers[0].get("b2key", "")
                    m_thumb = f"https://meo.comick.pictures/{b2key}"

                # --- CRITICAL CHANGE ---
                # The .dev search API does NOT provide the 'chapter_latest_by_langs'
                # To provide a valid MangaUrl, we link to the comic info page instead
                # or you can use a placeholder if your app requires a chapter URL.
                if not all([m_id, m_slug, m_hid]):
                    continue

                try:
                    results.append(
                        Manga(
                            mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                            mangaId=str(m_id),
                            mangaTitle=m_title,
                            mangaCover=(f"{m_thumb}" if m_thumb else ""),
                            # Since search doesn't provide chapters, we point to the manga detail page
                            mangaUrl=f"https://comick.live/api/comics/{m_slug}/{m_hid}-chapter-1-en",
                        )
                    )
                except Exception as e:
                    print(f"Error processing manga {m_id}: {e}")
                    continue

            return MangaSearchResponse(source=SOURCE_NAME, results=results)

    # async def scrape_manga_search(
    #     self, keyword: str, cookie: str
    # ) -> MangaSearchResponse:
    #     async with self.AsyncClient as client:
    #         search_url = f"https://api.comick.dev/v1.0/search?&limit=49&page=1&content_rating=safe&content_rating=suggestive&q={self._to_comickio_slug(keyword)}"

    #         response = await client.get(
    #             search_url, headers={**DEFAULT_HEADERS, "Cookie": cookie}
    #         )

    #         print(response.json())

    #         response.raise_for_status()
    #         # print(SUPPORTED_SOURCES[SOURCE_NAME])
    #         # print(str(manga["id"]))
    #         # print(manga.get("title", "Unknown Title"))
    #         # print(f"{IMAGE_PROXY_WORKER_URL}?url={manga['default_thumbnail']}")
    #         # print(
    #         #     f"https://comick.live/api/comics/{manga['slug']}/{manga['chapter_latest_by_langs']['en']['hid']}-chapter-{manga['chapter_latest_by_langs']['en']['chapter_number_slug']}-en"
    #         # )

    #         manga_search_data = response.json()["data"]

    #         results = []

    #         for manga in manga_search_data:
    #             # 1. Handle case where manga entry itself might be None
    #             if not manga:
    #                 continue

    #             # 2. Extract nested data safely
    #             latest_chapters = manga.get("chapter_latest_by_langs") or {}
    #             en_chapter = (
    #                 latest_chapters.get("en") or {}
    #             )  # Default to empty dict instead of None

    #             # 3. Gather all required fields
    #             m_id = manga.get("id")
    #             m_slug = manga.get("slug")
    #             m_title = manga.get("title", "Unknown Title")
    #             m_thumb = manga.get("default_thumbnail", "")

    #             # These are the sub-keys inside the 'en' dictionary
    #             c_hid = en_chapter.get("hid")
    #             c_num = en_chapter.get("chapter_number_slug")

    #             # 4. CRITICAL VERIFICATION: Skip if ANY essential info is None or Empty
    #             # This prevents the "NoneType" and "KeyError" issues entirely.
    #             if not all([m_id, m_slug, c_hid, c_num]):
    #                 continue

    #             try:
    #                 results.append(
    #                     Manga(
    #                         mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
    #                         mangaId=str(m_id),
    #                         mangaTitle=m_title,
    #                         mangaCover=f"{IMAGE_PROXY_WORKER_URL}?url={m_thumb}",
    #                         # All variables below are now guaranteed to be non-None strings
    #                         mangaUrl=f"https://comick.live/api/comics/{m_slug}/{c_hid}-chapter-{c_num}-en",
    #                     )
    #                 )
    #             except Exception as e:
    #                 print(f"Unexpected error processing manga {m_id}: {e}")
    #                 continue

    #         return MangaSearchResponse(source=SOURCE_NAME, results=results)

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
