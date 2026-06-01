"""Brief-fit critic: does the *finished* identity measure the way the brief asked?

We re-measure the identity's real attributes (warmth, chroma, contrast,
formality, density, hue variety, roundness) straight from the generated colors,
fonts and spacing — then compare to the brief's Target, weighted by how much
the brief constrained each axis. This is the "model-as-judge" role, but done
with measurement instead of an LLM so the loop stays deterministic and free.

(An optional LLM judge can be layered on top via ``judge.py``; this critic is
the always-on, reproducible core.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..brief import AXES
from ..color import contrast_ratio, hue_distance, parse_hex, rgb_to_lch
from .base import Critique, Defect

if TYPE_CHECKING:
    from ..identity import Identity

_CHROMATIC = ("primary", "secondary", "accent")


def measure(identity: Identity) -> dict[str, float]:
    """Recover the identity's position on each design axis from its artifacts.

    Deliberately independent of the generator's inputs: it reads the *output*,
    so the critic catches cases where generation drifted from intent.
    """
    lch = {r: rgb_to_lch(parse_hex(identity.color(r))) for r in identity.swatches}
    prim_h = lch["primary"][2]
    # warmth: hue near 0-60 / 300-360 (warm) vs 180-260 (cool) -> [0,1]
    warm_dist = min(hue_distance(prim_h, 35), hue_distance(prim_h, 0))
    cool_dist = hue_distance(prim_h, 250)
    warmth = cool_dist / (warm_dist + cool_dist) if (warm_dist + cool_dist) else 0.5

    chroma = min(1.0, max(lch[r][1] for r in _CHROMATIC) / 90.0)

    contrast = min(1.0, contrast_ratio(parse_hex(identity.color("text")),
                                       parse_hex(identity.color("bg"))) / 21.0 * 1.6)

    formality = (identity.pairing.heading.formality + identity.pairing.body.formality) / 2

    base_unit = identity.spacing[0]
    density = 1.0 - min(1.0, max(0.0, (base_unit - 4) / 4))  # 4px->dense(1), 8px->airy(0)

    hues = [lch[r][2] for r in _CHROMATIC]
    spread = max(hue_distance(hues[0], h) for h in hues)
    hue_variety = min(1.0, spread / 160.0)

    roundness = min(1.0, identity.radius / 22.0)

    return {
        "warmth": warmth,
        "chroma": chroma,
        "contrast": min(1.0, contrast),
        "formality": formality,
        "density": density,
        "hue_variety": hue_variety,
        "roundness": roundness,
    }


class BriefFitCritic:
    name = "brief_fit"
    weight = 0.25

    def critique(self, identity: Identity) -> Critique:
        target = identity.brief.target
        actual = measure(identity)
        defects: list[Defect] = []

        wsum = 0.0
        err_acc = 0.0
        per_axis: list[str] = []
        for axis in AXES:
            w = target.weights[axis]
            if w <= 0:
                continue
            err = abs(actual[axis] - target.values[axis])
            wsum += w
            err_acc += w * err
            if err > 0.3:
                defects.append(
                    Defect(
                        kind="axis_miss",
                        detail=f"{axis}: got {actual[axis]:.2f}, brief wants {target.values[axis]:.2f}",
                        severity=min(1.0, err),
                        data={"axis": axis, "actual": actual[axis], "target": target.values[axis]},
                    )
                )
            per_axis.append(f"{axis} Δ{err:+.2f}")

        if wsum == 0:
            return Critique(
                self.name, 1.0,
                "brief gave no measurable design cues; intrinsic quality only.", [],
            )

        mean_err = err_acc / wsum
        score = max(0.0, 1.0 - mean_err * 1.4)  # 0.7 mean error -> 0 score
        rationale = f"weighted brief match {score:.2f} (mean Δ {mean_err:.2f}); " + ", ".join(per_axis)
        return Critique(self.name, score, rationale, defects)
