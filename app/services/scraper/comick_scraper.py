import asyncio
from requests import Response
import httpx, cloudscraper
from app.core.sources import SUPPORTED_SOURCES
from .base import BaseScraper
from app.schemas.manga_schema import (
    Manga,
    MangaInfoResponse,
    MangaDetails, MangaChapter,
    LatestMangaListResponse,
    PopularMangaListResponse,
    MangaChapterPage,
    MangaSearchResponse
)

from urllib.parse import quote


IMAGE_PROXY_WORKER_URL = "https://mangako-page-image-proxy.REDACTED.workers.dev/"
IMAGE_METADATA_PROXY_WORKER_URL = "https://mangako-image-metadata-worker.REDACTED.workers.dev/"
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

cookies = {
}

status_map = {
    1: "Ongoing",
    2: "Completed",
    3: "Cancelled",
    4: "Hiatus"
}

SOURCE_NAME = "comick"
MAX_CONCURRENT_REQUESTS = 10
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"


class ComickioScrapper(BaseScraper):

    def __init__(self):
        self.cloudflare_scraper = cloudscraper.create_scraper()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch_with_scraper(self, url: str) -> Response:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.cloudflare_scraper.get(url))

    async def scrape(self) -> dict:
        url = 'https://api.comick.fun/v1.0/comic/genius-corpse-collecting-warrior'

        async with self.semaphore:
            response = await self.fetch_with_scraper(url)
            response.raise_for_status()

        return {'res': "Comick source is working without hiccups!", 'source': SOURCE_NAME}

    async def scrape_latest_manga(self, url: str):
        async with self.semaphore:
            response = await self.fetch_with_scraper(url)
            response.raise_for_status()
            print(f"[DEBUG] Fetched URL: {url}")

            latest_manga = [Manga(
                mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                mangaId=str(manga['hid']),
                mangaTitle=manga['title'],
                mangaCover=f"https://meo.comick.pictures/{manga['md_covers'][0]["b2key"]}",
                mangaUrl=f"https://api.comick.fun/v1.0/comic/{manga['slug']}"
            ) for manga in response.json()]

            return LatestMangaListResponse(
                source=SOURCE_NAME,
                latest_manga=latest_manga
            )

    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.semaphore:
            response = await self.fetch_with_scraper(url)
            response.raise_for_status()

            popular_manga = [Manga(
                mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                mangaId=str(manga['hid']),
                mangaTitle=manga['title'],
                mangaCover=f"https://meo.comick.pictures/{manga['md_covers'][0]["b2key"]}",
                mangaUrl=f"https://api.comick.fun/v1.0/comic/{manga['slug']}"
            ) for manga in response.json()]


            return PopularMangaListResponse(
                sourceName=SOURCE_NAME,
                popular_manga=popular_manga
            )
    
    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with self.semaphore:

            response = await self.fetch_with_scraper(url)
            response.raise_for_status()
            # 1/Ongoing 2/Completed 3/Cancelled 4/Hiatus

            

            manga_details = MangaDetails(
                mangaDescription=response.json()['comic']['desc'],
                mangaAuthor=", ".join(author['name'] for author in response.json().get('authors', [])),
                mangaStatus=status_map.get(response.json()['comic']['status'], "Unknown"),
                mangaTags=[
                    genre['md_genres']['name']
                    for genre in response.json()['comic'].get('md_comic_md_genres', [])
                ],
                mangaAlternativeNames=[
                    title['title']
                    for title in response.json()['comic'].get('md_titles', [])
                    if title['title'] != response.json()['comic']['title']
                ]
            )
            manga_hid = response.json()['comic']['hid']
            manga_chapters: list[MangaChapter] = []

            chapter_url = f"https://api.comick.fun/comic/{manga_hid}/chapters?limit=10000&lang=en"

            response = await self.fetch_with_scraper(chapter_url)
            response.raise_for_status()

            for chapter in response.json()['chapters']:
                # print(f"[DEBUG] Processing chapter: {chapter['hid']}")
                res_chapter = MangaChapter(
                    chapterId=chapter['hid'],
                    chapterTitle=f"Chapter {chapter['chap']}" if chapter['chap'] else "No Title",
                    chapterUrl=f"https://api.comick.fun/chapter/{chapter['hid']}/get_images",  # Replace with your actual URL format
                    chapterTimeUploaded=chapter['updated_at']
                )
                
                if len(manga_chapters) == 0:
                    manga_chapters.append(res_chapter)
                    continue

                if manga_chapters[-1].chapterTitle != res_chapter.chapterTitle:
                    manga_chapters.append(res_chapter)

            chapterNavigationMap = self._build_chapters_navigation_map(manga_chapters)

            return MangaInfoResponse(
                mangaDetails=manga_details,
                mangaChapters=manga_chapters,
                chaptersNavigationMap=chapterNavigationMap
            )

    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with self.semaphore:
            search_url = f"https://api.comick.fun/v1.0/search/?page=1&limit=300&sort=user_follow_count&showall=false&q={self._to_comickio_slug(keyword)}"
            response = await self.fetch_with_scraper(search_url)
            response.raise_for_status()
            results = []

            for manga in response.json():
                if (
                    not manga.get('slug') or
                    not manga.get('md_covers') or
                    not isinstance(manga['md_covers'], list) or
                    not manga['md_covers'][0].get('b2key')
                ):
                    continue  # Skip if essential data is missing

                results.append(Manga(
                    mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                    mangaId=manga['hid'],
                    mangaTitle=manga.get('title', 'Unknown Title'),
                    mangaCover=f"https://meo.comick.pictures/{manga['md_covers'][0]['b2key']}",
                    mangaUrl=f"https://api.comick.fun/v1.0/comic/{manga['slug']}"
                ))

            return MangaSearchResponse(
                source=SOURCE_NAME,
                results=results
            )

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with self.semaphore:
            response = await self.fetch_with_scraper(url)
            response.raise_for_status()
            
            pages_data = response.json()

            # Construct full image URLs
            image_urls = [f"https://meo.comick.pictures/{page['b2key']}" for page in pages_data]
            async with httpx.AsyncClient() as client:
            # Fetch blurhashes concurrently with limited concurrency
                blurhash_tasks = [
                    self.get_blurhash(client, BLURHASH_ENDPOINT, image_url)
                    for image_url in image_urls
                ]
                blurhashes = await asyncio.gather(*blurhash_tasks)

            # Construct MangaChapterPage list
            pages = []
            for page_data, image_url, blurhash in zip(pages_data, image_urls, blurhashes):
                pages.append(MangaChapterPage(
                    pageId=page_data['b2key'],
                    pageUrl=url,
                    pageImageUrl=image_url,
                    pageWidth=page_data['w'],
                    pageHeight=page_data['h'],
                    pageBlurhash=blurhash or "",  # fallback to empty string
                ))

            return pages
    
    async def get_blurhash(self, client: httpx.AsyncClient, endpoint: str, image_url: str) -> str | None:
        print('[DEBUG] OVERRIDEN Fetching blurhash for image URL:', image_url)
        try:
            async with self.semaphore:
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
        query = re.sub(r'[^\w\s]', '', query)  # Remove special characters
        query = re.sub(r'\s+', '_', query)     # Replace spaces with underscores
        return query