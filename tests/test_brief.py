"""The brief parser turns language into a measurable target."""

from art_director.brief import AXES, parse_brief


def test_known_adjectives_match():
    b = parse_brief("a calm fintech app")
    assert "calm" in b.matched
    assert "fintech" in b.matched


def test_calm_is_cool_and_low_chroma():
    t = parse_brief("a calm serene app").target
    assert t.values["warmth"] < 0.4
    assert t.values["chroma"] < 0.45
    assert t.weights["warmth"] > 0


def test_brutalist_is_stark_and_sharp():
    t = parse_brief("a brutalist label").target
    assert t.values["contrast"] > 0.8
    assert t.values["roundness"] < 0.2
    assert t.values["chroma"] < 0.3


def test_playful_is_round_and_saturated():
    t = parse_brief("a playful kids app").target
    assert t.values["roundness"] > 0.7
    assert t.values["chroma"] > 0.6
    assert t.values["formality"] < 0.35


def test_unknown_words_give_neutral_zero_weight():
    b = parse_brief("the quux frobnicate plover")
    assert b.matched == []
    for axis in AXES:
        assert b.target.weights[axis] == 0.0
        assert b.target.values[axis] == 0.5


def test_all_axes_present():
    t = parse_brief("an elegant modern brand").target
    assert set(t.values) == set(AXES)
    assert set(t.weights) == set(AXES)


def test_values_in_unit_range():
    for text in ["a bold energetic gaming brand", "a refined luxury studio", "a warm organic shop"]:
        t = parse_brief(text).target
        for axis in AXES:
            assert 0.0 <= t.values[axis] <= 1.0
            assert 0.0 <= t.weights[axis] <= 1.0
