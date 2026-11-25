"""3-Tab Mobile Mini App & 2-Stage Automation API for @goandalan (FastAPI)."""

from __future__ import annotations

import hmac
import secrets
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

import carousel_generator as cg
import content_review as cr
import database as db
import demo_generator as dg
import scraper as gmaps_scraper
from config import settings
from creative_agent import copy_engine, lead_enricher

db.init_db()
dg.rebuild_portfolio_index()

app = FastAPI(
    title="@goandalan — 2-Stage Outreach & Multi-Style Demo Mini App",
    version="2.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

if settings.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.CORS_ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
app.mount("/demos", StaticFiles(directory=str(settings.DEMOS_DIR), html=True), name="demos")
app.mount("/portfolio", StaticFiles(directory=str(settings.SITE_DIR), html=True), name="portfolio")

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

REVIEWER_ALLOWED_LEAD_STATUSES = {
    "NEW",
    "CONCEPT_READY",
    "CONTACTED_DM",
    "CONTACTED_CALL",
    "IGNORED_48H",
    "INTERESTED",
    "DP_PAID",
    "WON",
    "RECYCLED_CONTENT",
}

_BLOCKED_PATH_SEGMENTS = (
    "/.env",
    ".env.",
    "leads.db",
    ".sqlite",
    "/skills/",
    "/creative_agent/",
    "/templates/",
    "/.git",
    "/reviews/",
)


def _is_https(request: Request) -> bool:
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return settings.HTTPS_ENABLED or proto == "https" or request.url.scheme == "https"


def _client_ip(request: Request) -> str:
    cf_ip = (request.headers.get("cf-connecting-ip") or "").strip()
    if cf_ip:
        return cf_ip[:64]
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return "unknown"


def _set_session_cookie(response: Response, request: Request, raw_token: str, max_age: int) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=int(max_age),
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
    )


def _is_same_origin(origin: str, request: Request) -> bool:
    clean_origin = origin.strip().rstrip("/")
    if not clean_origin:
        return True
    if clean_origin in settings.CORS_ALLOWED_ORIGINS:
        return True
    try:
        parsed_origin = urlparse(clean_origin)
        req_host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
        return parsed_origin.netloc.lower() == req_host.lower() and parsed_origin.scheme in {"http", "https"}
    except Exception:
        return False


@app.middleware("http")
async def security_headers_and_guard_middleware(request: Request, call_next):
    raw_path = (request.url.path or "").lower()
    if (
        ".." in raw_path
        or raw_path.endswith(".py")
        or raw_path.endswith(".db")
        or raw_path.endswith(".db-wal")
        or raw_path.endswith(".db-shm")
        or raw_path.endswith(".env")
        or any(seg in raw_path for seg in _BLOCKED_PATH_SEGMENTS)
    ):
        resp = JSONResponse({"detail": "Akses ditolak."}, status_code=403)
    elif (
        raw_path.startswith("/api/")
        and request.method.upper() in {"POST", "PATCH", "PUT", "DELETE"}
        and request.cookies.get(settings.SESSION_COOKIE_NAME)
        and request.headers.get("origin")
        and not _is_same_origin(request.headers.get("origin") or "", request)
    ):
        resp = JSONResponse({"detail": "Permintaan lintas-origin (CSRF) ditolak."}, status_code=403)
    else:
        try:
            resp = await call_next(request)
        except Exception:
            resp = JSONResponse(
                {"detail": "Terjadi kesalahan internal server."},
                status_code=500,
            )

    if getattr(request.state, "clear_session_cookie", False):
        _clear_session_cookie(resp, request)
    elif getattr(request.state, "renew_session_cookie", None):
        raw_tok, ttl_sec = request.state.renew_session_cookie
        _set_session_cookie(resp, request, raw_tok, ttl_sec)

    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if raw_path.startswith("/demos/") or raw_path.startswith("/portfolio/"):
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
    else:
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    if raw_path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, private"
    return resp


class LeadCreatePayload(BaseModel):
    business_name: str = Field(..., min_length=1)
    category: str = "Bisnis Lokal"
    design_style: str = ""
    city: str = ""
    address: str = ""
    phone_raw: str = ""
    website_url: str = ""
    instagram_handle: str = ""
    ig_observation: str = ""
    ux_flaw: str = ""
    auto_generate: bool = False
    queue_for_dm: bool = True


class LeadUpdatePayload(BaseModel):
    business_name: str | None = None
    category: str | None = None
    design_style: str | None = None
    city: str | None = None
    address: str | None = None
    phone_raw: str | None = None
    website_url: str | None = None
    instagram_handle: str | None = None
    ig_observation: str | None = None
    ux_flaw: str | None = None
    notes: str | None = None
    status: str | None = None


class ContactPayload(BaseModel):
    method: str = Field(..., pattern="^(CONTACTED_CALL|CONTACTED_DM)$")


class StatusPayload(BaseModel):
    status: str
    ig_observation: str | None = None


class CopyLogPayload(BaseModel):
    lead_id: int
    channel: str = Field(..., pattern="^(cold_dm_1|followup|cold_call|caption)$")
    original_draft: str = ""
    final_text: str = Field(..., min_length=1)
    voice: str = ""
    sapaan: str = ""
    patterns_used: list[str] = Field(default_factory=list)
    levers: list[str] = Field(default_factory=list)
    exploration_candidate: str = ""
    notes: str = ""


class CaptionCopiedPayload(BaseModel):
    original_draft: str = ""
    final_text: str = ""
    patterns_used: list[str] = Field(default_factory=list)


class StyleOverridePayload(BaseModel):
    design_style: str | None = None
    production: bool = False


class ScrapeJobPayload(BaseModel):
    query: str = Field(..., min_length=2)
    limit: int = Field(default=6, ge=1, le=30)
    city: str = ""
    auto_generate: bool = False
    auto_enrich: bool = True


class BatchGeneratePayload(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)


class LoginPayload(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class SubmitReviewPayload(BaseModel):
    note: str = ""
    source: str = "recycled_lead"


class ContentGeneratePayload(BaseModel):
    content_format: str = "carousel"
    art_direction_preset: str = "auto"
    sequence_type: str = "auto"
    voice_id: str = "auto"
    hook_pattern_id: str = "auto"
    audio_mode: str = "voiceover_and_music"
    motion_intensity: str = "auto"
    target_duration: float = 10.0
    vo_script: str = ""
    vo_style: str = "auto"
    bgm_track: str = "auto"
    creative_note: str = ""
    note: str = ""


class ReelsIdeasScrapePayload(BaseModel):
    topic: str = ""
    limit: int = Field(default=3, ge=1, le=4)


class PostedMetricsPayload(BaseModel):
    views: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    dm_in: int = Field(default=0, ge=0)


class CorrectionItemPayload(BaseModel):
    slide_index: int | None = None
    note: str = Field(..., min_length=1)


class CorrectionsRequestPayload(BaseModel):
    corrections: list[CorrectionItemPayload] = Field(..., min_length=1)
    expected_status: str | None = None


class ApprovePayload(BaseModel):
    expected_status: str | None = None
    expected_version: int | None = None


class PostedPayload(BaseModel):
    posted_url: str = ""
    posted_at: str | None = None
    expected_status: str | None = None


class CommentPayload(BaseModel):
    body: str = Field(..., min_length=1)


def _format_retry_wait(seconds: int) -> str:
    mins, secs = divmod(max(1, int(seconds)), 60)
    if mins > 0:
        return f"{mins} menit {secs} detik"
    return f"{secs} detik"


def _verify_credentials(username: str, password: str) -> tuple[str | None, str, str | None]:
    """Fail-closed constant-time verification against `.env` credentials.

    Returns `(role, canonical_username, config_error)`. Never prints or logs secrets.
    """
    admin_configured = bool(settings.ADMIN_USN and settings.ADMIN_PASS)
    review_configured = bool(settings.REVIEW_USN and settings.REVIEW_PASS)
    if not admin_configured and not review_configured:
        return None, "", "Kredensial login belum dikonfigurasi pada file .env server."

    in_user = (username or "").strip()
    in_pass = password or ""

    dummy_u = "__unconfigured_account_placeholder__"
    dummy_p = "__unconfigured_password_placeholder__"

    admin_u_ok = hmac.compare_digest(in_user, settings.ADMIN_USN if admin_configured else dummy_u)
    admin_p_ok = hmac.compare_digest(in_pass, settings.ADMIN_PASS if admin_configured else dummy_p)
    review_u_ok = hmac.compare_digest(in_user, settings.REVIEW_USN if review_configured else dummy_u)
    review_p_ok = hmac.compare_digest(in_pass, settings.REVIEW_PASS if review_configured else dummy_p)

    if admin_configured and admin_u_ok and admin_p_ok:
        return "admin", settings.ADMIN_USN, None
    if review_configured and review_u_ok and review_p_ok:
        return "reviewer", settings.REVIEW_USN, None
    return None, "", None


def _validate_session_cookie(request: Request) -> dict[str, Any]:
    """Validate HttpOnly session cookie against SQLite, enforcing expiry and 7-day sliding renewal for reviewer."""
    raw_token = (request.cookies.get(settings.SESSION_COOKIE_NAME) or "").strip()
    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Silakan masuk terlebih dahulu menggunakan akun Admin atau Reviewer.",
        )

    sess = db.get_auth_session(raw_token)
    if not sess:
        request.state.clear_session_cookie = True
        raise HTTPException(
            status_code=401,
            detail="Sesi tidak ditemukan atau sudah berakhir. Silakan login kembali.",
        )

    now = db.utc_now()
    expires_dt = _parse_iso(sess.get("expires_at"))
    if expires_dt is None or now >= expires_dt:
        db.delete_auth_session(raw_token)
        request.state.clear_session_cookie = True
        raise HTTPException(
            status_code=401,
            detail="Sesi Anda telah berakhir. Silakan login kembali.",
        )

    role = sess["role"]
    last_seen_iso = sess.get("last_seen_at") or sess.get("created_at")
    expires_iso = sess["expires_at"]

    if role == "reviewer":
        last_seen_dt = _parse_iso(last_seen_iso)
        elapsed = (now - last_seen_dt).total_seconds() if last_seen_dt else settings.SESSION_RENEW_THROTTLE_SECONDS + 1
        if elapsed >= settings.SESSION_RENEW_THROTTLE_SECONDS:
            new_last_seen = now.isoformat(timespec="seconds")
            new_expires = (now + timedelta(seconds=settings.REVIEW_SESSION_TTL_SECONDS)).isoformat(timespec="seconds")
            db.touch_auth_session(raw_token, new_expires_at=new_expires, new_last_seen_at=new_last_seen)
            last_seen_iso = new_last_seen
            expires_iso = new_expires
            request.state.renew_session_cookie = (raw_token, settings.REVIEW_SESSION_TTL_SECONDS)

    return {
        "role": role,
        "username": sess["username"],
        "actor": sess["username"],
        "expires_at": expires_iso,
        "last_seen_at": last_seen_iso,
    }


def require_role(*allowed_roles: str):
    """Server-side session & RBAC dependency reading ONLY the HttpOnly cookie (no URL query tokens)."""

    def _dep(request: Request) -> dict[str, Any]:
        auth = _validate_session_cookie(request)
        if auth["role"] not in allowed_roles:
            expected_label = " / ".join(r.title() for r in allowed_roles)
            raise HTTPException(
                status_code=403,
                detail=f"Akses ditolak: aksi ini hanya diizinkan untuk peran {expected_label}.",
            )
        return auth

    return _dep


def _handle_review_error(exc: Exception) -> None:
    if isinstance(exc, cr.AnonymizationLeakError):
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "leak_report": exc.leak_report},
        ) from exc
    if isinstance(exc, cr.ReviewError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    raise exc


def _build_cold_dm(lead: dict[str, Any]) -> str:
    """Draft Message #1 for Instagram DM — strictly offers CONCEPT PHOTO (no link!), max 1 Alan mention."""
    name = lead["business_name"]
    obs = (lead.get("ig_observation") or "").strip() or "[isi 1 detail spesifik IG mereka]"
    return (
        f"Halo tim {name}, salam kenal! Suka banget sama vibe {name} di IG, apalagi {obs}.\n\n"
        f"Kemarin sempet cari info webnya dan ngerasa sayang aja tampilannya belum sekeren IG-nya. "
        f"Gw sama Alan iseng bikin konsep halaman depannya yang lebih rapi & enak dibuka di HP—"
        f"santuy aja gak ada kewajiban apa-apa, boleh gw kirim foto preview konsepnya di sini?"
    )


def _build_cold_call_script(lead: dict[str, Any]) -> dict[str, str]:
    name = lead["business_name"]
    flaw = (lead.get("ux_flaw") or "tampilan halaman mobile-nya bisa dibikin jauh lebih gampang dibaca").rstrip(".")
    return {
        "pembuka": (
            f"Halo selamat siang kak, saya dari gw sama Alan. Boleh minta waktu sebentar sekitar 30 detik buat ngobrol "
            f"sama pemilik atau admin {name}?"
        ),
        "inti": (
            f"Singkat aja kak: kemarin saya lihat profil {name} di Google Maps dan IG—tempatnya keren, tapi "
            f"{flaw.lower()}. Jadi saya iseng bikinin foto preview konsep halaman depan versi mobile yang lebih rapi, "
            f"gratis buat dilihat-lihat dulu tanpa komitmen apa-apa."
        ),
        "tutup": (
            f"Kalau kakak berkenan, boleh saya kirim foto preview konsepnya lewat WhatsApp atau DM Instagram @{settings.IG_USERNAME} "
            f"biar bisa dicek pas lagi senggang?"
        ),
    }


def _build_followup_draft(lead: dict[str, Any]) -> str:
    name = lead["business_name"]
    return (
        f"Halo kak, izin bump dikit ya barangkali pesan kemarin tenggelam. "
        f"Foto preview konsep buat {name} masih gw simpan kalau kapan-kapan pengen lihat—gak ada paksaan sama sekali kok. "
        f"Sukses terus buat {name}!"
    )


def _build_requirement_prompt(lead: dict[str, Any]) -> str:
    """Message template sent alongside the 1-page Pre-DP demo link to gather client requirements."""
    name = lead["business_name"]
    return (
        f"Halo kak, ini preview landing page demo 1-halaman buat {name} biar kebayang dulu vibe & tampilannya di HP.\n\n"
        f"Kalau arahnya udah cocok, boleh share detail requirement buat versi website penuhnya ya kak:\n"
        f"1. Daftar menu/layanan + harga final\n"
        f"2. Foto asli tempat/produk (atau link IG/Drive)\n"
        f"3. Jam buka, alamat & nomor WA tujuan\n"
        f"4. Info tambahan atau halaman ekstra yang diinginkan (mis. galeri, cabang, domain)"
    )


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _enrich_lead(lead: dict[str, Any]) -> dict[str, Any]:
    item = dict(lead)
    slug = item["slug"]
    demo_dir = settings.DEMOS_DIR / slug
    ig_dir = demo_dir / "ig"
    full_demo_file = demo_dir / "index.html"
    concept_preview_file = demo_dir / "concept_preview.png"

    style_key, theme = dg.select_style_for_lead(item)
    item["design_style"] = style_key
    item["style_label"] = theme["label"]
    item["style_source"] = theme["source"]

    slides: list[dict[str, str]] = []
    if ig_dir.exists():
        spec_slide_names: list[str] = []
        spec_file = ig_dir / "carousel_spec.json"
        if spec_file.exists():
            import json
            try:
                spec_obj = json.loads(spec_file.read_text(encoding="utf-8"))
                spec_slide_names = [f"{s['name']}.png" for s in spec_obj.get("slides", []) if s.get("name")]
            except Exception:
                spec_slide_names = []
        ordered_names = spec_slide_names or ["01_cover.png", "02_context.png", "03_reveal.png", "04_details.png"]
        for sname in ordered_names:
            spath = ig_dir / sname
            if spath.exists():
                mtime = int(spath.stat().st_mtime)
                slides.append({"name": sname, "url": f"/demos/{slug}/ig/{sname}?v={mtime}"})
        if not slides:
            for spath in sorted(ig_dir.glob("0[1-4]_*.png")):
                mtime = int(spath.stat().st_mtime)
                slides.append({"name": spath.name, "url": f"/demos/{slug}/ig/{spath.name}?v={mtime}"})

    art_direction = None
    art_dir_path = ig_dir / "art_direction.json"
    if art_dir_path.exists():
        import json
        try:
            art_direction = json.loads(art_dir_path.read_text(encoding="utf-8"))
        except Exception:
            art_direction = None
    item["art_direction"] = art_direction

    qa_report = None
    qa_path = ig_dir / "qa_report.json"
    if qa_path.exists():
        import json
        try:
            qa_report = json.loads(qa_path.read_text(encoding="utf-8"))
        except Exception:
            qa_report = None
    item["qa_report"] = qa_report

    contact_sheet_file = ig_dir / "contact_sheet.png"
    cover_grid_file = ig_dir / "cover_grid.png"
    item["contact_sheet_url"] = (
        f"/demos/{slug}/ig/contact_sheet.png?v={int(contact_sheet_file.stat().st_mtime)}"
        if contact_sheet_file.exists()
        else ""
    )
    item["cover_grid_url"] = (
        f"/demos/{slug}/ig/cover_grid.png?v={int(cover_grid_file.stat().st_mtime)}"
        if cover_grid_file.exists()
        else ""
    )

    caption = ""
    caption_path = ig_dir / "caption.txt"
    if caption_path.exists():
        caption = caption_path.read_text(encoding="utf-8")

    due_dt = _parse_iso(item.get("follow_up_due_at"))
    remaining_seconds = 0
    is_overdue = item["status"] == "IGNORED_48H"
    if due_dt is not None:
        diff = int((due_dt - datetime.now(timezone.utc)).total_seconds())
        remaining_seconds = max(0, diff)
        if diff <= 0:
            is_overdue = True

    item["display_name"] = (
        item["anonymized_name"]
        if item.get("is_anonymized") and item.get("anonymized_name")
        else item["business_name"]
    )
    item["has_concept_preview"] = concept_preview_file.exists()
    item["concept_preview_url"] = (
        f"/demos/{slug}/concept_preview.png?v={int(concept_preview_file.stat().st_mtime)}"
        if concept_preview_file.exists()
        else ""
    )
    item["has_full_demo"] = full_demo_file.exists()
    item["demo_href"] = f"/demos/{slug}/index.html" if full_demo_file.exists() else ""
    is_production_demo = False
    if full_demo_file.exists():
        try:
            head_snippet = full_demo_file.read_text(encoding="utf-8", errors="ignore")[:1500]
            is_production_demo = 'content="production-full"' in head_snippet
        except Exception:
            is_production_demo = False
    item["is_production_demo"] = is_production_demo
    item["slides"] = slides
    item["has_carousel"] = len(slides) == 4
    item["caption"] = caption

    dm_pack = copy_engine.draft_cold_dm(item)
    fu_pack = copy_engine.draft_followup(item)
    call_pack = copy_engine.draft_cold_call(item)

    item["cold_dm_draft"] = dm_pack["primary"]
    item["cold_dm_alt"] = dm_pack["alternate"]
    item["cold_dm_meta"] = {
        "voice": dm_pack["voice"],
        "archetype": dm_pack["archetype"],
        "caption_voice": dm_pack["caption_voice"],
        "sapaan": dm_pack["sapaan"],
        "patterns_used": dm_pack["patterns_used"],
        "levers": dm_pack["levers"],
        "needs_observation": dm_pack["needs_observation"],
        "exploration_candidate": dm_pack["exploration_candidate"],
        "validation": dm_pack["validation"],
    }
    item["cold_call_script"] = call_pack
    item["follow_up_draft"] = fu_pack["primary"]
    item["follow_up_meta"] = {
        "voice": fu_pack["voice"],
        "sapaan": fu_pack["sapaan"],
        "patterns_used": fu_pack["patterns_used"],
        "levers": fu_pack["levers"],
        "validation": fu_pack["validation"],
    }
    item["requirement_prompt"] = _build_requirement_prompt(item)
    item["remaining_seconds"] = remaining_seconds
    item["is_overdue"] = is_overdue
    rev = db.get_review_by_lead(item["id"])
    item["review_status"] = rev["review_status"] if rev else ""
    item["review_version"] = int(rev["current_version"]) if rev else 0
    return item


def _set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def _run_scrape_job(job_id: str, payload: ScrapeJobPayload) -> None:
    try:
        _set_job(job_id, status="running", message=f"Scraping Google Maps: '{payload.query}'...")
        res = gmaps_scraper.scrape_google_maps(
            query=payload.query,
            limit=payload.limit,
            city=payload.city,
        )
        enrich_summary: dict[str, Any] = {
            "available": False,
            "processed": 0,
            "updated": 0,
            "ux_flaw_updated": 0,
            "ig_observation_updated": 0,
            "ig_channel_paused": False,
        }
        if payload.auto_enrich and settings.ENABLE_POST_SCRAPE_ENRICHMENT and res["leads"]:
            eligible_ids = [
                int(l["id"])
                for l in res["leads"]
                if l.get("status") == "NEW" and not (l.get("ig_observation") or "").strip()
            ]
            if eligible_ids:
                try:
                    enrich_summary = lead_enricher.enrich_new_leads(
                        lead_ids=eligible_ids,
                        progress_cb=lambda idx, total, lead: _set_job(
                            job_id,
                            message=(
                                f"Enrichment prospek NEW via agent-reach ({idx}/{total}): "
                                f"{lead.get('business_name', '')}..."
                            ),
                        ),
                    )
                except Exception:
                    # Graceful fallback: scrape job stays successful even if enrichment fails
                    pass

        generated = 0
        if payload.auto_generate and res["leads"]:
            total = len(res["leads"])
            for idx, lead in enumerate(res["leads"], start=1):
                _set_job(
                    job_id,
                    message=f"Tahap A — Foto preview & carousel ({idx}/{total}): {lead['business_name']}...",
                )
                cg.generate_concept_package_for_lead(lead["id"], anonymize=False)
                generated += 1

        enrich_note = ""
        if enrich_summary.get("updated", 0) > 0:
            enrich_note = (
                f" Enrichment agent-reach: {enrich_summary['updated']} prospek NEW diperkaya "
                f"(ux_flaw: {enrich_summary['ux_flaw_updated']}, ig_observation: {enrich_summary['ig_observation_updated']})."
            )
        done_msg = (
            f"Selesai! {res['inserted']} baru, {res['updated']} update, "
            f"{generated} foto preview konsep (Tahap A) siap DM.{enrich_note}"
            if generated > 0
            else (
                f"Selesai! {res['inserted']} baru, {res['updated']} update tersimpan (metadata saja, "
                f"tanpa HTML landing page sebelum prospek INTERESTED).{enrich_note}"
            )
        )
        _set_job(
            job_id,
            status="done",
            message=done_msg,
            result={
                "inserted": res["inserted"],
                "updated": res["updated"],
                "generated": generated,
                "enrichment": {
                    "available": enrich_summary.get("available", False),
                    "processed": enrich_summary.get("processed", 0),
                    "updated": enrich_summary.get("updated", 0),
                    "ux_flaw_updated": enrich_summary.get("ux_flaw_updated", 0),
                    "ig_observation_updated": enrich_summary.get("ig_observation_updated", 0),
                    "ig_channel_paused": enrich_summary.get("ig_channel_paused", False),
                },
                "errors": res["errors"],
            },
            finished_at=db.iso_now(),
        )
    except Exception as exc:
        _set_job(job_id, status="error", message=f"Gagal: {exc}", finished_at=db.iso_now())


def _run_batch_generate_job(job_id: str, limit: int) -> None:
    try:
        targets = db.list_leads(statuses=["NEW"], limit=limit)
        if not targets:
            _set_job(job_id, status="done", message="Tidak ada lead berstatus NEW.", finished_at=db.iso_now())
            return

        total = len(targets)
        for idx, lead in enumerate(targets, start=1):
            _set_job(
                job_id,
                status="running",
                message=f"Tahap A — Foto preview ({idx}/{total}): {lead['business_name']}...",
            )
            cg.generate_concept_package_for_lead(lead["id"], anonymize=False)

        _set_job(
            job_id,
            status="done",
            message=f"Berhasil render {total} foto preview konsep + carousel (CONCEPT_READY).",
            finished_at=db.iso_now(),
        )
    except Exception as exc:
        _set_job(job_id, status="error", message=f"Gagal batch generate: {exc}", finished_at=db.iso_now())


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    db.refresh_expired_followups()
    return templates.TemplateResponse(
        request=request,
        name="mini_app.html",
        context={
            "ig_username": settings.IG_USERNAME,
            "ig_handle": settings.IG_HANDLE,
            "ig_url": settings.IG_URL,
            "brand_name": settings.BRAND_NAME,
            "follow_up_hours": settings.FOLLOW_UP_HOURS,
        },
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "brand": settings.BRAND_NAME,
        "ig": settings.IG_HANDLE,
    }


@app.post("/api/auth/login")
@app.post("/api/content/auth/verify")
async def login_account(request: Request) -> JSONResponse:
    """Authenticate Admin or Reviewer using `.env` credentials with rate limit, lockout & HttpOnly cookie."""
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
        form = await request.form()
        username = str(form.get("username") or "").strip()
        password = str(form.get("password") or "")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")

    ip = _client_ip(request)
    attempt_keys = [f"ip:{ip}"]
    if username:
        attempt_keys.append(f"user:{ip}:{username.lower()}")

    lock_rem = db.get_login_lockout_remaining(attempt_keys)
    if lock_rem > 0:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(lock_rem)},
            content={
                "detail": f"Terlalu banyak percobaan login gagal. Coba lagi dalam {_format_retry_wait(lock_rem)}.",
                "retry_after": lock_rem,
            },
        )

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username dan password wajib diisi.")

    role, canonical_username, config_error = _verify_credentials(username, password)
    if config_error:
        raise HTTPException(status_code=503, detail=config_error)

    if not role:
        time.sleep(settings.LOGIN_FAIL_DELAY_SECONDS)
        db.record_failed_login(attempt_keys)
        new_lock = db.get_login_lockout_remaining(attempt_keys)
        if new_lock > 0:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(new_lock)},
                content={
                    "detail": f"Terlalu banyak percobaan login gagal. Akun dikunci selama {_format_retry_wait(new_lock)}.",
                    "retry_after": new_lock,
                },
            )
        raise HTTPException(status_code=401, detail="Username atau password salah.")

    # Success: clear failed attempts, rotate any existing session, issue fresh cryptographically random token
    db.clear_login_attempts(attempt_keys)
    old_token = (request.cookies.get(settings.SESSION_COOKIE_NAME) or "").strip()
    if old_token:
        db.delete_auth_session(old_token)

    ttl = settings.REVIEW_SESSION_TTL_SECONDS if role == "reviewer" else settings.ADMIN_SESSION_TTL_SECONDS
    raw_token = secrets.token_urlsafe(32)
    sess = db.create_auth_session(
        raw_token=raw_token,
        role=role,
        username=canonical_username,
        ttl_seconds=ttl,
        ip_address=ip,
        user_agent=request.headers.get("user-agent") or "",
    )

    resp = JSONResponse(
        content={
            "ok": True,
            "role": role,
            "username": canonical_username,
            "actor": canonical_username,
            "expires_at": sess["expires_at"],
            "ttl_seconds": ttl,
        }
    )
    _set_session_cookie(resp, request, raw_token, ttl)
    return resp


@app.get("/api/auth/me")
def get_current_session(auth: dict[str, Any] = Depends(require_role("admin", "reviewer"))) -> dict[str, Any]:
    return {
        "authenticated": True,
        "role": auth["role"],
        "username": auth["username"],
        "actor": auth["actor"],
        "expires_at": auth["expires_at"],
        "last_seen_at": auth["last_seen_at"],
    }


@app.post("/api/auth/logout")
def logout_account(request: Request) -> JSONResponse:
    raw_token = (request.cookies.get(settings.SESSION_COOKIE_NAME) or "").strip()
    if raw_token:
        db.delete_auth_session(raw_token)
    resp = JSONResponse({"ok": True})
    _clear_session_cookie(resp, request)
    return resp


@app.get("/api/styles")
def get_styles(_auth: dict[str, Any] = Depends(require_role("admin", "reviewer"))) -> dict[str, Any]:
    return {"styles": dg.list_available_styles()}


@app.get("/api/dashboard")
def get_dashboard(_auth: dict[str, Any] = Depends(require_role("admin", "reviewer"))) -> dict[str, Any]:
    flipped = db.refresh_expired_followups()
    all_raw = db.list_leads()
    enriched = [_enrich_lead(l) for l in all_raw]

    outreach = [l for l in enriched if l["status"] == "CONCEPT_READY"]
    followup = [
        l for l in enriched
        if l["status"] in {"INTERESTED", "CONTACTED_DM", "CONTACTED_CALL", "IGNORED_48H"}
    ]
    # Show INTERESTED first (so "Generate Full Demo" is front-and-center), then overdue, then shortest timer
    followup.sort(
        key=lambda x: (
            0 if x["status"] == "INTERESTED" else (1 if x["is_overdue"] else 2),
            x["remaining_seconds"],
        )
    )

    pipeline = [
        l for l in enriched
        if l["status"] in {"INTERESTED", "FULL_DEMO_READY", "DP_PAID", "WON"}
    ]
    new_leads = [l for l in enriched if l["status"] == "NEW"]
    recycled = [l for l in enriched if l["status"] == "RECYCLED_CONTENT"]

    return {
        "stats": db.get_pipeline_stats(),
        "review_counts": db.get_review_counts(),
        "styles": dg.list_available_styles(),
        "auto_expired_count": flipped,
        "outreach_leads": outreach,
        "followup_leads": followup,
        "pipeline_leads": pipeline,
        "new_leads": new_leads,
        "recycled_leads": recycled,
        "server_time": db.iso_now(),
    }


@app.post("/api/leads")
def create_lead(
    payload: LeadCreatePayload,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    lead, created = db.upsert_lead(payload.model_dump(exclude={"auto_generate", "queue_for_dm"}))
    if payload.auto_generate:
        cg.generate_concept_package_for_lead(
            lead["id"],
            anonymize=False,
            force_style=payload.design_style or None,
        )
        lead = db.get_lead(lead["id"]) or lead
    elif payload.queue_for_dm and lead["status"] == "NEW":
        # Pre-INTERESTED metadata-only queue: ready for Cold DM without generating landing page HTML
        updates: dict[str, Any] = {"status": "CONCEPT_READY"}
        if payload.design_style:
            updates["design_style"] = payload.design_style
        lead = db.update_lead(lead["id"], updates) or lead
    return {"created": created, "lead": _enrich_lead(lead)}


@app.patch("/api/leads/{lead_id}")
def patch_lead(
    lead_id: int,
    payload: LeadUpdatePayload,
    auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if auth["role"] == "reviewer":
        if "status" in updates:
            try:
                norm_st = db.normalize_status(updates["status"])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if norm_st not in REVIEWER_ALLOWED_LEAD_STATUSES:
                raise HTTPException(
                    status_code=403,
                    detail="Akses ditolak: status teknis 'FULL_DEMO_READY' hanya diatur otomatis saat Admin menjalankan build demo.",
                )
            updates["status"] = norm_st
        # Reviewer only edits outreach/review fields (ig_observation, notes, ux_flaw, status)
        disallowed_fields = set(updates.keys()) - {"ig_observation", "notes", "ux_flaw", "status"}
        if disallowed_fields:
            raise HTTPException(
                status_code=403,
                detail="Akses ditolak: perubahan field metadata teknis hanya diizinkan untuk Admin.",
            )
    updated = db.update_lead(lead_id, updates)
    assert updated is not None
    if updates.get("status") == "INTERESTED":
        copy_engine.update_copy_outcome(lead_id, "interested")
    elif updates.get("status") == "IGNORED_48H":
        copy_engine.update_copy_outcome(lead_id, "ignored_48h")
    return {"lead": _enrich_lead(updated)}


@app.post("/api/leads/{lead_id}/contact")
def contact_lead(
    lead_id: int,
    payload: ContactPayload,
    _auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    updated = db.mark_contacted(lead_id, payload.method)
    assert updated is not None
    return {"lead": _enrich_lead(updated)}


@app.post("/api/leads/{lead_id}/status")
def set_lead_status(
    lead_id: int,
    payload: StatusPayload,
    auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    try:
        target_status = db.normalize_status(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if auth["role"] == "reviewer" and target_status not in REVIEWER_ALLOWED_LEAD_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak: status teknis '{target_status}' hanya diatur oleh Admin.",
        )

    updates: dict[str, Any] = {"status": target_status}
    if payload.ig_observation is not None:
        updates["ig_observation"] = payload.ig_observation.strip()

    if target_status in {"CONTACTED_DM", "CONTACTED_CALL"}:
        now = db.utc_now()
        updates["contacted_at"] = now.isoformat(timespec="seconds")
        updates["follow_up_due_at"] = (now + timedelta(hours=settings.FOLLOW_UP_HOURS)).isoformat(timespec="seconds")
    elif target_status in {"NEW", "CONCEPT_READY"}:
        updates["contacted_at"] = None
        updates["follow_up_due_at"] = None

    updated = db.update_lead(lead_id, updates)
    assert updated is not None
    if target_status == "INTERESTED":
        copy_engine.update_copy_outcome(lead_id, "interested")
    elif target_status == "IGNORED_48H":
        copy_engine.update_copy_outcome(lead_id, "ignored_48h")
    return {"lead": _enrich_lead(updated)}


@app.post("/api/copy/log")
def log_copy_interaction(
    payload: CopyLogPayload,
    auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Record human-edited copy (`original_draft`, `final_text`, `edit_summary`, patterns) to `copy_learning_log.md`."""
    lead = db.get_lead(payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    is_recycled = payload.channel == "caption" or bool(lead.get("is_anonymized")) or lead.get("status") == "RECYCLED_CONTENT"
    if is_recycled and payload.channel == "caption":
        leak = cr.check_anonymization_leak(lead, payload.final_text, "")
        if not leak["passed"]:
            raise HTTPException(
                status_code=422,
                detail={"message": "Caption mengandung data asli bisnis yang dilarang pada konten daur ulang.", "leak_report": leak},
            )

    val = copy_engine.validate_copy(payload.final_text, payload.channel, lead=lead, is_recycled=is_recycled)
    entry = copy_engine.log_copy_event(
        lead=lead,
        channel=payload.channel,
        original_draft=payload.original_draft or payload.final_text,
        final_text=payload.final_text,
        voice=payload.voice,
        sapaan=payload.sapaan,
        patterns_used=payload.patterns_used,
        levers=payload.levers,
        exploration_candidate=payload.exploration_candidate,
        outcome="n/a" if payload.channel == "caption" else "no_reply",
        notes=payload.notes or f"copied_by:{auth['actor']}",
        is_recycled=is_recycled,
    )
    return {"ok": True, "entry": entry, "validation": val}


@app.delete("/api/leads/{lead_id}")
def reject_or_delete_lead(
    lead_id: int,
    auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Reject/remove a client from curation or Cold DM queue (Reviewer limited to NEW/CONCEPT_READY)."""
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    if auth["role"] == "reviewer" and existing["status"] not in {"NEW", "CONCEPT_READY"}:
        raise HTTPException(
            status_code=403,
            detail=(
                "Akses ditolak: Reviewer hanya dapat menolak/menghapus prospek berstatus NEW atau CONCEPT_READY "
                f"(status saat ini: {existing['status']})."
            ),
        )
    if existing["status"] in {"DP_PAID", "WON"}:
        raise HTTPException(
            status_code=409,
            detail="Prospek berstatus DP_PAID / WON tidak dapat dihapus.",
        )

    slug = existing["slug"]
    deleted = db.delete_lead(lead_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    demo_dir = (settings.DEMOS_DIR / slug).resolve()
    if demo_dir.exists() and demo_dir.is_relative_to(settings.DEMOS_DIR.resolve()):
        shutil.rmtree(demo_dir, ignore_errors=True)
    dg.rebuild_portfolio_index()
    return {"ok": True, "deleted_id": lead_id}


@app.post("/api/leads/{lead_id}/concept")
@app.post("/api/leads/{lead_id}/generate")
def generate_concept_assets(
    lead_id: int,
    payload: StyleOverridePayload | None = None,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Stage A: Render concept hero HTML + Desktop/Mobile `concept_preview.png` + 4 IG slides."""
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    force_style = payload.design_style if payload and payload.design_style else None
    res = cg.generate_concept_package_for_lead(lead_id, anonymize=False, force_style=force_style)
    return {
        "stage": "CONCEPT_READY",
        "lead": _enrich_lead(res["lead"]),
        "design_style": res["design_style"],
        "style_label": res["style_label"],
        "concept_preview": res["concept_preview"],
        "slides_count": len(res["slides"]),
    }


@app.post("/api/leads/{lead_id}/full-demo")
def generate_full_demo_assets(
    lead_id: int,
    payload: StyleOverridePayload | None = None,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Build 1-page Pre-DP landing demo (INTERESTED/FULL_DEMO_READY) or full production site (DP_PAID/WON)."""
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")

    allowed_demo_statuses = {"INTERESTED", "FULL_DEMO_READY", "DP_PAID", "WON"}
    if existing["status"] not in allowed_demo_statuses:
        raise HTTPException(
            status_code=409,
            detail=(
                "Landing page demo belum boleh di-generate sebelum prospek merespons INTERESTED. "
                f"Status saat ini: {existing['status']}."
            ),
        )

    use_production = bool(payload and payload.production)
    if use_production and existing["status"] not in {"DP_PAID", "WON"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "Website produksi penuh (lepas watermark konsep) hanya dapat dibangun setelah status DP_PAID atau WON."
            ),
        )

    force_style = payload.design_style if payload and payload.design_style else None
    res = dg.generate_full_demo_for_lead(
        lead_id,
        anonymize=False,
        force_style=force_style,
        update_status=not use_production,
        production=use_production,
    )
    return {
        "stage": "PRODUCTION_READY" if use_production else "FULL_DEMO_READY",
        "mode": res["mode"],
        "watermark_removed": res["watermark_removed"],
        "lead": _enrich_lead(res["lead"]),
        "demo_file": res["demo_file"],
        "index_file": res["index_file"],
        "design_style": res["design_style"],
        "style_label": res["style_label"],
    }


@app.post("/api/leads/{lead_id}/recycle")
def recycle_lead(
    lead_id: int,
    auth: dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Anonymize prospect metadata and create a `draft_brief` in Tab 4 WITHOUT rendering PNG/video yet."""
    existing = db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    try:
        res = cr.create_draft_brief_from_recycle(
            lead_id,
            actor=f"{auth['actor']} (recycle)",
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)

    review_detail = res["review"]
    return {
        "lead": _enrich_lead(res["lead"]),
        "anonymized_name": res["anonymized_name"],
        "review_id": review_detail["review_id"],
        "review_status": review_detail["review_status"],
        "review_version": review_detail["current_version"],
        "brief": review_detail,
    }


# ==============================================================================
# REVIEW & PUBLISH WORKFLOW ENDPOINTS (/api/content/*)
# ==============================================================================
@app.get("/api/content/queue")
def get_content_review_queue(
    status: str | None = Query(default=None),
    _auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    return cr.list_review_queue(status_filter=status)


@app.post("/api/content/reels-ideas/scrape")
def scrape_reels_ideas_endpoint(
    payload: ReelsIdeasScrapePayload | None = None,
    auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Scrape real Indonesian UMKM business pain points (Agent-Reach + fallback) into Reels draft briefs."""
    p = payload or ReelsIdeasScrapePayload()
    try:
        return cr.create_reels_ideas_briefs(
            actor=auth["actor"],
            topic=p.topic,
            limit=p.limit,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/learning/evaluate")
def evaluate_learning_endpoint(
    _auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Deterministically refresh `learning_digest.json` (<= ~1,200 tokens) and propose max 3 candidates."""
    from creative_agent import token_optimizer

    return token_optimizer.evaluate_learning_signals()


@app.post("/api/content/{item_id}/generate")
def generate_content_item(
    item_id: int,
    payload: ContentGeneratePayload | None = None,
    auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    """Generate Carousel (4:5) or Reels (9:16 MP4) from a `draft_brief` or `changes_requested` item."""
    p = payload or ContentGeneratePayload()
    try:
        return cr.generate_content_from_brief(
            item_id=item_id,
            actor=auth["actor"],
            content_format=p.content_format,
            art_direction_preset=p.art_direction_preset,
            sequence_type=p.sequence_type,
            voice_id=p.voice_id,
            hook_pattern_id=p.hook_pattern_id,
            audio_mode=p.audio_mode,
            motion_intensity=p.motion_intensity,
            target_duration=p.target_duration,
            vo_script=p.vo_script,
            vo_style=p.vo_style,
            bgm_track=p.bgm_track,
            creative_note=p.creative_note,
            note=p.note,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.get("/api/content/{lead_id}")
def get_content_review_detail(
    lead_id: int,
    _auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    try:
        return cr.get_review_detail(lead_id)
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.get("/api/content/{lead_id}/preview/{version_number}/{asset_key}")
def preview_content_snapshot_asset(
    lead_id: int,
    version_number: int,
    asset_key: str,
    _auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> FileResponse:
    try:
        fpath = cr.resolve_preview_asset(lead_id, version_number, asset_key)
    except cr.ReviewError as exc:
        _handle_review_error(exc)
    mtype = "video/mp4" if fpath.suffix.lower() == ".mp4" else "image/png"
    return FileResponse(path=str(fpath), media_type=mtype)


@app.post("/api/content/{lead_id}/submit")
def submit_content_for_review(
    lead_id: int,
    payload: SubmitReviewPayload | None = None,
    auth: dict[str, str] = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        return cr.submit_for_review(
            lead_id=lead_id,
            actor=auth["actor"],
            note=(payload.note if payload else "") or "Submit manual ke antrean review",
            source=(payload.source if payload else "recycled_lead"),
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/corrections")
def create_content_corrections(
    lead_id: int,
    payload: CorrectionsRequestPayload,
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> dict[str, Any]:
    try:
        return cr.request_changes(
            lead_id=lead_id,
            actor=auth["actor"],
            corrections=[c.model_dump() for c in payload.corrections],
            expected_status=payload.expected_status,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/corrections/{correction_id}/resolve")
def resolve_content_correction(
    lead_id: int,
    correction_id: int,
    auth: dict[str, str] = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        return cr.resolve_correction(lead_id=lead_id, correction_id=correction_id, actor=auth["actor"])
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/revise")
async def revise_content_version(
    lead_id: int,
    request: Request,
    auth: dict[str, str] = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Admin creates a new version via JSON or multipart/form-data (regenerate or file upload + caption edit)."""
    content_type = (request.headers.get("content-type") or "").lower()
    regenerate = False
    caption: str | None = None
    hashtags: str | None = None
    note = ""
    expected_status: str | None = None
    uploaded_files: dict[str, tuple[str, bytes]] = {}

    if "multipart/form-data" in content_type:
        form = await request.form()
        regenerate = str(form.get("regenerate") or "").lower() in {"1", "true", "yes", "on"}
        if "caption" in form and form.get("caption") is not None:
            caption = str(form.get("caption"))
        if "hashtags" in form and form.get("hashtags") is not None:
            hashtags = str(form.get("hashtags"))
        note = str(form.get("note") or "")
        expected_status = str(form.get("expected_status") or "") or None

        field_to_asset = {
            "slide_1": "slide-1",
            "slide-1": "slide-1",
            "slide_2": "slide-2",
            "slide-2": "slide-2",
            "slide_3": "slide-3",
            "slide-3": "slide-3",
            "slide_4": "slide-4",
            "slide-4": "slide-4",
            "contact_sheet": "contact_sheet",
            "concept_preview": "concept_preview",
        }
        for field_name, asset_key in field_to_asset.items():
            up = form.get(field_name)
            if up is not None and hasattr(up, "read"):
                raw = await up.read()
                if raw:
                    uploaded_files[asset_key] = (getattr(up, "filename", f"{asset_key}.png") or f"{asset_key}.png", raw)
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        regenerate = bool(body.get("regenerate", False))
        caption = body.get("caption")
        hashtags = body.get("hashtags")
        note = str(body.get("note") or "")
        expected_status = body.get("expected_status")

    try:
        return cr.revise_content(
            lead_id=lead_id,
            actor=auth["actor"],
            regenerate=regenerate,
            uploaded_files=uploaded_files,
            caption=caption,
            hashtags=hashtags,
            note=note,
            expected_status=expected_status,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/approve")
def approve_content_review(
    lead_id: int,
    payload: ApprovePayload | None = None,
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> dict[str, Any]:
    try:
        return cr.approve_content(
            lead_id=lead_id,
            actor=auth["actor"],
            expected_status=payload.expected_status if payload else None,
            expected_version=payload.expected_version if payload else None,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.get("/api/content/{lead_id}/download.zip")
def download_approved_content_zip(
    lead_id: int,
    items: str | None = Query(default=None),
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> Response:
    item_list = [x.strip() for x in items.split(",") if x.strip()] if items else None
    try:
        zip_bytes, filename = cr.build_approved_zip_bytes(lead_id, item_list, actor=auth["actor"])
    except cr.ReviewError as exc:
        _handle_review_error(exc)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/content/{lead_id}/download/{asset_key}")
def download_approved_single_asset(
    lead_id: int,
    asset_key: str,
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> FileResponse:
    try:
        fpath, filename = cr.resolve_approved_download_asset(lead_id, asset_key, actor=auth["actor"])
    except cr.ReviewError as exc:
        _handle_review_error(exc)
    mtype = "video/mp4" if fpath.suffix.lower() == ".mp4" else "image/png"
    return FileResponse(
        path=str(fpath),
        media_type=mtype,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/content/{lead_id}/caption-copied")
def log_content_caption_copied(
    lead_id: int,
    payload: CaptionCopiedPayload | None = None,
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> dict[str, Any]:
    try:
        res = cr.record_caption_copied(lead_id=lead_id, actor=auth["actor"])
    except cr.ReviewError as exc:
        _handle_review_error(exc)

    lead = db.get_lead(lead_id)
    if lead:
        orig_cap = (payload.original_draft if payload and payload.original_draft else res.get("full_caption") or "")
        final_cap = (payload.final_text if payload and payload.final_text else orig_cap)
        if final_cap:
            leak = cr.check_anonymization_leak(lead, final_cap, "")
            if not leak["passed"]:
                raise HTTPException(
                    status_code=422,
                    detail={"message": "Editan caption mengandung data asli bisnis yang dilarang pada konten daur ulang.", "leak_report": leak},
                )
            copy_engine.log_copy_event(
                lead=lead,
                channel="caption",
                original_draft=orig_cap,
                final_text=final_cap,
                patterns_used=(payload.patterns_used if payload else []),
                outcome="n/a",
                notes=f"review_caption_copied_by:{auth['actor']}",
                is_recycled=True,
            )
    return res


@app.post("/api/content/{lead_id}/posted")
def mark_content_posted(
    lead_id: int,
    payload: PostedPayload | None = None,
    auth: dict[str, str] = Depends(require_role("reviewer")),
) -> dict[str, Any]:
    try:
        return cr.mark_posted(
            lead_id=lead_id,
            actor=auth["actor"],
            posted_url=payload.posted_url if payload else "",
            posted_at=payload.posted_at if payload else None,
            expected_status=payload.expected_status if payload else None,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/metrics")
def save_content_posted_metrics(
    lead_id: int,
    payload: PostedMetricsPayload,
    auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    try:
        return cr.save_posted_metrics(
            lead_id=lead_id,
            actor=auth["actor"],
            views=payload.views,
            saves=payload.saves,
            shares=payload.shares,
            dm_in=payload.dm_in,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/content/{lead_id}/comments")
def create_content_comment(
    lead_id: int,
    payload: CommentPayload,
    auth: dict[str, str] = Depends(require_role("admin", "reviewer")),
) -> dict[str, Any]:
    try:
        return cr.add_comment(
            lead_id=lead_id,
            author=auth["actor"],
            role=auth["role"],
            body=payload.body,
        )
    except cr.ReviewError as exc:
        _handle_review_error(exc)


@app.post("/api/jobs/scrape")
def start_scrape_job(
    payload: ScrapeJobPayload,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:10]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "type": "scrape",
            "status": "queued",
            "message": "Menyiapkan browser scraper...",
            "created_at": db.iso_now(),
        }
    t = threading.Thread(target=_run_scrape_job, args=(job_id, payload), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@app.post("/api/jobs/generate-batch")
def start_batch_generate_job(
    payload: BatchGeneratePayload,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:10]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "type": "generate_batch",
            "status": "queued",
            "message": "Menyiapkan batch generator Tahap A...",
            "created_at": db.iso_now(),
        }
    t = threading.Thread(target=_run_batch_generate_job, args=(job_id, payload.limit), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: str,
    _auth: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    return job


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=False)
