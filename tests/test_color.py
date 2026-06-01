"""Color science validated against published reference values.

If these pass, every downstream 'measured' claim rests on correct math.
"""


import pytest

from art_director.color import (
    contrast_ratio,
    delta_e_2000,
    parse_hex,
    relative_luminance,
    rgb_to_lab,
    to_hex,
    wcag_level,
)


def test_contrast_black_white_is_21():
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=1e-6)


def test_contrast_is_order_independent():
    a = contrast_ratio((10, 20, 30), (240, 240, 240))
    b = contrast_ratio((240, 240, 240), (10, 20, 30))
    assert a == pytest.approx(b)


def test_contrast_identity_is_one():
    assert contrast_ratio((123, 45, 67), (123, 45, 67)) == pytest.approx(1.0)


def test_relative_luminance_endpoints():
    assert relative_luminance((0, 0, 0)) == pytest.approx(0.0)
    assert relative_luminance((255, 255, 255)) == pytest.approx(1.0)


def test_wcag_levels():
    assert wcag_level(21.0) == "AAA"
    assert wcag_level(4.6) == "AA"
    assert wcag_level(3.0) == "fail"
    assert wcag_level(3.0, large_text=True) == "AA"


def test_hex_roundtrip():
    for h in ("#000000", "#ffffff", "#1b2a4f", "#d43f34"):
        assert to_hex(parse_hex(h)) == h


def test_parse_hex_optional_hash_and_case():
    assert parse_hex("1B2A4F") == parse_hex("#1b2a4f") == (27, 42, 79)


def test_parse_hex_rejects_bad():
    with pytest.raises(ValueError):
        parse_hex("#12g")


def test_lab_white_and_midgray():
    L, a, b = rgb_to_lab((255, 255, 255))
    assert L == pytest.approx(100.0, abs=0.1)
    assert abs(a) < 0.1 and abs(b) < 0.1
    assert rgb_to_lab((128, 128, 128))[0] == pytest.approx(53.6, abs=0.3)


# Canonical Sharma, Wu & Dalal (2005) CIEDE2000 test pairs — the ones that
# break naive implementations at hue discontinuities.
SHARMA_PAIRS = [
    ((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
    ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000),
    ((50, 2.49, -0.001), (50, -2.49, 0.0009), 7.1792),
    ((50, 2.49, -0.001), (50, -2.49, 0.0011), 7.2195),
    ((50, -0.001, 2.49), (50, 0.0009, -2.49), 4.8045),
    ((50, 2.5, 0), (50, 0, -2.5), 4.3065),
    ((50, 2.5, 0), (73, 25, -18), 27.1492),
    ((50, 2.5, 0), (50, 3.1736, 0.5854), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
]


@pytest.mark.parametrize("lab1,lab2,expected", SHARMA_PAIRS)
def test_ciede2000_reference(lab1, lab2, expected):
    assert delta_e_2000(lab1, lab2) == pytest.approx(expected, abs=1e-4)


def test_ciede2000_is_symmetric():
    for lab1, lab2, _ in SHARMA_PAIRS:
        assert delta_e_2000(lab1, lab2) == pytest.approx(delta_e_2000(lab2, lab1), abs=1e-9)


def test_ciede2000_zero_for_identical():
    assert delta_e_2000((50, 2, -3), (50, 2, -3)) == pytest.approx(0.0, abs=1e-9)
