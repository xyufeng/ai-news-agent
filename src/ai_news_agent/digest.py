import smtplib
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic

from ai_news_agent import config, db

# Use Haiku for per-source synthesis (faster, cheaper)
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Fallback models if primary fails
FALLBACK_MODELS = ["claude-sonnet-4-6", "claude-3-5-sonnet-20241022"]

# Reusable client
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client (singleton pattern)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client

# Prompt for synthesizing a single source group
SOURCE_SYNTHESIS_PROMPT = """\
You are an AI news analyst specializing in enterprise technology. Analyze the following articles from {source_name} and produce a concise summary.

Your task:
1. Identify the 3-5 most important stories and rank them by significance
2. Extract key insights and emerging trends
3. Flag any stories relevant to enterprise AI adoption (mark with 🏢)
4. Note any breaking news or urgent developments (mark with ⚡)

Format your response as:
## {source_name}

**Top Stories:**
1. [Story title] - 1-2 sentence summary (include URL from article)
2. ...

**Key Insights:** [2-3 bullet points on trends/patterns]
**Enterprise Relevance:** [What matters for enterprise AI adoption, if any]

Articles:
{articles}
"""

# Prompt for combining all source summaries into final digest
FINAL_SYNTHESIS_PROMPT = """\
You are an AI news curator creating a daily executive briefing. You have summaries from multiple news sources about AI, machine learning, and enterprise technology.

Create a polished daily digest with these sections (in this order):

## 🔥 Emerging Trends
Cross-source patterns and themes you noticed. What's gaining momentum?
- New research breakthroughs
- Rising technologies
- Market shifts

## 🏢 Enterprise AI Radar
Stories that matter most for enterprise AI adoption. Focus on:
- New product releases and features
- Security, compliance, and governance
- Cost and deployment considerations
- Vendor landscape changes

## 💡 Quick Takes
2-3 brief observations or predictions based on today's news.

## 📰 Top Headlines
The 5 most significant stories across ALL sources, ranked by industry impact.

## 📚 By Source
Include the key highlights from each source (condensed versions).

Keep the total digest under 2000 words. Use markdown formatting with links.

Source Summaries:
{summaries}
"""


def _group_by_source(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by their source."""
    groups = defaultdict(list)
    for a in articles:
        groups[a["source"]].append(a)
    return dict(groups)


def _format_source_articles(articles: list[dict]) -> str:
    """Format articles for source-level synthesis."""
    lines = []
    for a in articles:
        parts = [f"- **{a['title']}**"]
        if a.get("score"):
            parts.append(f"  Score: {a['score']} pts")
        if a.get("summary"):
            parts.append(f"  Summary: {a['summary'][:300]}")
        parts.append(f"  URL: {a['url']}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _synthesize_source(client: anthropic.Anthropic, source_name: str, articles: list[dict]) -> str:
    """Synthesize a single source group using Haiku."""
    formatted = _format_source_articles(articles)

    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": SOURCE_SYNTHESIS_PROMPT.format(
                    source_name=source_name,
                    articles=formatted,
                ),
            },
        ],
    )
    return message.content[0].text


def _synthesize_with_fallback(client: anthropic.Anthropic, summaries: list[str]) -> str:
    """Combine all source summaries into final digest with model fallback."""
    combined = "\n\n---\n\n".join(summaries)
    models_to_try = [config.ANTHROPIC_MODEL] + FALLBACK_MODELS

    for model in models_to_try:
        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": FINAL_SYNTHESIS_PROMPT.format(summaries=combined),
                    },
                ],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            if model == models_to_try[-1]:
                raise  # Re-raise if all models failed
            continue  # Try next model

    raise RuntimeError("All models failed")


def synthesize(articles: list[dict]) -> str:
    """Two-step synthesis: per-source with Haiku, then combined with Sonnet."""
    client = _get_client()

    # Step 1: Group by source
    source_groups = _group_by_source(articles)

    # Step 2: Synthesize each source with Haiku
    source_summaries = []
    for source_name, source_articles in source_groups.items():
        try:
            summary = _synthesize_source(client, source_name, source_articles)
            source_summaries.append(summary)
        except Exception as e:
            # If a source fails, include a basic fallback
            source_summaries.append(f"## {source_name}\n\nError synthesizing: {e}")

    # Step 3: Combine into final digest with Sonnet (with fallback)
    final_digest = _synthesize_with_fallback(client, source_summaries)

    return final_digest


def send_email(digest_content: str, digest_id: int) -> None:
    """Send the digest via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "AI News Digest"
    msg["From"] = config.DIGEST_EMAIL_FROM or config.SMTP_USER
    msg["To"] = config.DIGEST_EMAIL_TO

    msg.attach(MIMEText(digest_content, "plain"))
    msg.attach(
        MIMEText(
            f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{digest_content}</pre>",
            "html",
        )
    )

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)

    db.mark_digest_emailed(digest_id)


def generate_digest(since: str, dry_run: bool = False) -> str:
    """Full digest pipeline: query articles, synthesize, optionally email."""
    from ai_news_agent.preferences import score_article
    
    articles = db.get_articles_since(since)
    if not articles:
        return "No articles found for the given period."
    
    preferences = db.get_all_preferences()
    scored = [(a, score_article(a, preferences)) for a in articles]
    sorted_articles = sorted(scored, key=lambda x: x[1], reverse=True)
    top_articles = [a for a, s in sorted_articles[:50]]
    
    content = synthesize(top_articles)
    digest_id = db.save_digest(content, len(top_articles))
    
    if not dry_run:
        send_email(content, digest_id)
    
    return content
