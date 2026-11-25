"""Utility script: reset all leads in local `leads.db` back to `CONCEPT_READY` (Siap DM).

Usage:
    python scripts/reset_dummies_siap_dm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database as db
import demo_generator as dg


def main() -> None:
    db.init_db()
    res = db.reset_all_leads_to_siap_dm(clear_synthetic_reels_ideas=True, clear_reviews=True)
    dg.rebuild_portfolio_index()
    print(
        f"[OK] {res['reset_count']} lead dikembalikan ke CONCEPT_READY (Siap DM) "
        f"| synthetic dihapus: {res['deleted_synthetic']}"
    )
    for row in res["leads"]:
        print(f"  - #{row['id']} [{row['status']}] {row['business_name']} ({row['category']})")


if __name__ == "__main__":
    main()
