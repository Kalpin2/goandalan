"""Central configuration for the @goandalan Mini App & 2-Stage Automation Pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    BASE_DIR: Path = BASE_DIR
    IG_USERNAME: str = os.getenv("IG_USERNAME", "goandalan").lstrip("@")
    IG_HANDLE: str = f"@{os.getenv('IG_USERNAME', 'goandalan').lstrip('@')}"
    IG_URL: str = os.getenv("IG_URL", "https://instagram.com/goandalan")
    BRAND_NAME: str = os.getenv("BRAND_NAME", "gw sama alan")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    DB_PATH: Path = (BASE_DIR / os.getenv("DB_PATH", "leads.db")).resolve()
    SITE_DIR: Path = (BASE_DIR / os.getenv("SITE_DIR", "site")).resolve()
    DEMOS_DIR: Path = SITE_DIR / "demos"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    CONTENT_QUEUE_DIR: Path = BASE_DIR / "content_queue"

    FOLLOW_UP_HOURS: int = int(os.getenv("FOLLOW_UP_HOURS", "48"))
    DEFAULT_CITY: str = os.getenv("DEFAULT_CITY", "Jakarta")

    SCRAPER_HEADLESS: bool = os.getenv("SCRAPER_HEADLESS", "true").lower() in {"1", "true", "yes"}
    SCRAPER_TIMEOUT_MS: int = int(os.getenv("SCRAPER_TIMEOUT_MS", "25000"))

    # Agent-Reach Read-Only Lead Enrichment (isolated venv, optional graceful fallback)
    AGENT_REACH_BIN: str = os.getenv(
        "AGENT_REACH_BIN",
        r"D:\AI WORKSPACE\tools\Agent-Reach\.venv\Scripts\agent-reach.exe",
    ).strip()
    ENABLE_POST_SCRAPE_ENRICHMENT: bool = (
        os.getenv("ENABLE_POST_SCRAPE_ENRICHMENT", "true").lower() in {"1", "true", "yes"}
    )

    # Authentication & Session Security (FAIL-CLOSED: zero hardcoded default credentials)
    ADMIN_USN: str = os.getenv("ADMIN_USN", "").strip()
    ADMIN_PASS: str = os.getenv("ADMIN_PASS", "")
    REVIEW_USN: str = os.getenv("REVIEW_USN", "").strip()
    REVIEW_PASS: str = os.getenv("REVIEW_PASS", "")

    SESSION_COOKIE_NAME: str = "goandalan_session"
    REVIEW_SESSION_TTL_SECONDS: int = 7 * 24 * 3600   # 7 days sliding window
    ADMIN_SESSION_TTL_SECONDS: int = 12 * 3600        # 12 hours
    SESSION_RENEW_THROTTLE_SECONDS: int = 3600        # 1 hour throttle for sliding renewal

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 15 * 60               # 15 minutes
    LOGIN_FAIL_DELAY_SECONDS: float = 0.25            # Constant delay on invalid login

    HTTPS_ENABLED: bool = os.getenv("HTTPS_ENABLED", "false").lower() in {"1", "true", "yes"}
    CORS_ALLOWED_ORIGINS: tuple[str, ...] = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )

    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
    REVIEW_STATUSES = (
        "draft_brief",
        "pending_review",
        "changes_requested",
        "revised",
        "approved",
        "posted",
    )

    # Warm Editorial Palette (@goandalan Brand Identity for IG Carousels & Mini App)
    COLORS = {
        "bg": "#F6F3EC",
        "surface": "#EDE8DD",
        "ink": "#1E1E1E",
        "muted": "#6B675F",
        "accent": "#3E4E3C",
        "border": "rgba(30, 30, 30, 0.12)",
    }

    # 2-Stage Pipeline Status Flow
    LEAD_STATUSES = (
        "NEW",
        "CONCEPT_READY",
        "CONTACTED_DM",
        "CONTACTED_CALL",
        "IGNORED_48H",
        "INTERESTED",
        "FULL_DEMO_READY",
        "DP_PAID",
        "WON",
        "RECYCLED_CONTENT",
    )


settings = Settings()
settings.SITE_DIR.mkdir(parents=True, exist_ok=True)
settings.DEMOS_DIR.mkdir(parents=True, exist_ok=True)
