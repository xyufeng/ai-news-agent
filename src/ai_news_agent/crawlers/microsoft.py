from datetime import datetime, timezone

import feedparser

from ai_news_agent.crawlers.base import Article, BaseCrawler

# Microsoft RSS feeds
RSS_FEEDS: dict[str, str] = {
    "microsoft-ai": "https://blogs.microsoft.com/ai/feed/",
    "azure-blog": "https://azure.microsoft.com/en-us/blog/feed/",
    "m365-copilot": "https://techcommunity.microsoft.com/gxcuf89792/rss/board?board.id=Microsoft365CopilotBlog",
    "azure-ai-foundry": "https://techcommunity.microsoft.com/gxcuf89792/rss/board?board.id=AzureAIFoundryBlog",
    "devblog-foundry": "https://devblogs.microsoft.com/foundry/feed/",
}

# GitHub releases (Atom feeds)
GITHUB_RELEASES = {
    "agent-framework": "https://github.com/microsoft/agent-framework/releases.atom",
}

MAX_PER_FEED = 10


class MicrosoftCrawler(BaseCrawler):
    name = "microsoft"

    def crawl(self) -> list[Article]:
        articles = []

        # RSS feeds
        for source_name, feed_url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:MAX_PER_FEED]:
                    published = self._parse_published(entry)
                    summary = self._clean_summary(entry.get("summary", ""))

                    articles.append(
                        Article(
                            url=entry.link,
                            title=entry.title.strip(),
                            source=f"microsoft/{source_name}",
                            author=entry.get("author"),
                            summary=summary[:500] or None,
                            published_at=published,
                        )
                    )
            except Exception:
                continue

        # GitHub releases
        for repo_name, atom_url in GITHUB_RELEASES.items():
            try:
                feed = feedparser.parse(atom_url)
                for entry in feed.entries[:5]:
                    published = self._parse_published(entry)
                    articles.append(
                        Article(
                            url=entry.link,
                            title=f"[Release] {entry.title.strip()}",
                            source=f"microsoft/github-{repo_name}",
                            published_at=published,
                        )
                    )
            except Exception:
                continue

        return articles

    def _parse_published(self, entry) -> str | None:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        return None

    def _clean_summary(self, summary: str) -> str:
        if "<" in summary:
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(summary, "html.parser").get_text()
        return summary
