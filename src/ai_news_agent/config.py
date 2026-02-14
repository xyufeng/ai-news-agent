import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.getenv("DB_PATH", str(PROJECT_DIR / "news.db"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DIGEST_EMAIL_TO = os.getenv("DIGEST_EMAIL_TO", "")
DIGEST_EMAIL_FROM = os.getenv("DIGEST_EMAIL_FROM", "news@example.com")
