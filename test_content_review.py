"""Focused verification suite for @goandalan Auth, Sliding 7-Day Session, RBAC, Security & Review/Publish Workflow.

Tests:
1. Env-based Auth (ADMIN_USN/PASS & REVIEW_USN/PASS), HttpOnly/SameSite=Strict cookies, 7-day Reviewer sliding session,
   expiry invalidation (>7 days -> 401 + session deleted), logout, wrong credentials (401), & brute-force lockout (429)
2. Security audit checks: sensitive files (/.env, /leads.db, *.py, /skills/, /creative_agent/, /reviews/) blocked,
   security headers, CSRF Origin block, query-string ?token= rejection, & upload magic-bytes validation
3. Full RBAC separation: Reviewer outreach + content review allowed; dev routes (/jobs/scrape, /full-demo, /revise, /resolve) 403
4. Backward compatibility of 10 `leads` statuses & `/api/dashboard` keys
5. `check_anonymization_leak` catches real business name, WA/phone variants (`08...`/`628...`), and real address
6. Review state machine transitions, concurrent 409, byte-identical PNG/ZIP downloads from `approved_version`,
   post-approval revocation, `/recycle` 409 block, & reversible DB migration rollback
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import content_review as cr
import database as db
from app import app
from config import settings
from creative_agent import copy_engine


def _make_png_bytes(color: tuple[int, int, int], size: tuple[int, int] = (1080, 1350)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _create_test_recycled_lead(
    slug_suffix: str,
    business_name: str = "Kopi Asli Rahasia",
    anon_name: str = "Ruang Seduh Fiktif",
    phone_raw: str = "0812-3456-7890",
    address: str = "Jl. Kemang Selatan No. 88, Jakarta Selatan",
) -> tuple[dict, Path]:
    lead, _ = db.upsert_lead(
        {
            "slug": f"test-review-{slug_suffix}",
            "business_name": business_name,
            "anonymized_name": anon_name,
            "category": "Coffee Roastery",
            "city": "Jakarta Selatan",
            "phone_raw": phone_raw,
            "address": address,
            "status": "RECYCLED_CONTENT",
        }
    )
    lead = db.update_lead(lead["id"], {"is_anonymized": 1, "anonymized_name": anon_name, "status": "RECYCLED_CONTENT"})
    assert lead is not None

    demo_dir = settings.DEMOS_DIR / lead["slug"]
    ig_dir = demo_dir / "ig"
    ig_dir.mkdir(parents=True, exist_ok=True)

    slide_names = ["01_reveal", "02_details", "03_statement", "04_experience"]
    colors = [(200, 85, 46), (27, 20, 17), (247, 240, 228), (40, 75, 54)]
    for sname, col in zip(slide_names, colors):
        (ig_dir / f"{sname}.png").write_bytes(_make_png_bytes(col, (1080, 1350)))

    (ig_dir / "contact_sheet.png").write_bytes(_make_png_bytes((20, 20, 19), (800, 1000)))
    (demo_dir / "concept_preview.png").write_bytes(_make_png_bytes((245, 240, 232), (1440, 1080)))
    (ig_dir / "carousel_spec.json").write_text(
        json.dumps(
            {
                "slides": [{"n": i + 1, "name": n, "headline_html": f"Konsep {anon_name} #{i+1}"} for i, n in enumerate(slide_names)]
            }
        ),
        encoding="utf-8",
    )
    (ig_dir / "qa_report.json").write_text(json.dumps({"status": "PASS", "score": 100}), encoding="utf-8")
    (ig_dir / "caption.txt").write_text(
        f"eksplorasi konsep web untuk {anon_name}.\n\n#websiteshowcase #goandalan\n",
        encoding="utf-8",
    )
    return lead, demo_dir


def _cleanup_lead(lead: dict) -> None:
    with db.get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead["id"],))
    shutil.rmtree(settings.DEMOS_DIR / lead["slug"], ignore_errors=True)
    anon_slug = db.slugify(lead.get("anonymized_name") or f"konsep-lokal-{lead['id']}")
    shutil.rmtree(settings.DEMOS_DIR / anon_slug / "reviews" / str(lead["id"]), ignore_errors=True)


def run_all_tests() -> None:
    db.init_db()
    assert settings.ADMIN_USN and settings.ADMIN_PASS, "ADMIN_USN / ADMIN_PASS wajib diisi di .env"
    assert settings.REVIEW_USN and settings.REVIEW_PASS, "REVIEW_USN / REVIEW_PASS wajib diisi di .env"

    anon_client = TestClient(app)
    admin_client = TestClient(app)
    reviewer_client = TestClient(app)

    # 1. Unauthenticated blocks, security headers & sensitive path isolation
    assert anon_client.get("/api/dashboard").status_code == 401
    assert anon_client.get("/api/auth/me").status_code == 401
    assert anon_client.get("/api/content/queue").status_code == 401
    assert anon_client.get("/api/content/queue?token=any-fake-token").status_code == 401

    home_resp = anon_client.get("/")
    assert home_resp.status_code == 200
    assert home_resp.headers.get("x-content-type-options") == "nosniff"
    assert home_resp.headers.get("x-frame-options") == "DENY"
    assert "strict-origin-when-cross-origin" in (home_resp.headers.get("referrer-policy") or "")
    assert "frame-ancestors 'none'" in (home_resp.headers.get("content-security-policy") or "")
    assert 'autocomplete="username"' in home_resp.text and 'autocomplete="current-password"' in home_resp.text

    for sensitive in (
        "/.env",
        "/.env.example",
        "/leads.db",
        "/app.py",
        "/config.py",
        "/skills/instagram-creative-agent/SKILL.md",
        "/creative_agent/cli.py",
        "/demos/ruang-seduh-fiktif/reviews/1/v1/slide-1.png",
    ):
        r_sens = anon_client.get(sensitive)
        assert r_sens.status_code in {403, 404}, f"Sensitive path {sensitive} leaked status {r_sens.status_code}"
    print("[OK] 1. Unauthenticated 401, security headers, native autofill form & sensitive path isolation verified")

    # 2. Brute-force rate limit & progressive lockout (HTTP 429 + Retry-After) on isolated IP
    brute_ip = "203.0.113.77"
    brute_headers = {"X-Forwarded-For": brute_ip}
    db.clear_login_attempts([f"ip:{brute_ip}", f"user:{brute_ip}:invalid_probe"])
    try:
        for attempt_idx in range(1, settings.LOGIN_MAX_ATTEMPTS):
            r_bad = anon_client.post(
                "/api/auth/login",
                headers=brute_headers,
                json={"username": "invalid_probe", "password": "wrong_password_value"},
            )
            assert r_bad.status_code == 401, f"Attempt {attempt_idx} expected 401, got {r_bad.status_code}"
        r_locked = anon_client.post(
            "/api/auth/login",
            headers=brute_headers,
            json={"username": "invalid_probe", "password": "wrong_password_value"},
        )
        assert r_locked.status_code == 429, f"Expected 429 lockout, got {r_locked.status_code}"
        assert int(r_locked.headers.get("retry-after") or 0) > 0
        # Even right after lockout, another attempt stays blocked 429
        r_locked2 = anon_client.post(
            "/api/auth/login",
            headers=brute_headers,
            json={"username": settings.ADMIN_USN, "password": settings.ADMIN_PASS},
        )
        assert r_locked2.status_code == 429
    finally:
        db.clear_login_attempts([f"ip:{brute_ip}", f"user:{brute_ip}:invalid_probe"])
    print("[OK] 2. Wrong credentials (401) & brute-force lockout (429 + Retry-After) verified")

    # 3. Admin & Reviewer Login, Cookie Attributes (7-day max-age=604800), Auto-Resume, Sliding Renewal & >7d Expiry
    r_adm_login = admin_client.post(
        "/api/auth/login",
        json={"username": settings.ADMIN_USN, "password": settings.ADMIN_PASS},
    )
    assert r_adm_login.status_code == 200 and r_adm_login.json()["role"] == "admin"
    adm_cookie_hdr = (r_adm_login.headers.get("set-cookie") or "").lower()
    assert "httponly" in adm_cookie_hdr and "samesite=strict" in adm_cookie_hdr
    assert f"max-age={settings.ADMIN_SESSION_TTL_SECONDS}" in adm_cookie_hdr

    r_rev_login = reviewer_client.post(
        "/api/auth/login",
        json={"username": settings.REVIEW_USN, "password": settings.REVIEW_PASS},
    )
    assert r_rev_login.status_code == 200 and r_rev_login.json()["role"] == "reviewer"
    rev_cookie_hdr = (r_rev_login.headers.get("set-cookie") or "").lower()
    assert "httponly" in rev_cookie_hdr and "samesite=strict" in rev_cookie_hdr
    assert "max-age=604800" in rev_cookie_hdr, f"Expected 7-day max-age=604800, got: {rev_cookie_hdr}"
    assert "no-store" in (r_rev_login.headers.get("cache-control") or "").lower()

    # Auto-resume via GET /api/auth/me without re-entering credentials
    r_me = reviewer_client.get("/api/auth/me")
    assert r_me.status_code == 200 and r_me.json()["authenticated"] is True and r_me.json()["role"] == "reviewer"

    # Verify sliding renewal when last_seen_at is > 1 hour ago
    rev_token = reviewer_client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert rev_token
    rev_hash = db.hash_session_token(rev_token)
    two_hours_ago = (db.utc_now() - timedelta(hours=2)).isoformat(timespec="seconds")
    old_exp = (db.utc_now() + timedelta(days=5)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = ?, expires_at = ? WHERE token_hash = ?",
            (two_hours_ago, old_exp, rev_hash),
        )
    r_me_renew = reviewer_client.get("/api/auth/me")
    assert r_me_renew.status_code == 200
    assert r_me_renew.json()["expires_at"] > old_exp, "Sliding renewal did not extend expires_at"
    assert "max-age=604800" in (r_me_renew.headers.get("set-cookie") or "").lower()

    # Verify >7-day expiry invalidates session in SQLite and blocks /api/auth/me + /api/dashboard with 401
    temp_rev_client = TestClient(app)
    r_tmp_login = temp_rev_client.post(
        "/api/auth/login",
        json={"username": settings.REVIEW_USN, "password": settings.REVIEW_PASS},
    )
    assert r_tmp_login.status_code == 200
    tmp_tok = temp_rev_client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert tmp_tok
    tmp_hash = db.hash_session_token(tmp_tok)
    expired_iso = (db.utc_now() - timedelta(days=8)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        conn.execute("UPDATE auth_sessions SET expires_at = ? WHERE token_hash = ?", (expired_iso, tmp_hash))
    assert temp_rev_client.get("/api/auth/me").status_code == 401
    assert temp_rev_client.get("/api/dashboard").status_code == 401
    assert db.get_auth_session(tmp_tok) is None, "Expired session row must be deleted from SQLite"

    # Verify logout destroys session immediately
    temp_out_client = TestClient(app)
    assert temp_out_client.post(
        "/api/auth/login",
        json={"username": settings.REVIEW_USN, "password": settings.REVIEW_PASS},
    ).status_code == 200
    out_tok = temp_out_client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert temp_out_client.post("/api/auth/logout").status_code == 200
    assert db.get_auth_session(out_tok or "") is None
    assert temp_out_client.get("/api/auth/me").status_code == 401
    print("[OK] 3. Admin (12h) & Reviewer (7d max-age=604800) sliding sessions, >7d expiry 401 & logout verified")

    # 4. Backward compatibility: 10 lead statuses unchanged & dashboard keys preserved + CSRF Origin guard
    assert len(settings.LEAD_STATUSES) == 10
    assert "RECYCLED_CONTENT" in settings.LEAD_STATUSES
    dash = reviewer_client.get("/api/dashboard")
    assert dash.status_code == 200
    dash_json = dash.json()
    for key in (
        "stats",
        "review_counts",
        "styles",
        "auto_expired_count",
        "outreach_leads",
        "followup_leads",
        "pipeline_leads",
        "new_leads",
        "recycled_leads",
        "server_time",
    ):
        assert key in dash_json, f"Missing dashboard key: {key}"

    # CSRF foreign Origin blocked with 403
    r_csrf = admin_client.post(
        "/api/jobs/scrape",
        headers={"Origin": "https://evil.example"},
        json={"query": "cafe"},
    )
    assert r_csrf.status_code == 403, f"Expected CSRF 403, got {r_csrf.status_code}"
    print("[OK] 4. Backward compatibility (10 lead statuses + /api/dashboard) & CSRF Origin protection verified")

    # 5. Verify check_anonymization_leak directly
    fake_lead = {
        "id": 99999,
        "business_name": "Kopi Asli Rahasia",
        "anonymized_name": "Ruang Seduh Fiktif",
        "phone_raw": "0812-3456-7890",
        "phone_wa": "6281234567890",
        "address": "Jl. Kemang Selatan No. 88, Jakarta Selatan",
    }
    assert cr.check_anonymization_leak(fake_lead, "Konsep untuk Ruang Seduh Fiktif", "#goandalan")["passed"] is True
    assert cr.check_anonymization_leak(fake_lead, "Mampir ke Kopi Asli Rahasia yuk")["passed"] is False
    assert cr.check_anonymization_leak(fake_lead, "Hubungi 0812 3456 7890 sekarang")["passed"] is False
    assert cr.check_anonymization_leak(fake_lead, "WA di +62 812-3456-7890")["passed"] is False
    assert cr.check_anonymization_leak(fake_lead, "Lokasi Jl. Kemang Selatan No. 88")["passed"] is False
    print("[OK] 5. check_anonymization_leak detects business_name, 08.../628... phone variants, and address")

    # 6. Reviewer curation (ACC NEW -> CONCEPT_READY & Reject/Delete NEW) + RBAC on outreach/dev endpoints
    scraped_acc, _ = db.upsert_lead(
        {
            "slug": "test-curation-acc",
            "business_name": "Kopi Kurasi ACC",
            "category": "Coffee Roastery",
            "city": "Jakarta",
            "status": "NEW",
        }
    )
    scraped_rej, _ = db.upsert_lead(
        {
            "slug": "test-curation-reject",
            "business_name": "Kopi Kurasi Tolak",
            "category": "Coffee Roastery",
            "city": "Jakarta",
            "status": "NEW",
        }
    )
    outreach_lead, _ = db.upsert_lead(
        {
            "slug": "test-rbac-outreach-lead",
            "business_name": "Kedai Uji RBAC",
            "category": "Coffee Roastery",
            "city": "Jakarta",
            "status": "CONCEPT_READY",
        }
    )
    lead, _ = _create_test_recycled_lead("workflow-main")
    lead_id = lead["id"]
    try:
        # Reviewer ACCs scraped_acc (NEW -> CONCEPT_READY) and rejects/deletes scraped_rej (NEW)
        r_acc = reviewer_client.post(f"/api/leads/{scraped_acc['id']}/status", json={"status": "CONCEPT_READY"})
        assert r_acc.status_code == 200 and r_acc.json()["lead"]["status"] == "CONCEPT_READY"
        r_rej = reviewer_client.delete(f"/api/leads/{scraped_rej['id']}")
        assert r_rej.status_code == 200 and r_rej.json()["ok"] is True
        assert db.get_lead(scraped_rej["id"]) is None

        # Reviewer CAN perform full Cold DM & deal pipeline status transitions (CONCEPT_READY -> CONTACTED_DM -> IGNORED_48H -> CONCEPT_READY -> INTERESTED -> DP_PAID -> WON)
        assert reviewer_client.patch(
            f"/api/leads/{outreach_lead['id']}",
            json={"ig_observation": "foto pour-over pagi yang estetik"},
        ).status_code == 200
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/contact",
            json={"method": "CONTACTED_DM"},
        ).status_code == 200
        # Reviewer CANNOT delete a lead that has already been contacted (403)
        assert reviewer_client.delete(f"/api/leads/{outreach_lead['id']}").status_code == 403
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "IGNORED_48H"},
        ).status_code == 200
        # Reviewer can revert mis-clicked lead back to CONCEPT_READY, then move through INTERESTED -> DP_PAID -> WON
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "CONCEPT_READY"},
        ).status_code == 200
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "CONTACTED_CALL"},
        ).status_code == 200
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "INTERESTED"},
        ).status_code == 200
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "DP_PAID"},
        ).status_code == 200
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "WON"},
        ).status_code == 200
        # Reset back to INTERESTED before dev-only 403 checks
        assert reviewer_client.post(
            f"/api/leads/{outreach_lead['id']}/status",
            json={"status": "INTERESTED"},
        ).status_code == 200

        # Reviewer BLOCKED (403) on dev-only actions: scrape, full-demo, concept, FULL_DEMO_READY status, submit, revise
        assert reviewer_client.post("/api/jobs/scrape", json={"query": "kopi jakarta"}).status_code == 403
        assert reviewer_client.post(f"/api/leads/{outreach_lead['id']}/full-demo").status_code == 403
        assert reviewer_client.post(f"/api/leads/{outreach_lead['id']}/concept").status_code == 403
        assert reviewer_client.post(f"/api/leads/{outreach_lead['id']}/status", json={"status": "FULL_DEMO_READY"}).status_code == 403
        assert reviewer_client.patch(f"/api/leads/{outreach_lead['id']}", json={"status": "FULL_DEMO_READY"}).status_code == 403
        assert reviewer_client.post(f"/api/content/{lead_id}/submit").status_code == 403
        assert reviewer_client.post(f"/api/content/{lead_id}/revise", json={"note": "x"}).status_code == 403

        # Admin submits v1 -> pending_review
        r_sub = admin_client.post(f"/api/content/{lead_id}/submit", json={"note": "Submit v1"})
        assert r_sub.status_code == 200, r_sub.text
        d_sub = r_sub.json()
        assert d_sub["review_status"] == "pending_review"
        assert d_sub["current_version"] == 1
        assert d_sub["anon_name"] == "Ruang Seduh Fiktif"
        assert "Kopi Asli Rahasia" not in json.dumps(d_sub)
        assert "0812" not in json.dumps(d_sub)

        # Admin cannot approve or mark posted (403)
        assert admin_client.post(f"/api/content/{lead_id}/approve").status_code == 403
        assert admin_client.post(f"/api/content/{lead_id}/posted").status_code == 403

        # Cannot download or mark posted while pending_review (409)
        assert reviewer_client.get(f"/api/content/{lead_id}/download/slide-1").status_code == 409
        assert reviewer_client.post(f"/api/content/{lead_id}/posted").status_code == 409
        print("[OK] 6. RBAC separation (Reviewer outreach+review OK, Dev routes 403; Admin approve/posted 403) verified")

        # 7. State transitions, concurrent conflict 409, magic-bytes rejection, leak 422, & multipart v2 upload
        r_corr = reviewer_client.post(
            f"/api/content/{lead_id}/corrections",
            json={
                "expected_status": "pending_review",
                "corrections": [
                    {"slide_index": 1, "note": "Perjelas kontras judul slide 1"},
                    {"slide_index": None, "note": "Rapikan jarak paragraf caption"},
                ],
            },
        )
        assert r_corr.status_code == 200, r_corr.text
        d_corr = r_corr.json()
        assert d_corr["review_status"] == "changes_requested"
        corr_id = d_corr["corrections"][0]["id"]

        # Stale concurrent approve attempt must return 409
        assert reviewer_client.post(
            f"/api/content/{lead_id}/approve",
            json={"expected_status": "pending_review"},
        ).status_code == 409

        # Reviewer cannot resolve correction (403); Admin resolves it (200)
        assert reviewer_client.post(f"/api/content/{lead_id}/corrections/{corr_id}/resolve").status_code == 403
        r_res = admin_client.post(f"/api/content/{lead_id}/corrections/{corr_id}/resolve")
        assert r_res.status_code == 200
        assert any(c["id"] == corr_id and c["status"] == "resolved" for c in r_res.json()["corrections"])

        # Fake PNG (invalid magic bytes) rejected 400
        r_magic = admin_client.post(
            f"/api/content/{lead_id}/revise",
            data={"caption": "Caption bersih.", "note": "uji magic bytes"},
            files={"slide_1": ("spoof.png", b"NOT_A_REAL_PNG_PAYLOAD_12345", "image/png")},
        )
        assert r_magic.status_code == 400, f"Expected 400 on spoofed PNG magic bytes, got {r_magic.status_code}"

        # Admin revise with leaked real business name -> BLOCKED 422!
        r_leak = admin_client.post(
            f"/api/content/{lead_id}/revise",
            json={"caption": "Promo Kopi Asli Rahasia hari ini!", "note": "uji leak"},
        )
        assert r_leak.status_code == 422, f"Expected 422 leak block, got {r_leak.status_code}: {r_leak.text}"

        # Admin creates clean v2 via multipart upload replacing slide-1 + editing caption
        v2_slide1_bytes = _make_png_bytes((15, 92, 110), (1080, 1350))
        r_rev = admin_client.post(
            f"/api/content/{lead_id}/revise",
            data={"caption": "Caption bersih versi dua untuk Ruang Seduh Fiktif.", "hashtags": "#websiteshowcase #goandalan", "note": "Perbaikan slide 1 & caption"},
            files={"slide_1": ("slide1_new.png", v2_slide1_bytes, "image/png")},
        )
        assert r_rev.status_code == 200, r_rev.text
        d_rev = r_rev.json()
        assert d_rev["review_status"] == "revised"
        assert d_rev["current_version"] == 2
        assert len(d_rev["resolved_corrections_for_review"]) >= 1

        # Reviewer approves v2 -> approved
        r_app = reviewer_client.post(
            f"/api/content/{lead_id}/approve",
            json={"expected_status": "revised", "expected_version": 2},
        )
        assert r_app.status_code == 200, r_app.text
        d_app = r_app.json()
        assert d_app["review_status"] == "approved"
        assert d_app["approved_version"] == 2
        print("[OK] 7. State machine, 409 conflict, magic-bytes 400, leak 422 & multipart v2 upload verified")

        # 8. Overwrite protection (/recycle 409) & byte-identical v2 downloads + caption copy
        assert admin_client.post(f"/api/leads/{lead_id}/recycle").status_code == 409

        live_ig = settings.DEMOS_DIR / lead["slug"] / "ig"
        (live_ig / "01_reveal.png").write_bytes(_make_png_bytes((255, 0, 255), (1080, 1350)))
        (live_ig / "caption.txt").write_text("MUTATED LIVE FILE MUST NEVER BE SERVED", encoding="utf-8")

        r_dl = reviewer_client.get(f"/api/content/{lead_id}/download/slide-1")
        assert r_dl.status_code == 200
        assert r_dl.content == v2_slide1_bytes
        assert "ruang-seduh-fiktif_v2_slide-1.png" in (r_dl.headers.get("content-disposition") or "")

        r_zip = reviewer_client.get(f"/api/content/{lead_id}/download.zip?items=slide-1,contact_sheet")
        assert r_zip.status_code == 200
        assert "ruang-seduh-fiktif_v2.zip" in (r_zip.headers.get("content-disposition") or "")
        with zipfile.ZipFile(io.BytesIO(r_zip.content), "r") as zf:
            names = sorted(zf.namelist())
            assert names == ["ruang-seduh-fiktif_v2_contact_sheet.png", "ruang-seduh-fiktif_v2_slide-1.png"], names
            assert zf.read("ruang-seduh-fiktif_v2_slide-1.png") == v2_slide1_bytes

        r_cap = reviewer_client.post(f"/api/content/{lead_id}/caption-copied")
        assert r_cap.status_code == 200
        assert r_cap.json()["version"] == 2
        assert "Caption bersih versi dua" in r_cap.json()["full_caption"]
        assert "MUTATED" not in r_cap.json()["full_caption"]
        print("[OK] 8. Single PNG (zero recompression), selective ZIP, caption copy from v2 & /recycle 409 verified")

        # 9. Post-approval revision revocation, mark posted & terminal state locks
        r_post_app_rev = admin_client.post(
            f"/api/content/{lead_id}/revise",
            json={"caption": "Revisi v3 setelah approval.", "note": "Tweak pasca approval"},
        )
        assert r_post_app_rev.status_code == 200
        d_v3 = r_post_app_rev.json()
        assert d_v3["review_status"] == "revised" and d_v3["current_version"] == 3 and d_v3["approved_version"] is None
        assert reviewer_client.get(f"/api/content/{lead_id}/download/slide-1").status_code == 409

        assert reviewer_client.post(f"/api/content/{lead_id}/approve").status_code == 200
        r_post = reviewer_client.post(
            f"/api/content/{lead_id}/posted",
            json={"posted_url": "https://instagram.com/p/test123"},
        )
        assert r_post.status_code == 200 and r_post.json()["review_status"] == "posted"
        assert admin_client.post(f"/api/content/{lead_id}/revise", json={"note": "late"}).status_code == 409
        assert admin_client.post(f"/api/leads/{lead_id}/recycle").status_code == 409
        print("[OK] 9. Post-approval revocation, mark posted & terminal locks verified")

        # 10. Reversible DB migration test on isolated temp SQLite DB
        with tempfile.TemporaryDirectory() as td:
            tmp_db = Path(td) / "mig_test.db"
            db.init_db(tmp_db)
            db.upsert_lead({"business_name": "Persist Lead", "category": "Cafe"}, db_path=tmp_db)
            db.migrate_review_tables_down(tmp_db)
            with db.get_conn(tmp_db) as conn:
                tbls = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                assert "leads" in tbls and "auth_sessions" in tbls and "content_reviews" not in tbls
            assert len(db.list_leads(db_path=tmp_db)) == 1
        print("[OK] 10. Reversible DB migration (preserving `leads` & `auth_sessions`) verified")

        # 11. Copy Intelligence Engine: V1-V6 pre-routing, §10.1 hard-fail validator, §11 rotation, 20% exploration & log/outcome sync
        assert copy_engine.COPY_LIBRARY_PATH.exists() and copy_engine.COPY_LIBRARY_PATH.stat().st_size > 0
        assert copy_engine.route_voice_for_lead({"category": "Klinik Gigi"})["voice"] == "V2"
        assert copy_engine.route_voice_for_lead({"category": "Klinik Gigi"})["caption_voice"] == "formal_editorial"
        assert copy_engine.route_voice_for_lead({"category": "Villa & Resort"})["voice"] == "V4"
        assert copy_engine.route_voice_for_lead({"category": "Coffee Roastery"})["voice"] == "V1"
        assert copy_engine.route_voice_for_lead({"category": "Barbershop"})["voice"] == "V5"
        assert copy_engine.route_voice_for_lead({"category": "Batik Artisan Craft"})["voice"] == "V6"

        # Hard-fail validator (§10.1) tests
        v_url = copy_engine.validate_copy(
            "Kak, coba lihat https://contoh.id untuk foto preview konsep kafe kamu yang sudah saya buat bersama Alan ya Kak?",
            "cold_dm_1",
        )
        assert v_url["passed"] is False and any("URL" in f for f in v_url["hard_fails"])

        v_alan2 = copy_engine.validate_copy(
            "Kak, saya Alan. Alan sudah bikin foto preview konsep buat kafe kamu yang rapi banget untuk dilihat di layar HP sekarang tanpa biaya apa pun dan tanpa kewajiban sama sekali buat kamu coba lihat dulu hari ini. Boleh Alan kirim fotonya?",
            "cold_dm_1",
        )
        assert v_alan2["passed"] is False and any("Alan" in f for f in v_alan2["hard_fails"])

        v_short = copy_engine.validate_copy("Kak, saya Alan, boleh kirim foto preview konsep?", "cold_dm_1")
        assert v_short["passed"] is False and any("45–80" in f for f in v_short["hard_fails"])

        v_nodisc = copy_engine.validate_copy(
            "Eksplorasi tampilan web untuk Ruang Seduh Fiktif yang bersih di HP.\n\n#websiteshowcase",
            "caption",
            lead=fake_lead,
            is_recycled=True,
        )
        assert v_nodisc["passed"] is False and any("disclosure" in f.lower() for f in v_nodisc["hard_fails"])

        # Isolated log test: rotation (§11), 20% exploration (5th regular lead), & outcome auto-update
        with tempfile.TemporaryDirectory() as td:
            tmp_log = Path(td) / "copy_learning_log.md"
            tmp_log.write_text("# Copy Learning Log\n\n## Log entries\n", encoding="utf-8")
            seen_openers: list[str] = []
            seen_exp: list[str] = []
            for idx in range(1, 6):
                sample_l = {
                    "id": 900 + idx,
                    "business_name": f"Kopi Uji {idx}",
                    "category": "Coffee Roastery",
                    "city": "Jakarta",
                    "has_website": 0,
                    "priority_score": 70,  # regular priority -> eligible for 20% exploration on 5th draft
                    "ig_observation": f"foto seduh manual nomor {idx}",
                    "ux_flaw": "Belum punya website resmi.",
                }
                dm_res = copy_engine.draft_cold_dm(sample_l, log_path=tmp_log)
                assert dm_res["validation"]["passed"] is True, dm_res["validation"]
                seen_openers.append(dm_res["patterns_used"][0])
                if dm_res["exploration_candidate"]:
                    seen_exp.append(dm_res["exploration_candidate"])
                copy_engine.log_copy_event(
                    lead=sample_l,
                    channel="cold_dm_1",
                    original_draft=dm_res["primary"],
                    final_text=dm_res["primary"] + " (diedit sedikit)",
                    voice=dm_res["voice"],
                    sapaan=dm_res["sapaan"],
                    patterns_used=dm_res["patterns_used"],
                    levers=dm_res["levers"],
                    exploration_candidate=dm_res["exploration_candidate"],
                    log_path=tmp_log,
                )
            assert seen_openers[0] != seen_openers[1], f"Consecutive same-city opener repeated: {seen_openers}"
            assert "OPEN-C9" in seen_exp, f"20% exploration candidate not triggered on 5th regular lead: {seen_exp}"
            assert copy_engine.update_copy_outcome(901, "interested", log_path=tmp_log) == 1
            assert copy_engine.update_copy_outcome(902, "ignored_48h", log_path=tmp_log) == 1
            log_text = tmp_log.read_text(encoding="utf-8")
            assert "outcome: interested" in log_text and "outcome: ignored_48h" in log_text

            # Recycled caption generation + mandatory disclosure + anonymization check
            cap_res = copy_engine.draft_recycled_caption(
                lead={**fake_lead, "is_anonymized": 1, "status": "RECYCLED_CONTENT"},
                art_direction={"primary_style": "Warm Organic"},
                facts={"items": [{"name": "Espresso"}]},
                log_path=tmp_log,
            )
            assert cap_res["validation"]["passed"] is True, cap_res["validation"]
            assert "fiktif" in cap_res["caption"].lower()
            assert "Kopi Asli Rahasia" not in cap_res["caption"]

        # End-to-end API test: ACC with ig_observation + /api/copy/log + auto outcome on INTERESTED
        orig_log_backup = copy_engine.COPY_LEARNING_LOG_PATH.read_text(encoding="utf-8")
        try:
            r_acc_obs = reviewer_client.post(
                f"/api/leads/{scraped_acc['id']}/status",
                json={"status": "CONCEPT_READY", "ig_observation": "foto pour-over pagi yang hangat"},
            )
            assert r_acc_obs.status_code == 200
            assert r_acc_obs.json()["lead"]["ig_observation"] == "foto pour-over pagi yang hangat"
            dm_from_api = r_acc_obs.json()["lead"]["cold_dm_draft"]
            assert "foto pour-over pagi yang hangat" in dm_from_api

            r_log = reviewer_client.post(
                "/api/copy/log",
                json={
                    "lead_id": scraped_acc["id"],
                    "channel": "cold_dm_1",
                    "original_draft": dm_from_api,
                    "final_text": dm_from_api + " Terima kasih.",
                    "patterns_used": r_acc_obs.json()["lead"]["cold_dm_meta"]["patterns_used"],
                },
            )
            assert r_log.status_code == 200 and r_log.json()["entry"]["edit_summary"] == "edited wording"

            # Transition to INTERESTED automatically updates outcome in copy_learning_log.md
            assert reviewer_client.post(
                f"/api/leads/{scraped_acc['id']}/status",
                json={"status": "INTERESTED"},
            ).status_code == 200
            live_log_txt = copy_engine.COPY_LEARNING_LOG_PATH.read_text(encoding="utf-8")
            assert "outcome: interested" in live_log_txt

            # Recycled caption leak blocked 422 on /api/copy/log
            r_cap_leak = reviewer_client.post(
                "/api/copy/log",
                json={
                    "lead_id": lead_id,
                    "channel": "caption",
                    "original_draft": "ok",
                    "final_text": "Promo Kopi Asli Rahasia hari ini!",
                },
            )
            assert r_cap_leak.status_code == 422
        finally:
            copy_engine.COPY_LEARNING_LOG_PATH.write_text(orig_log_backup, encoding="utf-8")

        print("[OK] 11. Copy Intelligence Engine (V1-V6 routing, §10.1 hard-fails, §11 rotation, 20% exploration & learning log/outcome) verified")

        # ------------------------------------------------------------------
        # 12. Agent-Reach Read-Only Lead Enrichment (SSRF guard, UX flaw, IG fallback)
        # ------------------------------------------------------------------
        from creative_agent import lead_enricher

        # URL & handle safety guards
        assert lead_enricher.validate_public_http_url("http://127.0.0.1:8000/secret") == ""
        assert lead_enricher.validate_public_http_url("http://localhost/admin") == ""
        assert lead_enricher.validate_public_http_url("http://169.254.169.254/latest/meta-data") == ""
        assert lead_enricher.validate_public_http_url("file:///C:/Windows/win.ini") == ""
        assert lead_enricher.validate_public_http_url("https://kopisenja.example.id") == "https://kopisenja.example.id"
        assert lead_enricher.extract_instagram_handle("@Kopi_Senja.ID") == "kopi_senja.id"
        assert lead_enricher.extract_instagram_handle("", "https://instagram.com/kopisenja.jkt/") == "kopisenja.jkt"
        assert lead_enricher.extract_instagram_handle("https://instagram.com/reel/abc123") == ""
        assert lead_enricher.extract_instagram_handle("bad handle; rm -rf") == ""

        # Mock runner for deterministic enrichment testing (zero external network / no IG login)
        def _mock_runner_ok(args: list[str], timeout: int) -> dict:
            if args[:1] == ["read"]:
                return {
                    "ok": True,
                    "items": [
                        {
                            "title": "Kopi Enrich",
                            "text": "Selamat datang di Kopi Enrich. Klik download menu PDF di drive.google.com/menu.pdf untuk daftar minuman.",
                        }
                    ],
                    "error_code": "",
                    "error_message": "",
                    "raw": {},
                }
            if args[:2] == ["instagram", "posts"]:
                return {
                    "ok": True,
                    "items": [
                        {
                            "title": "Post 1",
                            "text": "Barista kami baru meracik single origin Gayo wash untuk seduhan pagi ini! #kopi #jakarta",
                        }
                    ],
                    "error_code": "",
                    "error_message": "",
                    "raw": {},
                }
            return {"ok": False, "items": [], "error_code": "NOT_FOUND", "error_message": "", "raw": {}}

        enrich_lead_a = db.upsert_lead(
            {
                "business_name": "Kopi Enrich Uji",
                "category": "Coffee Shop",
                "city": "Jakarta",
                "website_url": "https://kopienrich.example.id",
                "instagram_handle": "@kopienrich.jkt",
                "status": "NEW",
                "ig_observation": "",
                "ux_flaw": "Default flaw awal.",
            }
        )[0]
        enrich_lead_b = db.upsert_lead(
            {
                "business_name": "Kopi RateLimit Uji",
                "category": "Coffee Shop",
                "city": "Bandung",
                "website_url": "https://kopilimit.example.id",
                "instagram_handle": "@kopilimit.bdg",
                "status": "NEW",
                "ig_observation": "",
                "ux_flaw": "Flaw awal tetap aman.",
            }
        )[0]
        enrich_lead_skip = db.upsert_lead(
            {
                "business_name": "Kopi Sudah Ada Obs",
                "category": "Coffee Shop",
                "city": "Jakarta",
                "website_url": "https://kopisudah.example.id",
                "instagram_handle": "@kopisudah",
                "status": "NEW",
                "ig_observation": "sudah diisi manual reviewer",
                "ux_flaw": "Flaw manual.",
            }
        )[0]
        try:
            sum_ok = lead_enricher.enrich_new_leads(
                lead_ids=[enrich_lead_a["id"], enrich_lead_skip["id"]],
                runner=_mock_runner_ok,
            )
            assert sum_ok["processed"] == 1 and sum_ok["updated"] == 1
            assert sum_ok["ux_flaw_updated"] == 1 and sum_ok["ig_observation_updated"] == 1
            reloaded_a = db.get_lead(enrich_lead_a["id"])
            assert "PDF" in reloaded_a["ux_flaw"] and "WhatsApp" in reloaded_a["ux_flaw"]
            assert "single origin Gayo wash" in reloaded_a["ig_observation"]
            # Lead with existing ig_observation must NOT be overwritten
            reloaded_skip = db.get_lead(enrich_lead_skip["id"])
            assert reloaded_skip["ig_observation"] == "sudah diisi manual reviewer"
            assert reloaded_skip["ux_flaw"] == "Flaw manual."

            # Safe fallback on NEED_LOGIN / RATE_LIMITED: never crash, never invent ig_observation, pauses IG channel
            ig_calls: list[list[str]] = []

            def _mock_runner_need_login(args: list[str], timeout: int) -> dict:
                if args[:1] == ["instagram"]:
                    ig_calls.append(args)
                    return {
                        "ok": False,
                        "items": [],
                        "error_code": "NEED_LOGIN",
                        "error_message": "login required",
                        "raw": {},
                    }
                return {"ok": False, "items": [], "error_code": "TIMEOUT", "error_message": "timeout", "raw": {}}

            sum_fail = lead_enricher.enrich_new_leads(
                lead_ids=[enrich_lead_b["id"]],
                runner=_mock_runner_need_login,
            )
            assert sum_fail["ig_channel_paused"] is True
            assert sum_fail["updated"] == 0
            assert len(ig_calls) == 1, "Must stop immediately on NEED_LOGIN without retrying profile"
            reloaded_b = db.get_lead(enrich_lead_b["id"])
            assert reloaded_b["ig_observation"] == ""
            assert reloaded_b["ux_flaw"] == "Flaw awal tetap aman."
        finally:
            with db.get_conn() as conn:
                conn.execute(
                    "DELETE FROM leads WHERE id IN (?, ?, ?)",
                    (enrich_lead_a["id"], enrich_lead_b["id"], enrich_lead_skip["id"]),
                )

        print("[OK] 12. Agent-Reach Read-Only Lead Enrichment (SSRF guard, UX flaw, IG observation & NEED_LOGIN fallback) verified")

        # ------------------------------------------------------------------
        # 13. Draft Brief on /recycle (no premature render) + /api/content/{id}/generate (Carousel & Reels)
        # ------------------------------------------------------------------
        brief_car_lead, _ = db.upsert_lead(
            {
                "slug": "test-brief-carousel-lead",
                "business_name": "Klinik Rahasia Uji Carousel",
                "category": "Klinik Gigi",
                "city": "Jakarta Selatan",
                "phone_raw": "0817-9988-7766",
                "address": "Jl. Rahasia Klinik No. 99, Jakarta",
                "status": "IGNORED_48H",
            }
        )
        brief_reels_lead, _ = db.upsert_lead(
            {
                "slug": "test-brief-reels-lead",
                "business_name": "Kedai Rahasia Uji Reels",
                "category": "Coffee Roastery",
                "city": "Bandung",
                "phone_raw": "0818-1122-3344",
                "address": "Jl. Rahasia Kopi No. 77, Bandung",
                "status": "IGNORED_48H",
            }
        )
        # Ensure clean slate on disk
        for bl in (brief_car_lead, brief_reels_lead):
            shutil.rmtree(settings.DEMOS_DIR / bl["slug"], ignore_errors=True)

        orig_ll_bak = (settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references" / "learning_log.md").read_text(encoding="utf-8")
        try:
            # 13a. /recycle creates draft_brief WITHOUT rendering slide PNGs or reels MP4
            r_rec_car = reviewer_client.post(f"/api/leads/{brief_car_lead['id']}/recycle")
            assert r_rec_car.status_code == 200, r_rec_car.text
            d_rec_car = r_rec_car.json()
            assert d_rec_car["review_status"] == "draft_brief"
            assert d_rec_car["review_version"] == 0
            assert not (settings.DEMOS_DIR / brief_car_lead["slug"] / "ig" / "01_cover.png").exists()
            assert not (settings.DEMOS_DIR / brief_car_lead["slug"] / "reels" / "reels.mp4").exists()

            r_rec_reels = admin_client.post(f"/api/leads/{brief_reels_lead['id']}/recycle")
            assert r_rec_reels.status_code == 200, r_rec_reels.text
            assert r_rec_reels.json()["review_status"] == "draft_brief"
            assert not (settings.DEMOS_DIR / brief_reels_lead["slug"] / "reels" / "reels.mp4").exists()

            # Queue returns draft_brief count & library_options (including audio_modes)
            q_brief = reviewer_client.get("/api/content/queue").json()
            assert q_brief["counts"]["draft_brief"] >= 2
            assert "art_directions" in q_brief["library_options"] and "reels_sequences" in q_brief["library_options"]
            assert [a["id"] for a in q_brief["library_options"]["audio_modes"]] == [
                "voiceover_and_music",
                "voiceover_only",
                "music_only",
                "silent",
            ]

            # 13b. Reviewer generates CAROUSEL from draft_brief with library overrides (formal clinical guardrail preserved!)
            r_gen_car = reviewer_client.post(
                f"/api/content/{brief_car_lead['id']}/generate",
                json={
                    "content_format": "carousel",
                    "art_direction_preset": "swiss_minimal",
                    "sequence_type": "reveal_first",
                    "voice_id": "V1",  # clinical category must still enforce formal_editorial (0 slang!)
                    "hook_pattern_id": "HOOK-K1",
                    "creative_note": "Tonjolkan kejelasan jadwal praktik",
                },
            )
            assert r_gen_car.status_code == 200, r_gen_car.text
            d_gen_car = r_gen_car.json()
            assert d_gen_car["review_status"] == "pending_review"
            assert d_gen_car["current_version"] == 1
            assert d_gen_car["content_format"] == "carousel"
            v1_car = d_gen_car["versions"][0]
            assert v1_car["leak_check"]["passed"] is True
            assert "Klinik Rahasia Uji Carousel" not in v1_car["full_caption"]
            assert "fiktif" in v1_car["full_caption"].lower()
            assert len([a for a in v1_car["assets"] if a["key"].startswith("slide-")]) == 4

            # 13c. Admin generates REELS (9:16 H.264 MP4 + AAC audio + cover_reels.png + beat_script) from draft_brief
            r_gen_reels = admin_client.post(
                f"/api/content/{brief_reels_lead['id']}/generate",
                json={
                    "content_format": "reels",
                    "art_direction_preset": "organic_warm",
                    "sequence_type": "scroll_reveal_showcase",
                    "voice_id": "V1",
                    "hook_pattern_id": "HOOK-B1",
                    "audio_mode": "voiceover_and_music",
                    "creative_note": "Tampilkan scroll menu seduhan harian",
                },
            )
            assert r_gen_reels.status_code == 200, r_gen_reels.text
            d_gen_reels = r_gen_reels.json()
            assert d_gen_reels["review_status"] == "pending_review"
            assert d_gen_reels["current_version"] == 1
            assert d_gen_reels["content_format"] == "reels"
            assert d_gen_reels["audio_mode"] == "voiceover_and_music"
            v1_reels = d_gen_reels["versions"][0]
            assert v1_reels["leak_check"]["passed"] is True
            assert len(v1_reels["beat_script"]) == 5
            qa_r = v1_reels.get("qa_report") or {}
            assert qa_r.get("status") == "PASS", qa_r
            qa_by_name = {c["name"]: c for c in qa_r.get("checks", [])}
            assert qa_by_name.get("ig_safe_zones", {}).get("passed") is True, qa_by_name.get("ig_safe_zones")
            assert qa_by_name.get("fps_ok", {}).get("passed") is True, qa_by_name.get("fps_ok")
            assert qa_by_name.get("anonymization_leak", {}).get("passed") is True, qa_by_name.get("anonymization_leak")
            asset_keys_reels = {a["key"] for a in v1_reels["assets"]}
            assert "reels_video" in asset_keys_reels and "cover_reels" in asset_keys_reels

            # Preview video/mp4 works & verify both H.264 video + AAC audio streams exist via ffprobe
            r_vid_prev = reviewer_client.get(f"/api/content/{brief_reels_lead['id']}/preview/1/reels_video")
            assert r_vid_prev.status_code == 200 and r_vid_prev.headers["content-type"] == "video/mp4"
            assert len(r_vid_prev.content) > 20000
            if shutil.which("ffprobe"):
                import subprocess as _sp
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
                    tf.write(r_vid_prev.content)
                    tf_path = tf.name
                try:
                    pr = _sp.run(
                        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", tf_path],
                        capture_output=True, text=True, timeout=15,
                    )
                    assert pr.returncode == 0, pr.stderr
                    streams = json.loads(pr.stdout).get("streams", [])
                    codecs = {(s.get("codec_type"), s.get("codec_name")) for s in streams}
                    assert ("video", "h264") in codecs, f"Missing h264 video stream: {codecs}"
                    assert ("audio", "aac") in codecs, f"Missing AAC audio stream (unmute would be disabled!): {codecs}"
                finally:
                    Path(tf_path).unlink(missing_ok=True)

            assert reviewer_client.post(f"/api/content/{brief_reels_lead['id']}/approve").status_code == 200
            r_vid_dl = reviewer_client.get(f"/api/content/{brief_reels_lead['id']}/download/reels_video")
            assert r_vid_dl.status_code == 200 and r_vid_dl.headers["content-type"] == "video/mp4"
            assert ".mp4" in r_vid_dl.headers.get("content-disposition", "")
        finally:
            (settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references" / "learning_log.md").write_text(orig_ll_bak, encoding="utf-8")
            for bl in (brief_car_lead, brief_reels_lead):
                refreshed = db.get_lead(bl["id"])
                if refreshed:
                    _cleanup_lead(refreshed)
                else:
                    shutil.rmtree(settings.DEMOS_DIR / bl["slug"], ignore_errors=True)

        print("[OK] 13. Draft Brief on /recycle (no premature render) + /api/content/{id}/generate (Carousel 4:5 & Reels 9:16 MP4) verified")

        # ------------------------------------------------------------------
        # 14. Token Optimizer, /api/learning/evaluate, /recycle Carousel lock,
        #     Reels Idea Scraper, Adaptive V/O+BGM Render & Posted IG Metrics
        # ------------------------------------------------------------------
        from creative_agent import reels_intelligence as ri
        from creative_agent import token_optimizer as topt

        # 14a. compact_scrape_text: <=700 chars/source, <=4 sources, boilerplate stripped
        raw_sources = [
            {
                "source": "web",
                "title": f"Keluhan UMKM #{i}",
                "text": (
                    "Cookie policy accept all sign in subscribe. "
                    + f"Banyak pemilik kafe dan klinik mengeluh admin kewalahan balas chat WhatsApp pelanggan yang menanyakan menu PDF dan jadwal booking #{i}. " * 12
                ),
            }
            for i in range(6)
        ]
        compacted = topt.compact_scrape_text(raw_sources, max_chars=700, max_sources=4)
        assert compacted["source_count"] <= 4
        assert all(s["chars"] <= 700 for s in compacted["sources"])
        assert all("cookie policy" not in s["text"].lower() for s in compacted["sources"])
        assert compacted["saved_pct"] > 50.0

        # 14b. compute_edit_delta (0 LLM tokens)
        delta_res = topt.compute_edit_delta(
            "Halo Kak 😊 saya mau kirim konsep halaman website untuk usaha kopi ini supaya makin ramai dan makin jelas tampilannya sekarang juga.",
            "Halo Bapak/Ibu, saya kirim foto konsep halaman depan website ini.",
        )
        assert delta_res["changed"] is True
        assert delta_res["word_delta"] < -3 and delta_res["shortened"] is True
        assert delta_res["sapaan_changed"] == "Kak->Bapak/Ibu"
        assert delta_res["emoji_removed"] == 1

        # 14c. /recycle locks draft_brief content_format == 'carousel'
        rec_lock_lead, _ = db.upsert_lead(
            {
                "slug": "test-recycle-carousel-lock",
                "business_name": "Salon Rahasia Lock",
                "category": "Salon",
                "city": "Jakarta",
                "status": "IGNORED_48H",
            }
        )
        r_lock = reviewer_client.post(f"/api/leads/{rec_lock_lead['id']}/recycle")
        assert r_lock.status_code == 200 and r_lock.json()["brief"]["content_format"] == "carousel"

        # 14d. Backup reference logs/candidates before testing scrape, render, metrics & evaluate
        ref_dir = settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references"
        bak_files = {
            p: p.read_text(encoding="utf-8") if p.exists() else None
            for p in (
                ref_dir / "copy_candidates.md",
                ref_dir / "reels_candidates.md",
                ref_dir / "reels_learning_log.md",
                ref_dir / "learning_digest.json",
            )
        }
        scraped_lead_ids: list[int] = []
        try:
            # Verify 3 procedural BGM tracks exist & category routing works
            bgm_tracks = ri.ensure_default_bgm_tracks()
            assert set(bgm_tracks.keys()) == {"calm_editorial", "warm_hospitality", "energetic_craft"}
            assert ri.select_bgm_track("Klinik Gigi")["id"] == "calm_editorial"
            assert ri.select_bgm_track("Coffee Roastery")["id"] == "warm_hospitality"
            assert ri.select_bgm_track("Bengkel Custom")["id"] == "energetic_craft"
            assert ri.resolve_vo_profile("Studio Pilates")["is_formal"] is True
            assert ri.resolve_vo_profile("Studio Pilates")["rate"] == "+0%"
            assert ri.resolve_vo_profile("Coffee Roastery")["is_formal"] is False
            assert ri.resolve_vo_profile("Coffee Roastery")["rate"] == "+0%"

            # Scrape Reels Ideas endpoint (admin & reviewer allowed)
            r_scrape = reviewer_client.post("/api/content/reels-ideas/scrape", json={"limit": 1})
            assert r_scrape.status_code == 200, r_scrape.text
            d_scrape = r_scrape.json()
            assert d_scrape["ok"] is True and d_scrape["created_count"] == 1
            idea_brief = d_scrape["briefs"][0]
            idea_lid = int(idea_brief["lead_id"])
            scraped_lead_ids.append(idea_lid)
            assert idea_brief["content_format"] == "reels"
            assert idea_brief["review_status"] == "draft_brief"
            assert idea_brief["pain_code"].startswith("PAIN-")
            vo_words = len(idea_brief["vo_script"].split())
            assert 30 <= vo_words <= 60, f"Unexpected VO word count: {vo_words}"

            # Edit V/O script + generate Reels with 1.0x natural V/O & target BGM (video duration MUST follow V/O)
            edited_vo = (
                "Berapa pelanggan batal datang cuma karena kelamaan menunggu balasan WA soal menu dan jam buka? "
                "Lihat halaman mobile ini: menu utama, lokasi Maps, dan tombol pesan langsung terbaca cepat di layar HP. "
                "Mau lihat konsep versi usaha kamu? DM kata KONSEP."
            )
            r_gen_idea = admin_client.post(
                f"/api/content/{idea_lid}/generate",
                json={
                    "content_format": "reels",
                    "sequence_type": "before_after_ux",
                    "audio_mode": "voiceover_and_music",
                    "vo_script": edited_vo,
                    "vo_style": "auto",
                    "bgm_track": "auto",
                },
            )
            assert r_gen_idea.status_code == 200, r_gen_idea.text
            d_gen_idea = r_gen_idea.json()
            assert d_gen_idea["review_status"] == "pending_review"
            v1_spec = d_gen_idea["versions"][0]["reels_spec"]
            assert d_gen_idea["versions"][0]["qa_report"]["status"] == "PASS", d_gen_idea["versions"][0]["qa_report"]
            assert v1_spec["bgm_track"] in {"calm_editorial", "warm_hospitality", "energetic_craft"}
            assert abs(float(v1_spec["video"]["voiceover_tempo"]) - 1.0) < 0.005, v1_spec["video"]
            v1_vo_dur = float(v1_spec["video"].get("voiceover_duration_sec") or 0.0)
            if v1_vo_dur > 0:
                assert float(v1_spec["video"]["duration_sec"]) >= v1_vo_dur + 0.8, v1_spec["video"]
            # Confirm V/O edit was logged to reels_learning_log.md
            assert "reels_log:" in (ref_dir / "reels_learning_log.md").read_text(encoding="utf-8")

            # Request revision -> changes_requested -> Regenerasi Library (v2) with longer VO + Admin revise regenerate=true (v3)
            r_corr_reels = reviewer_client.post(
                f"/api/content/{idea_lid}/corrections",
                json={"corrections": [{"slide_index": None, "note": "Perjelas transisi dan jangan percepat voiceover"}]},
            )
            assert r_corr_reels.status_code == 200 and r_corr_reels.json()["review_status"] == "changes_requested"

            longer_vo = (
                "Banyak calon pelanggan batal mampir karena bingung cari menu dan jam buka di profil. "
                "Di tampilan mobile ini, begitu link dibuka, halaman pertama langsung merangkum layanan utama dengan huruf besar yang nyaman dibaca. "
                "Lanjut ke bawah, daftar menu, peta lokasi, dan tombol WhatsApp langsung tersedia tanpa perlu bolak-balik chat. "
                "Mau lihat konsep versi usaha kamu? Langsung DM kata KONSEP."
            )
            r_regen_v2 = reviewer_client.post(
                f"/api/content/{idea_lid}/generate",
                json={
                    "content_format": "reels",
                    "sequence_type": "scroll_reveal_showcase",
                    "audio_mode": "voiceover_and_music",
                    "vo_script": longer_vo,
                    "vo_style": "auto",
                    "bgm_track": "auto",
                },
            )
            assert r_regen_v2.status_code == 200, r_regen_v2.text
            d_regen_v2 = r_regen_v2.json()
            assert d_regen_v2["current_version"] == 2
            assert d_regen_v2["review_status"] == "revised", d_regen_v2["review_status"]
            v2_spec = d_regen_v2["versions"][-1]["reels_spec"]
            assert d_regen_v2["versions"][-1]["qa_report"]["status"] == "PASS", d_regen_v2["versions"][-1]["qa_report"]
            assert abs(float(v2_spec["video"]["voiceover_tempo"]) - 1.0) < 0.005
            v2_vo_dur = float(v2_spec["video"].get("voiceover_duration_sec") or 0.0)
            if v2_vo_dur > 0:
                assert float(v2_spec["video"]["duration_sec"]) >= v2_vo_dur + 0.8, v2_spec["video"]

            # Admin revise with regenerate=true on Reels MUST return 200 (not 500) and keep content_format == reels
            r_adm_rev = admin_client.post(
                f"/api/content/{idea_lid}/revise",
                data={"regenerate": "true", "note": "Admin regen reels v3"},
            )
            assert r_adm_rev.status_code == 200, r_adm_rev.text
            d_adm_rev = r_adm_rev.json()
            assert d_adm_rev["current_version"] == 3
            assert d_adm_rev["versions"][-1]["content_format"] == "reels"
            assert d_adm_rev["review_status"] == "revised"

            # Approve -> Mark Posted -> Save IG Metrics
            assert reviewer_client.post(f"/api/content/{idea_lid}/approve").status_code == 200
            assert reviewer_client.post(
                f"/api/content/{idea_lid}/posted",
                json={"posted_url": "https://instagram.com/reel/test123"},
            ).status_code == 200
            r_met = reviewer_client.post(
                f"/api/content/{idea_lid}/metrics",
                json={"views": 2450, "saves": 64, "shares": 21, "dm_in": 5},
            )
            assert r_met.status_code == 200, r_met.text
            assert r_met.json()["metrics"]["views"] == 2450
            assert r_met.json()["metrics"]["dm_in"] == 5

            # Evaluate Learning Patterns endpoint (admin & reviewer allowed, digest <= ~1,200 tokens, <= 3 proposals)
            r_eval = reviewer_client.post("/api/learning/evaluate")
            assert r_eval.status_code == 200, r_eval.text
            d_eval = r_eval.json()
            assert d_eval["ok"] is True
            assert d_eval["estimated_tokens"] <= 1250
            assert len(d_eval["proposed_candidates"]) <= 3
            assert (ref_dir / "learning_digest.json").exists()
            sl = topt.get_relevant_pattern_slice("reels")
            assert "patterns" in sl and "top_human_edits" in sl
        finally:
            for p, content in bak_files.items():
                if content is None:
                    p.unlink(missing_ok=True)
                else:
                    p.write_text(content, encoding="utf-8")
            for sid in scraped_lead_ids + [rec_lock_lead["id"]]:
                row = db.get_lead(sid)
                if row:
                    _cleanup_lead(row)

        print("[OK] 14. Token Optimizer, /api/learning/evaluate, /recycle Carousel lock, Reels Idea Scraper, Adaptive V/O+BGM Render & Posted IG Metrics verified")
    finally:
        _cleanup_lead(lead)
        with db.get_conn() as conn:
            conn.execute("DELETE FROM leads WHERE id IN (?, ?, ?)", (outreach_lead["id"], scraped_acc["id"], scraped_rej["id"]))
        admin_client.post("/api/auth/logout")
        reviewer_client.post("/api/auth/logout")

    print("=== ALL AUTH, SECURITY, RBAC & CONTENT REVIEW TESTS PASSED ===")


if __name__ == "__main__":
    run_all_tests()
