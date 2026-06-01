"""Type-pairing knowledge, encoded as data + rules.

A font pairing is *good* for reasons that can be written down: the two faces
should differ enough in classification to create hierarchy, but share enough
structure (x-height band, proportion) to feel intentional rather than
accidental. We encode a small, hand-curated catalogue of web-safe / Google
fonts with the attributes the rules need, then score pairings against the
brief's formality and roundness target.
"""

from __future__ import annotations

from dataclasses import dataclass

# classification axis: serifness 0 = geometric sans ... 1 = high-contrast serif
# formality 0 = casual ... 1 = formal; xheight 0 = small ... 1 = tall.


@dataclass(frozen=True)
class Face:
    name: str
    stack: str            # CSS font-family fallback stack
    category: str         # serif | sans | slab | mono | display
    formality: float
    roundness: float
    xheight: float
    contrast: float       # stroke contrast: 0 monoline ... 1 high modulation
    google: bool = True   # available on Google Fonts


CATALOGUE: tuple[Face, ...] = (
    # --- serifs ---
    Face("Playfair Display", "'Playfair Display', Georgia, serif", "serif", 0.90, 0.30, 0.55, 0.95),
    Face("Source Serif 4", "'Source Serif 4', Georgia, serif", "serif", 0.70, 0.45, 0.62, 0.55),
    Face("Lora", "'Lora', Georgia, serif", "serif", 0.65, 0.55, 0.60, 0.50),
    Face("Fraunces", "'Fraunces', Georgia, serif", "serif", 0.75, 0.50, 0.58, 0.70),
    Face("Spectral", "'Spectral', Georgia, serif", "serif", 0.72, 0.40, 0.55, 0.60),
    # --- sans ---
    Face("Inter", "'Inter', system-ui, sans-serif", "sans", 0.55, 0.45, 0.72, 0.10),
    Face("Source Sans 3", "'Source Sans 3', system-ui, sans-serif", "sans", 0.55, 0.50, 0.66, 0.12),
    Face("Work Sans", "'Work Sans', system-ui, sans-serif", "sans", 0.50, 0.55, 0.64, 0.10),
    Face("Manrope", "'Manrope', system-ui, sans-serif", "sans", 0.48, 0.60, 0.68, 0.08),
    Face("Space Grotesk", "'Space Grotesk', system-ui, sans-serif", "sans", 0.45, 0.35, 0.66, 0.10),
    Face("DM Sans", "'DM Sans', system-ui, sans-serif", "sans", 0.45, 0.65, 0.62, 0.08),
    Face("Archivo", "'Archivo', system-ui, sans-serif", "sans", 0.55, 0.30, 0.66, 0.10),
    Face("Nunito", "'Nunito', system-ui, sans-serif", "sans", 0.30, 0.90, 0.64, 0.06),
    # --- slab / display / mono ---
    Face("Roboto Slab", "'Roboto Slab', Georgia, serif", "slab", 0.55, 0.45, 0.66, 0.25),
    Face("Bricolage Grotesque", "'Bricolage Grotesque', system-ui, sans-serif", "display", 0.40, 0.45, 0.68, 0.20),
    Face("JetBrains Mono", "'JetBrains Mono', ui-monospace, monospace", "mono", 0.50, 0.40, 0.62, 0.10),
)

_BY_NAME = {f.name: f for f in CATALOGUE}


@dataclass(frozen=True)
class Pairing:
    heading: Face
    body: Face
    scale_ratio: float    # modular scale (e.g. 1.25 = major third)

    def score(self, formality: float, roundness: float) -> tuple[float, dict[str, float]]:
        """Score this pairing in [0, 1] against target formality/roundness.

        Combines four encoded rules; returns the total and the per-rule
        breakdown so the critic can explain *why*.
        """
        # 1. hierarchy: heading and body should differ in category/contrast
        category_diff = 1.0 if self.heading.category != self.body.category else 0.35
        contrast_diff = min(1.0, abs(self.heading.contrast - self.body.contrast) / 0.5)
        hierarchy = 0.5 * category_diff + 0.5 * contrast_diff
        # 2. cohesion: x-heights should sit in a similar band (shared rhythm)
        cohesion = 1.0 - min(1.0, abs(self.heading.xheight - self.body.xheight) / 0.25)
        # 3. body legibility: body face must be reasonably tall + low-contrast
        legibility = 0.6 * self.body.xheight + 0.4 * (1.0 - self.body.contrast)
        # 4. register fit: the heading carries brand voice, so weight its
        #    formality/roundness toward the brief more than the body's. Squared
        #    error makes the brief genuinely discriminate between pairings
        #    rather than letting one "objectively tidy" pair always win.
        avg_form = 0.65 * self.heading.formality + 0.35 * self.body.formality
        avg_round = 0.65 * self.heading.roundness + 0.35 * self.body.roundness
        form_err = (avg_form - formality) ** 2
        round_err = (avg_round - roundness) ** 2
        register = 1.0 - min(1.0, (form_err + round_err) * 2.2)

        parts = {
            "hierarchy": hierarchy,
            "cohesion": cohesion,
            "legibility": legibility,
            "register": max(0.0, register),
        }
        total = 0.22 * hierarchy + 0.13 * cohesion + 0.15 * legibility + 0.50 * parts["register"]
        return total, parts


def google_fonts_url(pairing: Pairing) -> str:
    """Build a Google Fonts CSS URL for the two faces in a pairing."""
    fams = []
    for f in {pairing.heading.name, pairing.body.name}:
        if _BY_NAME[f].google:
            fams.append("family=" + f.replace(" ", "+") + ":wght@400;500;600;700")
    if not fams:
        return ""
    return "https://fonts.googleapis.com/css2?" + "&".join(sorted(fams)) + "&display=swap"


def best_pairing(formality: float, roundness: float, *, density: float) -> Pairing:
    """Search the catalogue for the highest-scoring heading/body pairing.

    Scale ratio is chosen from density: airier briefs get a more dramatic
    modular scale (more whitespace to carry it), denser briefs a tighter one.
    """
    scale_ratio = round(1.33 - 0.13 * density, 3)  # 1.33 (airy) .. 1.20 (dense)
    best: Pairing | None = None
    best_score = -1.0
    for h in CATALOGUE:
        for b in CATALOGUE:
            if h.name == b.name:
                continue
            # body must be a text-friendly category
            if b.category not in {"sans", "serif", "slab"}:
                continue
            p = Pairing(h, b, scale_ratio)
            s, _ = p.score(formality, roundness)
            if s > best_score:
                best_score, best = s, p
    assert best is not None
    return best
