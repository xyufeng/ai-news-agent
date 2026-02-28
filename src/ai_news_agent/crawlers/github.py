from datetime import datetime, timezone

import httpx

from ai_news_agent.crawlers.base import Article, BaseCrawler

GITHUB_REPOS: dict[str, str] = {
    "deepseek": "deepseek-ai",
    "qwen": "QwenLM",
    "mistral": "mistralai",
    "meta-llama": "meta-llama",
    "black-forest-labs": "black-forest-labs",
}

MAX_RELEASES = 5


class GitHubReleasesCrawler(BaseCrawler):
    name = "github-releases"

    def crawl(self) -> list[Article]:
        articles = []
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        for source_name, org in GITHUB_REPOS.items():
            try:
                resp = httpx.get(
                    f"https://api.github.com/orgs/{org}/repos?per_page=100&sort=updated",
                    headers=headers,
                    timeout=15,
                )
                resp.raise_for_status()
                repos = resp.json()

                for repo in repos[:10]:
                    repo_name = repo["name"]
                    try:
                        releases_resp = httpx.get(
                            f"https://api.github.com/repos/{org}/{repo_name}/releases?per_page={MAX_RELEASES}",
                            headers=headers,
                            timeout=10,
                        )
                        releases_resp.raise_for_status()
                        releases = releases_resp.json()

                        for release in releases:
                            if release.get("draft") or release.get("prerelease"):
                                continue

                            published = None
                            if release.get("published_at"):
                                published = release["published_at"].replace("Z", "+00:00")

                            articles.append(
                                Article(
                                    url=release["html_url"],
                                    title=f"[{repo_name}] {release.get('tag_name', 'Release')}",
                                    source=f"github/{source_name}",
                                    summary=release.get("body", "")[:500] if release.get("body") else None,
                                    published_at=published,
                                )
                            )
                    except Exception:
                        continue
            except Exception:
                continue

        return articles
