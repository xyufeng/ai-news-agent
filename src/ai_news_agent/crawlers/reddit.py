import httpx

from ai_news_agent.crawlers.base import Article, BaseCrawler

SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA", "ClaudeAI"]
MAX_POSTS = 15


class RedditCrawler(BaseCrawler):
    name = "reddit"

    def crawl(self) -> list[Article]:
        articles = []
        headers = {"User-Agent": "ai-news-agent/0.1 (research bot)"}

        for sub in SUBREDDITS:
            try:
                resp = httpx.get(
                    f"https://www.reddit.com/r/{sub}/hot.json?limit={MAX_POSTS}",
                    headers=headers,
                    timeout=15,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                posts = resp.json()["data"]["children"]
            except Exception:
                continue

            for post in posts:
                data = post["data"]
                if data.get("stickied"):
                    continue
                articles.append(
                    Article(
                        url=f"https://reddit.com{data['permalink']}",
                        title=data["title"],
                        source=f"reddit/{sub}",
                        author=data.get("author"),
                        summary=data.get("selftext", "")[:500] or None,
                        score=data.get("score"),
                    )
                )
        return articles
