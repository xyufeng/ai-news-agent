import subprocess
from datetime import datetime, timedelta, timezone

import click

from ai_news_agent import db
from ai_news_agent.crawlers import get_all_crawlers, get_crawler, list_crawler_names


@click.group()
def cli():
    """AI News Agent — crawl, digest, and deliver AI news."""
    db.init_db()


@cli.command()
@click.option("--source", "-s", help="Crawl a specific source only")
def crawl(source: str | None):
    """Crawl news sources and save articles to the database."""
    if source:
        crawler = get_crawler(source)
        if not crawler:
            click.echo(f"Unknown source: {source}. Available: {', '.join(list_crawler_names())}")
            raise SystemExit(1)
        crawlers = [crawler]
    else:
        crawlers = get_all_crawlers()

    total = 0
    for c in crawlers:
        click.echo(f"Crawling {c.name}...")
        try:
            articles = c.crawl()
            dicts = [a.to_dict() for a in articles]
            saved = db.save_articles(dicts)
            click.echo(f"  {c.name}: {saved} new articles (of {len(articles)} fetched)")
            total += saved
        except Exception as e:
            click.echo(f"  {c.name}: error — {e}")

    click.echo(f"\nTotal: {total} new articles saved.")


@cli.command("list")
@click.option("--today", is_flag=True, help="Show only today's articles")
@click.option("--source", "-s", help="Filter by source")
@click.option("--limit", "-n", default=50, help="Max articles to show")
def list_articles(today: bool, source: str | None, limit: int):
    """List articles from the database."""
    if today:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    articles = db.get_articles_since(since, source=source)[:limit]

    if not articles:
        click.echo("No articles found.")
        return

    for a in articles:
        score = f" [{a['score']}pts]" if a.get("score") else ""
        click.echo(f"• {a['title']}{score}")
        click.echo(f"  {a['source']} | {a['url']}")
        click.echo()

    click.echo(f"Showing {len(articles)} articles.")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Generate digest without emailing")
@click.option("--since", help="ISO timestamp (default: today midnight UTC)")
def digest(dry_run: bool, since: str | None):
    """Generate an AI digest of today's articles."""
    from ai_news_agent.digest import generate_digest

    if not since:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()

    click.echo("Generating digest...")
    content = generate_digest(since, dry_run=dry_run)
    click.echo(content)

    if dry_run:
        click.echo("\n(Dry run — email not sent)")


@cli.command()
@click.option("--port", "-p", default=8501, help="Port to run dashboard on")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
def dashboard(port: int, host: str):
    """Launch the Streamlit dashboard."""
    import os

    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
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
