from abc import ABC, abstractmethod
from app.schemas.manga_schema import (
    MangaInfoResponse,
    LatestMangaListResponse,
    PopularMangaListResponse,
    MangaChapterPage,
    MangaSearchResponse
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

    @abstractmethod
    async def get_image_dimensions(self, *args, **kwargs) -> tuple[int, int]:
        pass


