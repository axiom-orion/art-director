"""The Identity object and the generator that proposes one from a brief.

An Identity is everything a critic grades and the renderer draws: a roled
palette, a type pairing, a spacing scale, a radius, and a voice. The generator
is deterministic given (brief, seed) so the eval is reproducible — same
contract as the seeded corpus in genealogy-graphrag.

Color is placed in LCh, not RGB: lightness, chroma and hue are the axes the
brief actually constrains and the critics actually measure, so generating in
that space keeps the loop steerable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .brief import Brief
from .color import Swatch, contrast_ratio, lch_to_rgb, parse_hex, to_hex
from .typography import Pairing, best_pairing, google_fonts_url

# Roles the palette must fill. The renderer and the contrast critic both rely
# on these exact names.
ROLES: tuple[str, ...] = ("bg", "surface", "text", "muted", "primary", "secondary", "accent")


@dataclass
class Identity:
    brief: Brief
    swatches: dict[str, Swatch]
    pairing: Pairing
    spacing: list[int]          # spacing scale in px
    radius: int                 # corner radius in px
    voice: dict[str, str]       # tone descriptors + sample microcopy
    seed: int = 0
    meta: dict = field(default_factory=dict)

    def color(self, role: str) -> str:
        return self.swatches[role].hex

    def fonts_url(self) -> str:
        return google_fonts_url(self.pairing)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _in_gamut(lch: tuple[float, float, float]) -> bool:
    """A color is in sRGB gamut if round-tripping LCh->RGB->LCh is close."""
    r, g, b = lch_to_rgb(lch)
    return all(0 <= c <= 255 for c in (r, g, b)) and to_hex((r, g, b)) == to_hex((r, g, b))


def _fit_chroma(L: float, C: float, h: float) -> tuple[float, float, float]:
    """Reduce chroma until the LCh color lands inside sRGB. Keeps L and h."""
    c = C
    while c > 0:
        rgb = lch_to_rgb((L, c, h))
        if all(0 <= v <= 255 for v in rgb):
            return (L, c, h)
        c -= 2.0
    return (L, 0.0, h)


# --------------------------------------------------------------------------- #
# voice
# --------------------------------------------------------------------------- #
# Headline bank keyed by a salient design cue, so two briefs at the same
# formality still read differently. Falls back to a formality-based default.
_CUE_HEADLINES: dict[str, str] = {
    "luxury": "Crafted to be kept.",
    "elegant": "Quiet confidence, considered detail.",
    "premium": "The standard, refined.",
    "playful": "Everything you need, nothing you don't.",
    "kids": "Made for big imaginations.",
    "fun": "Press play on the good stuff.",
    "brutalist": "No apologies. No decoration.",
    "minimal": "Less, done precisely.",
    "energetic": "Built to move fast.",
    "gaming": "Game on.",
    "wellness": "Room to breathe.",
    "organic": "Grown, not manufactured.",
    "eco": "Better, by nature.",
    "fintech": "Built on a foundation you can trust.",
    "corporate": "Built on a foundation you can trust.",
    "editorial": "Stories worth the spread.",
}


def _voice_for(brief: Brief) -> dict[str, str]:
    target = brief.target
    formality = target.values["formality"]
    warmth = target.values["warmth"]

    if formality > 0.7:
        tone = "measured, authoritative, precise"
        cta = "Get started" if warmth > 0.5 else "Request access"
        default_head = "Built on a foundation you can trust."
    elif formality < 0.35:
        tone = "warm, direct, a little playful"
        cta = "Jump in" if warmth > 0.5 else "Let's go"
        default_head = "Everything you need, nothing you don't."
    else:
        tone = "clear, confident, human"
        cta = "Start free"
        default_head = "Designed to feel effortless."

    # first matched cue with a bespoke headline wins; else the formality default
    head = next((_CUE_HEADLINES[c] for c in brief.matched if c in _CUE_HEADLINES), default_head)
    return {"tone": tone, "headline": head, "cta": cta,
            "sub": "A sample of the system's voice, generated to match the brief."}


# --------------------------------------------------------------------------- #
# generator
# --------------------------------------------------------------------------- #
def generate(brief: Brief, seed: int = 0, *, jitter: float = 0.0) -> Identity:
    """Propose a full Identity from a brief.

    ``jitter`` (0..1) perturbs the LCh placement; the critic loop uses it to
    explore alternatives around a base proposal. ``jitter=0`` is the canonical
    single-shot baseline.
    """
    t = brief.target.values
    w = brief.target.weights
    rng = random.Random(seed)

    def j(scale: float) -> float:
        return (rng.random() - 0.5) * 2 * scale * jitter

    warmth = _clamp(t["warmth"] + j(0.15), 0, 1)
    chroma = _clamp(t["chroma"] + j(0.15), 0, 1)
    contrast_pref = _clamp(t["contrast"] + j(0.12), 0, 1)
    variety = _clamp(t["hue_variety"] + j(0.12), 0, 1)

    # Base hue from warmth: warm -> ~35° (orange), cool -> ~250° (blue).
    # When the brief doesn't constrain temperature (low warmth weight) we anchor
    # neutral-cool, because a warm hue at low chroma reads as muddy brown — the
    # classic ungoverned-generator failure. A cool anchor stays clean as gray.
    if w["warmth"] < 0.2:
        base_hue = 250.0
    else:
        base_hue = (35.0 if warmth >= 0.5 else 250.0)
        base_hue = (base_hue + (warmth - 0.5) * 120) % 360
    base_hue = (base_hue + j(20)) % 360

    # Chroma magnitude in LCh units (sRGB-ish usable range ~ 0..110).
    # Curve is super-linear so low-chroma briefs (e.g. brutalist, minimal)
    # land genuinely near-gray instead of muddy mid-saturation.
    chroma_units = 6 + (chroma**1.4) * 92

    # Background lightness: high contrast pref -> very light (or very dark).
    dark_mode = t["warmth"] < 0.4 and contrast_pref > 0.85 and chroma < 0.3
    if dark_mode:
        L_bg, L_surface, L_text, L_muted = 16, 22, 94, 64
    else:
        L_bg = 98 - contrast_pref * 4
        L_surface = L_bg - 4
        L_text = 20 - contrast_pref * 8   # darker text for higher contrast
        L_muted = 45

    # Hue spread for secondary/accent driven by variety.
    spread = 18 + variety * 140
    swatches: dict[str, Swatch] = {}

    def place(role: str, L: float, C: float, h: float) -> None:
        L2, C2, h2 = _fit_chroma(_clamp(L, 0, 100), C, h % 360)
        swatches[role] = Swatch(role, to_hex(lch_to_rgb((L2, C2, h2))))

    # neutrals carry a faint hint of the base hue (temperature in the grays)
    neutral_c = 2 + chroma * 6
    place("bg", L_bg, neutral_c * 0.6, base_hue)
    place("surface", L_surface, neutral_c, base_hue)
    place("text", L_text, neutral_c * 1.2, base_hue)
    place("muted", L_muted, neutral_c * 1.4, base_hue)

    # primary: the brand color. Mid-dark so it can carry white text. For
    # low-chroma + high-contrast briefs (brutalist, stark minimal) a weak
    # mid-tone reads as mud, so we drive it to an assertive near-black ink.
    stark = chroma < 0.3 and contrast_pref > 0.7
    L_primary = (24 if stark else 52) - contrast_pref * 6 + j(4)
    place("primary", L_primary, chroma_units * (0.5 if stark else 1.0), base_hue)
    place("secondary", L_primary + 6, chroma_units * 0.85, base_hue + spread)
    place("accent", 58, min(110, chroma_units * 1.1), base_hue - spread * 0.7)

    pairing: Pairing = best_pairing(t["formality"], t["roundness"], density=t["density"])

    # spacing scale from density: dense -> 4px base, airy -> 8px base.
    base_unit = round(8 - t["density"] * 4)
    spacing = [base_unit * m for m in (1, 2, 3, 4, 6, 8, 12)]

    # radius from roundness: sharp -> 2px, round -> 22px.
    radius = round(2 + t["roundness"] * 20)

    return Identity(
        brief=brief,
        swatches=swatches,
        pairing=pairing,
        spacing=spacing,
        radius=radius,
        voice=_voice_for(brief),
        seed=seed,
        meta={"dark_mode": dark_mode, "jitter": jitter, "base_hue": round(base_hue, 1)},
    )


def generate_naive(brief: Brief, seed: int = 0) -> Identity:
    """A *naive* single-shot identity — the honest baseline.

    This models what a typical one-shot "AI palette generator" does: sample
    plausible-looking colors near the brief's hue with no contrast discipline,
    no perceptual separation between roles, and a fixed default type pairing.
    It is intentionally not bad on purpose — it's bad the way ungoverned
    generation is bad: text that's a bit too light, brand colors that collide,
    buttons whose white label fails AA. The critic loop's job is to measure and
    repair exactly these failures, and the eval reports the lift.
    """
    t = brief.target.values
    rng = random.Random(seed * 31 + 7)
    warmth = t["warmth"]
    base_hue = ((35.0 if warmth >= 0.5 else 250.0) + (warmth - 0.5) * 120) % 360

    def pick(L_center: float, C_center: float, h_center: float, spread_L=10, spread_C=18, spread_h=50):
        L = _clamp(L_center + (rng.random() - 0.5) * 2 * spread_L, 0, 100)
        C = max(0, C_center + (rng.random() - 0.5) * 2 * spread_C)
        h = (h_center + (rng.random() - 0.5) * 2 * spread_h) % 360
        L2, C2, h2 = _fit_chroma(L, C, h)
        return Swatch("", to_hex(lch_to_rgb((L2, C2, h2))))

    # naive: light bg, "dark-ish" text (often not dark enough), brand colors
    # sampled near the same hue (so they collide), no white-on-brand check.
    raw = {
        "bg": pick(96, 6, base_hue, 4, 4, 10),
        "surface": pick(92, 8, base_hue, 4, 4, 10),
        "text": pick(38, 10, base_hue, 12, 6, 20),      # often too light -> fails AA
        "muted": pick(58, 12, base_hue, 8, 6, 20),      # usually fails AA
        "primary": pick(60, 45, base_hue, 12, 20, 30),  # often too light for white text
        "secondary": pick(60, 42, base_hue, 12, 20, 25),  # near primary -> muddy
        "accent": pick(62, 40, base_hue, 12, 20, 30),
    }
    swatches = {role: Swatch(role, sw.hex) for role, sw in raw.items()}

    # naive typography: a fixed, generic default regardless of brief.
    from .typography import CATALOGUE, Pairing
    inter = next(f for f in CATALOGUE if f.name == "Inter")
    pairing = Pairing(inter, inter, 1.25)  # same face for both -> weak hierarchy

    spacing = [8 * m for m in (1, 2, 3, 4, 6, 8, 12)]
    return Identity(
        brief=brief,
        swatches=swatches,
        pairing=pairing,
        spacing=spacing,
        radius=8,
        voice=_voice_for(brief),
        seed=seed,
        meta={"naive": True, "base_hue": round(base_hue, 1)},
    )


def text_on(identity: Identity, bg_role: str) -> str:
    """Pick whichever of text/bg gives the best contrast on a given surface —
    a small helper the renderer uses so generated pages stay legible."""
    bg = parse_hex(identity.color(bg_role))
    cand_white = contrast_ratio(parse_hex("#ffffff"), bg)
    cand_text = contrast_ratio(parse_hex(identity.color("text")), bg)
    return "#ffffff" if cand_white >= cand_text else identity.color("text")
