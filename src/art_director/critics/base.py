"""Critic protocol and the Critique result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..identity import Identity


@dataclass(frozen=True)
class Defect:
    """A specific, actionable problem a repair step can target."""

    kind: str                 # e.g. "low_contrast", "muddy_pair", "hue_clash"
    detail: str
    severity: float           # 0..1, how bad
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Critique:
    name: str
    score: float              # 0..1, higher is better
    rationale: str
    defects: list[Defect] = field(default_factory=list)

    @property
    def worst_defect(self) -> Defect | None:
        return max(self.defects, key=lambda d: d.severity, default=None)


class Critic(Protocol):
    name: str
    weight: float             # contribution to the aggregate score

    def critique(self, identity: Identity) -> Critique: ...
