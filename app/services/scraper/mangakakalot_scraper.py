import hashlib
import re
import asyncio
from typing import List

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
    MangaSearchResponse,
    ChaptersNavigationMap,
    ChapterNavigation
)

IMAGE_PROXY_WORKER_URL = "https://mangako-page-image-proxy.REDACTED.workers.dev/"
IMAGE_METADATA_PROXY_WORKER_URL = "https://mangako-image-metadata-worker.REDACTED.workers.dev/"

DEFAULT_HEADERS = {
    "Referer": "https://www.mangakakalot.gg/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
}

SOURCE_NAME = "mangakakalot"
BLURHASH_ENDPOINT = "https://REDACTED/api/blurhash"

class MangakakalotScraper(BaseScraper):
    async def scrape(self) -> dict:
        return {"source": SOURCE_NAME, "message": "this is the mangakakalot scraper"}

    async def scrape_latest_manga(self, url: str) -> LatestMangaListResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)


            latest_manga: List[Manga] = []

            for item in tree.css("div.list-comic-item-wrap"):
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
        async with httpx.AsyncClient() as client:
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
                manga_cover = f"{IMAGE_PROXY_WORKER_URL}?url={quote(original_cover_url)}"

                if not manga_url:
                    continue

                manga_id = hashlib.md5(manga_url.encode()).hexdigest()

                popular_manga.append(Manga(
                    mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
                    mangaId=manga_id,
                    mangaTitle=manga_title,
                    mangaUrl=manga_url,
                    mangaCover=manga_cover
                ))

            return PopularMangaListResponse(
                sourceName=SOURCE_NAME,
                popular_manga=popular_manga
            )
        
    async def scrape_manga_search(self, keyword: str) -> MangaSearchResponse:
        async with httpx.AsyncClient() as client:
            search_url = f"https://www.mangakakalot.gg/search/story/{self._to_mangakakalot_slug(keyword)}"
            response = await client.get(search_url, headers=DEFAULT_HEADERS)
            tree = HTMLParser(response.text)

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
                    mangaSource=SUPPORTED_SOURCES[SOURCE_NAME],
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
            html = HTMLParser(resp.text)

            desc_node = html.css_first('#contentBox')
            raw_description = desc_node.text(strip=True) if desc_node else ""
            manga_description = re.sub(r'\s+', ' ', raw_description).strip()

            author_node = html.css_first('.comic-info-section .info-wrap a[href*="/author/"]')
            manga_author = author_node.text(strip=True) if author_node else ""

            status_node = html.css_first('.comic-info-section .info-wrap div:nth-of-type(2) p:nth-of-type(2)')
            manga_status = status_node.text(strip=True) if status_node else ""

            genre_nodes = html.css('.genre-list a')
            manga_tags = [node.text(strip=True) for node in genre_nodes]

            alt_node = html.css_first('h2.story-alternative')
            raw_alt_text = alt_node.text(strip=True) if alt_node else ""
            cleaned_alt_text = re.sub(r'^Alternative\s*:\s*', '', raw_alt_text)
            manga_alternative_names = [alt.strip() for alt in re.split(r'[;,]', cleaned_alt_text) if alt.strip()]

            details = MangaDetails(
                mangaDescription=manga_description,
                mangaAuthor=manga_author,
                mangaStatus=manga_status,
                mangaTags=manga_tags,
                mangaAlternativeNames=manga_alternative_names,
            )

            chapter_container_nodes = html.css('div#chapter-list-container')

            if chapter_container_nodes:
                element = chapter_container_nodes[0]
                
                raw_api_url = element.attributes.get("data-api-url")
                comic_slug = element.attributes.get("data-comic-slug")
                url_template = element.attributes.get("data-chapter-url-template")

                final_api_url = raw_api_url.replace("__SLUG__", comic_slug)
                print(f"Fetching Chapters API: {final_api_url}")

                resp = await client.get(final_api_url, headers=DEFAULT_HEADERS)
                
                data = resp.json()
                
                chapters = []
                
                if data.get("success") and "data" in data:
                    chapter_list = data["data"].get("chapters", [])

                    for item in chapter_list:
                        chapter_name = item.get("chapter_name")  # e.g. "Chapter 33"
                        chapter_slug = item.get("chapter_slug")  # e.g. "chapter-33"
                        chapter_time = item.get("updated_at")

                        chapter_url = url_template.replace("__MANGA__", comic_slug).replace("__CHAPTER__", chapter_slug)

                        # Generate ID
                        chapter_id = hashlib.md5(chapter_url.encode()).hexdigest()

                        chapters.append(MangaChapter(
                            chapterId=chapter_id,
                            chapterTitle=chapter_name,
                            chapterUrl=chapter_url,
                            chapterTimeUploaded=chapter_time
                        ))

            # Build navigation map
            chapters_navigation_map = self._build_chapters_navigation_map(chapters)

            return MangaInfoResponse(
                mangaDetails=details,
                mangaChapters=chapters,
                chaptersNavigationMap=chapters_navigation_map
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

                # Proxify the URL now and save it
                proxied_url = f"{IMAGE_PROXY_WORKER_URL}?url={quote(image_url)}"
                image_urls.append((index, image_url, proxied_url))

            

            # Fetch all metadata and blurhash concurrently using the proxied URL
            blurhash_tasks = [self.get_blurhash(client, BLURHASH_ENDPOINT, proxied_url) for _, _, proxied_url in image_urls]

            blurhashes = await asyncio.gather(*blurhash_tasks)

            for (index, image_url, proxied_url), (blurhash, width, height) in zip(image_urls, blurhashes):
                page_id = hashlib.md5(f"{url}-{index}".encode()).hexdigest()

                pages.append(MangaChapterPage(
                    pageId=page_id,
                    pageUrl=url,
                    pageImageUrl=proxied_url,
                    pageWidth=width,
                    pageHeight=height,
                    pageBlurhash=blurhash or "",  # fallback to empty string
                ))

            return pages


    async def get_image_dimensions(self, client: httpx.AsyncClient, image_url: str) -> tuple[int, int]:
        try:
            res = await client.get(f"{IMAGE_METADATA_PROXY_WORKER_URL}?url={quote(image_url)}", headers=DEFAULT_HEADERS, timeout=5)
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
        query = re.sub(r'[^\w\s]', '', query)  # Remove special characters
        query = re.sub(r'\s+', '_', query)     # Replace spaces with underscores
        return query
    
