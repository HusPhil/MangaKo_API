from abc import ABC, abstractmethod
from typing import List
import httpx
from urllib.parse import quote
from app.schemas.manga_schema import (
    MangaInfoResponse,
    LatestMangaListResponse,
    PopularMangaListResponse,
    MangaChapterPage,
    MangaSearchResponse,
    ChaptersNavigationMap,
    ChapterNavigation,
    MangaChapter
)


class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> dict:
        pass
    
    @abstractmethod
    async def scrape_latest_manga(self, *args, **kwargs) -> LatestMangaListResponse:
        pass

    @abstractmethod
    async def scrape_popular_manga(self, *args, **kwargs) -> PopularMangaListResponse:
        pass

    @abstractmethod
    async def scrape_manga_search(self, *args, **kwargs) -> MangaSearchResponse:
        pass

    @abstractmethod
    async def scrape_manga_info(self, *args, **kwargs) -> MangaInfoResponse:
        pass

    @abstractmethod
    async def scrape_chapter_pages(self, *args, **kwargs) -> list[MangaChapterPage]:
        pass

    def _build_chapters_navigation_map(self, chapters: List[MangaChapter]) -> ChaptersNavigationMap:
        """
        Build navigation map for efficient chapter navigation using the ChaptersNavigationMap schema.
        Returns a ChaptersNavigationMap instance.
        """
        navigation_dict = {}
        
        for index, chapter in enumerate(chapters):
            prev_chapter = None
            next_chapter = None
            
            # Previous chapter (index - 1)
            if index > 0:
                next_chapter = chapters[index - 1]
            
            # Next chapter (index + 1)
            if index < len(chapters) - 1:
                prev_chapter = chapters[index + 1]
            
            # Create ChapterNavigation instance
            navigation_entry = ChapterNavigation(
                prev=prev_chapter,
                next=next_chapter
            )
            
            navigation_dict[chapter.chapterId] = navigation_entry
        
        # Return ChaptersNavigationMap instance
        return ChaptersNavigationMap(navigation_dict)


    async def get_blurhash(self, client: httpx.AsyncClient, endpoint: str, image_url: str) -> str | None:
        # return ""
        try:
            res = await client.get(f"{endpoint}?url={quote(image_url)}", timeout=5)
            res.raise_for_status()
            return res.json().get("blurhash")
        except Exception:
            return None

