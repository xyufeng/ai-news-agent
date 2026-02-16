import httpx

from ai_news_agent.crawlers.base import Article, BaseCrawler

HF_PAPERS_API = "https://huggingface.co/api/daily_papers"
MAX_PAPERS = 20


class HuggingFaceCrawler(BaseCrawler):
    name = "huggingface"

    def crawl(self) -> list[Article]:
        resp = httpx.get(HF_PAPERS_API, timeout=15)
        resp.raise_for_status()
        papers = resp.json()

        articles = []
        for paper in papers[:MAX_PAPERS]:
            paper_id = paper.get("paper", {}).get("id", "")
            title = paper.get("paper", {}).get("title", "")
            summary = paper.get("paper", {}).get("summary", "")
            upvotes = paper.get("numUpvotes", 0)

            if not paper_id or not title:
                continue

            articles.append(
                Article(
                    url=f"https://huggingface.co/papers/{paper_id}",
                    title=title,
                    source=self.name,
                    summary=summary[:500] if summary else None,
                    score=upvotes,
                )
            )
        return articles
