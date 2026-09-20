from app.services.scraper.mahuato_scraper import ManhuatoScraper
from app.services.scraper.mangafox_scraper import MangafoxScraper
from app.services.scraper.weebcentral_scraper import WeebCentralScraper
from .asura_scans_scraper import AsuraScansScraper
from .mangakakalot_scraper import MangakakalotScraper
from .comick_scraper import ComickioScrapper
from .manhuaplus_scraper import ManhuaPlusScraper

from .base import BaseScraper

# from .manganelo import ManganeloScraper  # when implemented

SCRAPER_MAP = {
    "mangakakalot": MangakakalotScraper,
    "comickio": ComickioScrapper,
    "asura_scans": AsuraScansScraper,
    "manhuato": ManhuatoScraper,
    "mangafox": MangafoxScraper,
    "weeb_central": WeebCentralScraper,
    "manhuaplus": ManhuaPlusScraper,
}


def get_scraper(source: str) -> BaseScraper:
    scraper_class = SCRAPER_MAP.get(source)
    if not scraper_class:
        raise ValueError(f"No scraper available for source: {source}")
    return scraper_class()
