#!/usr/bin/env python3
"""Render every eval brief to an HTML page plus an index gallery.

Produces gallery/index.html linking each generated identity — the visual
counterpart to the eval table. Screenshots (gallery/*.png) are committed for
the README; regenerate them with `make shots` if you have a browser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from art_director import parse_brief  # noqa: E402
from art_director.loop import direct  # noqa: E402
from art_director.render import render_page  # noqa: E402

GALLERY = ROOT / "gallery"
SEED = 7


def main() -> None:
    GALLERY.mkdir(exist_ok=True)
    briefs = [json.loads(line) for line in
              (ROOT / "eval" / "briefs.jsonl").read_text().splitlines() if line.strip()]

    cards = []
    for entry in briefs:
        bid, text = entry["id"], entry["brief"]
        res = direct(parse_brief(text), seed=SEED)
        (GALLERY / f"{bid}.html").write_text(render_page(res))
        idn = res.final.identity
        cards.append((bid, text, idn.color("bg"), idn.color("primary"),
                      idn.color("accent"), idn.color("text"),
                      res.baseline.aggregate, res.final.aggregate))
        print(f"rendered {bid:22} {res.baseline.aggregate:.3f} -> {res.final.aggregate:.3f}")

    tiles = "\n".join(
        f"""<a class="tile" href="{bid}.html" style="background:{bg};color:{tx}">
          <div class="bar"><span style="background:{pr}"></span><span style="background:{ac}"></span></div>
          <div class="t-brief">{text}</div>
          <div class="t-score">{base:.2f} → <b>{final:.2f}</b></div>
        </a>"""
        for bid, text, bg, pr, ac, tx, base, final in cards
    )
    index = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>art-director · gallery</title>
<style>
 body{{margin:0;font-family:system-ui,sans-serif;background:#0d0d10;color:#e8e8ea;padding:48px}}
 h1{{font-weight:800;letter-spacing:-.02em}} .sub{{color:#9a9aa2;max-width:60ch;line-height:1.6}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;margin-top:32px}}
 .tile{{display:block;text-decoration:none;border-radius:14px;padding:22px;min-height:150px;
   border:1px solid rgba(255,255,255,.08);transition:transform .15s}}
 .tile:hover{{transform:translateY(-3px)}}
 .bar{{display:flex;gap:6px;margin-bottom:14px}} .bar span{{width:28px;height:28px;border-radius:7px;display:block}}
 .t-brief{{font-weight:600;font-size:1.05rem;line-height:1.3}} .t-score{{margin-top:10px;opacity:.8;font-variant-numeric:tabular-nums}}
</style></head><body>
<h1>art-director</h1>
<p class="sub">Each tile is a complete visual identity generated from a one-line brief, then
critiqued and repaired against measurable rubrics. The number is the aggregate critic score:
naive single-shot → critic-directed.</p>
<div class="grid">{tiles}</div>
</body></html>"""
    (GALLERY / "index.html").write_text(index)
    print(f"\nwrote {GALLERY/'index.html'} ({len(cards)} identities)")


if __name__ == "__main__":
    main()
