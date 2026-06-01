#!/usr/bin/env python3
"""Screenshot the gallery pages with Playwright (optional; needs a browser).

Used to refresh the PNGs embedded in the README. Skips gracefully if no
browser is installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "gallery"

FEATURED = ["fintech_calm", "record_brutalist", "kids_playful", "luxury_jewelry"]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; `pip install -e '.[shots]'` then `playwright install chromium`")
        return 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for bid in FEATURED:
            page_path = GALLERY / f"{bid}.html"
            if not page_path.exists():
                print(f"missing {page_path}; run scripts/build_gallery.py first")
                continue
            pg = browser.new_page(viewport={"width": 1100, "height": 1400})
            pg.goto(page_path.as_uri())
            pg.wait_for_timeout(900)
            pg.screenshot(path=str(GALLERY / f"{bid}.png"), full_page=True)
            print("shot", bid)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
