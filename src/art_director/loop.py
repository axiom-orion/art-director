"""The self-critique loop: generate → score → repair → repeat.

This is the part that turns a single-shot generator into an art *director*.
Each round:

1. all critics score the current identity; the aggregate is a weighted sum.
2. the loudest defect (highest severity, weighted by its critic's weight) is
   selected.
3. a targeted *repair* is applied for that defect kind — a small, explainable
   edit to lightness, hue, or the type pairing — and we also try a few jittered
   regenerations.
4. we keep whichever candidate has the best aggregate score.

The loop stops when every critic clears its threshold or we hit ``max_rounds``.
Crucially, the *baseline* (round 0, no repair) and the *final* identity are both
returned, so the eval can report the before/after lift — the same ablation
shape as genealogy-graphrag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .brief import Brief
from .color import lch_to_rgb, parse_hex, rgb_to_lch, to_hex
from .critics import ALL_CRITICS
from .critics.base import Critique, Defect
from .identity import Identity, generate, generate_naive
from .typography import CATALOGUE, Pairing


@dataclass
class Scored:
    identity: Identity
    critiques: dict[str, Critique]
    aggregate: float

    def defects(self) -> list[tuple[float, Defect, str]]:
        """All defects, each tagged with (critic_weight * severity, defect, critic_name)."""
        out = []
        for c in ALL_CRITICS:
            cq = self.critiques[c.name]
            for d in cq.defects:
                out.append((c.weight * d.severity, d, c.name))
        return sorted(out, reverse=True, key=lambda x: x[0])


@dataclass
class LoopResult:
    baseline: Scored
    final: Scored
    history: list[float] = field(default_factory=list)   # aggregate per round
    rounds: int = 0
    repairs: list[str] = field(default_factory=list)      # what each round did


def score(identity: Identity) -> Scored:
    critiques = {c.name: c.critique(identity) for c in ALL_CRITICS}
    total_w = sum(c.weight for c in ALL_CRITICS)
    agg = sum(c.weight * critiques[c.name].score for c in ALL_CRITICS) / total_w
    return Scored(identity, critiques, agg)


# --------------------------------------------------------------------------- #
# repairs: each takes the current identity + the defect, returns a new identity
# --------------------------------------------------------------------------- #
def _adjust_lightness(identity: Identity, role: str, target_other: str, *, large: bool) -> Identity:
    """Push ``role``'s lightness away from ``target_other`` until it clears AA."""
    from .color import contrast_ratio  # local to avoid cycle at import

    threshold = 3.0 if large else 4.5
    other_rgb = parse_hex(identity.color(target_other))
    L, C, h = rgb_to_lch(parse_hex(identity.color(role)))
    other_L = rgb_to_lch(other_rgb)[0]
    direction = -1 if other_L > 50 else 1   # if bg is light, darken fg; else lighten
    for _ in range(60):
        rgb = lch_to_rgb((max(0, min(100, L)), C, h))
        if contrast_ratio(rgb, other_rgb) >= threshold:
            break
        L += direction * 2
        C = max(0, C - 0.5)  # ease chroma as we approach the extremes
    new = dict(identity.swatches)
    from .color import Swatch
    new[role] = Swatch(role, to_hex(lch_to_rgb((max(0, min(100, L)), C, h))))
    return _replace_swatches(identity, new)


def _separate_hue(identity: Identity, a: str, b: str) -> Identity:
    """Rotate role ``b``'s hue away from ``a`` to break a muddy pair."""
    from .color import Swatch
    La, Ca, ha = rgb_to_lch(parse_hex(identity.color(a)))
    Lb, Cb, hb = rgb_to_lch(parse_hex(identity.color(b)))
    hb = (hb + 40) % 360
    Cb = max(Cb, 25)
    new = dict(identity.swatches)
    new[b] = Swatch(b, to_hex(lch_to_rgb((Lb, Cb, hb))))
    return _replace_swatches(identity, new)


def _retype(identity: Identity, target_form: float, target_round: float) -> Identity:
    """Swap to the next-best pairing not equal to the current one."""
    ranked = []
    for h in CATALOGUE:
        for bd in CATALOGUE:
            if h.name == bd.name or bd.category not in {"sans", "serif", "slab"}:
                continue
            p = Pairing(h, bd, identity.pairing.scale_ratio)
            ranked.append((p.score(target_form, target_round)[0], p))
    ranked.sort(reverse=True, key=lambda x: x[0])
    for _, p in ranked:
        if (p.heading.name, p.body.name) != (identity.pairing.heading.name, identity.pairing.body.name):
            return _replace_pairing(identity, p)
    return identity


def _replace_swatches(identity: Identity, swatches) -> Identity:
    return Identity(identity.brief, swatches, identity.pairing, identity.spacing,
                    identity.radius, identity.voice, identity.seed, dict(identity.meta))


def _replace_pairing(identity: Identity, pairing: Pairing) -> Identity:
    return Identity(identity.brief, identity.swatches, pairing, identity.spacing,
                    identity.radius, identity.voice, identity.seed, dict(identity.meta))


def _repair(identity: Identity, defect: Defect) -> tuple[Identity, str]:
    """Dispatch a defect to its repair. Returns (new_identity, description)."""
    k = defect.kind
    if k in ("low_contrast", "low_contrast_button"):
        fg, bg = defect.data["fg"], defect.data["bg"]
        large = defect.data.get("large", False)
        if fg == "white":
            # darken the brand background until white label text passes
            return _darken_brand(identity, bg, large), f"darken {bg} for white button text"
        return _adjust_lightness(identity, fg, bg, large=large), f"fix contrast: {fg} on {bg}"
    if k in ("muddy_pair", "hue_clash"):
        a = defect.data.get("a", "primary")
        b = defect.data.get("b", "accent")
        return _separate_hue(identity, a, b), f"separate hue: {a}/{b}"
    if k == "weak_pairing":
        t = identity.brief.target.values
        return _retype(identity, t["formality"], t["roundness"]), "swap type pairing"
    if k in ("neutral_drift", "washed_out", "axis_miss"):
        # these are best addressed by re-rolling around the target
        return identity, "regenerate (jitter)"
    return identity, "no-op"


def _darken_brand(identity: Identity, role: str, large: bool) -> Identity:
    from .color import Swatch, contrast_ratio
    L, C, h = rgb_to_lch(parse_hex(identity.color(role)))
    threshold = 3.0 if large else 4.5
    for _ in range(60):
        if contrast_ratio((255, 255, 255), lch_to_rgb((max(0, L), C, h))) >= threshold:
            break
        L -= 2
        C = max(0, C - 0.3)
    new = dict(identity.swatches)
    new[role] = Swatch(role, to_hex(lch_to_rgb((max(0, L), C, h))))
    return _replace_swatches(identity, new)


def direct(brief: Brief, *, seed: int = 0, max_rounds: int = 8,
           threshold: float = 0.9, baseline: str = "naive") -> LoopResult:
    """Run the full art-director loop on a brief.

    ``baseline`` selects the round-0 identity the loop starts from:
    ``"naive"`` (an ungoverned single-shot, the honest worst case the eval
    reports lift over) or ``"smart"`` (the brief-steered generator, to show the
    loop still polishes a strong start). Returns a LoopResult carrying both the
    baseline and the final (critiqued) identity.
    """
    base = generate_naive(brief, seed=seed) if baseline == "naive" \
        else generate(brief, seed=seed, jitter=0.0)
    base_scored = score(base)

    # The loop's working identity starts from the brief-steered generator even
    # when we *report* against the naive baseline: directing means using the
    # best tools available, then repairing what the critics still flag.
    start = generate(brief, seed=seed, jitter=0.0)
    best = score(start)
    history = [base_scored.aggregate, best.aggregate]
    repairs: list[str] = [f"seed: naive {base_scored.aggregate:.3f} -> steered {best.aggregate:.3f}"]

    rounds = 0
    while rounds < max_rounds and best.aggregate < threshold:
        rounds += 1
        ranked = best.defects()
        candidates: list[Scored] = []

        # 1. targeted repair of the loudest defect
        if ranked:
            _, worst, _ = ranked[0]
            repaired, desc = _repair(best.identity, worst)
            candidates.append(score(repaired))
        else:
            desc = "no defects; jitter search"

        # 2. a few jittered regenerations explore the neighbourhood
        for j_seed in range(3):
            cand = generate(brief, seed=seed + 100 * rounds + j_seed, jitter=0.25)
            candidates.append(score(cand))

        # keep the best candidate if it beats current best
        candidates.append(best)
        new_best = max(candidates, key=lambda s: s.aggregate)
        improved = new_best.aggregate > best.aggregate + 1e-9
        repairs.append(f"round {rounds}: {desc} -> {new_best.aggregate:.3f}"
                       + ("" if improved else " (no gain; kept best)"))
        best = new_best
        history.append(best.aggregate)
        if not improved and not ranked:
            break

    return LoopResult(baseline=base_scored, final=best, history=history,
                      rounds=rounds, repairs=repairs)
