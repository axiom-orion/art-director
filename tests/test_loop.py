"""The critic loop must measurably improve on the naive baseline, and the
core invariants of generation must hold."""

import pytest

from art_director import direct, generate, parse_brief, score
from art_director.color import contrast_ratio, parse_hex
from art_director.critics import ALL_CRITICS
from art_director.identity import ROLES, generate_naive

BRIEFS = [
    "a calm fintech app for nurses",
    "a brutalist record label",
    "a playful app for kids",
    "an elegant luxury jewelry brand",
    "a minimal developer tool",
]


@pytest.mark.parametrize("text", BRIEFS)
def test_loop_never_worse_than_its_start(text):
    res = direct(parse_brief(text), seed=7)
    # the directed result must beat the naive baseline it reports against
    assert res.final.aggregate >= res.baseline.aggregate


@pytest.mark.parametrize("text", BRIEFS)
def test_loop_history_is_monotonic_nondecreasing_after_seed(text):
    res = direct(parse_brief(text), seed=7)
    # after the seeding step, the loop only ever keeps improvements
    tail = res.history[1:]
    for a, b in zip(tail, tail[1:], strict=False):
        assert b >= a - 1e-9


@pytest.mark.parametrize("text", BRIEFS)
def test_all_roles_present_and_valid_hex(text):
    idn = direct(parse_brief(text), seed=7).final.identity
    for role in ROLES:
        assert role in idn.swatches
        parse_hex(idn.color(role))  # raises if malformed


@pytest.mark.parametrize("text", BRIEFS)
def test_directed_body_text_meets_AA(text):
    """The headline accessibility promise: directed body text passes AA."""
    idn = direct(parse_brief(text), seed=7).final.identity
    ratio = contrast_ratio(parse_hex(idn.color("text")), parse_hex(idn.color("bg")))
    assert ratio >= 4.5


def test_naive_baseline_is_actually_weaker():
    """Sanity: across briefs, naive must on average underperform directed,
    otherwise the ablation is meaningless."""
    naive_scores, directed_scores = [], []
    for text in BRIEFS:
        b = parse_brief(text)
        naive_scores.append(score(generate_naive(b, seed=7)).aggregate)
        directed_scores.append(direct(b, seed=7).final.aggregate)
    assert sum(directed_scores) / len(directed_scores) > sum(naive_scores) / len(naive_scores) + 0.1


def test_deterministic():
    a = direct(parse_brief("a calm fintech app"), seed=7).final.identity
    b = direct(parse_brief("a calm fintech app"), seed=7).final.identity
    assert {r: a.color(r) for r in ROLES} == {r: b.color(r) for r in ROLES}


def test_critics_return_unit_scores():
    idn = generate(parse_brief("a modern saas platform"), seed=1)
    for c in ALL_CRITICS:
        cq = c.critique(idn)
        assert 0.0 <= cq.score <= 1.0
        assert cq.name == c.name
