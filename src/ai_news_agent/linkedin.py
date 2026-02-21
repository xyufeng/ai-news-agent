"""LinkedIn content generator using Claude and Yufeng's writing style."""

import anthropic

from ai_news_agent import config

# Reusable client
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client (singleton pattern)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


LINKEDIN_POST_PROMPT = """\
You are Yufeng, a technology professional writing a LinkedIn post. Write in a conversational, reflective style grounded in real experience. Avoid generic AI-sounding language.

Based on the following news topics, write a LinkedIn POST (shorter, ~150-200 words):

Style guidelines:
- Start with a hook or personal observation
- Use short paragraphs and line breaks for readability
- Include 1-2 specific insights or hot takes
- End with a question or call to engagement
- Be authentic, not promotional
- Use emojis sparingly (1-2 max)

Topics to write about:
{topics}

Write the LinkedIn post now:
"""

LINKEDIN_ARTICLE_PROMPT = """\
You are Yufeng, a technology professional writing a LinkedIn article. Write in a conversational, reflective style grounded in real experience. Avoid generic AI-sounding language.

Based on the following news topics, write a LinkedIn ARTICLE (longer, ~500-800 words):

Style guidelines:
- Compelling headline that sparks curiosity
- Open with a personal anecdote or observation
- Break into clear sections with subheadings
- Include specific examples and concrete details
- Share genuine opinions and lessons learned
- End with actionable takeaways or thought-provoking questions
- Be authentic and vulnerable where appropriate

Topics to write about:
{topics}

Write the LinkedIn article now with a headline:
"""


def generate_linkedin_post(topics: list[dict]) -> str:
    """Generate a LinkedIn post from selected topics."""
    client = _get_client()

    topics_text = _format_topics(topics)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": LINKEDIN_POST_PROMPT.format(topics=topics_text)},
        ],
    )
    return message.content[0].text


def generate_linkedin_article(topics: list[dict]) -> str:
    """Generate a LinkedIn article from selected topics."""
    client = _get_client()

    topics_text = _format_topics(topics)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "user", "content": LINKEDIN_ARTICLE_PROMPT.format(topics=topics_text)},
        ],
    )
    return message.content[0].text


def _format_topics(topics: list[dict]) -> str:
    """Format topics for the prompt."""
    lines = []
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. **{t['title']}**")
        if t.get("summary"):
            lines.append(f"   {t['summary'][:200]}")
        lines.append(f"   Source: {t['source']}")
        lines.append("")
    return "\n".join(lines)
