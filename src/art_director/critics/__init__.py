"""Critics: each scores an Identity on one measurable dimension of quality.

A critic returns a Critique — a score in [0, 1], a human-readable rationale,
and a list of concrete *defects* the repair step can act on. The loop keeps the
critic that complains loudest and asks the generator to address its defects.

This package is the thesis of the repo: design quality, decomposed into
quantities you can compute and check, not vibes.
"""

from __future__ import annotations

from .accessibility import AccessibilityCritic
from .base import Critic, Critique
from .brief_fit import BriefFitCritic
from .harmony import HarmonyCritic
from .typography_critic import TypographyCritic

ALL_CRITICS: tuple[Critic, ...] = (
    AccessibilityCritic(),
    HarmonyCritic(),
    TypographyCritic(),
    BriefFitCritic(),
)

__all__ = [
    "Critique",
    "Critic",
    "AccessibilityCritic",
    "HarmonyCritic",
    "TypographyCritic",
    "BriefFitCritic",
    "ALL_CRITICS",
]
