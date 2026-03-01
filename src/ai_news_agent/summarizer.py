"""Neutral article summarizer using Claude and meta description extraction."""

import httpx
from bs4 import BeautifulSoup

from ai_news_agent import config, db

_client = None


def _get_client():
    """Get or create the Anthropic client."""
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


SUMMARY_PROMPT = """\
Summarize this article in one paragraph (150-200 words).

Requirements:
- Be factual and objective
- Remove all promotional language and marketing speak
- Use a neutral, journalistic tone
- Focus on key facts, context, and implications
- No opinions, speculation, or editorial commentary
- If it's a product release, focus on capabilities not hype
- If it's research, explain the finding not the breakthrough language

Title: {title}
Source: {source}
Content: {content}

Write a neutral, factual summary:"""


def fetch_meta_description(url: str) -> str | None:
    """Fetch meta description from a URL.
    
    Tries og:description first, then meta description tag.
    Returns None if not found or on error.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            
            if len(resp.content) > 500000:
                return None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                return og_desc["content"][:500].strip()
            
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                return meta_desc["content"][:500].strip()
            
            return None
    except Exception:
        return None


def generate_neutral_summary(article: dict) -> str | None:
    """Generate a neutral summary using Claude.
    
    Uses existing summary or fetched meta description as input.
    Returns None if no input content available.
    """
    content = article.get("summary", "")
    
    if not content or len(content) < 50:
        content = fetch_meta_description(article.get("url", ""))
    
    if not content or len(content) < 50:
        return None
    
    client = _get_client()
    
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(
                        title=article.get("title", ""),
                        source=article.get("source", ""),
                        content=content[:2000],
                    ),
                },
            ],
        )
        return message.content[0].text.strip()
    except Exception:
        return None


def batch_generate_summaries(batch_size: int = 20) -> int:
    """Generate neutral summaries for articles that don't have one.
    
    Returns the number of summaries generated.
    """
    articles = db.get_articles_without_neutral_summary(limit=batch_size)
    
    if not articles:
        return 0
    
    generated = 0
    for article in articles:
        summary = generate_neutral_summary(article)
        if summary:
            db.update_neutral_summary(article["id"], summary)
            generated += 1
    
    return generated
