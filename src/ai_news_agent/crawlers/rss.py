from datetime import datetime, timezone

import feedparser

from ai_news_agent.crawlers.base import Article, BaseCrawler

# Default RSS feeds — extend via RSS_FEEDS in registry
DEFAULT_FEEDS: dict[str, str] = {
    "techcrunch": "https://techcrunch.com/feed/",
    "venturebeat": "https://venturebeat.com/feed/",
    "theverge": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "anthropic": "https://www.anthropic.com/feed",
    "openai": "https://openai.com/blog/rss.xml",
    "google-ai": "https://blog.google/technology/ai/rss/",
    "meta-ai": "https://ai.meta.com/rss/",
    "replicate": "https://replicate.com/blog/rss",
    "eleutherai": "https://blog.eleuther.ai/index.xml",
    "lilianweng": "https://lilianweng.github.io/index.xml",
    "qwen": "https://qwenlm.github.io/blog/index.xml",
}


class RSSCrawler(BaseCrawler):
    name = "rss"

    def __init__(self, feeds: dict[str, str] | None = None):
        self.feeds = feeds or DEFAULT_FEEDS

    def crawl(self) -> list[Article]:
        articles = []
        for source_name, feed_url in self.feeds.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

                    summary = entry.get("summary", "") or ""
                    # Strip HTML tags from summary
                    if "<" in summary:
                        from bs4 import BeautifulSoup
                        summary = BeautifulSoup(summary, "html.parser").get_text()

                    articles.append(
                        Article(
                            url=entry.link,
                            title=entry.title.strip(),
                            source=source_name,
                            author=entry.get("author"),
                            summary=summary[:500] or None,
                            published_at=published,
                        )
                    )
            except Exception:
                continue
        return articles
