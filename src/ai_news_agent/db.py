import sqlite3
from datetime import datetime, timezone

from ai_news_agent import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            author TEXT,
            summary TEXT,
            published_at TEXT,
            crawled_at TEXT NOT NULL,
            score INTEGER
        );

        CREATE TABLE IF NOT EXISTS digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            content TEXT NOT NULL,
            article_count INTEGER,
            emailed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS article_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER REFERENCES articles(id),
            rating TEXT CHECK(rating IN ('up', 'down', 'neutral')),
            created_at TEXT NOT NULL,
            UNIQUE(article_id)
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT CHECK(category IN ('source', 'theme', 'type', 'insight')),
            key TEXT NOT NULL,
            weight REAL CHECK(weight BETWEEN -1.0 AND 1.0),
            sample_count INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL,
            UNIQUE(category, key)
        );

        CREATE INDEX IF NOT EXISTS idx_articles_crawled_at ON articles(crawled_at);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(score);
        CREATE INDEX IF NOT EXISTS idx_ratings_article ON article_ratings(article_id);
        CREATE INDEX IF NOT EXISTS idx_preferences_lookup ON user_preferences(category, key);
    """)
    conn.close()


def save_articles(articles: list[dict]) -> int:
    """Save articles to DB, skipping duplicates. Returns count of new articles."""
    conn = _connect()
    saved = 0
    for a in articles:
        try:
            conn.execute(
                """INSERT INTO articles (url, title, source, author, summary, published_at, crawled_at, score)
                   VALUES (:url, :title, :source, :author, :summary, :published_at, :crawled_at, :score)""",
                {
                    "url": a["url"],
                    "title": a["title"],
                    "source": a["source"],
                    "author": a.get("author"),
                    "summary": a.get("summary"),
                    "published_at": a.get("published_at"),
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "score": a.get("score"),
                },
            )
            saved += 1
        except sqlite3.IntegrityError:
            pass  # duplicate URL, skip
    conn.commit()
    conn.close()
    return saved


def get_articles_since(since: str, source: str | None = None) -> list[dict]:
    """Get articles crawled since the given ISO timestamp."""
    conn = _connect()
    if source:
        rows = conn.execute(
            "SELECT * FROM articles WHERE crawled_at >= ? AND source = ? ORDER BY score DESC NULLS LAST, crawled_at DESC",
            (since, source),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM articles WHERE crawled_at >= ? ORDER BY score DESC NULLS LAST, crawled_at DESC",
            (since,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_digest(content: str, article_count: int) -> int:
    """Save a digest and return its ID."""
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO digests (created_at, content, article_count) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), content, article_count),
    )
    digest_id = cur.lastrowid
    conn.commit()
    conn.close()
    return digest_id


def mark_digest_emailed(digest_id: int) -> None:
    conn = _connect()
    conn.execute(
        "UPDATE digests SET emailed_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), digest_id),
    )
    conn.commit()
    conn.close()


# ===== Rating Functions =====

def save_rating(article_id: int, rating: str) -> None:
    """Save or update rating for an article. rating: 'up', 'down', or 'neutral'."""
    if rating not in ("up", "down", "neutral"):
        raise ValueError(f"Invalid rating: {rating}")
    conn = _connect()
    conn.execute(
        """INSERT INTO article_ratings (article_id, rating, created_at)
           VALUES (?, ?, ?)
           ON CONFLICT(article_id) DO UPDATE SET rating = excluded.rating, created_at = excluded.created_at""",
        (article_id, rating, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_rating(article_id: int) -> dict | None:
    """Get rating for an article."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM article_ratings WHERE article_id = ?", (article_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_unrated_articles(since: str) -> list[dict]:
    """Get articles without ratings since given timestamp."""
    conn = _connect()
    rows = conn.execute(
        """SELECT a.* FROM articles a
           LEFT JOIN article_ratings r ON a.id = r.article_id
           WHERE a.crawled_at >= ? AND r.id IS NULL
           ORDER BY a.score DESC NULLS LAST, a.crawled_at DESC""",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rated_articles(since: str | None = None) -> list[dict]:
    """Get articles with ratings."""
    conn = _connect()
    if since:
        rows = conn.execute(
            """SELECT a.*, r.rating, r.created_at as rated_at
               FROM articles a
               JOIN article_ratings r ON a.id = r.article_id
               WHERE a.crawled_at >= ?
               ORDER BY r.created_at DESC""",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT a.*, r.rating, r.created_at as rated_at
               FROM articles a
               JOIN article_ratings r ON a.id = r.article_id
               ORDER BY r.created_at DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_article_by_id(article_id: int) -> dict | None:
    """Get a single article by ID."""
    conn = _connect()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ===== Preference Functions =====

def get_all_preferences() -> dict[tuple[str, str], dict]:
    """Get all preferences as dict of (category, key) -> {weight, sample_count}."""
    conn = _connect()
    rows = conn.execute("SELECT category, key, weight, sample_count FROM user_preferences").fetchall()
    conn.close()
    return {(r["category"], r["key"]): {"weight": r["weight"], "sample_count": r["sample_count"]} for r in rows}


def update_preference(category: str, key: str, delta: float) -> None:
    """Update preference weight by delta. Creates if not exists."""
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    
    existing = conn.execute(
        "SELECT weight, sample_count FROM user_preferences WHERE category = ? AND key = ?",
        (category, key),
    ).fetchone()
    
    if existing:
        new_weight = max(-1.0, min(1.0, existing["weight"] + delta))
        new_count = existing["sample_count"] + 1
        conn.execute(
            "UPDATE user_preferences SET weight = ?, sample_count = ?, updated_at = ? WHERE category = ? AND key = ?",
            (new_weight, new_count, now, category, key),
        )
    else:
        conn.execute(
            "INSERT INTO user_preferences (category, key, weight, sample_count, updated_at) VALUES (?, ?, ?, 1, ?)",
            (category, key, max(-1.0, min(1.0, delta)), now),
        )
    
    conn.commit()
    conn.close()


def get_preference(category: str, key: str) -> dict | None:
    """Get a specific preference."""
    conn = _connect()
    row = conn.execute(
        "SELECT weight, sample_count FROM user_preferences WHERE category = ? AND key = ?",
        (category, key),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def reset_preferences() -> None:
    """Reset all preferences."""
    conn = _connect()
    conn.execute("DELETE FROM user_preferences")
    conn.commit()
    conn.close()


def get_preference_stats() -> dict[str, list[dict]]:
    """Get preferences grouped by category for display."""
    conn = _connect()
    rows = conn.execute(
        "SELECT category, key, weight, sample_count FROM user_preferences ORDER BY weight DESC"
    ).fetchall()
    conn.close()
    
    result: dict[str, list[dict]] = {"source": [], "theme": [], "type": [], "insight": []}
    for r in rows:
        if r["category"] in result:
            result[r["category"]].append({
                "key": r["key"],
                "weight": r["weight"],
                "sample_count": r["sample_count"],
            })
    return result
