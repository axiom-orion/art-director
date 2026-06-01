"""art-director — taste, made computable.

Turn a one-line brief into a complete visual identity, then critique and repair
it against measurable rubrics (WCAG contrast, color-theory harmony, type-pairing
rules, brief-fit). The critic loop is the point: design quality decomposed into
quantities you can check, with an honest before/after eval.
"""

from __future__ import annotations

from .brief import Brief, parse_brief
from .identity import Identity, generate
from .loop import LoopResult, Scored, direct, score

__all__ = [
    "Brief",
    "parse_brief",
    "Identity",
    "generate",
    "LoopResult",
    "Scored",
    "direct",
    "score",
    "__version__",
]

__version__ = "0.1.0"
