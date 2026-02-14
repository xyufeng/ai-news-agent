from datetime import datetime, timezone

import feedparser

from ai_news_agent.crawlers.base import Article, BaseCrawler

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
MAX_RESULTS = 20


class ArxivCrawler(BaseCrawler):
    name = "arxiv"

    def crawl(self) -> list[Article]:
        cat_query = "+OR+".join(f"cat:{c}" for c in CATEGORIES)
        url = (
            f"http://export.arxiv.org/api/query?search_query={cat_query}"
            f"&sortBy=submittedDate&sortOrder=descending&max_results={MAX_RESULTS}"
        )
        feed = feedparser.parse(url)

        articles = []
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

            articles.append(
                Article(
                    url=entry.link,
                    title=entry.title.replace("\n", " ").strip(),
                    source=self.name,
                    author=", ".join(a.get("name", "") for a in entry.get("authors", [])) or None,
                    summary=entry.get("summary", "").replace("\n", " ").strip()[:500] or None,
                    published_at=published,
                )
            )
        return articles
