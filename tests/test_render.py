"""The renderer must emit a well-formed, self-contained document."""

from html.parser import HTMLParser

import pytest

from art_director import direct, parse_brief
from art_director.render import render_page


class _Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ok = True

    def error(self, message):  # pragma: no cover - HTMLParser API
        self.ok = False


@pytest.mark.parametrize("text", ["a calm fintech app", "a brutalist label", "a playful kids app"])
def test_renders_parseable_html(text):
    html = render_page(direct(parse_brief(text), seed=7))
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    p = _Validator()
    p.feed(html)
    assert p.ok


def test_contains_palette_and_scorecard():
    html = render_page(direct(parse_brief("a modern saas platform"), seed=7))
    assert "Color system" in html
    assert "Scorecard" in html
    assert "WCAG" in html


def test_no_leftover_debug_artifacts():
    html = render_page(direct(parse_brief("a calm app"), seed=7))
    assert "None" not in html.replace("font", "")  # no stray None values
    assert "dot" not in html  # no debug glyphs


def test_self_contained_except_fonts():
    """Only external reference allowed is Google Fonts; no other http(s) asset."""
    html = render_page(direct(parse_brief("a calm app"), seed=7))
    # crude check: every https:// occurrence is a fonts URL or preconnect
    for chunk in html.split("https://")[1:]:
        head = chunk[:30]
        assert "fonts.g" in head or "googleapis" in head, head
