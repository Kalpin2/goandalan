"""SQLite database layer for @goandalan 2-stage outreach & demo pipeline."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from config import settings

VALID_STATUSES = set(settings.LEAD_STATUSES)

LEGACY_STATUS_MAP = {
    "DEMO_READY": "CONCEPT_READY",
    "REPLIED": "INTERESTED",
}

ALLOWED_UPDATE_FIELDS = {
    "business_name",
    "anonymized_name",
    "category",
    "design_style",
    "address",
    "city",
    "phone_raw",
    "phone_wa",
    "website_url",
    "instagram_handle",
    "rating",
    "review_count",
    "has_website",
    "priority_score",
    "ig_observation",
    "ux_flaw",
    "concept_preview_path",
    "demo_path",
    "demo_url",
    "carousel_dir",
    "status",
    "contacted_at",
    "follow_up_due_at",
    "follow_up_sent_at",
    "is_anonymized",
    "notes",
    "source_query",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return cleaned or "bisnis-lokal"


def normalize_indo_phone(raw: str | None) -> str:
    """Normalize Indonesian phone numbers (08... -> 628..., +628... -> 628...)."""
    if not raw:
        return ""
    digits = re.sub(r"\D+", "", str(raw))
    if not digits:
        return ""
    if digits.startswith("0062"):
        digits = "62" + digits[4:]
    elif digits.startswith("08"):
        digits = "62" + digits[1:]
    elif digits.startswith("8") and 9 <= len(digits) <= 13:
        digits = "62" + digits
    elif digits.startswith("0") and len(digits) >= 9:
        digits = "62" + digits[1:]
    return digits


def compute_priority_score(
    website_url: str | None,
    rating: float | None = None,
    review_count: int = 0,
) -> tuple[int, int, str]:
    """Return (has_website, priority_score, default_ux_flaw)."""
    url = (website_url or "").strip().lower()
    weak_hosts = (
        "linktr.ee",
        "linktree",
        "bit.ly",
        "beacons.ai",
        "carrd.co",
        "facebook.com",
        "instagram.com",
        "business.site",
        "blogspot.",
        "wordpress.com",
        "wixsite.com",
        "wa.me",
        "desty.page",
        "taplink",
        "lynk.id",
    )

    if not url:
        has_website = 0
        score = 80
        flaw = "Belum punya website resmi—pengunjung dari Maps & IG belum punya halaman info yang rapi."
    elif any(host in url for host in weak_hosts):
        has_website = 1
        score = 65
        flaw = "Masih mengandalkan link aggregator/sosmed, belum ada halaman web khusus yang tenang & cepat di HP."
    else:
        has_website = 1
        score = 40
        flaw = "Tampilan mobile masih bisa dirapikan supaya katalog layanan dan tombol WA langsung ketemu dalam 3 detik."

    if rating and rating >= 4.4:
        score += 10
    if review_count and review_count >= 50:
        score += 10
    elif review_count and review_count >= 15:
        score += 5

    return has_website, min(score, 100), flaw


@contextmanager
def get_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or settings.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_CREATE_LEADS_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    business_name TEXT NOT NULL,
    anonymized_name TEXT DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Bisnis Lokal',
    design_style TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    phone_raw TEXT DEFAULT '',
    phone_wa TEXT DEFAULT '',
    website_url TEXT DEFAULT '',
    instagram_handle TEXT DEFAULT '',
    rating REAL,
    review_count INTEGER DEFAULT 0,
    has_website INTEGER DEFAULT 0,
    priority_score INTEGER DEFAULT 50,
    ig_observation TEXT DEFAULT '',
    ux_flaw TEXT DEFAULT '',
    concept_preview_path TEXT DEFAULT '',
    demo_path TEXT DEFAULT '',
    demo_url TEXT DEFAULT '',
    carousel_dir TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'NEW'
        CHECK (status IN (
            'NEW', 'CONCEPT_READY', 'CONTACTED_DM', 'CONTACTED_CALL',
            'IGNORED_48H', 'INTERESTED', 'FULL_DEMO_READY',
            'DP_PAID', 'WON', 'RECYCLED_CONTENT'
        )),
    contacted_at TEXT,
    follow_up_due_at TEXT,
    follow_up_sent_at TEXT,
    is_anonymized INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    source_query TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority_score DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_followup ON leads(follow_up_due_at);")


_CREATE_CONTENT_REVIEW_TABLES_SQL = (
    """
    CREATE TABLE IF NOT EXISTS content_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER UNIQUE NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
        source TEXT NOT NULL DEFAULT 'recycled_lead',
        review_status TEXT NOT NULL DEFAULT 'draft_brief'
            CHECK (review_status IN (
                'draft_brief', 'pending_review', 'changes_requested', 'revised', 'approved', 'posted'
            )),
        content_format TEXT NOT NULL DEFAULT 'carousel'
            CHECK (content_format IN ('carousel', 'reels')),
        art_direction_preset TEXT NOT NULL DEFAULT 'auto',
        sequence_type TEXT NOT NULL DEFAULT 'auto',
        voice_id TEXT NOT NULL DEFAULT 'auto',
        hook_pattern_id TEXT NOT NULL DEFAULT 'auto',
        audio_mode TEXT NOT NULL DEFAULT 'voiceover_and_music',
        creative_note TEXT NOT NULL DEFAULT '',
        current_version INTEGER NOT NULL DEFAULT 0,
        approved_version INTEGER,
        approved_by TEXT NOT NULL DEFAULT '',
        approved_at TEXT,
        posted_at TEXT,
        posted_url TEXT NOT NULL DEFAULT '',
        posted_by TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS content_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL REFERENCES content_reviews(id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL,
        content_format TEXT NOT NULL DEFAULT 'carousel',
        caption TEXT NOT NULL DEFAULT '',
        hashtags TEXT NOT NULL DEFAULT '',
        slides_dir TEXT NOT NULL,
        config_json TEXT NOT NULL DEFAULT '{}',
        beat_script_json TEXT NOT NULL DEFAULT '[]',
        qa_report_json TEXT NOT NULL DEFAULT '{}',
        leak_check_json TEXT NOT NULL DEFAULT '{}',
        created_by TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        UNIQUE (review_id, version_number)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS content_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL REFERENCES content_reviews(id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL,
        slide_index INTEGER,
        note TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'resolved')),
        created_by TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        resolved_by TEXT NOT NULL DEFAULT '',
        resolved_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS content_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL REFERENCES content_reviews(id) ON DELETE CASCADE,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS content_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL REFERENCES content_reviews(id) ON DELETE CASCADE,
        author TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'reviewer')),
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
)


def _create_review_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_reviews_status ON content_reviews(review_status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_versions_review ON content_versions(review_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_corrections_review ON content_corrections(review_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_corrections_status ON content_corrections(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_activity_review ON content_activity(review_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_comments_review ON content_comments(review_id);")


def migrate_review_tables_up(conn: sqlite3.Connection) -> None:
    """Safe idempotent migration adding/upgrading content review & publish tables without touching `leads`."""
    for ddl in _CREATE_CONTENT_REVIEW_TABLES_SQL:
        conn.execute(ddl)

    # Upgrade legacy `content_reviews` table (missing `draft_brief` CHECK or brief config columns) without losing data
    row_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'content_reviews'"
    ).fetchone()
    table_sql = str(row_sql["sql"] or "") if row_sql else ""
    rev_cols = {r["name"] for r in conn.execute("PRAGMA table_info(content_reviews)").fetchall()}
    needs_rebuild = ("'draft_brief'" not in table_sql) or ("content_format" not in rev_cols)
    if needs_rebuild:
        fk_prev = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.execute("PRAGMA foreign_keys=OFF;")
        conn.execute("DROP TABLE IF EXISTS content_reviews_migrated;")
        conn.execute(
            """
            CREATE TABLE content_reviews_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER UNIQUE NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                source TEXT NOT NULL DEFAULT 'recycled_lead',
                review_status TEXT NOT NULL DEFAULT 'draft_brief'
                    CHECK (review_status IN (
                        'draft_brief', 'pending_review', 'changes_requested', 'revised', 'approved', 'posted'
                    )),
                content_format TEXT NOT NULL DEFAULT 'carousel'
                    CHECK (content_format IN ('carousel', 'reels')),
                art_direction_preset TEXT NOT NULL DEFAULT 'auto',
                sequence_type TEXT NOT NULL DEFAULT 'auto',
                voice_id TEXT NOT NULL DEFAULT 'auto',
                hook_pattern_id TEXT NOT NULL DEFAULT 'auto',
                creative_note TEXT NOT NULL DEFAULT '',
                current_version INTEGER NOT NULL DEFAULT 0,
                approved_version INTEGER,
                approved_by TEXT NOT NULL DEFAULT '',
                approved_at TEXT,
                posted_at TEXT,
                posted_url TEXT NOT NULL DEFAULT '',
                posted_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        fmt_expr = "content_format" if "content_format" in rev_cols else "'carousel'"
        ad_expr = "art_direction_preset" if "art_direction_preset" in rev_cols else "'auto'"
        seq_expr = "sequence_type" if "sequence_type" in rev_cols else "'auto'"
        voice_expr = "voice_id" if "voice_id" in rev_cols else "'auto'"
        hook_expr = "hook_pattern_id" if "hook_pattern_id" in rev_cols else "'auto'"
        note_expr = "creative_note" if "creative_note" in rev_cols else "''"
        conn.execute(
            f"""
            INSERT INTO content_reviews_migrated (
                id, lead_id, source, review_status,
                content_format, art_direction_preset, sequence_type,
                voice_id, hook_pattern_id, creative_note,
                current_version, approved_version, approved_by, approved_at,
                posted_at, posted_url, posted_by, created_at, updated_at
            )
            SELECT
                id, lead_id, source, review_status,
                {fmt_expr}, {ad_expr}, {seq_expr},
                {voice_expr}, {hook_expr}, {note_expr},
                current_version, approved_version, approved_by, approved_at,
                posted_at, posted_url, posted_by, created_at, updated_at
            FROM content_reviews;
            """
        )
        conn.execute("DROP TABLE content_reviews;")
        conn.execute("ALTER TABLE content_reviews_migrated RENAME TO content_reviews;")
        conn.execute(f"PRAGMA foreign_keys={'ON' if fk_prev else 'OFF'};")

    rev_cols_after = {r["name"] for r in conn.execute("PRAGMA table_info(content_reviews)").fetchall()}
    if "audio_mode" not in rev_cols_after:
        conn.execute("ALTER TABLE content_reviews ADD COLUMN audio_mode TEXT NOT NULL DEFAULT 'voiceover_and_music';")

    ver_cols = {r["name"] for r in conn.execute("PRAGMA table_info(content_versions)").fetchall()}
    if "content_format" not in ver_cols:
        conn.execute("ALTER TABLE content_versions ADD COLUMN content_format TEXT NOT NULL DEFAULT 'carousel';")
    if "config_json" not in ver_cols:
        conn.execute("ALTER TABLE content_versions ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}';")
    if "beat_script_json" not in ver_cols:
        conn.execute("ALTER TABLE content_versions ADD COLUMN beat_script_json TEXT NOT NULL DEFAULT '[]';")

    _create_review_indexes(conn)


def migrate_review_tables_down(db_path: Path | None = None) -> None:
    """Reversible rollback dropping only the 5 content review tables (preserves `leads` intact)."""
    with get_conn(db_path) as conn:
        for tbl in (
            "content_comments",
            "content_activity",
            "content_corrections",
            "content_versions",
            "content_reviews",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {tbl};")


_CREATE_AUTH_TABLES_SQL = (
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        token_hash TEXT PRIMARY KEY,
        role TEXT NOT NULL CHECK (role IN ('admin', 'reviewer')),
        username TEXT NOT NULL,
        ip_address TEXT NOT NULL DEFAULT '',
        user_agent TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_key TEXT NOT NULL,
        attempted_at TEXT NOT NULL
    );
    """,
)


def migrate_auth_tables_up(conn: sqlite3.Connection) -> None:
    """Safe idempotent migration adding `auth_sessions` (with `last_seen_at`) and `login_attempts`."""
    for ddl in _CREATE_AUTH_TABLES_SQL:
        conn.execute(ddl)
    # Safe column migration if auth_sessions existed without last_seen_at
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(auth_sessions)").fetchall()}
    if "last_seen_at" not in cols:
        conn.execute("ALTER TABLE auth_sessions ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT '';")
        conn.execute("UPDATE auth_sessions SET last_seen_at = created_at WHERE last_seen_at = '';")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_login_attempts_key_time ON login_attempts(attempt_key, attempted_at);")


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def create_auth_session(
    raw_token: str,
    role: str,
    username: str,
    ttl_seconds: int,
    ip_address: str = "",
    user_agent: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    now_iso = now.isoformat(timespec="seconds")
    expires_iso = (now + timedelta(seconds=int(ttl_seconds))).isoformat(timespec="seconds")
    token_hash = hash_session_token(raw_token)
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now_iso,))
        conn.execute(
            """
            INSERT INTO auth_sessions (
                token_hash, role, username, ip_address, user_agent,
                created_at, last_seen_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token_hash,
                role,
                username,
                ip_address[:128],
                user_agent[:256],
                now_iso,
                now_iso,
                expires_iso,
            ),
        )
    return {
        "token_hash": token_hash,
        "role": role,
        "username": username,
        "created_at": now_iso,
        "last_seen_at": now_iso,
        "expires_at": expires_iso,
    }


def get_auth_session(raw_token: str, db_path: Path | None = None) -> dict[str, Any] | None:
    if not raw_token:
        return None
    token_hash = hash_session_token(raw_token)
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM auth_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return _row_to_dict(row)


def touch_auth_session(
    raw_token: str,
    new_expires_at: str,
    new_last_seen_at: str,
    db_path: Path | None = None,
) -> None:
    token_hash = hash_session_token(raw_token)
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = ?, expires_at = ? WHERE token_hash = ?",
            (new_last_seen_at, new_expires_at, token_hash),
        )


def delete_auth_session(raw_token: str, db_path: Path | None = None) -> None:
    if not raw_token:
        return
    token_hash = hash_session_token(raw_token)
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))


def record_failed_login(attempt_keys: list[str], db_path: Path | None = None) -> None:
    now_iso = iso_now()
    with get_conn(db_path) as conn:
        for key in attempt_keys:
            if key:
                conn.execute(
                    "INSERT INTO login_attempts (attempt_key, attempted_at) VALUES (?, ?)",
                    (key[:160], now_iso),
                )


def get_login_lockout_remaining(
    attempt_keys: list[str],
    max_attempts: int | None = None,
    window_seconds: int | None = None,
    db_path: Path | None = None,
) -> int:
    """Return remaining lockout seconds (>0 if locked out), pruning expired attempts."""
    limit = max_attempts if max_attempts is not None else settings.LOGIN_MAX_ATTEMPTS
    window = window_seconds if window_seconds is not None else settings.LOGIN_WINDOW_SECONDS
    now = utc_now()
    cutoff_iso = (now - timedelta(seconds=window)).isoformat(timespec="seconds")

    max_remaining = 0
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff_iso,))
        for key in attempt_keys:
            if not key:
                continue
            rows = conn.execute(
                """
                SELECT attempted_at FROM login_attempts
                WHERE attempt_key = ? AND attempted_at >= ?
                ORDER BY attempted_at ASC
                """,
                (key[:160], cutoff_iso),
            ).fetchall()
            if len(rows) >= limit:
                oldest_str = rows[0]["attempted_at"]
                try:
                    oldest_dt = datetime.fromisoformat(oldest_str)
                    if oldest_dt.tzinfo is None:
                        oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
                    unlock_at = oldest_dt + timedelta(seconds=window)
                    rem = max(1, int((unlock_at - now).total_seconds()))
                    if rem > max_remaining:
                        max_remaining = rem
                except ValueError:
                    max_remaining = max(max_remaining, window)
    return max_remaining


def clear_login_attempts(attempt_keys: list[str], db_path: Path | None = None) -> None:
    with get_conn(db_path) as conn:
        for key in attempt_keys:
            if key:
                conn.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (key[:160],))


def _migrate_if_needed(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'"
    ).fetchone()
    if row is None:
        return
    table_sql = row["sql"] or ""
    if "CONCEPT_READY" in table_sql and "DP_PAID" in table_sql and "design_style" in table_sql:
        return

    existing_cols = {
        r["name"] for r in conn.execute("PRAGMA table_info(leads)").fetchall()
    }
    conn.execute("ALTER TABLE leads RENAME TO leads_legacy_backup;")
    conn.execute(_CREATE_LEADS_SQL)

    old_rows = conn.execute("SELECT * FROM leads_legacy_backup").fetchall()
    for r in old_rows:
        rd = dict(r)
        raw_status = (rd.get("status") or "NEW").upper()
        mapped_status = LEGACY_STATUS_MAP.get(raw_status, raw_status)
        if mapped_status not in VALID_STATUSES:
            mapped_status = "NEW"

        conn.execute(
            """
            INSERT INTO leads (
                id, slug, business_name, anonymized_name, category, design_style,
                address, city, phone_raw, phone_wa, website_url, instagram_handle,
                rating, review_count, has_website, priority_score, ig_observation,
                ux_flaw, concept_preview_path, demo_path, demo_url, carousel_dir,
                status, contacted_at, follow_up_due_at, follow_up_sent_at,
                is_anonymized, notes, source_query, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            (
                rd["id"],
                rd["slug"],
                rd["business_name"],
                rd.get("anonymized_name", ""),
                rd.get("category", "Bisnis Lokal"),
                rd.get("design_style", "") if "design_style" in existing_cols else "",
                rd.get("address", ""),
                rd.get("city", ""),
                rd.get("phone_raw", ""),
                rd.get("phone_wa", ""),
                rd.get("website_url", ""),
                rd.get("instagram_handle", ""),
                rd.get("rating"),
                rd.get("review_count", 0),
                rd.get("has_website", 0),
                rd.get("priority_score", 50),
                rd.get("ig_observation", ""),
                rd.get("ux_flaw", ""),
                rd.get("concept_preview_path", "") if "concept_preview_path" in existing_cols else "",
                rd.get("demo_path", ""),
                rd.get("demo_url", ""),
                rd.get("carousel_dir", ""),
                mapped_status,
                rd.get("contacted_at"),
                rd.get("follow_up_due_at"),
                rd.get("follow_up_sent_at"),
                rd.get("is_anonymized", 0),
                rd.get("notes", ""),
                rd.get("source_query", ""),
                rd.get("created_at") or iso_now(),
                rd.get("updated_at") or iso_now(),
            ),
        )
    conn.execute("DROP TABLE leads_legacy_backup;")


def init_db(db_path: Path | None = None) -> None:
    with get_conn(db_path) as conn:
        _migrate_if_needed(conn)
        conn.execute(_CREATE_LEADS_SQL)
        # Ensure optional `ig_observation` column exists on any legacy DB
        lead_cols = {r["name"] for r in conn.execute("PRAGMA table_info(leads)").fetchall()}
        if "ig_observation" not in lead_cols:
            conn.execute("ALTER TABLE leads ADD COLUMN ig_observation TEXT DEFAULT '';")
        _create_indexes(conn)
        migrate_review_tables_up(conn)
        migrate_auth_tables_up(conn)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _unique_slug(conn: sqlite3.Connection, base_slug: str) -> str:
    slug = base_slug
    idx = 2
    while conn.execute("SELECT 1 FROM leads WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{idx}"
        idx += 1
    return slug


def normalize_status(status: str) -> str:
    up = str(status or "NEW").strip().upper()
    up = LEGACY_STATUS_MAP.get(up, up)
    if up not in VALID_STATUSES:
        raise ValueError(f"Status tidak valid: {status}")
    return up


def upsert_lead(data: dict[str, Any], db_path: Path | None = None) -> tuple[dict[str, Any], bool]:
    """Insert or update a lead with deduplication by slug, normalized phone, or business_name."""
    business_name = (data.get("business_name") or "").strip()
    if not business_name:
        raise ValueError("business_name wajib diisi.")

    phone_raw = (data.get("phone_raw") or data.get("phone") or "").strip()
    phone_wa = normalize_indo_phone(data.get("phone_wa") or phone_raw)
    website_url = (data.get("website_url") or "").strip()
    rating = data.get("rating")
    try:
        rating = float(rating) if rating not in (None, "") else None
    except (TypeError, ValueError):
        rating = None
    try:
        review_count = int(data.get("review_count") or 0)
    except (TypeError, ValueError):
        review_count = 0

    has_website, auto_score, default_flaw = compute_priority_score(website_url, rating, review_count)
    priority_score = int(data.get("priority_score") or auto_score)
    ux_flaw = (data.get("ux_flaw") or "").strip() or default_flaw
    category = (data.get("category") or "Bisnis Lokal").strip() or "Bisnis Lokal"
    design_style = (data.get("design_style") or "").strip()
    requested_slug = slugify(data.get("slug") or business_name)
    now = iso_now()
    status = normalize_status(data.get("status") or "NEW")

    with get_conn(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM leads WHERE slug = ? OR lower(business_name) = lower(?)",
            (requested_slug, business_name),
        ).fetchone()
        if existing is None and phone_wa:
            existing = conn.execute(
                "SELECT * FROM leads WHERE phone_wa = ? AND phone_wa != ''",
                (phone_wa,),
            ).fetchone()

        if existing is not None:
            lead_id = existing["id"]
            conn.execute(
                """
                UPDATE leads
                SET category = COALESCE(NULLIF(?, ''), category),
                    design_style = COALESCE(NULLIF(?, ''), design_style),
                    address = COALESCE(NULLIF(?, ''), address),
                    city = COALESCE(NULLIF(?, ''), city),
                    phone_raw = COALESCE(NULLIF(?, ''), phone_raw),
                    phone_wa = COALESCE(NULLIF(?, ''), phone_wa),
                    website_url = COALESCE(NULLIF(?, ''), website_url),
                    instagram_handle = COALESCE(NULLIF(?, ''), instagram_handle),
                    rating = COALESCE(?, rating),
                    review_count = CASE WHEN ? > review_count THEN ? ELSE review_count END,
                    has_website = ?,
                    priority_score = ?,
                    ig_observation = COALESCE(NULLIF(?, ''), ig_observation),
                    ux_flaw = COALESCE(NULLIF(?, ''), ux_flaw),
                    source_query = COALESCE(NULLIF(?, ''), source_query),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    category,
                    design_style,
                    (data.get("address") or "").strip(),
                    (data.get("city") or "").strip(),
                    phone_raw,
                    phone_wa,
                    website_url,
                    (data.get("instagram_handle") or "").strip(),
                    rating,
                    review_count,
                    review_count,
                    has_website,
                    priority_score,
                    (data.get("ig_observation") or "").strip(),
                    ux_flaw,
                    (data.get("source_query") or "").strip(),
                    now,
                    lead_id,
                ),
            )
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
            return dict(row), False

        final_slug = _unique_slug(conn, requested_slug)
        cursor = conn.execute(
            """
            INSERT INTO leads (
                slug, business_name, anonymized_name, category, design_style,
                address, city, phone_raw, phone_wa, website_url, instagram_handle,
                rating, review_count, has_website, priority_score, ig_observation,
                ux_flaw, concept_preview_path, demo_path, demo_url, carousel_dir,
                status, notes, source_query, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            (
                final_slug,
                business_name,
                (data.get("anonymized_name") or "").strip(),
                category,
                design_style,
                (data.get("address") or "").strip(),
                (data.get("city") or settings.DEFAULT_CITY).strip(),
                phone_raw,
                phone_wa,
                website_url,
                (data.get("instagram_handle") or "").strip(),
                rating,
                review_count,
                has_website,
                priority_score,
                (data.get("ig_observation") or "").strip(),
                ux_flaw,
                (data.get("concept_preview_path") or "").strip(),
                (data.get("demo_path") or "").strip(),
                (data.get("demo_url") or "").strip(),
                (data.get("carousel_dir") or "").strip(),
                status,
                (data.get("notes") or "").strip(),
                (data.get("source_query") or "").strip(),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row), True


def get_lead(lead_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return _row_to_dict(row)


def delete_lead(lead_id: int, db_path: Path | None = None) -> bool:
    """Delete a lead row by ID (cascades any review rows if present)."""
    with get_conn(db_path) as conn:
        cursor = conn.execute("DELETE FROM leads WHERE id = ?", (int(lead_id),))
        return cursor.rowcount > 0


def get_lead_by_slug(slug: str, db_path: Path | None = None) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM leads WHERE slug = ?", (slug,)).fetchone()
        return _row_to_dict(row)


def list_leads(
    statuses: list[str] | tuple[str, ...] | None = None,
    search: str | None = None,
    limit: int | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if statuses:
        clean_statuses = []
        for s in statuses:
            try:
                clean_statuses.append(normalize_status(s))
            except ValueError:
                continue
        if not clean_statuses:
            return []
        placeholders = ", ".join("?" for _ in clean_statuses)
        clauses.append(f"status IN ({placeholders})")
        params.extend(clean_statuses)

    if search:
        pattern = f"%{search.strip()}%"
        clauses.append("(business_name LIKE ? OR category LIKE ? OR city LIKE ? OR notes LIKE ?)")
        params.extend([pattern, pattern, pattern, pattern])

    sql = "SELECT * FROM leads"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY priority_score DESC, updated_at DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    with get_conn(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def update_lead(lead_id: int, fields: dict[str, Any], db_path: Path | None = None) -> dict[str, Any] | None:
    if not fields:
        return get_lead(lead_id, db_path=db_path)

    clean: dict[str, Any] = {}
    for key, val in fields.items():
        if key not in ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field tidak diizinkan untuk update: {key}")
        if key == "status":
            val = normalize_status(str(val))
        if key == "phone_raw" and val:
            clean.setdefault("phone_wa", normalize_indo_phone(str(val)))
        if key == "phone_wa" and val:
            val = normalize_indo_phone(str(val))
        clean[key] = val

    clean["updated_at"] = iso_now()

    assignments = ", ".join(f"{col} = ?" for col in clean.keys())
    values = list(clean.values()) + [lead_id]

    with get_conn(db_path) as conn:
        conn.execute(f"UPDATE leads SET {assignments} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return _row_to_dict(row)


def mark_contacted(
    lead_id: int,
    method: str,
    hours: int | None = None,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Mark a lead as CONTACTED_CALL or CONTACTED_DM and start the 48h follow-up timer."""
    status = normalize_status(method)
    if status not in {"CONTACTED_CALL", "CONTACTED_DM"}:
        raise ValueError("Method harus CONTACTED_CALL atau CONTACTED_DM.")

    now = utc_now()
    due = now + timedelta(hours=hours if hours is not None else settings.FOLLOW_UP_HOURS)
    return update_lead(
        lead_id,
        {
            "status": status,
            "contacted_at": now.isoformat(timespec="seconds"),
            "follow_up_due_at": due.isoformat(timespec="seconds"),
        },
        db_path=db_path,
    )


def refresh_expired_followups(db_path: Path | None = None) -> int:
    """Auto-flip CONTACTED_CALL / CONTACTED_DM leads past follow_up_due_at to IGNORED_48H and sync copy outcome."""
    now_iso = iso_now()
    expired_ids: list[int] = []
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id FROM leads
            WHERE status IN ('CONTACTED_CALL', 'CONTACTED_DM')
              AND follow_up_due_at IS NOT NULL
              AND follow_up_due_at <= ?
            """,
            (now_iso,),
        ).fetchall()
        expired_ids = [int(r["id"]) for r in rows]
        if expired_ids:
            conn.execute(
                """
                UPDATE leads
                SET status = 'IGNORED_48H', updated_at = ?
                WHERE status IN ('CONTACTED_CALL', 'CONTACTED_DM')
                  AND follow_up_due_at IS NOT NULL
                  AND follow_up_due_at <= ?
                """,
                (now_iso, now_iso),
            )
    if expired_ids:
        try:
            from creative_agent.copy_engine import update_copy_outcome
            for lid in expired_ids:
                update_copy_outcome(lid, "ignored_48h")
        except Exception:
            pass
    return len(expired_ids)


def get_pipeline_stats(db_path: Path | None = None) -> dict[str, int]:
    counts = {status: 0 for status in settings.LEAD_STATUSES}
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM leads GROUP BY status").fetchall()
        for r in rows:
            if r["status"] in counts:
                counts[r["status"]] = int(r["cnt"])
    counts["TOTAL"] = sum(counts.values())
    return counts


def get_review_counts(db_path: Path | None = None) -> dict[str, int]:
    counts = {st: 0 for st in settings.REVIEW_STATUSES}
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT review_status, COUNT(*) AS cnt FROM content_reviews GROUP BY review_status"
        ).fetchall()
        for r in rows:
            if r["review_status"] in counts:
                counts[r["review_status"]] = int(r["cnt"])
    counts["needs_attention"] = (
        counts["draft_brief"]
        + counts["pending_review"]
        + counts["changes_requested"]
        + counts["revised"]
    )
    return counts


def get_review_by_lead(lead_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)
        ).fetchone()
        return _row_to_dict(row)


if __name__ == "__main__":
    init_db()
    print(f"[OK] SQLite initialized & migrated at {settings.DB_PATH}")
