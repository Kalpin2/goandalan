"""Self-Expanding Niche-to-Goal Engine for @goandalan.

Maps any business prospect from:
  business_category
    -> primary_business_goal
    -> website_section_architecture
    -> website_visual_theme
    -> 4-layer carousel typography_direction

Also integrates with `D:\\AI WORKSPACE` (`REPOSITORY-REGISTRY.md` + NVIDIA SkillSpector)
to verify skill coverage and enforce the mandatory pre-clone security audit gate:
  scout -> audit NVIDIA SkillSpector -> clone (if PASS) -> update registry.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from creative_agent.typography_engine import plan_typography_direction


AI_WORKSPACE_ROOT = Path(r"D:\AI WORKSPACE")
SKILLSPECTOR_EXE = AI_WORKSPACE_ROOT / "tools" / "SkillSpector" / ".venv" / "Scripts" / "skillspector.exe"
REPOS_DIR = AI_WORKSPACE_ROOT / "repos"
REGISTRY_PATH = (
    AI_WORKSPACE_ROOT
    / "obsidian-vault"
    / "hermes"
    / "MASTER-OBSIDIAN-HERMES"
    / "04-REPOSITORIES"
    / "REPOSITORY-REGISTRY.md"
)


NICHE_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "coffee_roastery": {
        "match": ("kopi", "coffee", "roast", "cafe", "kafe", "espresso", "matcha", "kedai"),
        "label": "Coffee Shop & Specialty Roastery",
        "primary_business_goal": "Hadirkan atmosfer ruang seduh, kurasi beans & menu dengan fotografi tajam, serta jam seduh + lokasi + pre-order WA tanpa ribet.",
        "website_section_architecture": [
            {"id": "atmosphere_hero", "purpose": "Atmosfer ruang seduh & fotografi full-bleed slow bar"},
            {"id": "curated_menu", "purpose": "Kurasi beans mingguan & menu minuman dengan foto editorial + harga jernih tanpa kartu kaku"},
            {"id": "space_ritual", "purpose": "Cerita ruang & ritual sangrai (suasana WFC, roast profile, manual brew)"},
            {"id": "hours_location_wa", "purpose": "Jam seduh harian, alamat + peta lokasi, FAQ ringkas, dan jalur pre-order WA"},
        ],
        "recommended_demo_style": "warm_organic_hospitality",
        "recommended_carousel_style": "organic_warm",
        "required_skill_domains": ["anti-slop-web-design", "editorial-typography", "hospitality-photography"],
        "photo_set": {
            "hero": "assets/demos/coffee_hero.png",
            "secondary": "assets/demos/coffee_beans.png",
            "accent": "assets/demos/coffee_matcha.png",
        },
    },
    "barbershop_grooming": {
        "match": ("barber", "pangkas", "cukur", "grooming", "salon", "hair"),
        "label": "Barbershop & Men's Grooming",
        "primary_business_goal": "Tampilkan presisi galeri gaya potongan, daftar layanan & tarif bersih tanpa kotak berat, dan alur booking slot WhatsApp tanpa antre.",
        "website_section_architecture": [
            {"id": "craft_hero", "purpose": "Hero arsitektural ruang pangkas dengan fotografi kursi & alat grooming"},
            {"id": "style_gallery", "purpose": "Galeri visual hasil potongan & detail craft barber"},
            {"id": "tariff_sheet", "purpose": "Daftar layanan & tarif bergaya editorial menu sheet (garis tipis, nol kotak berat)"},
            {"id": "booking_slot_wa", "purpose": "Alur 3 langkah booking slot, jam operasional, lokasi, FAQ & tombol WA langsung"},
        ],
        "recommended_demo_style": "figcraft_sharp_grid",
        "recommended_carousel_style": "swiss_minimal",
        "required_skill_domains": ["anti-slop-web-design", "swiss-constructivist-typography", "grooming-editorial"],
        "photo_set": {
            "hero": "assets/demos/barber_hero.png",
            "secondary": "assets/demos/barber_craft.png",
            "accent": "assets/demos/barber_tools.png",
        },
    },
    "aesthetic_clinic": {
        "match": ("estetika", "perawatan kulit", "derma", "skincare clinic", "aesthetic"),
        "label": "Klinik Estetika & Perawatan Kulit",
        "primary_business_goal": "Hadirkan kredibilitas dermatologi yang tenang lewat daftar tindakan transparan, alur konsultasi dokter, dan reservasi jadwal privat via WA.",
        "website_section_architecture": [
            {"id": "luxury_clinical_hero", "purpose": "Hero editorial tenang yang menampilkan standar klinis dan jalur konsultasi awal"},
            {"id": "treatment_dossier", "purpose": "Daftar perawatan kulit terkurasi lengkap dengan durasi dan estimasi transparan"},
            {"id": "consultation_protocol", "purpose": "Protokol analisis kulit, kenyamanan ruang privat, dan standar keamanan"},
            {"id": "schedule_location_wa", "purpose": "Jam praktik, lokasi klinik, FAQ pasien & reservasi konsultasi WA"},
        ],
        "recommended_demo_style": "dark_moody_luxury",
        "recommended_carousel_style": "cinematic_premium",
        "required_skill_domains": ["anti-slop-web-design", "editorial-typography"],
        "photo_set": {
            "hero": "assets/demos/clinic_hero.png",
            "secondary": "assets/demos/clinic_room.png",
            "accent": "assets/demos/clinic_serum.png",
        },
    },
    "pilates_movement": {
        "match": ("pilates", "movement", "reformer", "barre", "yoga"),
        "label": "Studio Pilates & Movement",
        "primary_business_goal": "Tunjukkan ketenangan ruang reformer, pilihan kelas kecil dan sesi privat, serta jadwal & booking sesi cepat lewat WA.",
        "website_section_architecture": [
            {"id": "sanctuary_hero", "purpose": "Hero terang penuh cahaya alami yang memperlihatkan ruang reformer studio"},
            {"id": "class_curations", "purpose": "Daftar kelas kecil, sesi privat, dan paket rutin dengan tarif jernih"},
            {"id": "movement_philosophy", "purpose": "Pendekatan postur, napas, dan pendampingan instruktur bersertifikat"},
            {"id": "schedule_booking_wa", "purpose": "Jam studio harian, lokasi tenang, FAQ pemula & booking sesi via WA"},
        ],
        "recommended_demo_style": "modern_editorial",
        "recommended_carousel_style": "organic_warm",
        "required_skill_domains": ["anti-slop-web-design", "editorial-typography", "hospitality-photography"],
        "photo_set": {
            "hero": "assets/demos/pilates_hero.png",
            "secondary": "assets/demos/pilates_studio.png",
            "accent": "assets/demos/pilates_detail.png",
        },
    },
    "artisan_bakery": {
        "match": ("sourdough", "bakery", "bakehouse", "pastry", "croissant", "viennoiserie", "roti"),
        "label": "Artisan Sourdough & Pastry Bakery",
        "primary_business_goal": "Pamerkan tekstur sourdough & viennoiserie hangat setiap pagi, jadwal keluar oven, dan pre-order loaf langsung lewat WA.",
        "website_section_architecture": [
            {"id": "oven_hero", "purpose": "Hero katalog kuliner dengan foto sourdough & pastry segar keluar oven"},
            {"id": "daily_bake_sheet", "purpose": "Menu harian sourdough & pastry lengkap dengan jam batch panggang dan harga"},
            {"id": "fermentation_craft", "purpose": "Proses fermentasi alami 24 jam, tepung pilihan, dan mentega laminasi"},
            {"id": "preorder_location_wa", "purpose": "Jam buka pagi, alamat bakehouse, FAQ simpan roti & pre-order WA"},
        ],
        "recommended_demo_style": "vibrant_modern_cafe",
        "recommended_carousel_style": "product_first",
        "required_skill_domains": ["anti-slop-web-design", "catalog-editorial-typography"],
        "photo_set": {
            "hero": "assets/demos/bakery_hero.png",
            "secondary": "assets/demos/bakery_sourdough.png",
            "accent": "assets/demos/bakery_pastry.png",
        },
    },
    "custom_garage": {
        "match": ("bengkel", "motor custom", "custom garage", "garage", "cafe racer", "scrambler", "chopper", "kustom"),
        "label": "Bengkel Motor Custom & Garage",
        "primary_business_goal": "Tampilkan karakter hasil bangun motor, rincian layanan fabrikasi & servis transparan, serta konsultasi konsep build langsung lewat WA.",
        "website_section_architecture": [
            {"id": "workshop_hero", "purpose": "Hero industrial tegas menonjolkan motor hasil bangun & ruang bengkel"},
            {"id": "build_service_sheet", "purpose": "Daftar layanan custom build, fabrikasi, tune-up & cat tanpa clutter"},
            {"id": "workshop_craft", "purpose": "Standar pengerjaan sasis, kelistrikan rapi, dan jadwal pengerjaan jelas"},
            {"id": "consult_location_wa", "purpose": "Jam bengkel, alamat workshop, FAQ estimasi build & konsultasi WA"},
        ],
        "recommended_demo_style": "neo_brutalist_street",
        "recommended_carousel_style": "bold_brutalist",
        "required_skill_domains": ["anti-slop-web-design", "swiss-constructivist-typography"],
        "photo_set": {
            "hero": "assets/demos/garage_hero.png",
            "secondary": "assets/demos/garage_build.png",
            "accent": "assets/demos/garage_tools.png",
        },
    },
    "clinic_wellness": {
        "match": ("klinik", "clinic", "gigi", "dental", "dokter", "skin", "derma", "estetika", "fisioterapi", "spa", "wellness"),
        "label": "Klinik, Dental & Wellness",
        "primary_business_goal": "Bangun rasa tenang & kepercayaan pasien lewat transparansi layanan, jadwal praktik jelas, dan reservasi konsultasi WA.",
        "website_section_architecture": [
            {"id": "calm_hero", "purpose": "Hero bersih yang menenangkan dengan jadwal praktik & jalur reservasi"},
            {"id": "treatment_ledger", "purpose": "Daftar perawatan terstruktur dengan estimasi transparan tanpa kartu ramai"},
            {"id": "care_standards", "purpose": "Alur kunjungan pasien dan standar kenyamanan klinik"},
            {"id": "schedule_location_wa", "purpose": "Jam praktik, lokasi mudah ditemukan, FAQ pasien & tombol jadwal WA"},
        ],
        "recommended_demo_style": "clean_swiss_minimal",
        "recommended_carousel_style": "data_infographic",
        "required_skill_domains": ["anti-slop-web-design", "swiss-grid-typography"],
        "photo_set": {
            "hero": "assets/demos/coffee_hero.png",
            "secondary": "assets/demos/barber_hero.png",
            "accent": "assets/demos/coffee_beans.png",
        },
    },
    "culinary_bistro": {
        "match": ("resto", "restaurant", "bakmi", "bakery", "roti", "cake", "pastry", "bistro", "kitchen", "dapur", "warung", "makan", "kuliner"),
        "label": "Kuliner, Bakery & Bistro",
        "primary_business_goal": "Gugah selera lewat sajian andalan, harga transparan tanpa PDF buram, dan reservasi meja / takeaway cepat lewat WA.",
        "website_section_architecture": [
            {"id": "dish_hero", "purpose": "Hero kuliner atmosferik dengan highlight sajian harian"},
            {"id": "menu_editorial", "purpose": "Daftar menu editorial dengan kategori jelas dan harga mudah dipindai"},
            {"id": "kitchen_story", "purpose": "Standar dapur segar & opsi grup / takeaway"},
            {"id": "reserve_location_wa", "purpose": "Jam buka, alamat, FAQ & tombol reservasi WA"},
        ],
        "recommended_demo_style": "coastal_terracotta",
        "recommended_carousel_style": "product_first",
        "required_skill_domains": ["anti-slop-web-design", "catalog-editorial-typography"],
        "photo_set": {
            "hero": "assets/demos/coffee_matcha.png",
            "secondary": "assets/demos/coffee_hero.png",
            "accent": "assets/demos/coffee_beans.png",
        },
    },
    "agro_hospitality": {
        "match": ("farm", "kebun", "wisata", "villa", "resort", "hotel", "homestay", "glamping", "florist", "garden"),
        "label": "Destinasi, Villa & Agro Hospitality",
        "primary_business_goal": "Tampilkan suasana destinasi, paket kunjungan/menginap transparan, serta reservasi jadwal langsung via WA.",
        "website_section_architecture": [
            {"id": "destination_hero", "purpose": "Hero destinasi penuh atmosfer dan akses lokasi"},
            {"id": "experience_packages", "purpose": "Daftar paket kunjungan & durasi aktivitas tanpa kotak kaku"},
            {"id": "guest_guide", "purpose": "Panduan fasilitas keluarga, cuaca & reschedule"},
            {"id": "visit_wa", "purpose": "Jam buka, arah lokasi, FAQ & reservasi WA"},
        ],
        "recommended_demo_style": "warm_organic_hospitality",
        "recommended_carousel_style": "organic_warm",
        "required_skill_domains": ["anti-slop-web-design", "editorial-typography"],
        "photo_set": {
            "hero": "assets/demos/coffee_hero.png",
            "secondary": "assets/demos/coffee_beans.png",
            "accent": "assets/demos/coffee_matcha.png",
        },
    },
    "general_local": {
        "match": (),
        "label": "Bisnis Lokal Terkurasi",
        "primary_business_goal": "Susun penawaran inti, jam operasional, alamat, dan kontak WhatsApp dalam hierarki visual tajam tanpa clutter.",
        "website_section_architecture": [
            {"id": "editorial_hero", "purpose": "Identitas brand jelas & proposisi layanan langsung"},
            {"id": "service_sheet", "purpose": "Daftar layanan & estimasi bersih tanpa kartu berat"},
            {"id": "working_rhythm", "purpose": "Cara kerja & kenyamanan pelanggan"},
            {"id": "contact_location_wa", "purpose": "Alamat, jam operasional, FAQ & akses WA langsung"},
        ],
        "recommended_demo_style": "modern_editorial",
        "recommended_carousel_style": "editorial_magazine",
        "required_skill_domains": ["anti-slop-web-design", "modernist-typography"],
        "photo_set": {
            "hero": "assets/demos/coffee_hero.png",
            "secondary": "assets/demos/barber_hero.png",
            "accent": "assets/demos/barber_tools.png",
        },
    },
}


def check_registry_skill_coverage(required_domains: list[str]) -> dict[str, Any]:
    """Inspect `D:\\AI WORKSPACE\\...\\REPOSITORY-REGISTRY.md` for installed skill coverage."""
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8").lower() if REGISTRY_PATH.exists() else ""
    skillspector_ready = SKILLSPECTOR_EXE.exists()

    domain_signals = {
        "anti-slop-web-design": ("anti-slop", "impeccable", "taste-skill", "frontend-design", "ui-ux-pro-max"),
        "editorial-typography": ("jakubkrehel/skills", "better-typography", "designer-skills", "anthropics/skills"),
        "swiss-constructivist-typography": ("jakubkrehel/skills", "designer-skills", "anthropics/skills"),
        "swiss-grid-typography": ("jakubkrehel/skills", "impeccable", "anthropics/skills"),
        "catalog-editorial-typography": ("jakubkrehel/skills", "designer-skills", "anthropics/skills"),
        "modernist-typography": ("jakubkrehel/skills", "impeccable", "anthropics/skills"),
        "hospitality-photography": ("taste-skill", "impeccable", "anthropics/skills"),
        "grooming-editorial": ("taste-skill", "impeccable", "anthropics/skills"),
    }

    covered: list[str] = []
    missing: list[str] = []
    for dom in required_domains:
        tokens = domain_signals.get(dom, (dom,))
        if any(tok in registry_text for tok in tokens):
            covered.append(dom)
        else:
            missing.append(dom)

    return {
        "registry_path": str(REGISTRY_PATH),
        "registry_exists": REGISTRY_PATH.exists(),
        "skillspector_ready": skillspector_ready,
        "skillspector_path": str(SKILLSPECTOR_EXE),
        "covered_domains": covered,
        "missing_domains": missing,
        "needs_scout": len(missing) > 0,
    }


def audit_repo_with_skillspector(repo_url: str, timeout_sec: int = 180) -> dict[str, Any]:
    """Run mandatory NVIDIA SkillSpector pre-clone security audit on a candidate GitHub URL."""
    if not SKILLSPECTOR_EXE.exists():
        return {
            "passed": False,
            "error": f"NVIDIA SkillSpector not found at {SKILLSPECTOR_EXE}",
            "repo_url": repo_url,
        }

    proc = subprocess.run(
        [str(SKILLSPECTOR_EXE), "scan", repo_url, "--no-llm", "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    stdout = proc.stdout.strip()
    idx = stdout.find("{")
    if idx == -1:
        return {
            "passed": False,
            "exit_code": proc.returncode,
            "repo_url": repo_url,
            "error": proc.stderr.strip()[:400] or "No JSON report emitted by SkillSpector",
        }

    report = json.loads(stdout[idx:])
    ra = report.get("risk_assessment") or {}
    risk_score = int(ra.get("score", report.get("risk_score", 100)))
    severity = str(ra.get("severity", report.get("severity", "UNKNOWN"))).upper()
    recommendation = str(ra.get("recommendation", report.get("recommendation", "DO_NOT_INSTALL"))).upper()
    max_sev = str(ra.get("max_issue_severity", "UNKNOWN")).upper()
    findings = report.get("findings") or report.get("issues") or []
    passed = (
        proc.returncode == 0
        and recommendation in {"SAFE", "SAFE_TO_INSTALL", "APPROVE", "CAUTION"}
        and max_sev not in {"HIGH", "CRITICAL"}
        and severity not in {"HIGH", "CRITICAL"}
    )
    return {
        "passed": passed,
        "repo_url": repo_url,
        "exit_code": proc.returncode,
        "risk_score": risk_score,
        "severity": severity,
        "max_issue_severity": max_sev,
        "recommendation": recommendation,
        "findings_count": len(findings),
    }


def resolve_niche_blueprint(
    category: str,
    business_name: str = "",
    city: str = "",
    preferred_demo_style: str | None = None,
) -> dict[str, Any]:
    """Map prospect category -> business goal -> site sections -> theme -> 4-layer typography."""
    hay = f"{category} {business_name}".lower()
    matched_key = "general_local"
    blueprint = NICHE_BLUEPRINTS["general_local"]
    for key, bp in NICHE_BLUEPRINTS.items():
        if key == "general_local":
            continue
        if any(tok in hay for tok in bp["match"]):
            matched_key = key
            blueprint = bp
            break

    demo_style = preferred_demo_style or blueprint["recommended_demo_style"]
    typography_direction = plan_typography_direction(
        brand_name=business_name or blueprint["label"],
        industry=category or blueprint["label"],
        audience=f"Calon pelanggan {category or blueprint['label']} di {city or 'Indonesia'} via Instagram & mobile web",
        style_hint=demo_style,
        auto_register_gap=False,
    )
    registry_check = check_registry_skill_coverage(blueprint["required_skill_domains"])

    return {
        "niche_key": matched_key,
        "niche_label": blueprint["label"],
        "business_name": business_name,
        "category": category,
        "city": city,
        "primary_business_goal": blueprint["primary_business_goal"],
        "website_section_architecture": list(blueprint["website_section_architecture"]),
        "website_visual_theme": demo_style,
        "carousel_style_key": blueprint["recommended_carousel_style"],
        "photo_set": dict(blueprint["photo_set"]),
        "typography_direction": typography_direction,
        "registry_audit": registry_check,
    }
