import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_news_agent import config

# Page config
st.set_page_config(
    page_title="AI News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stSidebar {
        background-color: #161b22;
    }
    .stMetric {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
    }
    .stMetric label {
        color: #8b949e;
    }
    .stMetric value {
        color: #fafafa;
    }
    div[data-testid="stDataFrame"] {
        background-color: #161b22;
    }
    .source-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .article-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .article-title {
        font-size: 18px;
        font-weight: 600;
        color: #58a6ff;
        margin-bottom: 8px;
    }
    .article-meta {
        color: #8b949e;
        font-size: 14px;
    }
    .article-summary {
        color: #c9d1d9;
        margin-top: 8px;
    }
    .tag {
        background-color: #238636;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 4px;
    }
    .tag-enterprise {
        background-color: #1f6feb;
    }
    .tag-trending {
        background-color: #f78166;
    }
    h1, h2, h3 {
        color: #fafafa;
    }
    .stExpander {
        background-color: #161b22;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_project_dir() -> str:
    """Get the project directory path (works locally and on EC2)."""
    import os

    cwd = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if os.path.exists(os.path.join(cwd, "pyproject.toml")):
        return cwd
    return "/home/ubuntu/ai-news-agent"  # EC2 fallback


@st.cache_resource
def get_sources() -> list[str]:
    """Get list of all sources."""
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT source FROM articles ORDER BY source").fetchall()
    conn.close()
    return [r["source"] for r in rows]


@st.cache_resource
def get_source_stats() -> pd.DataFrame:
    """Get stats per source."""
    conn = get_db_connection()
    query = """
        SELECT
            source,
            COUNT(*) as article_count,
            MAX(crawled_at) as last_crawl,
            AVG(score) as avg_score
        FROM articles
        GROUP BY source
        ORDER BY article_count DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def get_articles(
    sources: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    limit: int = 500,
) -> pd.DataFrame:
    """Get articles with filters."""
    conn = get_db_connection()

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if sources:
        placeholders = ",".join("?" * len(sources))
        query += f" AND source IN ({placeholders})"
        params.extend(sources)

    if date_from:
        query += " AND crawled_at >= ?"
        params.append(date_from)

    if date_to:
        query += " AND crawled_at <= ?"
        params.append(date_to)

    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    query += " ORDER BY crawled_at DESC LIMIT ?"
    params.append(limit)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


@st.cache_data(ttl=300)
def get_trending_topics(days: int = 7) -> list[tuple[str, int]]:
    """Extract trending topics from recent articles."""
    conn = get_db_connection()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT title, summary FROM articles WHERE crawled_at >= ?",
        (since,),
    ).fetchall()
    conn.close()

    # Extract keywords from titles
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "it", "its", "this", "that", "these", "those", "i", "you", "he", "she", "we", "they", "what", "which", "who", "whom", "when", "where", "why", "how", "all", "each", "every", "both", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "also", "now", "here", "there", "then", "once", "from", "new", "about", "into", "over", "after", "before", "between", "under", "again", "further", "their", "your", "our", "his", "her", "my", "up", "out", "as", "if", "because", "until", "while", "get", "got", "getting", "via", "like", "using"}

    word_counts = Counter()
    for row in rows:
        text = f"{row['title']} {row['summary'] or ''}".lower()
        words = [w for w in text.split() if len(w) > 3 and w.isalpha() and w not in stop_words]
        word_counts.update(words)

    return word_counts.most_common(20)


@st.cache_data(ttl=300)
def get_latest_digest() -> dict | None:
    """Get the most recent digest."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM digests ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


@st.cache_data(ttl=300)
def get_daily_article_counts(days: int = 14) -> pd.DataFrame:
    """Get article counts per day."""
    conn = get_db_connection()
    query = """
        SELECT
            DATE(crawled_at) as date,
            source,
            COUNT(*) as count
        FROM articles
        WHERE crawled_at >= DATE('now', ?)
        GROUP BY DATE(crawled_at), source
        ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn, params=[f"-{days} days"])
    conn.close()
    return df


def render_sidebar():
    """Render sidebar filters."""
    st.sidebar.title("🔎 Filters")

    # Source filter
    all_sources = get_sources()
    sources = st.sidebar.multiselect(
        "Sources",
        all_sources,
        default=[],
        help="Select sources to filter articles",
    )

    # Date range
    st.sidebar.subheader("Date Range")
    date_from = st.sidebar.date_input("From", value=datetime.now() - timedelta(days=7))
    date_to = st.sidebar.date_input("To", value=datetime.now())

    # Search
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
        cwd = get_project_dir()
        with st.sidebar.status("Crawling sources...", expanded=True):
            result = subprocess.run(
                ["uv", "run", "news", "crawl"],
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode == 0:
                st.sidebar.success("Crawl complete!")
                st.cache_data.clear()
            else:
                st.sidebar.error(f"Crawl failed: {result.stderr[:200]}")
        st.rerun()

    # Digest button
    if st.sidebar.button("📧 Send Digest", use_container_width=True):
        cwd = get_project_dir()
        with st.sidebar.status("Generating digest with Claude...", expanded=True):
            result = subprocess.run(
                ["uv", "run", "news", "digest"],
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode == 0:
                st.sidebar.success("Digest sent!")
                st.cache_data.clear()
            else:
                st.sidebar.error(f"Digest failed: {result.stderr[:200]}")
        st.rerun()

    # Convert dates to ISO format
    date_from_iso = datetime.combine(date_from, datetime.min.time()).isoformat() if date_from else None
    date_to_iso = datetime.combine(date_to, datetime.max.time()).isoformat() if date_to else None

    return sources or None, date_from_iso, date_to_iso, search or None


def render_source_health():
    """Render source health monitor."""
    st.subheader("🏥 Source Health Monitor")

    stats = get_source_stats()

    # Create columns for metrics
    cols = st.columns(min(len(stats), 4))

    for idx, row in stats.head(8).iterrows():
        col_idx = idx % 4
        with cols[col_idx]:
            last_crawl = datetime.fromisoformat(row["last_crawl"].replace("Z", "+00:00")) if row["last_crawl"] else None
            hours_ago = (datetime.now(timezone.utc) - last_crawl).total_seconds() / 3600 if last_crawl else None

            status_color = "🟢" if hours_ago and hours_ago < 24 else "🟡" if hours_ago and hours_ago < 48 else "🔴"

            st.metric(
                label=f"{status_color} {row['source']}",
                value=f"{row['article_count']} articles",
                delta=f"Avg {row['avg_score']:.0f} pts" if row['avg_score'] else None,
            )


def render_trending():
    """Render trending topics section."""
    st.subheader("🔥 Trending This Week")

    trending = get_trending_topics(7)

    if not trending:
        st.info("No trending data available yet.")
        return

    # Create word cloud-style display
    cols = st.columns(5)
    for idx, (word, count) in enumerate(trending[:15]):
        col_idx = idx % 5
        with cols[col_idx]:
            # Scale font size based on count
            font_size = min(24, 12 + count)
            st.markdown(
                f"<div style='text-align:center; font-size:{font_size}px; padding:8px; "
                f"background-color:#238636; border-radius:8px; margin:4px;'>"
                f"{word} <span style='font-size:12px;color:#8b949e'>({count})</span></div>",
                unsafe_allow_html=True,
            )


def render_articles_chart(articles_df: pd.DataFrame):
    """Render articles over time chart."""
    if articles_df.empty:
        return

    st.subheader("📊 Articles Over Time")

    # Group by date and source
    df = articles_df.copy()
    df["date"] = pd.to_datetime(df["crawled_at"]).dt.date

    daily_counts = df.groupby(["date", "source"]).size().reset_index(name="count")

    fig = px.area(
        daily_counts,
        x="date",
        y="count",
        color="source",
        title="Articles by Source Over Time",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font_color="#fafafa",
        legend=dict(bgcolor="#161b22", font_color="#fafafa"),
    )
    fig.update_xaxes(gridcolor="#30363d")
    fig.update_yaxes(gridcolor="#30363d")

    st.plotly_chart(fig, use_container_width=True)


def render_digest():
    """Render the latest synthesized digest."""
    st.subheader("📰 Today's Digest")

    digest = get_latest_digest()

    if not digest:
        st.info("No digest available yet. Run `news digest` to generate one.")
        return

    # Show digest metadata
    created = datetime.fromisoformat(digest["created_at"].replace("Z", "+00:00"))
    st.caption(f"Generated: {created.strftime('%Y-%m-%d %H:%M')} UTC | {digest['article_count']} articles")

    # Render digest content
    st.markdown(digest["content"])

    if digest.get("emailed_at"):
        emailed = datetime.fromisoformat(digest["emailed_at"].replace("Z", "+00:00"))
        st.success(f"✉️ Email sent at {emailed.strftime('%Y-%m-%d %H:%M')} UTC")


def render_articles_list(articles_df: pd.DataFrame):
    """Render list of articles with ranking."""
    st.subheader(f"📚 Articles ({len(articles_df)} found)")

    if articles_df.empty:
        st.info("No articles match your filters.")
        return

    # Sort by score
    articles_df = articles_df.sort_values("score", ascending=False, na_position="last")

    for _, row in articles_df.head(50).iterrows():
        with st.container():
            st.markdown(f"""
            <div class="article-card">
                <div class="article-title">
                    <a href="{row['url']}" target="_blank" style="color:#58a6ff;text-decoration:none;">
                        {row['title']}
                    </a>
                </div>
                <div class="article-meta">
                    {row['source']} | {row['crawled_at'][:10]}
                    {f" | ⭐ {int(row['score'])} pts" if row['score'] else ""}
                </div>
                {f'<div class="article-summary">{row["summary"][:200]}...</div>' if row['summary'] else ''}
            </div>
            """, unsafe_allow_html=True)


def render_linkedin_generator():
    """Render LinkedIn content generator."""
    st.subheader("📝 LinkedIn Content Generator")

    st.markdown("""
    Select topics from today's headlines to generate LinkedIn content in your personal writing style.
    """)

    # Get today's top articles
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    articles_df = get_articles(date_from=today, limit=50)

    if articles_df.empty:
        st.info("No articles from today. Run a crawl first.")
        return

    # Sort by score and show top articles
    articles_df = articles_df.sort_values("score", ascending=False, na_position="last")

    # Topic selection
    st.markdown("### Select Topics")

    # Select all checkbox
    select_all = st.checkbox("Select all topics", value=False)

    # Display articles with checkboxes
    selected_topics = []
    cols = st.columns(2)

    for idx, row in articles_df.head(20).iterrows():
        col_idx = idx % 2
        with cols[col_idx]:
            # Use score for default selection (top 5 by default)
            default_checked = select_all or (row["score"] and row["score"] > articles_df["score"].quantile(0.8))

            if st.checkbox(
                f"**{row['title'][:80]}{'...' if len(row['title']) > 80 else ''}**\n{row['source']} | ⭐ {int(row['score']) if row['score'] else 0} pts",
                value=default_checked,
                key=f"topic_{idx}",
            ):
                selected_topics.append({
                    "title": row["title"],
                    "summary": row["summary"],
                    "source": row["source"],
                    "url": row["url"],
                    "score": row["score"],
                })

    st.markdown(f"**{len(selected_topics)} topics selected**")

    if not selected_topics:
        st.warning("Please select at least one topic.")
        return

    # Content type selection
    st.markdown("### Content Type")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📱 Generate LinkedIn Post", use_container_width=True, type="primary"):
            with st.spinner("Generating post with Claude..."):
                from ai_news_agent.linkedin import generate_linkedin_post

                post = generate_linkedin_post(selected_topics)

            st.markdown("### Generated LinkedIn Post")
            st.markdown("---")
            st.markdown(post)
            st.markdown("---")

            # Copy button
            st.code(post, language=None)
            st.caption("↑ Copy the text above")

    with col2:
        if st.button("📄 Generate LinkedIn Article", use_container_width=True, type="primary"):
            with st.spinner("Generating article with Claude..."):
                from ai_news_agent.linkedin import generate_linkedin_article

                article = generate_linkedin_article(selected_topics)

            st.markdown("### Generated LinkedIn Article")
            st.markdown("---")
            st.markdown(article)
            st.markdown("---")

            # Copy button
            st.code(article, language=None)
            st.caption("↑ Copy the text above")


def main():
    st.title("📰 AI News Dashboard")

    # Render sidebar and get filters
    sources, date_from, date_to, search = render_sidebar()

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Digest", "Articles", "Analytics", "LinkedIn"])

    with tab1:
        render_digest()
        st.divider()
        render_trending()

    with tab2:
        # Get filtered articles
        articles_df = get_articles(
            sources=sources,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        render_articles_list(articles_df)

    with tab3:
        render_source_health()
        st.divider()

        # Get all articles for charts
        all_articles = get_articles(date_from=date_from, date_to=date_to)
        render_articles_chart(all_articles)

        # Source distribution pie chart
        if not all_articles.empty:
            st.subheader("🥧 Source Distribution")
            source_counts = all_articles["source"].value_counts().reset_index()
            source_counts.columns = ["source", "count"]

            fig = px.pie(
                source_counts,
                values="count",
                names="source",
                title="Articles by Source",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                paper_bgcolor="#0e1117",
                font_color="#fafafa",
                legend=dict(bgcolor="#161b22", font_color="#fafafa"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        render_linkedin_generator()


if __name__ == "__main__":
    main()
