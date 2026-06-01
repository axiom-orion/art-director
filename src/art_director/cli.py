"""Command line: turn a brief into an identity, a page, or design tokens.

    python -m art_director "a calm fintech app for nurses"
    python -m art_director "a brutalist record label" --html out.html
    python -m art_director "a playful kids app" --tokens tokens.json
"""

from __future__ import annotations

import argparse
import json
import sys

from . import parse_brief
from .loop import direct
from .render import render_page


def _tokens(identity) -> dict:
    """Export the identity as design tokens (a portable JSON contract)."""
    return {
        "brief": identity.brief.text,
        "color": {r: identity.color(r) for r in identity.swatches},
        "type": {
            "heading": {"name": identity.pairing.heading.name, "stack": identity.pairing.heading.stack},
            "body": {"name": identity.pairing.body.name, "stack": identity.pairing.body.stack},
            "scaleRatio": identity.pairing.scale_ratio,
            "googleFontsUrl": identity.fonts_url(),
        },
        "space": identity.spacing,
        "radius": identity.radius,
        "voice": identity.voice,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="art_director", description="Taste, made computable.")
    ap.add_argument("brief", help="one-line design brief, e.g. 'a calm fintech app for nurses'")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--html", metavar="PATH", help="write the rendered style guide to PATH")
    ap.add_argument("--tokens", metavar="PATH", help="write design tokens JSON to PATH")
    ap.add_argument("--quiet", action="store_true", help="suppress the scorecard summary")
    args = ap.parse_args(argv)

    brief = parse_brief(args.brief)
    result = direct(brief, seed=args.seed)
    idn = result.final.identity

    if args.html:
        with open(args.html, "w") as f:
            f.write(render_page(result))
    if args.tokens:
        with open(args.tokens, "w") as f:
            json.dump(_tokens(idn), f, indent=2)

    if not args.quiet:
        print(brief.describe())
        print(f"\n  naive {result.baseline.aggregate:.3f}  ->  directed "
              f"{result.final.aggregate:.3f}  ({result.rounds} rounds)\n")
        for name, cq in result.final.critiques.items():
            base = result.baseline.critiques[name].score
            print(f"  {name:14} {base:.3f} -> {cq.score:.3f}   {cq.rationale}")
        print("\n  palette: " + "  ".join(f"{r}:{idn.color(r)}" for r in idn.swatches))
        print(f"  type   : {idn.pairing.heading.name} / {idn.pairing.body.name} "
              f"(scale {idn.pairing.scale_ratio})")
        if args.html:
            print(f"\n  wrote {args.html}")
        if args.tokens:
            print(f"  wrote {args.tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
