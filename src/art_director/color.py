"""Color science used by the critics.

Everything downstream that claims to *measure* taste — contrast pass-rates,
palette harmony, perceptual spacing — bottoms out here. So this module is
plain, dependency-free, and validated against published reference values
(WCAG relative luminance; Sharma et al. CIEDE2000 test data) in the tests.

Conventions
-----------
- An ``RGB`` is a 3-tuple of ints in ``[0, 255]``.
- Hex strings are ``#rrggbb`` (case-insensitive, leading ``#`` optional).
- Lab is CIE L*a*b* under a D65 white point; LCh is its cylindrical form.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

RGB = tuple[int, int, int]

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")

# D65 reference white in XYZ (2° observer), the white point sRGB is defined against.
_XN, _YN, _ZN = 0.95047, 1.00000, 1.08883


# --------------------------------------------------------------------------- #
# parsing / formatting
# --------------------------------------------------------------------------- #
def parse_hex(value: str) -> RGB:
    """``"#1b2a4f"`` (or ``"1b2a4f"``) -> ``(27, 42, 79)``."""
    m = _HEX_RE.match(value.strip())
    if not m:
        raise ValueError(f"not a 6-digit hex color: {value!r}")
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def to_hex(rgb: RGB) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------- #
# sRGB <-> linear <-> XYZ <-> Lab <-> LCh
# --------------------------------------------------------------------------- #
def _srgb_to_linear(c: float) -> float:
    """Inverse companding for one channel, ``c`` in [0, 1] (IEC 61966-2-1)."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def relative_luminance(rgb: RGB) -> float:
    """WCAG 2.1 relative luminance Y in [0, 1].

    Black -> 0.0, white -> 1.0; this is the quantity the contrast ratio is
    built from.
    """
    r, g, b = (_srgb_to_linear(c / 255.0) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgb_to_xyz(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(c / 255.0) for c in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    return x, y, z


def _f_lab(t: float) -> float:
    delta = 6.0 / 29.0
    return t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4.0 / 29.0


def rgb_to_lab(rgb: RGB) -> tuple[float, float, float]:
    x, y, z = rgb_to_xyz(rgb)
    fx, fy, fz = _f_lab(x / _XN), _f_lab(y / _YN), _f_lab(z / _ZN)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def rgb_to_lch(rgb: RGB) -> tuple[float, float, float]:
    """Return ``(L*, C*, h°)``. Hue is degrees in [0, 360)."""
    L, a, b = rgb_to_lab(rgb)
    c = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360.0
    return (L, c, h)


def _f_lab_inv(t: float) -> float:
    delta = 6.0 / 29.0
    return t**3 if t > delta else 3 * delta**2 * (t - 4.0 / 29.0)


def lab_to_rgb(lab: tuple[float, float, float]) -> RGB:
    L, a, b = lab
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    x = _XN * _f_lab_inv(fx)
    y = _YN * _f_lab_inv(fy)
    z = _ZN * _f_lab_inv(fz)
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bl = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return tuple(int(round(255 * _linear_to_srgb(c))) for c in (r, g, bl))  # type: ignore[return-value]


def lch_to_rgb(lch: tuple[float, float, float]) -> RGB:
    L, c, h = lch
    a = c * math.cos(math.radians(h))
    b = c * math.sin(math.radians(h))
    return lab_to_rgb((L, a, b))


# --------------------------------------------------------------------------- #
# perceptual / accessibility metrics
# --------------------------------------------------------------------------- #
def contrast_ratio(fg: RGB, bg: RGB) -> float:
    """WCAG 2.1 contrast ratio in [1, 21]. Order-independent.

    Black on white returns 21.0 exactly; identical colors return 1.0.
    """
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def wcag_level(ratio: float, *, large_text: bool = False) -> str:
    """Map a contrast ratio to the highest WCAG level it satisfies.

    Returns one of ``"AAA"``, ``"AA"``, ``"fail"``. Thresholds follow SC 1.4.3
    / 1.4.6: normal text needs 4.5 (AA) / 7.0 (AAA); large text 3.0 / 4.5.
    """
    aa, aaa = (3.0, 4.5) if large_text else (4.5, 7.0)
    if ratio >= aaa:
        return "AAA"
    if ratio >= aa:
        return "AA"
    return "fail"


def delta_e_2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """CIEDE2000 color difference ΔE00.

    Implements Sharma, Wu & Dalal (2005); validated against their published
    test pairs in the tests. ~1.0 is a just-noticeable difference.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_Lp = (L1 + L2) / 2.0
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    avg_C = (C1 + C2) / 2.0

    G = 0.5 * (1 - math.sqrt(avg_C**7 / (avg_C**7 + 25.0**7)))
    a1p = (1 + G) * a1
    a2p = (1 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)
    avg_Cp = (C1p + C2p) / 2.0

    def _hp(ap: float, bp: float) -> float:
        if ap == 0 and bp == 0:
            return 0.0
        return math.degrees(math.atan2(bp, ap)) % 360.0

    h1p = _hp(a1p, b1)
    h2p = _hp(a2p, b2)

    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360

    dLp = L2 - L1
    dCp = C2p - C1p
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2.0)

    if C1p * C2p == 0:
        avg_hp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        avg_hp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        avg_hp = (h1p + h2p + 360) / 2.0
    else:
        avg_hp = (h1p + h2p - 360) / 2.0

    T = (
        1
        - 0.17 * math.cos(math.radians(avg_hp - 30))
        + 0.24 * math.cos(math.radians(2 * avg_hp))
        + 0.32 * math.cos(math.radians(3 * avg_hp + 6))
        - 0.20 * math.cos(math.radians(4 * avg_hp - 63))
    )
    d_ro = 30 * math.exp(-(((avg_hp - 275) / 25.0) ** 2))
    Rc = 2 * math.sqrt(avg_Cp**7 / (avg_Cp**7 + 25.0**7))
    Sl = 1 + (0.015 * (avg_Lp - 50) ** 2) / math.sqrt(20 + (avg_Lp - 50) ** 2)
    Sc = 1 + 0.045 * avg_Cp
    Sh = 1 + 0.015 * avg_Cp * T
    Rt = -math.sin(math.radians(2 * d_ro)) * Rc

    return math.sqrt(
        (dLp / Sl) ** 2
        + (dCp / Sc) ** 2
        + (dHp / Sh) ** 2
        + Rt * (dCp / Sc) * (dHp / Sh)
    )


def delta_e(rgb1: RGB, rgb2: RGB) -> float:
    """Convenience: CIEDE2000 between two sRGB colors."""
    return delta_e_2000(rgb_to_lab(rgb1), rgb_to_lab(rgb2))


def hue_distance(h1: float, h2: float) -> float:
    """Shortest angular distance between two hues, in degrees [0, 180]."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


@dataclass(frozen=True)
class Swatch:
    """A named color carrying its role in the system (e.g. ``bg``, ``primary``)."""

    role: str
    hex: str

    @property
    def rgb(self) -> RGB:
        return parse_hex(self.hex)

    @property
    def lch(self) -> tuple[float, float, float]:
        return rgb_to_lch(self.rgb)
