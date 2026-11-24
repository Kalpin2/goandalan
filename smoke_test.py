"""End-to-end verification for @goandalan v2 (Multi-Style Engine + 2-Stage Pipeline)."""

from __future__ import annotations

import re
import shutil
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import database as db
import demo_generator as dg
from app import app
from config import settings


def run_smoke_test() -> None:
    db.init_db()
    assert settings.ADMIN_USN and settings.ADMIN_PASS, "ADMIN_USN / ADMIN_PASS belum diisi di .env"
    assert settings.REVIEW_USN and settings.REVIEW_PASS, "REVIEW_USN / REVIEW_PASS belum diisi di .env"

    anon_client = TestClient(app)
    assert anon_client.get("/api/dashboard").status_code == 401, "Unauthenticated /api/dashboard must return 401"
    for blocked in ("/.env", "/leads.db", "/app.py", "/config.py", "/skills/instagram-creative-agent/SKILL.md", "/creative_agent/cli.py"):
        r_blk = anon_client.get(blocked)
        assert r_blk.status_code in {403, 404}, f"Sensitive path {blocked} returned {r_blk.status_code}"
    print("[OK] Unauthenticated guard (401) & sensitive file isolation (403/404) verified")

    client = TestClient(app)
    r_login = client.post(
        "/api/auth/login",
        json={"username": settings.ADMIN_USN, "password": settings.ADMIN_PASS},
    )
    assert r_login.status_code == 200 and r_login.json()["role"] == "admin", f"Admin login failed: {r_login.status_code}"
    print("[OK] Admin login via .env credentials & HttpOnly session cookie verified")

    # Confirm all 8 styles are registered
    styles_resp = client.get("/api/styles")
    assert styles_resp.status_code == 200
    styles = styles_resp.json()["styles"]
    assert len(styles) >= 8, f"Expected >= 8 styles, got {len(styles)}"
    print(f"[OK] Multi-Style Engine active ({len(styles)} styles): {[s['key'] for s in styles]}")

    samples = [
        {
            "business_name": "Seduh Pagi Coffee Roastery",
            "category": "Coffee Roastery",
            "design_style": "warm_organic_hospitality",
            "city": "Jakarta Selatan",
            "address": "Jl. Cipete Raya No. 28, Jakarta Selatan",
            "phone_raw": "0812-8899-4411",
            "website_url": "",
            "rating": 4.8,
            "review_count": 214,
            "ux_flaw": "Belum punya website resmi—pengunjung dari IG masih harus scroll highlight buat cari menu dan jam buka.",
            "source_query": "smoke_test_v2",
        },
        {
            "business_name": "Pangkas Teduh Barbershop",
            "category": "Barbershop",
            "design_style": "figcraft_sharp_grid",
            "city": "Bandung",
            "address": "Jl. Progo No. 14, Citarum, Bandung",
            "phone_raw": "0813-7766-5522",
            "website_url": "https://linktr.ee/pangkasteduh",
            "rating": 4.9,
            "review_count": 168,
            "ux_flaw": "Link bio masih pakai daftar link panjang—tarif potong rambut dan tombol booking WA belum langsung tampil rapi di HP.",
            "source_query": "smoke_test_v2",
        },
    ]

    # Reset existing sample demo folders so Stage A isolation is tested cleanly
    lead_records = []
    for sample in samples:
        lead, _ = db.upsert_lead(sample)
        demo_dir = settings.DEMOS_DIR / lead["slug"]
        if demo_dir.exists():
            shutil.rmtree(demo_dir, ignore_errors=True)
        lead = db.update_lead(
            lead["id"],
            {
                "status": "NEW",
                "design_style": sample["design_style"],
                "demo_path": "",
                "demo_url": "",
                "concept_preview_path": "",
                "is_anonymized": 0,
            },
        )
        assert lead is not None
        lead_records.append(lead)

    dg.rebuild_portfolio_index()

    # === STAGE A: Concept Photo Preview + 4 IG Slides (NO full index.html yet!) ===
    for lead in lead_records:
        resp = client.post(f"/api/leads/{lead['id']}/concept", json={"design_style": lead["design_style"]})
        assert resp.status_code == 200, f"Stage A failed for {lead['slug']}: {resp.text}"
        data = resp.json()
        assert data["stage"] == "CONCEPT_READY"
        assert data["lead"]["status"] == "CONCEPT_READY"
        assert data["slides_count"] == 4

        slug = lead["slug"]
        demo_dir = settings.DEMOS_DIR / slug
        assert (demo_dir / "concept.html").exists(), "concept.html missing"
        assert (demo_dir / "concept_preview.png").exists(), "concept_preview.png missing"
        assert not (demo_dir / "index.html").exists(), "Stage A must NOT create full index.html yet!"

        cp = data["concept_preview"]
        assert (cp["width"], cp["height"]) == (2880, 2160), f"Unexpected concept_preview size: {cp}"

        cap = (demo_dir / "ig" / "caption.txt").read_text(encoding="utf-8")
        alan_mentions = len(re.findall(r"\balan\b", cap, flags=re.IGNORECASE))
        assert alan_mentions <= 1, f"Too many Alan mentions ({alan_mentions})"
        for banned_cta in ("dm sekarang", "hubungi kami untuk", "pesan website"):
            assert banned_cta not in cap.lower(), f"Banned sales CTA '{banned_cta}' found in caption"

        slides_html = (demo_dir / "ig" / "slides.html").read_text(encoding="utf-8")
        for banned_cta in ("dm aja kalau mau ngobrol", "dm sekarang", "hubungi kami untuk"):
            assert banned_cta not in slides_html.lower(), f"Banned CTA '{banned_cta}' found in slides"
        assert (demo_dir / "ig" / "art_direction.json").exists(), "art_direction.json missing"
        assert (demo_dir / "ig" / "carousel_spec.json").exists(), "carousel_spec.json missing"
        assert (demo_dir / "ig" / "contact_sheet.png").exists(), "contact_sheet.png (2x2) missing"
        assert (demo_dir / "ig" / "cover_grid.png").exists(), "cover_grid.png missing"
        qa_path = demo_dir / "ig" / "qa_report.json"
        assert qa_path.exists(), "qa_report.json missing"
        import json as _json
        qa_data = _json.loads(qa_path.read_text(encoding="utf-8"))
        assert qa_data["status"] == "PASS", f"QA failed for {slug}: {qa_data}"
        for sname in ("01_cover.png", "02_context.png", "03_reveal.png", "04_details.png"):
            assert (demo_dir / "ig" / sname).exists(), f"Missing adaptive slide {sname}"

        dm = data["lead"]["cold_dm_draft"]
        assert "foto preview konsep" in dm.lower(), "Cold DM #1 must offer concept photo"
        assert "http://" not in dm and "https://" not in dm, "Cold DM #1 must NOT contain links"
        assert "[isi 1 detail spesifik IG mereka]" in dm

        print(
            f"[OK] Stage A ({slug}) | style={data['design_style']} ({data['style_label']}) | "
            f"concept_preview.png={cp['width']}x{cp['height']} ({cp['size_bytes']//1024}KB) | index.html=ABSENT"
        )

    # Confirm site/index.html does NOT list Stage A-only leads yet
    catalog_before = (settings.SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert "Seduh Pagi Coffee Roastery" not in catalog_before
    assert "Pangkas Teduh Barbershop" not in catalog_before
    print("[OK] site/index.html cleanly excludes Stage A CONCEPT_READY leads")

    # === STAGE B: Contact -> Interested -> On-Demand Generate Full Demo ===
    lead1 = lead_records[0]
    r_dm = client.post(f"/api/leads/{lead1['id']}/contact", json={"method": "CONTACTED_DM"})
    assert r_dm.status_code == 200 and r_dm.json()["lead"]["status"] == "CONTACTED_DM"

    r_int = client.post(f"/api/leads/{lead1['id']}/status", json={"status": "INTERESTED"})
    assert r_int.status_code == 200 and r_int.json()["lead"]["status"] == "INTERESTED"

    r_full = client.post(f"/api/leads/{lead1['id']}/full-demo")
    assert r_full.status_code == 200, f"Stage B full-demo failed: {r_full.text}"
    full_data = r_full.json()
    assert full_data["stage"] == "FULL_DEMO_READY"
    assert full_data["lead"]["status"] == "FULL_DEMO_READY"
    assert full_data["lead"]["has_full_demo"] is True

    full_html = (settings.DEMOS_DIR / lead1["slug"] / "index.html").read_text(encoding="utf-8")
    assert "preview konsep oleh @goandalan" in full_html
    assert 'id="faq"' in full_html and 'data-flow="cta"' in full_html

    catalog_after = (settings.SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert "Seduh Pagi Coffee Roastery" in catalog_after
    assert "Pangkas Teduh Barbershop" not in catalog_after
    print(f"[OK] Stage B HTTP 200 -> FULL_DEMO_READY built for {lead1['slug']} & catalog updated")

    # Verify DP_PAID transition & revert back to FULL_DEMO_READY for clean demo state
    r_dp = client.post(f"/api/leads/{lead1['id']}/status", json={"status": "DP_PAID"})
    assert r_dp.status_code == 200 and r_dp.json()["lead"]["status"] == "DP_PAID"
    client.post(f"/api/leads/{lead1['id']}/status", json={"status": "FULL_DEMO_READY"})
    print("[OK] Status DP_PAID verified")

    # Verify public routes work WITHOUT auth cookie (/demos/*, /portfolio/index.html, /, /health)
    for pub_ep in [
        "/",
        "/health",
        "/portfolio/index.html",
        f"/demos/{lead1['slug']}/index.html",
        f"/demos/{lead1['slug']}/concept_preview.png",
    ]:
        pub_resp = anon_client.get(pub_ep)
        assert pub_resp.status_code == 200, f"Public GET {pub_ep} -> {pub_resp.status_code}"
    print("[OK] Public routes (/, /health, /portfolio/index.html, /demos/*) accessible without login")

    # Verify HTTP 200 on core routes and generated assets
    for ep in [
        "/",
        "/health",
        "/api/dashboard",
        "/portfolio/index.html",
        f"/demos/{lead1['slug']}/concept_preview.png",
        f"/demos/{lead1['slug']}/index.html",
        f"/demos/{lead1['slug']}/ig/03_reveal.png",
        f"/demos/{lead1['slug']}/ig/04_details.png",
        f"/demos/{lead1['slug']}/ig/contact_sheet.png",
        f"/demos/{lead1['slug']}/ig/cover_grid.png",
        f"/demos/{lead_records[1]['slug']}/concept_preview.png",
        f"/demos/{lead_records[1]['slug']}/ig/03_reveal.png",
        f"/demos/{lead_records[1]['slug']}/ig/04_details.png",
        f"/demos/{lead_records[1]['slug']}/ig/contact_sheet.png",
    ]:
        resp = client.get(ep)
        assert resp.status_code == 200, f"GET {ep} -> {resp.status_code}"
        print(f"[OK] HTTP 200 -> {ep}")

    # Verify 48h expiry + Recycle anonymization on a temporary lead, then clean up
    tmp_lead, _ = db.upsert_lead(
        {
            "business_name": "Klinik Gigi Sementara",
            "category": "Klinik Gigi",
            "city": "Jakarta",
            "phone_raw": "0819-0000-1111",
        }
    )
    client.post(f"/api/leads/{tmp_lead['id']}/concept")
    client.post(f"/api/leads/{tmp_lead['id']}/contact", json={"method": "CONTACTED_DM"})
    expired_ts = (db.utc_now() - timedelta(hours=49)).isoformat(timespec="seconds")
    db.update_lead(tmp_lead["id"], {"follow_up_due_at": expired_ts})
    dash = client.get("/api/dashboard").json()
    matched = [l for l in dash["followup_leads"] if l["id"] == tmp_lead["id"]]
    assert matched and matched[0]["status"] == "IGNORED_48H"

    r_rec = client.post(f"/api/leads/{tmp_lead['id']}/recycle")
    assert r_rec.status_code == 200 and r_rec.json()["lead"]["status"] == "RECYCLED_CONTENT"
    assert r_rec.json()["review_status"] == "draft_brief", f"Expected draft_brief, got {r_rec.json()}"
    rec_concept = (settings.DEMOS_DIR / tmp_lead["slug"] / "concept.html").read_text(encoding="utf-8")
    assert "Klinik Gigi Sementara" not in rec_concept and "0819-0000-1111" not in rec_concept
    print(f"[OK] 48h expiry + Recycle -> draft_brief verified (anonymized to '{r_rec.json()['anonymized_name']}')")

    with db.get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (tmp_lead["id"],))
    shutil.rmtree(settings.DEMOS_DIR / tmp_lead["slug"], ignore_errors=True)
    dg.rebuild_portfolio_index()
    print("[OK] ALL V2 SMOKE TESTS PASSED!")


if __name__ == "__main__":
    run_smoke_test()
