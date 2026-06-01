"""Typography critic: is the type pairing well-formed and on-register?

Delegates the rule math to ``typography.Pairing.score`` and turns the weakest
sub-rule into an actionable defect (so the repair step can try a different
pairing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Critique, Defect

if TYPE_CHECKING:
    from ..identity import Identity


class TypographyCritic:
    name = "typography"
    weight = 0.15

    def critique(self, identity: Identity) -> Critique:
        t = identity.brief.target.values
        total, parts = identity.pairing.score(t["formality"], t["roundness"])
        defects: list[Defect] = []
        # surface the weakest rule as a defect if the pairing is mediocre
        if total < 0.7:
            worst_rule = min(parts, key=parts.get)
            defects.append(
                Defect(
                    kind="weak_pairing",
                    detail=(
                        f"{identity.pairing.heading.name} / {identity.pairing.body.name}: "
                        f"weakest on {worst_rule} ({parts[worst_rule]:.2f})"
                    ),
                    severity=1.0 - total,
                    data={"rule": worst_rule, **{k: round(v, 3) for k, v in parts.items()}},
                )
            )
        rationale = (
            f"{identity.pairing.heading.name} + {identity.pairing.body.name} "
            f"(scale {identity.pairing.scale_ratio}): "
            + ", ".join(f"{k} {v:.2f}" for k, v in parts.items())
        )
        return Critique(self.name, total, rationale, defects)
