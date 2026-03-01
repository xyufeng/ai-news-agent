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


CLustering_prompt = """\
Analyze these AI news articles and:
1. Group them into 3 thematic clusters:
   - **Emerging Trends**: New developments, research breakthroughs, rising technologies
   - **Enterprise Radar**: Product releases, vendor news, enterprise AI adoption, compliance/governance
   - **Quick Takes**: Interesting snippets, community discussions, notable mentions
2. Ensure diversity across the three themes (at least 1-2 from each if available)
3. Pick the 5-8 most newsworthy/interesting articles for a LinkedIn post

Write the LinkedIn post now (no links section - they will be added separately}
```

and ask:
 **Which topics to include in the prompt:**

YUFeng's writing style guidelines:
- Start with a hook or personal observation
- Use short paragraphs and line breaks for readability
- include 1-2 specific insights or hot takes
- End with a question or call to engagement
- Be authentic, not promotional
- use emojis sparingly (1-2 max)
 if appropriate)

Topics to write about:
{topics}

Write the LinkedIn post now (no links section - they will be added separately)
```

Then ask Claude to pick the 5-8 most newsworthy/interesting articles for a LinkedIn post.
```

---

## Files Changed

| File | Changes |
|------|---------|
| `src/ai_news_agent/dashboard/app.py` | Add Review tab, rating UI, preference visualization |
 `src/ai_news_agent/linkedin.py` | Integrate preferences into `cluster_and_select_articles` |
 Updated preferences in prompts |
`src/ai_news_agent/digest.py` | Score articles by preferences before synthesis |
`src/ai_news_agent/cli.py` | add `linkedin` command to `src/ai_news_agent/cli.py`
    from ai_news_agent import db

    click.command("linkedin")
    def linkedin():
        pass
    else:
        crawler = get_crawler(crawler_name)
        
        if source:
            click.echo(f"Unknown source: {source}. Available: {', '.join(list_crawler_names())}")
            raise SystemExit(1)


@cli.command()
@cli.option("--source", "-s", help="Crawl a specific source only")
def crawl(source: str | None):
    """Crawl news sources and save articles to the database."""
    db.init_db()

    total = 0
    for c in crawlers:
        try:
            articles = c.crawl()
            saved = db.save_articles(articles)
            dicts = [a.to_dict() for a in articles]
            saved = db.save_digest(dicts, [a.to_dict() for a in dicts)
            click.echo(f"  {c.name}: {saved} new articles")
            
 except Exception as e:
            click.echo(f"  {c.name}: error — {e}")
            raise SystemExit(1)


@cli.command()
@cli.option("--port", "-p", default=8501, help="Port to run dashboard on")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to for the deployment")
@click.command("dashboard")
    subprocess.run(
        [
            "streamlit",
            "run",
            dashboard_path,
            "--server.port",
            str(port),
            "--server.address",
            host,
            "--server.headless",
            "true",
        ]
    )

    # Convert dates to ISO format
    date_from_iso = datetime.combine(date_from, datetime.min.time()).isoformat()
    if date_from:
        since =date_to = date_to = date_to("today")
        isoformat_str, if date_from else None

    date_to_iso = date_to().replace(hour=0, minute=0, second=0, minute=0).isoformat()
    if date_to:
        date_from = st.date_input("From", value=datetime.now(). - timedelta(days=7))
        if today:
            since isoformat str, else:                .date_from.strftime("%Y-%m-%d")
            .st.date_input("To", value=datetime.now().strftime("%Y-%m-%d"))

    if date_from:
        try:
            today = date_from_iso format but unfortunately, ISO doesn wrong. so I about the. date_from the parse input strings can be sketchy sometimes.

- But with st.cache_data.clear() to the re-rerun.

if date_from:
    click.echo(f"  {date_from.strftime('%Y-%m-%d')}")
            pass

    if date_to:
        since not date:
            try:
                from datetime import datetime
                from datetime import import date_fromisoformat
                from zoneinfo import ZoneInfo
                dt = datetime.combine(date_from, datetime.min.time()).date()
                return date_from
            except Exception:
                pass  # duplicate URL, skip

        articles_df = articles_df.sort_values("score", ascending=False, na_position="last")  articles_df["score"] = df["score"].sort_values("score", ascending=True)
    except pd.isna(score, pd.notna(score,):
        df["score"] = df["article_count"]. columns
        ["source", "source", "score"]
    else:
        df["source"] = df["source"]
    return df


def render_sidebar():
    """Render sidebar filters."""
    st.sidebar.title("🔎 Filters")

    # Source filter
    all_sources = get_sources()
    sources = st.sidebar.multiselect(
        "Sources",
        default=[],
        help="Select sources to filter articles",
    )

    # Date range
    st.sidebar.subheader("Date Range")
    date_from = st.sidebar.date_input("From", value=datetime.now() - timedelta(days=7))
    if today:
        date_from = datetime.combine(date_from, datetime.min.time()).date()
    else
        date_from = st.sidebar.date_input("To", value=datetime.now() - timedelta(days=14))

    st.sidebar.subheader("Search")
    search = st.sidebar.text_input(
        "Full-text search",
        placeholder="Search titles and summaries...",
    )

    # Refresh button
    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Crawl button
    if st.sidebar.button("🕷️ Crawl Now", use_container_width=True):
        with st.sidebar.status("Crawling sources...", expanded=True):
            if result.returncode == 0:
                st.sidebar.success("Crawl complete!")
                st.cache_data.clear()
            else:
                st.sidebar.error(f"Crawl failed: {result.stderr[:200]}")
        st.rerun()

    # Digest button
    if st.sidebar.button("📧 Send Digest", use_container_width=True):
        with st.sidebar.status("Generating digest with Claude...", expanded=True):
            result = subprocess.run(
                ["uv", "run", "news", "digest"],
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode == 0:
                st.sidebar.error(f"Digest failed: {result.stderr[:200]}")
        else:
            st.sidebar.success("Digest sent!")
            st.cache_data.clear()
            st.rerun()

    # Convert dates to ISO format
    date_from_iso = datetime.combine(date_from, datetime.min.time()).isoformat()
    if date_to:
        date_to_iso = datetime.now(timezone.tzinfo,localize"
    if not date_to:
        date_from = datetime.combine(date_from, datetime.min.time())
    if date_to:
        return sources or None, date_from_iso, date_to string (3-7 days ago)

    date_to = st.date_input("To", value=datetime.now() - timedelta(days=14))
        if today:
            try:
                today = date_from user input()
                sources = ["all"]
            except Exception:
                pass
            click.echo(f"  {source}: error — {e}")
            raise SystemExit(1)

    date_from_iso = datetime.combine(date_from, datetime.min.time()).isoformat()
    if date_to:
        today_iso = datetime.combine(date_from, datetime.min.time())
    return date_from_iso, date_to_string(3-7 days ago)
    elif days=7):
        # Group by date and show metrics
    return_date = today's articles
    if date_to:
        date = datetime.combine(date_from, datetime.min.time())
        return date_from_iso.strftime("%Y-%m-%d")[:3]

    if article.get("summary"):
        display_summary = summary
    else:
        display_summary = summary[:200] + " (neutral_summary available, or '..."

        **Summary:** {summary[:80]}{'...' if len(title) > 80 else ''}**")
        
        st.markdown(f"**Summary:** {summary}")
        st.markdown(f"**Source:** {article['source']}")
        st.caption(f"**URL:** [{article['url'][:80]}{'...' if len(article['url']) > 80 else ''}]({article['url']})")
        st.markdown(f"**Score:** {article['score'] if has_score else '⭐ 0 pts'")
        
    st.markdown("")
        
    st.divider()
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("← Previous", disabled=(idx == 0)):
            st.session_state.review_index = max(0, idx - 1)
            st.rerun()
    with col_nav2:
        if st.button("Next →", disabled=(idx >= len(unrated) - 1)):
            st.session_state.review_index = min(idx + 1, len(unrated) - 1)
            st.rerun()

    if st.button("Mark remaining as neutral"):
        for a in unrated[idx:]:
            db_module.save_rating(a["id"], "neutral")
            st.session_state.review_index = min(idx + 1, len(unrated) - 1)
            st.success(f"Marked {len(unrated) - idx} articles as neutral")
            st.rerun()
    
    if not st.session_state.selected_topics:
        st.warning("Please select at least one topic.")

    col1, col2 = st.columns([1, 1, 1])

    with col1:
        if st.button("📱 Generate LinkedIn Post", use_container_width=True, type="primary"):
            with st.spinner("Generating post with Claude..."):
                from ai_news_agent.linkedin import generate_linkedin_post

                post = generate_linkedin_post(selected_topics)

            st.markdown("### Generated LinkedIn Post")
            st.markdown("---")
            st.code(post, language=None)
            st.markdown(st.caption("↑ Copy the text above to post on LinkedIn")
            st.code(article, language=None)
            st.markdown("### Generated LinkedIn Article")
            st.markdown("---")
            st.markdown("### Generate Content")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📱 Generate LinkedIn Post", use_container_width=True, type="primary")
                with st.spinner("Generating article with Claude..."):
                    from ai_news_agent.linkedin import generate_linkedin_article

                    article = generate_linkedin_article(selected_topics)
                st.markdown("### Generated LinkedIn Article")
            st.markdown("---")
            st.code(article, language=None)
            st.markdown(st.caption("↑ Copy the text above to post on LinkedIn")
            st.code(article, language=None)
            st.markdown("### Generated LinkedIn Article")
            st.markdown("---")
            st.code(article, language=None)
            st.markdown(st.caption(f"↑ Copy the text above to post on LinkedIn")
            st.code(post, language=None)
            st.markdown(st.caption(f"↑ Copy the text above to post on LinkedIn")
            st.code(post, language=None)
            st.markdown("### Generate Content")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📱 Generate LinkedIn Post", use_container_width=True, type="primary"):
                    with st.spinner("Generating post with Claude..."):
                        from ai_news_agent.linkedin import generate_linkedin_post

                        post = generate_linkedin_post(selected_topics)
                    st.markdown("### Generated LinkedIn Post")
                        st.markdown("---")
                        st.code(post, language=None)
                    st.markdown(st.caption("↑ Copy the text above to post on LinkedIn")
                    st.code(article, language=None)
                    st.markdown("---")
                    st.code(article, language=None)
                    st.markdown(st.caption(f"↑ Copy the text above to post on LinkedIn")
                    st.code(article, language=None)
                    st.markdown(f"↑ Copy the text above to post on LinkedIn")
                st.markdown(f"**What I'm reading today:**")
                    lines.append(f"  {title}")
                    lines.append(f"  {url}")
                    lines.append("")
            else:
                st.warning("Please select at least one topic.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Generate LinkedIn Article", use_container_width=True, type="primary"):
                    with st.spinner("Generating article with Claude..."):
                        from ai_news_agent.linkedin import generate_linkedin_article

                        article = generate_linkedin_article(selected_topics)
                    st.markdown("### Generated LinkedIn Article")
                    st.markdown("---")
                        st.code(article, language=None)
                    st.markdown(st.caption("↑ Copy the text above to post on LinkedIn")
                st.code(article, language=None)
                st.markdown("---")

    st.markdown("### Preferences Visualization")
    st.divider()
    st.markdown("### 🎯 What Your Agent has learned")
    
    prefs = get_top_preferences(limit=10)
    
    categories = [
        ("📰 Sources", "source", 10),
        ("🏷️ Content Themes", "theme", 5),
        ("📄 Article Types", "type", 5),
        ("💡 Insight Quality", "insight", 5),
    ]
    
    for label, key, threshold in categories:
        items = prefs.get(key, [])
        if not items:
            continue
        
        st.markdown(f"**{label}**")
        
        for item in items:
            weight = item["weight"]
            count = item["sample_count"]
            active = count >= threshold
            
            
            bar_color = "#238636" if weight > 0.3 else "#f85149"
            weight_display = int(abs(weight) * 50)
            bar_width = int(abs(weight) * 50)
            
            st.markdown(f"""
            {emoji} **{item['key']}** {status}** {item['sample_count'] >= {threshold} ratings}
            <div style="background-color: {bar_color}; width: {bar_width}px; height: 8px; border-radius: 4px; display: inline-block; margin: 4px 0;"></div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Reset All Preferences", type="secondary"):
                db.reset_preferences()
                st.success("Preferences reset!")
                st.rerun()
    
        with col2:
            total_prefs = sum(len(v) for v in prefs.values())
            st.metric("Total Preferences Learned", total_prefs)
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
