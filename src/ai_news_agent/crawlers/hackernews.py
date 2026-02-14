import httpx

from ai_news_agent.crawlers.base import Article, BaseCrawler

HN_API = "https://hacker-news.firebaseio.com/v0"
MAX_STORIES = 30


class HackerNewsCrawler(BaseCrawler):
    name = "hackernews"

    def crawl(self) -> list[Article]:
        resp = httpx.get(f"{HN_API}/topstories.json", timeout=15)
        resp.raise_for_status()
        story_ids = resp.json()[:MAX_STORIES]

        articles = []
        for sid in story_ids:
            item = httpx.get(f"{HN_API}/item/{sid}.json", timeout=10).json()
            if not item or item.get("type") != "story":
                continue
            url = item.get("url") or f"https://news.ycombinator.com/item?id={sid}"
            articles.append(
                Article(
                    url=url,
                    title=item.get("title", ""),
                    source=self.name,
                    author=item.get("by"),
                    score=item.get("score"),
                )
            )
        return articles
