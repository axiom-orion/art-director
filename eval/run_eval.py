#!/usr/bin/env python3
"""Ablation eval for the art-director critic loop.

Mirrors the philosophy of the other axiom-orion evals: the numbers below are
produced by this script, not asserted. We compare, on the same set of briefs,
what each stage of the system buys — adding one capability at a time:

    naive            single-shot, ungoverned generation (the honest baseline)
    + steer          brief-steered generator (LCh placement, type rules)
    + critic-loop    full self-critique + targeted repair

For each configuration we report the mean critic scores and, crucially, the
**WCAG AA pass-rate over every text/background pairing** — the one number a
design system absolutely must get right and the one naive generation reliably
fails. Output is written to eval/results.md and eval/results.json.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from art_director import parse_brief  # noqa: E402
from art_director.color import contrast_ratio, parse_hex  # noqa: E402
from art_director.critics import ALL_CRITICS  # noqa: E402
from art_director.critics.accessibility import _ON_BRAND, _PAIRS  # noqa: E402
from art_director.identity import generate, generate_naive  # noqa: E402
from art_director.loop import direct, score  # noqa: E402

HERE = Path(__file__).resolve().parent
SEED = 7


def aa_pass_rate(identity) -> tuple[int, int]:
    """Count WCAG-AA passing text pairings on an identity. Returns (pass, total)."""
    passes = total = 0
    for fg_role, bg_role, large in _PAIRS:
        ratio = contrast_ratio(parse_hex(identity.color(fg_role)), parse_hex(identity.color(bg_role)))
        total += 1
        passes += ratio >= (3.0 if large else 4.5)
    white = parse_hex("#ffffff")
    for role in _ON_BRAND:
        total += 1
        passes += contrast_ratio(white, parse_hex(identity.color(role))) >= 3.0
    return passes, total


def eval_config(briefs, builder) -> dict:
    """Run one configuration over all briefs, aggregating critic + AA metrics."""
    per_critic: dict[str, list[float]] = {c.name: [] for c in ALL_CRITICS}
    aggregates: list[float] = []
    aa_pass = aa_total = 0
    rounds: list[int] = []
    for b in briefs:
        identity, n_rounds = builder(b)
        sc = score(identity)
        for name, cq in sc.critiques.items():
            per_critic[name].append(cq.score)
        aggregates.append(sc.aggregate)
        p, t = aa_pass_rate(identity)
        aa_pass += p
        aa_total += t
        rounds.append(n_rounds)
    return {
        "aggregate": round(statistics.mean(aggregates), 3),
        "critics": {k: round(statistics.mean(v), 3) for k, v in per_critic.items()},
        "aa_pass_rate": round(aa_pass / aa_total, 3),
        "aa_pass": aa_pass,
        "aa_total": aa_total,
        "mean_rounds": round(statistics.mean(rounds), 2),
    }


def main() -> None:
    briefs = [parse_brief(json.loads(line)["brief"])
              for line in (HERE / "briefs.jsonl").read_text().splitlines() if line.strip()]

    configs = {
        "naive": lambda b: (generate_naive(b, seed=SEED), 0),
        "steer": lambda b: (generate(b, seed=SEED, jitter=0.0), 0),
        "critic-loop": lambda b: (lambda r: (r.final.identity, r.rounds))(direct(b, seed=SEED)),
    }

    results = {name: eval_config(briefs, fn) for name, fn in configs.items()}

    # ---- write JSON ----
    (HERE / "results.json").write_text(json.dumps({"n_briefs": len(briefs), "seed": SEED,
                                                   "configs": results}, indent=2) + "\n")

    # ---- write Markdown ----
    crit_names = [c.name for c in ALL_CRITICS]
    lines = []
    lines.append("# Ablation results\n")
    lines.append(f"_{len(briefs)} briefs · seed {SEED} · scores in [0,1], higher is better. "
                 "Produced by `eval/run_eval.py`._\n")
    header = "| configuration | " + " | ".join(crit_names) + " | **aggregate** | **WCAG AA pass** |"
    sep = "|" + "---|" * (len(crit_names) + 3)
    lines.append(header)
    lines.append(sep)
    label = {"naive": "naive (single-shot)", "steer": "+ brief-steered generator",
             "critic-loop": "**+ critic loop**"}
    for name in ("naive", "steer", "critic-loop"):
        r = results[name]
        cells = " | ".join(f"{r['critics'][c]:.3f}" for c in crit_names)
        agg = f"**{r['aggregate']:.3f}**" if name == "critic-loop" else f"{r['aggregate']:.3f}"
        aa = f"**{r['aa_pass_rate']:.3f}**" if name == "critic-loop" else f"{r['aa_pass_rate']:.3f}"
        lines.append(f"| {label[name]} | {cells} | {agg} | {aa} ({r['aa_pass']}/{r['aa_total']}) |")
    lines.append("")
    n = results["naive"]
    f = results["critic-loop"]
    lines.append("## What moves\n")
    lines.append(f"- **Accessibility** is where ungoverned generation fails hardest: "
                 f"naive lands **{n['aa_pass_rate']*100:.0f}%** of text pairings at WCAG AA "
                 f"({n['aa_pass']}/{n['aa_total']}); the critic loop reaches "
                 f"**{f['aa_pass_rate']*100:.0f}%** ({f['aa_pass']}/{f['aa_total']}) by measuring every "
                 f"pairing and repairing lightness until it clears the threshold.")
    lines.append(f"- **Aggregate quality** rises {n['aggregate']:.3f} → {f['aggregate']:.3f} "
                 f"across {len(briefs)} briefs, in a mean of {f['mean_rounds']:.1f} repair rounds.")
    lines.append("- The **brief-steered generator alone** (middle row) already recovers most of "
                 "the harmony and brief-fit gap; the critic loop's distinct contribution is "
                 "closing the *accessibility* gap that generation-by-taste leaves open — you cannot "
                 "eyeball a 4.5:1 contrast ratio, you have to compute it.")
    lines.append("")
    lines.append("## Honest notes\n")
    lines.append("- Scores are **rubric scores, not human ratings.** They measure conformance to "
                 "encoded design rules (WCAG contrast, CIEDE2000 separation, type-pairing heuristics, "
                 "brief-fit). They are a proxy for taste, not taste itself; the rules are defensible "
                 "and inspectable, which is the point.")
    lines.append("- The **naive baseline is not a strawman**: it samples plausible colors near the "
                 "brief hue, exactly as an ungoverned single-shot generator does. Its failure mode is "
                 "the real one — text a touch too light, brand colors that collide, buttons whose "
                 "white label misses AA.")
    lines.append("- Brief-fit is measured from the **rendered artifact** (re-derived warmth, chroma, "
                 "contrast, etc.), independent of the generator's inputs, so it catches drift between "
                 "intent and output.")
    (HERE / "results.md").write_text("\n".join(lines) + "\n")

    # ---- console summary ----
    print(f"briefs: {len(briefs)}  seed: {SEED}\n")
    print(f"{'config':28} {'agg':>6} {'a11y':>6} {'harm':>6} {'type':>6} {'brief':>6} {'AA%':>6}")
    for name in ("naive", "steer", "critic-loop"):
        r = results[name]
        c = r["critics"]
        print(f"{name:28} {r['aggregate']:6.3f} {c['accessibility']:6.3f} {c['harmony']:6.3f} "
              f"{c['typography']:6.3f} {c['brief_fit']:6.3f} {r['aa_pass_rate']*100:5.0f}%")
    print(f"\nwrote {HERE/'results.md'} and {HERE/'results.json'}")


if __name__ == "__main__":
    main()
