from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> dict:
        pass
