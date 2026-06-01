"""Turn a one-line brief into a *measurable* design target.

This is the move that makes the rest computable. "A calm fintech app for
nurses" is not a number — but the adjectives in it map to target positions on
axes we *can* measure on a finished identity: warmth, chroma, contrast,
formality, density, hue variety, roundness.

The lexicon below is the encoded-taste part. Each design adjective contributes
a pull toward target values on one or more axes; the brief's target vector is
the (confidence-weighted) average of the adjectives it triggers. A critic can
then score an identity by how close its *measured* attributes land to this
target — no model-as-judge required for the core loop, exactly as the dense
cross-encoder is optional in genealogy-graphrag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The axes every identity is measured on. All normalized to [0, 1].
AXES: tuple[str, ...] = (
    "warmth",      # 0 = cool blues/greens, 1 = warm reds/oranges
    "chroma",      # 0 = near-grayscale, 1 = highly saturated
    "contrast",    # 0 = soft/low-contrast, 1 = stark/high-contrast
    "formality",   # 0 = casual/playful, 1 = formal/institutional
    "density",     # 0 = airy/generous spacing, 1 = tight/dense
    "hue_variety", # 0 = monochrome, 1 = many distinct hues
    "roundness",   # 0 = sharp/geometric, 1 = soft/rounded
)


@dataclass(frozen=True)
class Target:
    """A target position on each axis, with a per-axis weight (how much the
    brief actually constrains that axis). Weight 0 means "don't care"."""

    values: dict[str, float]
    weights: dict[str, float]

    @staticmethod
    def neutral() -> Target:
        return Target({a: 0.5 for a in AXES}, {a: 0.0 for a in AXES})


# adjective -> list of (axis, target_value, pull_strength)
# Pull strength encodes how strongly the word implies that axis position.
_LEXICON: dict[str, list[tuple[str, float, float]]] = {
    # temperature / mood
    "calm":      [("warmth", 0.25, 1.0), ("chroma", 0.30, 0.8), ("contrast", 0.40, 0.6), ("density", 0.30, 0.7)],
    "serene":    [("warmth", 0.25, 1.0), ("chroma", 0.25, 0.9), ("density", 0.25, 0.8)],
    "trustworthy":[("warmth", 0.30, 0.8), ("chroma", 0.45, 0.5), ("formality", 0.70, 0.8)],
    "warm":      [("warmth", 0.80, 1.0), ("chroma", 0.55, 0.5)],
    "cool":      [("warmth", 0.20, 1.0)],
    "energetic": [("warmth", 0.70, 0.8), ("chroma", 0.85, 1.0), ("contrast", 0.70, 0.7), ("hue_variety", 0.65, 0.6)],
    "bold":      [("chroma", 0.80, 0.9), ("contrast", 0.85, 1.0), ("formality", 0.55, 0.3)],
    "vibrant":   [("chroma", 0.90, 1.0), ("hue_variety", 0.70, 0.7)],
    "playful":   [("chroma", 0.75, 0.8), ("roundness", 0.85, 1.0), ("hue_variety", 0.70, 0.8), ("formality", 0.20, 0.9)],
    "friendly":  [("roundness", 0.75, 0.8), ("warmth", 0.60, 0.5), ("formality", 0.30, 0.7)],
    "fun":       [("chroma", 0.80, 0.8), ("roundness", 0.80, 0.8), ("hue_variety", 0.75, 0.7)],
    # formality / register
    "elegant":   [("chroma", 0.35, 0.7), ("contrast", 0.70, 0.7), ("formality", 0.85, 1.0), ("hue_variety", 0.30, 0.7)],
    "luxury":    [("chroma", 0.30, 0.8), ("contrast", 0.80, 0.8), ("formality", 0.90, 1.0), ("hue_variety", 0.25, 0.8)],
    "premium":   [("chroma", 0.35, 0.7), ("contrast", 0.75, 0.7), ("formality", 0.85, 0.9)],
    "minimal":   [("chroma", 0.20, 1.0), ("hue_variety", 0.20, 1.0), ("density", 0.25, 0.8), ("contrast", 0.65, 0.5)],
    "refined":   [("chroma", 0.35, 0.7), ("formality", 0.80, 0.8), ("hue_variety", 0.30, 0.6)],
    "professional":[("chroma", 0.45, 0.6), ("formality", 0.80, 0.9), ("contrast", 0.60, 0.5)],
    "corporate": [("warmth", 0.35, 0.6), ("chroma", 0.45, 0.6), ("formality", 0.85, 0.9)],
    "institutional":[("formality", 0.90, 1.0), ("chroma", 0.35, 0.7), ("hue_variety", 0.25, 0.7)],
    "editorial": [("contrast", 0.75, 0.8), ("formality", 0.70, 0.7), ("density", 0.55, 0.5), ("hue_variety", 0.30, 0.6)],
    "classic":   [("formality", 0.75, 0.8), ("chroma", 0.40, 0.6), ("roundness", 0.40, 0.4)],
    # structure / form
    "brutalist": [("contrast", 0.95, 1.0), ("chroma", 0.15, 0.9), ("roundness", 0.05, 1.0), ("density", 0.70, 0.8), ("hue_variety", 0.15, 0.9)],
    "geometric": [("roundness", 0.15, 0.9)],
    "modern":    [("roundness", 0.35, 0.5), ("chroma", 0.55, 0.4), ("formality", 0.55, 0.3)],
    "futuristic":[("warmth", 0.35, 0.5), ("chroma", 0.70, 0.6), ("contrast", 0.75, 0.6), ("roundness", 0.30, 0.5)],
    "organic":   [("roundness", 0.80, 0.9), ("warmth", 0.60, 0.5), ("chroma", 0.45, 0.4)],
    "soft":      [("contrast", 0.35, 0.8), ("roundness", 0.80, 0.9), ("chroma", 0.45, 0.4)],
    "clean":     [("chroma", 0.40, 0.6), ("density", 0.30, 0.7), ("hue_variety", 0.30, 0.6)],
    "dense":     [("density", 0.85, 1.0)],
    "airy":      [("density", 0.15, 1.0)],
    "spacious":  [("density", 0.15, 0.9)],
    # domain cues (sectors carry conventional palettes)
    "fintech":   [("formality", 0.75, 0.7), ("warmth", 0.35, 0.5), ("chroma", 0.45, 0.4)],
    "finance":   [("formality", 0.80, 0.7), ("warmth", 0.35, 0.5)],
    "healthcare":[("warmth", 0.40, 0.5), ("chroma", 0.40, 0.5), ("contrast", 0.55, 0.4), ("roundness", 0.60, 0.5)],
    "medical":   [("chroma", 0.35, 0.6), ("formality", 0.70, 0.6), ("roundness", 0.55, 0.4)],
    "wellness":  [("warmth", 0.45, 0.5), ("chroma", 0.40, 0.6), ("roundness", 0.70, 0.6), ("density", 0.30, 0.6)],
    "nature":    [("warmth", 0.45, 0.5), ("chroma", 0.50, 0.5), ("roundness", 0.65, 0.5)],
    "eco":       [("warmth", 0.40, 0.5), ("chroma", 0.50, 0.5), ("roundness", 0.65, 0.5)],
    "gaming":    [("chroma", 0.85, 0.9), ("contrast", 0.80, 0.8), ("hue_variety", 0.70, 0.6)],
    "kids":      [("chroma", 0.85, 0.9), ("roundness", 0.90, 1.0), ("hue_variety", 0.80, 0.8), ("formality", 0.15, 0.9)],
    "developer": [("warmth", 0.35, 0.4), ("density", 0.65, 0.6), ("formality", 0.55, 0.4)],
    "saas":      [("formality", 0.65, 0.5), ("chroma", 0.55, 0.4)],
}

# Words that carry no design signal; dropped before lexicon lookup.
_STOPWORDS = frozenset(
    "a an the for of to and with in on app site brand identity for studio "
    "company platform service product team users user people".split()
)


@dataclass
class Brief:
    """A parsed brief: the raw text, the matched design adjectives, and the
    resulting measurable Target."""

    text: str
    matched: list[str] = field(default_factory=list)
    target: Target = field(default_factory=Target.neutral)

    def describe(self) -> str:
        cues = ", ".join(self.matched) if self.matched else "(no strong cues — using neutral target)"
        return f"brief: {self.text!r}\n  design cues: {cues}"


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z]+", text.lower()) if t not in _STOPWORDS]


def parse_brief(text: str) -> Brief:
    """Parse a free-text brief into a measurable Target.

    Unknown words are ignored; if nothing matches, the target is neutral with
    zero weight everywhere (the critic will then only judge intrinsic quality
    like contrast and harmony, not brief-fit).
    """
    tokens = _tokenize(text)
    matched: list[str] = []
    # accumulate weighted pulls per axis
    acc: dict[str, list[tuple[float, float]]] = {a: [] for a in AXES}
    for tok in tokens:
        if tok in _LEXICON:
            matched.append(tok)
            for axis, value, strength in _LEXICON[tok]:
                acc[axis].append((value, strength))

    values: dict[str, float] = {}
    weights: dict[str, float] = {}
    for axis in AXES:
        pulls = acc[axis]
        if not pulls:
            values[axis] = 0.5
            weights[axis] = 0.0
        else:
            wsum = sum(s for _, s in pulls)
            values[axis] = sum(v * s for v, s in pulls) / wsum
            # weight saturates: more agreeing cues => more confident constraint
            weights[axis] = min(1.0, wsum / 1.5)

    return Brief(text=text, matched=matched, target=Target(values, weights))
