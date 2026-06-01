"""Harmony critic: is the palette coherent by color-theory math?

Two failure modes a palette can have, both measurable:

1. **Hue incoherence** — the chromatic colors don't sit in a recognised
   relationship (analogous, complementary, triadic). We score the brand hues
   against the nearest named scheme.
2. **Muddy separation** — adjacent roles are *almost* the same color (low
   ΔE00), so the system looks accidental rather than deliberate; or so far
   apart it looks unrelated. We want brand colors perceptually distinct but
   neutrals tightly related.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..color import delta_e, hue_distance, parse_hex, rgb_to_lch
from .base import Critique, Defect

if TYPE_CHECKING:
    from ..identity import Identity

_CHROMATIC = ("primary", "secondary", "accent")


def _scheme_score(hues: list[float]) -> tuple[float, str]:
    """Score how close the chromatic hues sit to a recognised scheme."""
    if len(hues) < 2:
        return 1.0, "single hue"
    # pairwise hue gaps
    gaps = [hue_distance(hues[i], hues[j]) for i in range(len(hues)) for j in range(i + 1, len(hues))]
    max_gap = max(gaps)
    # candidate schemes by characteristic spread
    schemes = {
        "analogous": 40,
        "complementary": 180,
        "triadic": 120,
        "split-complementary": 150,
    }
    best_name, best_err = "analogous", 999.0
    for name, ideal in schemes.items():
        err = abs(max_gap - ideal)
        if err < best_err:
            best_err, best_name = err, name
    # tolerance: within 30° of an ideal scheme is "harmonious"
    score = max(0.0, 1.0 - best_err / 90.0)
    return score, best_name


class HarmonyCritic:
    name = "harmony"
    weight = 0.25

    def critique(self, identity: Identity) -> Critique:
        defects: list[Defect] = []
        rgbs = {r: parse_hex(identity.color(r)) for r in identity.swatches}
        hues = [rgb_to_lch(rgbs[r])[2] for r in _CHROMATIC]
        chromas = [rgb_to_lch(rgbs[r])[1] for r in _CHROMATIC]

        scheme_score, scheme_name = _scheme_score(hues)
        if scheme_score < 0.5:
            defects.append(
                Defect(
                    kind="hue_clash",
                    detail=f"brand hues don't form a clean scheme (closest: {scheme_name})",
                    severity=1.0 - scheme_score,
                    data={"hues": [round(h, 1) for h in hues]},
                )
            )

        # brand colors should be perceptually distinct (ΔE00 >= 10)
        sep_penalty = 0.0
        for i in range(len(_CHROMATIC)):
            for k in range(i + 1, len(_CHROMATIC)):
                d = delta_e(rgbs[_CHROMATIC[i]], rgbs[_CHROMATIC[k]])
                if d < 10:
                    sep = (10 - d) / 10
                    sep_penalty = max(sep_penalty, sep)
                    defects.append(
                        Defect(
                            kind="muddy_pair",
                            detail=f"{_CHROMATIC[i]}/{_CHROMATIC[k]} nearly identical (ΔE {d:.1f}, want ≥10)",
                            severity=sep,
                            data={"a": _CHROMATIC[i], "b": _CHROMATIC[k], "delta_e": d},
                        )
                    )

        # neutrals should be tightly related to each other (shared temperature)
        neutral_hues = [rgb_to_lch(rgbs[r])[2] for r in ("bg", "surface", "text", "muted")]
        neutral_spread = max(hue_distance(neutral_hues[0], h) for h in neutral_hues)
        neutral_ok = neutral_spread < 35
        if not neutral_ok:
            defects.append(
                Defect(
                    kind="neutral_drift",
                    detail=f"neutrals span {neutral_spread:.0f}° hue (want <35° for a coherent gray family)",
                    severity=min(1.0, (neutral_spread - 35) / 90),
                )
            )

        # chroma discipline: at least one brand color should be assertive
        chroma_ok = max(chromas) > 20
        if not chroma_ok:
            defects.append(
                Defect(
                    kind="washed_out",
                    detail=f"no brand color exceeds chroma 20 (max {max(chromas):.0f}) — palette reads gray",
                    severity=0.5,
                )
            )

        score = (
            0.45 * scheme_score
            + 0.30 * (1.0 - sep_penalty)
            + 0.15 * (1.0 if neutral_ok else 0.4)
            + 0.10 * (1.0 if chroma_ok else 0.3)
        )
        rationale = (
            f"hues ≈ {scheme_name} ({scheme_score:.2f}); "
            f"brand separation {'clean' if sep_penalty == 0 else 'muddy'}; "
            f"neutral spread {neutral_spread:.0f}°."
        )
        return Critique(self.name, score, rationale, defects)
