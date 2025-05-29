from pydantic import BaseModel, RootModel
from typing import List, Optional, Dict

class Manga(BaseModel):
    mangaId: str
    mangaTitle: str
    mangaUrl: str
    mangaCover: str

class LatestMangaListResponse(BaseModel):
    source: str
    latest_manga: List[Manga]


class PopularMangaListResponse(BaseModel):
    source: str
    popular_manga: List[Manga]

class MangaSearchResponse(BaseModel):
    source: str
    results: List[Manga]

class MangaDetails(BaseModel):
    mangaDescription: str
    mangaAuthor: str
    mangaStatus: str
    mangaTags: List[str]
    mangaAlternativeNames: List[str]

class MangaChapter(BaseModel):
    chapterId: str
    chapterTitle: str
    chapterUrl:str
    chapterTimeUploaded: str

class MangaChapterPage(BaseModel):
    pageId: str
    pageUrl: str
    pageImageUrl: str
    pageWidth: int
    pageHeight: int

class ChapterNavigation(BaseModel):
    prev: Optional[MangaChapter]
    next: Optional[MangaChapter]

class ChaptersNavigationMap(RootModel[Dict[str, ChapterNavigation]]):
    pass

class MangaInfoResponse(BaseModel):
    mangaChapters: list[MangaChapter]
    mangaDetails: MangaDetails
    chaptersNavigationMap: ChaptersNavigationMap



