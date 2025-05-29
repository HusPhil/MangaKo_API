from .mangakakalot_scraper import MangakakalotScraper
from .comickio_scrapper import ComickioScrapper
# from .manganelo import ManganeloScraper  # when implemented

SCRAPER_MAP = {
    "mangakakalot": MangakakalotScraper,
    "comickio": ComickioScrapper,
    # "manganelo": ManganeloScraper,
}

def get_scraper(source: str):
    scraper_class = SCRAPER_MAP.get(source)
    if not scraper_class:
        raise ValueError(f"No scraper available for source: {source}")
    return scraper_class()
