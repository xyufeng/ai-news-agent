"""Preference learning engine for personalized article selection."""

import anthropic

from ai_news_agent import config, db

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


THEME_KEYWORDS = {
    "open_source": ["open source", "github", "apache", "mit license", "open-source", "open weights"],
    "reasoning": ["reasoning", "o1", "r1", "chain of thought", "thinking", "cot"],
    "benchmarks": ["benchmark", "sota", "performance", "evaluation", "leaderboard"],
    "product_launch": ["launch", "announce", "available now", "release", "introducing"],
    "funding": ["funding", "raised", "series a", "series b", "investment", "valuation"],
    "safety": ["safety", "alignment", "harmful", "responsible ai", "guardrails"],
    "multimodal": ["vision", "image", "video", "audio", "multimodal"],
    "agents": ["agent", "autonomous", "tool use", "function calling", "agentic"],
    "training": ["training", "fine-tuning", "rlhf", "pre-training", "distillation"],
    "efficiency": ["efficient", "faster", "cheaper", "optimization", "quantization"],
    "enterprise": ["enterprise", "business", "b2b", "api", "production"],
    "research": ["paper", "arxiv", "study", "research", "novel"],
}

TYPE_KEYWORDS = {
    "research_paper": ["arxiv", "paper", "we propose", "we present", "study shows"],
    "technical_deep_dive": ["architecture", "implementation", "how it works", "under the hood", "technical"],
    "opinion_piece": ["opinion", "why i", "thoughts on", "my take", "reflection"],
    "press_release": ["announces", "proud to", "excited to", "thrilled to", "pleased to"],
    "tutorial": ["how to", "guide", "tutorial", "step by step", "walkthrough"],
    "news": ["breaking", "reportedly", "according to", "sources say"],
}

INSIGHT_KEYWORDS = {
    "technical_details": ["architecture", "parameters", "training", "inference", "model size"],
    "practical_takeaways": ["you can", "try this", "use case", "application", "how to use"],
    "industry_analysis": ["market", "competition", "landscape", "trend", "industry"],
    "hot_take": ["controversial", "unpopular opinion", "i believe", "actually", "hot take"],
}


def extract_themes(article: dict) -> list[str]:
    """Extract content themes from article using keywords + Claude fallback."""
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            themes.append(theme)
    
    if not themes:
        themes = _classify_with_claude(article, "themes", list(THEME_KEYWORDS.keys()))
    
    return themes[:3]


def classify_type(article: dict) -> str:
    """Classify article type using keywords + Claude fallback."""
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    for article_type, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return article_type
    
    result = _classify_with_claude(article, "type", list(TYPE_KEYWORDS.keys()))
    return result[0] if result else "news"


def assess_insights(article: dict) -> list[str]:
    """Assess what types of insights the article provides."""
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    insights = []
    for insight_type, keywords in INSIGHT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            insights.append(insight_type)
    
    if not insights:
        insights = _classify_with_claude(article, "insights", list(INSIGHT_KEYWORDS.keys()))
    
    return insights[:2]


def _classify_with_claude(article: dict, category: str, options: list[str]) -> list[str]:
    """Use Claude to classify article when keywords don't match."""
    try:
        client = _get_client()
        prompt = f"""Classify this article into relevant {category}.

Title: {article.get('title', '')}
Summary: {article.get('summary', '')[:300]}

Available {category}: {', '.join(options)}

Return a JSON array of 1-3 most relevant {category}. Example: ["open_source", "reasoning"]

Only return the JSON array, nothing else."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        
        import json
        response = message.content[0].text.strip()
        return json.loads(response)
    except Exception:
        return []


def learn_from_rating(article_id: int, rating: str) -> None:
    """Update preferences based on article rating."""
    if rating == "neutral":
        return
    
    article = db.get_article_by_id(article_id)
    if not article:
        return
    
    signal = 1.0 if rating == "up" else -1.0
    
    db.update_preference("source", article["source"], signal * 0.1)
    
    themes = extract_themes(article)
    for theme in themes:
        db.update_preference("theme", theme, signal * 0.1)
    
    article_type = classify_type(article)
    db.update_preference("type", article_type, signal * 0.1)
    
    insights = assess_insights(article)
    for insight in insights:
        db.update_preference("insight", insight, signal * 0.1)


def score_article(article: dict, preferences: dict | None = None) -> float:
    """Score an article based on learned preferences."""
    if preferences is None:
        preferences = db.get_all_preferences()
    
    score = 0.0
    
    source_pref = preferences.get(("source", article.get("source", "")))
    if source_pref and source_pref["sample_count"] >= 10:
        score += source_pref["weight"] * 2.0
    
    for theme in extract_themes(article):
        theme_pref = preferences.get(("theme", theme))
        if theme_pref and theme_pref["sample_count"] >= 5:
            score += theme_pref["weight"]
    
    type_pref = preferences.get(("type", classify_type(article)))
    if type_pref and type_pref["sample_count"] >= 5:
        score += type_pref["weight"] * 1.5
    
    for insight in assess_insights(article):
        insight_pref = preferences.get(("insight", insight))
        if insight_pref and insight_pref["sample_count"] >= 5:
            score += insight_pref["weight"] * 0.5
    
    base = article.get("score") or 0
    score += base * 0.001
    
    return score


def get_top_preferences(limit: int = 5) -> dict[str, list[dict]]:
    """Get top preferences by absolute weight for display."""
    stats = db.get_preference_stats()
    
    result = {}
    for category, prefs in stats.items():
        sorted_prefs = sorted(prefs, key=lambda x: abs(x["weight"]), reverse=True)[:limit]
        result[category] = sorted_prefs
    
    return result
