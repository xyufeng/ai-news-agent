from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


@dataclass
class Article:
    url: str
    title: str
    source: str
    author: str | None = None
    summary: str | None = None
    published_at: str | None = None
    score: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class BaseCrawler(ABC):
    name: str = "base"

    @abstractmethod
    def crawl(self) -> list[Article]:
        """Crawl the source and return a list of articles."""
        ...
