from ai_news_agent.crawlers.base import BaseCrawler
from ai_news_agent.crawlers.hackernews import HackerNewsCrawler
from ai_news_agent.crawlers.reddit import RedditCrawler
from ai_news_agent.crawlers.arxiv import ArxivCrawler
from ai_news_agent.crawlers.rss import RSSCrawler
from ai_news_agent.crawlers.huggingface import HuggingFaceCrawler
from ai_news_agent.crawlers.microsoft import MicrosoftCrawler


def get_all_crawlers() -> list[BaseCrawler]:
    return [
        HackerNewsCrawler(),
        RedditCrawler(),
        ArxivCrawler(),
        HuggingFaceCrawler(),
        MicrosoftCrawler(),
        RSSCrawler(),
    ]


def get_crawler(name: str) -> BaseCrawler | None:
    for crawler in get_all_crawlers():
        if crawler.name == name:
            return crawler
    return None


def list_crawler_names() -> list[str]:
    return [c.name for c in get_all_crawlers()]
