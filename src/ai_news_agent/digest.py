import anthropic
import resend

from ai_news_agent import config, db

DIGEST_PROMPT = """\
You are an AI news curator. Given the following list of articles crawled today, produce a concise daily digest in Markdown format.

Group articles by theme (e.g., "LLM Research", "Industry News", "Open Source", "Policy & Safety").
For each group, write 2-3 sentence summaries of the most important stories.
Highlight the top 3 most significant stories at the top as "Headlines".
Include source links. Skip duplicates or low-quality items.
Keep the total digest under 1500 words.

Articles:
{articles}
"""


def _format_articles(articles: list[dict]) -> str:
    lines = []
    for a in articles:
        parts = [f"- **{a['title']}** ({a['source']})"]
        if a.get("summary"):
            parts.append(f"  {a['summary'][:200]}")
        parts.append(f"  URL: {a['url']}")
        if a.get("score"):
            parts.append(f"  Score: {a['score']}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def synthesize(articles: list[dict]) -> str:
    """Use Claude to synthesize a digest from articles."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    formatted = _format_articles(articles)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": DIGEST_PROMPT.format(articles=formatted)},
        ],
    )
    return message.content[0].text


def send_email(digest_content: str, digest_id: int) -> None:
    """Send the digest via Resend."""
    resend.api_key = config.RESEND_API_KEY

    resend.Emails.send(
        {
            "from": config.DIGEST_EMAIL_FROM,
            "to": [config.DIGEST_EMAIL_TO],
            "subject": "AI News Digest",
            "html": f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{digest_content}</pre>",
        }
    )
    db.mark_digest_emailed(digest_id)


def generate_digest(since: str, dry_run: bool = False) -> str:
    """Full digest pipeline: query articles, synthesize, optionally email."""
    articles = db.get_articles_since(since)
    if not articles:
        return "No articles found for the given period."

    content = synthesize(articles)
    digest_id = db.save_digest(content, len(articles))

    if not dry_run:
        send_email(content, digest_id)

    return content
