"""LinkedIn content generator using Claude and Yufeng's writing style."""

import anthropic

from ai_news_agent import config, db
from ai_news_agent.preferences import score_article

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client (singleton pattern)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


CLUSTERING_PROMPT = """\
Analyze these AI news articles and:
1. Group them into exactly 3 thematic clusters:
   - **Emerging Trends**: New developments, research breakthroughs, rising technologies
   - **Enterprise Radar**: Product releases, vendor news, enterprise AI adoption, compliance/governance
   - **Quick Takes**: Interesting snippets, community discussions, notable mentions
2. Pick the 5-8 most newsworthy/interesting articles for a LinkedIn post
3. Ensure diversity across the three themes (at least 1-2 from each if available)

{preferences_context}

Articles:
{articles}

Respond in JSON format:
{{
  "clusters": [
    {{"theme": "Emerging Trends", "article_indices": [0, 2, 5]}},
    {{"theme": "Enterprise Radar", "article_indices": [1, 3]}},
    {{"theme": "Quick Takes", "article_indices": [4, 6]}}
  ],
  "selected_indices": [0, 1, 2, 3, 5],
  "reasoning": "Brief explanation of selection and theme distribution"
}}
"""

LINKEDIN_POST_PROMPT = """\
You are Yufeng, a technology professional writing a LinkedIn post. Write in a conversational, reflective style grounded in real experience. Avoid generic AI-sounding language.

Based on the following news topics, write a LinkedIn POST (~150-200 words). Do NOT include links in the body - they will be added separately.

Style guidelines:
- Start with a hook or personal observation
- Use short paragraphs and line breaks for readability
- Include 1-2 specific insights or hot takes
- End with a question or call to engagement
- Be authentic, not promotional
- Use emojis sparingly (1-2 max)
- Do NOT add a "Links:" section or enumerate sources in the body

Topics to write about:
{topics}

Write the LinkedIn post now (no links section):
"""

LINKEDIN_ARTICLE_PROMPT = """\
You are Yufeng, a technology professional writing a LinkedIn article. Write in a conversational, reflective style grounded in real experience. Avoid generic AI-sounding language.

Based on the following news topics, write a LinkedIn ARTICLE (~500-800 words). Do NOT include links in the body - they will be added separately.

Style guidelines:
- Compelling headline that sparks curiosity
- Open with a personal anecdote or observation
- Break into clear sections with subheadings
- Include specific examples and concrete details
- Share genuine opinions and lessons learned
- End with actionable takeaways or thought-provoking questions
- Be authentic and vulnerable where appropriate
- Do NOT add a "Links:" section at the end

Topics to write about:
{topics}

Write the LinkedIn article now with a headline (no links section):
"""


def cluster_and_select_articles(articles: list[dict]) -> dict:
    """Use Claude to cluster articles by theme and select the most newsworthy ones."""
    client = _get_client()
    
    preferences = db.get_all_preferences()
    
    scored = [(a, score_article(a, preferences)) for a in articles]
    sorted_articles = sorted(scored, key=lambda x: x[1], reverse=True)
    top_articles = [a for a, s in sorted_articles[:25]]
    
    preferences_context = _build_preferences_context(preferences)
    
    articles_text = _format_articles_for_clustering(top_articles)
    
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": CLUSTERING_PROMPT.format(
                articles=articles_text,
                preferences_context=preferences_context
            )},
        ],
    )
    
    import json
    response_text = message.content[0].text
    
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        result = json.loads(response_text[json_start:json_end])
        
        if result.get("selected_indices"):
            result["selected_articles"] = [top_articles[i] for i in result["selected_indices"] if i < len(top_articles)]
        
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "clusters": [],
            "selected_indices": list(range(min(5, len(top_articles)))),
            "selected_articles": top_articles[:5],
            "reasoning": "Default selection"
        }


def _build_preferences_context(preferences: dict) -> str:
    """Build preference context string for the prompt."""
    if not preferences:
        return ""
    
    high_sources = []
    low_sources = []
    high_themes = []
    
    for (cat, key), pref in preferences.items():
        if pref["sample_count"] < 5:
            continue
        
        if cat == "source" and pref["sample_count"] >= 10:
            if pref["weight"] > 0.3:
                high_sources.append(key)
            elif pref["weight"] < -0.3:
                low_sources.append(key)
        elif cat == "theme" and pref["weight"] > 0.3:
            high_themes.append(key)
    
    if not high_sources and not low_sources and not high_themes:
        return ""
    
    lines = ["YUFENG'S LEARNED PREFERENCES:"]
    
    if high_sources:
        lines.append(f"- Preferred sources (prioritize): {', '.join(high_sources)}")
    if low_sources:
        lines.append(f"- Less relevant sources: {', '.join(low_sources)}")
    if high_themes:
        lines.append(f"- Topics of interest: {', '.join(high_themes)}")
    
    lines.append("Use these preferences when selecting articles.\n")
    
    return "\n".join(lines)


def generate_linkedin_post(topics: list[dict]) -> str:
    """Generate a LinkedIn post from selected topics with article links."""
    client = _get_client()
    topics_text = _format_topics(topics)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": LINKEDIN_POST_PROMPT.format(topics=topics_text)},
        ],
    )
    post_body = message.content[0].text
    links_section = _format_links_section(topics)
    return f"{post_body}\n\n{links_section}"


def generate_linkedin_article(topics: list[dict]) -> str:
    """Generate a LinkedIn article from selected topics with article links."""
    client = _get_client()
    topics_text = _format_topics(topics)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "user", "content": LINKEDIN_ARTICLE_PROMPT.format(topics=topics_text)},
        ],
    )
    article_body = message.content[0].text
    links_section = _format_links_section(topics)
    return f"{article_body}\n\n{links_section}"


def _format_articles_for_clustering(articles: list[dict]) -> str:
    """Format articles for the clustering prompt."""
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"[{i}] {a['title']}")
        if a.get("summary"):
            lines.append(f"    {a['summary'][:150]}")
        lines.append(f"    Source: {a['source']} | Score: {a.get('score', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


def _format_topics(topics: list[dict]) -> str:
    """Format topics for the prompt (includes URLs for context)."""
    lines = []
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. **{t['title']}**")
        if t.get("summary"):
            lines.append(f"   {t['summary'][:200]}")
        lines.append(f"   Source: {t['source']}")
        if t.get("url"):
            lines.append(f"   URL: {t['url']}")
        lines.append("")
    return "\n".join(lines)


def _format_links_section(topics: list[dict]) -> str:
    """Format the links section for the end of the post."""
    lines = ["---", "", "**What I'm reading today:**", ""]
    for t in topics[:8]:
        title = t["title"][:60] + "..." if len(t["title"]) > 60 else t["title"]
        url = t.get("url", "")
        if url:
            lines.append(f"• {title}")
            lines.append(f"  {url}")
            lines.append("")
    lines.append("#AI #MachineLearning #TechNews")
    return "\n".join(lines)
