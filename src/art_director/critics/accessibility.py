"""Accessibility critic: WCAG contrast on every text/background pairing.

This is the least subjective critic in the system — the numbers are computed
to spec, and the defects it raises (which role-pair fails, by how much) are
exactly what the repair step needs to fix lightness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..color import contrast_ratio, parse_hex, wcag_level
from .base import Critique, Defect

if TYPE_CHECKING:
    from ..identity import Identity

# The (foreground role, background role, is-large-text) combinations a real UI
# actually renders, and therefore must pass.
_PAIRS: tuple[tuple[str, str, bool], ...] = (
    ("text", "bg", False),
    ("text", "surface", False),
    ("muted", "bg", False),          # secondary text — easy to get wrong
    ("muted", "surface", False),
    ("primary", "bg", True),         # primary used as a large heading/link
)
# White text on these brand colors (buttons): must be legible.
_ON_BRAND: tuple[str, ...] = ("primary", "secondary", "accent")

_AA_NORMAL = 4.5
_AA_LARGE = 3.0


class AccessibilityCritic:
    name = "accessibility"
    weight = 0.35

    def critique(self, identity: Identity) -> Critique:
        defects: list[Defect] = []
        ratios: list[float] = []
        passes = 0
        total = 0

        for fg_role, bg_role, large in _PAIRS:
            fg = parse_hex(identity.color(fg_role))
            bg = parse_hex(identity.color(bg_role))
            ratio = contrast_ratio(fg, bg)
            ratios.append(ratio)
            threshold = _AA_LARGE if large else _AA_NORMAL
            total += 1
            if ratio >= threshold:
                passes += 1
            else:
                defects.append(
                    Defect(
                        kind="low_contrast",
                        detail=f"{fg_role} on {bg_role}: {ratio:.2f}:1 "
                        f"({wcag_level(ratio, large_text=large)}, need {threshold:.1f})",
                        severity=min(1.0, (threshold - ratio) / threshold),
                        data={"fg": fg_role, "bg": bg_role, "ratio": ratio, "large": large},
                    )
                )

        # white-on-brand for buttons
        white = parse_hex("#ffffff")
        for role in _ON_BRAND:
            ratio = contrast_ratio(white, parse_hex(identity.color(role)))
            ratios.append(ratio)
            total += 1
            if ratio >= _AA_LARGE:
                passes += 1
            else:
                defects.append(
                    Defect(
                        kind="low_contrast_button",
                        detail=f"white on {role}: {ratio:.2f}:1 (need {_AA_LARGE:.1f} for button text)",
                        severity=min(1.0, (_AA_LARGE - ratio) / _AA_LARGE),
                        data={"fg": "white", "bg": role, "ratio": ratio, "large": True},
                    )
                )

        pass_rate = passes / total
        worst = min(ratios)
        rationale = (
            f"{passes}/{total} text pairings meet WCAG AA "
            f"(worst {worst:.2f}:1). "
            + ("all clear." if not defects else f"{len(defects)} failing.")
        )
        # score blends pass-rate with how close the worst offender is to AA
        score = 0.7 * pass_rate + 0.3 * min(1.0, worst / _AA_NORMAL)
        return Critique(self.name, score, rationale, defects)
