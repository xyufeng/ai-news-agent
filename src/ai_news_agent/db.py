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
