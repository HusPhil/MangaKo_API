from .asura_scans_scraper import AsuraScansScraper
from .mangakakalot_scraper import MangakakalotScraper
from .comick_scraper import ComickioScrapper
from .base import BaseScraper

# from .manganelo import ManganeloScraper  # when implemented

SCRAPER_MAP = {
    "mangakakalot": MangakakalotScraper,
    "comickio": ComickioScrapper,
    # "manganelo": ManganeloScraper,
    "asura_scans": AsuraScansScraper,
}


def get_scraper(source: str) -> BaseScraper:
    scraper_class = SCRAPER_MAP.get(source)
    if not scraper_class:
        raise ValueError(f"No scraper available for source: {source}")
    return scraper_class()
