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
    if not url:
        return None
    
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


def fetch_article_content(url: str) -> str | None:
    """Fetch and extract main article content from a URL.
    
    Extracts readable text content from the page, excluding navigation, ads, etc.
    Returns None if content extraction fails.
    """
    if not url:
        return None
    
    # Skip known non-article URLs
    skip_domains = [
        'youtube.com', 'youtu.be', 'vimeo.com',
        'twitter.com', 'x.com', 'mastodon.',
        'reddit.com', 'hn.algolia.com',
    ]
    
    for domain in skip_domains:
        if domain in url.lower():
            return None
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            
            if len(resp.content) > 500000:
                return None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'iframe', 'header']):
                element.decompose()
            
            # Try to find main content areas
            main_content = (
                soup.find('article') or
                soup.find('main') or
                soup.find('div', class_=lambda x: x and any(term in str(x).lower() for term in ['content', 'article', 'post', 'entry'])) or
                soup.find('div', id=lambda x: x and any(term in str(x).lower() for term in ['content', 'article', 'post', 'entry']))
            )
            
            if not main_content:
                main_content = soup.find('body')
            
            if not main_content:
                return None
            
            # Extract text
            text = main_content.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = ' '.join(text.split())
            
            # Return first 2000 characters (enough for summarization)
            return text[:2000] if len(text) >= 100 else None
            
    except Exception:
        return None


def generate_neutral_summary(article: dict) -> str | None:
    """Generate a neutral summary using Claude.
    
    Priority order for content source:
    1. Existing summary from article
    2. Fetched article content from URL
    3. Meta description from URL
    
    Returns None if no content available.
    """
    content = article.get("summary", "")
    
    # If no summary, try to fetch article content
    if not content or len(content) < 50:
        url = article.get("url", "")
        
        # First try full article content (for HN links, etc.)
        content = fetch_article_content(url)
        
        # Fallback to meta description if article content failed
        if not content or len(content) < 50:
            content = fetch_meta_description(url)
    
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
