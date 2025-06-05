import hashlib
import re
from requests import Response
import asyncio
from typing import List

import cloudscraper, asyncio
import httpx
from urllib.parse import quote
from selectolax.parser import HTMLParser
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

IMAGE_PROXY_WORKER_URL = "https://mangako-page-image-proxy.REDACTED/"
IMAGE_METADATA_PROXY_WORKER_URL = "https://mangako-image-metadata-worker.REDACTED/"
DEFAULT_HEADERS = {
    "Referer": "https://comick.io/home2",
    "User-Agent": "Mozilla/5.0"
}


SOURCE_NAME = "comick"
MAX_CONCURRENT_REQUESTS = 10

class ComickioScrapper(BaseScraper):
    def __init__(self):
        self.cloudscraper = cloudscraper.create_scraper()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    def _get_with_cloudscraper(self, url: str) -> Response:
        response = self.cloudscraper.get(url)
        response.raise_for_status()
        return response

    
    async def scrape(self) -> dict:
        async with self.semaphore:
            cloudscraper_response = await asyncio.to_thread(self._get_with_cloudscraper, 'https://api.comick.fun/v1.0/search/?page=1&limit=15&tachiyomi=true&sort=created_at&showall=false&t=false')

            latest_manga = [Manga(
                mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                mangaId=str(manga['id']),
                mangaTitle=manga['title'],
                mangaCover=manga['cover_url'],
                mangaUrl=f"https://comick.io/comic/{manga['slug']}"
            ) for manga in cloudscraper_response.json()]
            # manga = cloudscraper_response.json()[0]  # Get the first manga item 
            
            # # return manga
            # latest_manga = Manga(
            #     mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
            #     mangaId=str(manga['id']),
            #     mangaTitle=manga['title'],
            #     mangaCover=manga['cover_url'],
            #     mangaUrl=f"https://comick.io/manga/{manga['slug']}"
            # )

            return {'res': latest_manga, 'source': SOURCE_NAME}
       
    #    return {'source': SOURCE_NAME, 'message': 'this is the comick scraper'}

    

    async def scrape_latest_manga(self, url: str):
        async with self.semaphore:
            cloudscraper_response = await asyncio.to_thread(self._get_with_cloudscraper, url)
            return {'res': cloudscraper_response.text, 'source': SOURCE_NAME}

            for item in tree.css("div.list-truyen-item-wrap"):
                a_tag = item.css_first("a[data-id]")
                if not a_tag:
                    continue

                manga_url = a_tag.attributes.get("href")
                manga_title = a_tag.attributes.get("title")
                img_tag = a_tag.css_first("img")

                if not manga_url or not manga_title or not img_tag:
                    continue

                original_cover_url = img_tag.attributes.get("data-src") or img_tag.attributes.get("src")
                manga_cover = f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"

                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                latest_manga.append(Manga(
                    mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                    mangaId=manga_id,
                    mangaTitle=manga_title,
                    mangaUrl=manga_url,
                    mangaCover=manga_cover,
                ))

            return LatestMangaListResponse(
                source=SOURCE_NAME,
                latest_manga=latest_manga
            )
        
    async def scrape_popular_manga(self, url: str) -> PopularMangaListResponse:
        async with self.semaphore:
            cloudscraper_response = await asyncio.to_thread(self._get_with_cloudscraper, url)

            latest_manga = [Manga(
                mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                mangaId=str(manga['id']),
                mangaTitle=manga['title'],
                mangaCover=manga['cover_url'],
                mangaUrl=f"https://comick.io/comic/{manga['slug']}"
            ) for manga in cloudscraper_response.json()]


            return PopularMangaListResponse(
                sourceName=SOURCE_NAME,
                popular_manga=latest_manga
            )
        
    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with httpx.AsyncClient() as client:
            search_url = f"https://comick.io/search?q={self._to_comickio_slug(keyword)}" # ewan ko pa to
            response = await client.get(search_url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)
            
            print(tree)
            print(tree.body.text())
            print(tree.css_first("title").text())
            print(tree.css_first("h1"))

            story_items = tree.css(".panel_story_list .story_item")
            results: list[Manga] = []

            for item in story_items:
                title_tag = item.css_first("h3.story_name a")
                img_tag = item.css_first("a img")

                if not title_tag or not img_tag:
                    continue

                manga_title = title_tag.text(strip=True)
                manga_url = title_tag.attributes.get("href")
                original_cover_url = img_tag.attributes.get("src")
                manga_cover = f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"

                if not manga_url:
                    continue

                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                results.append(Manga(
                    mangaId=manga_id,
                    mangaTitle=manga_title,
                    mangaUrl=manga_url,
                    mangaCover=manga_cover
                ))

            return MangaSearchResponse(
                source=SOURCE_NAME,
                results=results
            )

    async def scrape_manga_info(self, url: str) -> MangaInfoResponse:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=DEFAULT_HEADERS)
            print(f"[DEBUG] Status Code: {resp.status_code}")
            print(f"[DEBUG] Fetched URL: {url}")
            print(f"[DEBUG] Response snippet: {resp.text[:500]}")  # Preview first 500 chars

            html = HTMLParser(resp.text)

        # Description
        desc_node = html.css_first('#contentBox')
        print(f"[DEBUG] desc_node: {desc_node}")
        raw_description = desc_node.text(strip=True) if desc_node else ""
        manga_description = re.sub(r'\s+', ' ', raw_description).strip()
        print(f"[DEBUG] manga_description: {manga_description}")

        # Author
        author_node = html.css_first('.comic-info-section .info-wrap a[href*="/author/"]')
        print(f"[DEBUG] author_node: {author_node}")
        manga_author = author_node.text(strip=True) if author_node else ""
        print(f"[DEBUG] manga_author: {manga_author}")

        # Status
        status_node = html.css_first('.comic-info-section .info-wrap div:nth-of-type(2) p:nth-of-type(2)')
        print(f"[DEBUG] status_node: {status_node}")
        manga_status = status_node.text(strip=True) if status_node else ""
        print(f"[DEBUG] manga_status: {manga_status}")

        # Genres
        genre_nodes = html.css('.genre-list a')
        print(f"[DEBUG] genre_nodes: {genre_nodes}")
        manga_tags = [node.text(strip=True) for node in genre_nodes]
        print(f"[DEBUG] manga_tags: {manga_tags}")

        # Alternative Names
        alt_node = html.css_first('h2.story-alternative')
        print(f"[DEBUG] alt_node: {alt_node}")
        raw_alt_text = alt_node.text(strip=True) if alt_node else ""
        cleaned_alt_text = re.sub(r'^Alternative\s*:\s*', '', raw_alt_text)
        manga_alternative_names = [alt.strip() for alt in re.split(r'[;,]', cleaned_alt_text) if alt.strip()]
        print(f"[DEBUG] manga_alternative_names: {manga_alternative_names}")

        # Chapters
        chapter_nodes = html.css('.chapter-list .row')
        print(f"[DEBUG] chapter_nodes: {chapter_nodes}")
        chapters = []
        for row in chapter_nodes:
            link_node = row.css_first('a')
            time_node = row.css('span')[-1] if row.css('span') else None

            if link_node and time_node:
                chapter_title = link_node.text(strip=True)
                chapter_url = link_node.attributes.get("href", "")
                chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()
                chapter_time = time_node.text(strip=True)

                chapters.append(MangaChapter(
                    chapterId=chapter_id,
                    chapterTitle=chapter_title,
                    chapterUrl=chapter_url,
                    chapterTimeUploaded=chapter_time
                ))

        print(f"[DEBUG] chapters found: {len(chapters)}")

        details = MangaDetails(
            mangaDescription=manga_description,
            mangaAuthor=manga_author,
            mangaStatus=manga_status,
            mangaTags=manga_tags,
            mangaAlternativeNames=manga_alternative_names,
        )

        return MangaInfoResponse(
            mangaDetails=details,
            mangaChapters=chapters
        )

    async def scrape_chapter_pages(self, url: str) -> list[MangaChapterPage]:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)

            container = tree.css_first('.container-chapter-reader')
            if not container:
                return []

            image_nodes = container.css('img')
            pages: list[MangaChapterPage] = []

            image_urls = []
            for index, img in enumerate(image_nodes):
                src = img.attributes.get('src')
                onerror = img.attributes.get('onerror')
                fallback_src = re.search(r"this\.src='(.*?)'", onerror).group(1) if onerror else None
                image_url = src or fallback_src
                if not image_url:
                    continue
                image_urls.append((index, image_url))

            # Fetch all metadata concurrently
            tasks = [self.get_image_dimensions(client, image_url) for _, image_url in image_urls]
            dimensions = await asyncio.gather(*tasks)

            for (index, image_url), (width, height) in zip(image_urls, dimensions):
                proxied_image_url = f"{IMAGE_PROXY_WORKER_URL}?url={quote(image_url)}"
                page_id = hashlib.md5(f"{url}-{index}".encode()).hexdigest()

                pages.append(MangaChapterPage(
                    pageId=page_id,
                    pageUrl=url,
                    pageImageUrl=proxied_image_url,
                    pageWidth=width,
                    pageHeight=height
                ))

            return pages

    async def get_image_dimensions(self, client: httpx.AsyncClient, image_url: str) -> tuple[int, int]:
        try:
            res = await client.get(f"{IMAGE_METADATA_PROXY_WORKER_URL}?url={quote(image_url)}", headers={}, timeout=5)
            data = res.json()
            return int(data.get("width", 0)), int(data.get("height", 0))
        except Exception:
            return 0, 0
        
        
        
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