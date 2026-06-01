"""Render an Identity to a self-contained, art-directed HTML page.

The output is the proof of craft: a living style guide — palette with measured
contrast badges, the type scale in situ, components (buttons, card, input,
badges), a sample hero in the system's own voice, and the critic scorecard that
produced it. No build step, no external CSS; only the two Google Fonts the
pairing selected. One file you can open or deploy.
"""

from __future__ import annotations

from html import escape

from .color import contrast_ratio, parse_hex, wcag_level
from .identity import Identity, text_on
from .loop import LoopResult


def _contrast_badge(fg_hex: str, bg_hex: str, *, large: bool = False) -> str:
    ratio = contrast_ratio(parse_hex(fg_hex), parse_hex(bg_hex))
    level = wcag_level(ratio, large_text=large)
    cls = {"AAA": "ok", "AA": "ok", "fail": "bad"}[level]
    return f'<span class="badge {cls}">{ratio:.1f}:1 · {level}</span>'


def _swatch_card(identity: Identity, role: str) -> str:
    hexv = identity.color(role)
    on = text_on(identity, role)
    badge = _contrast_badge(on, hexv)
    return f"""
      <div class="swatch" style="background:{hexv};color:{on}">
        <div class="swatch-role">{role}</div>
        <div class="swatch-hex">{hexv}</div>
        <div class="swatch-foot">{badge}</div>
      </div>"""


def _scorecard(result: LoopResult) -> str:
    rows = []
    for name, cq in result.final.critiques.items():
        base = result.baseline.critiques[name].score
        delta = cq.score - base
        arrow = "▲" if delta > 0.001 else ("—" if abs(delta) <= 0.001 else "▼")
        rows.append(
            f"<tr><td>{name}</td><td class='num'>{base:.3f}</td>"
            f"<td class='num'>{cq.score:.3f}</td>"
            f"<td class='num delta'>{arrow} {delta:+.3f}</td>"
            f"<td class='why'>{escape(cq.rationale)}</td></tr>"
        )
    return f"""
    <table class="scorecard">
      <thead><tr><th>critic</th><th>naive</th><th>directed</th><th>Δ</th><th>rationale</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
      <tfoot><tr><td>aggregate</td><td class='num'>{result.baseline.aggregate:.3f}</td>
        <td class='num'>{result.final.aggregate:.3f}</td>
        <td class='num delta'>+{result.final.aggregate-result.baseline.aggregate:.3f}</td>
        <td class='why'>{result.rounds} repair rounds</td></tr></tfoot>
    </table>"""


def render_page(result: LoopResult, *, title: str | None = None) -> str:
    """Render a full LoopResult (baseline + directed) to one HTML document."""
    idn = result.final.identity
    s = idn.swatches
    fonts_url = idn.fonts_url()
    head_font = idn.pairing.heading.stack
    body_font = idn.pairing.body.stack
    ratio = idn.pairing.scale_ratio
    sp = idn.spacing
    rad = idn.radius
    voice = idn.voice
    brief_text = escape(idn.brief.text)
    title = title or f"Identity — {brief_text}"

    # modular type scale sizes (rem) from the pairing ratio
    base = 1.0
    sizes = {f"step{i}": round(base * (ratio ** i), 3) for i in range(-1, 6)}

    btn_text = text_on(idn, "primary")
    swatches = "".join(_swatch_card(idn, r) for r in
                       ("bg", "surface", "text", "muted", "primary", "secondary", "accent"))

    type_specimens = "".join(
        f'<div class="type-row"><span class="type-meta">{name} · {size}rem</span>'
        f'<div class="type-sample" style="font-size:{size}rem">The migration of forms</div></div>'
        for name, size in reversed(list(sizes.items()))
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
{f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="{fonts_url}" rel="stylesheet">' if fonts_url else ''}
<style>
  :root {{
    --bg:{s['bg'].hex}; --surface:{s['surface'].hex}; --text:{s['text'].hex};
    --muted:{s['muted'].hex}; --primary:{s['primary'].hex}; --secondary:{s['secondary'].hex};
    --accent:{s['accent'].hex}; --radius:{rad}px;
    --sp1:{sp[0]}px; --sp2:{sp[1]}px; --sp3:{sp[2]}px; --sp4:{sp[3]}px; --sp5:{sp[4]}px; --sp6:{sp[5]}px;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font-family:{body_font}; line-height:1.6; -webkit-font-smoothing:antialiased; }}
  h1,h2,h3 {{ font-family:{head_font}; line-height:1.12; margin:0 0 var(--sp2); letter-spacing:-0.01em; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:var(--sp6) var(--sp4); }}
  .eyebrow {{ font-family:{body_font}; text-transform:uppercase; letter-spacing:.16em;
    font-size:.72rem; font-weight:600; color:var(--muted); margin-bottom:var(--sp2); }}
  .hero {{ padding:var(--sp6) var(--sp5); border-radius:var(--radius); background:var(--surface);
    border:1px solid color-mix(in srgb, var(--text) 8%, transparent); margin-bottom:var(--sp6); }}
  .hero h1 {{ font-size:{sizes['step5']}rem; max-width:18ch; }}
  .hero p {{ font-size:{sizes['step1']}rem; color:var(--muted); max-width:54ch; }}
  .cta {{ display:inline-flex; gap:var(--sp2); margin-top:var(--sp3); }}
  .btn {{ font-family:{body_font}; font-weight:600; font-size:1rem; border:0; cursor:pointer;
    padding:calc(var(--sp2) + 2px) var(--sp4); border-radius:var(--radius); }}
  .btn-primary {{ background:var(--primary); color:{btn_text}; }}
  .btn-secondary {{ background:transparent; color:var(--text);
    border:1.5px solid var(--secondary); }}
  section {{ margin-bottom:var(--sp6); }}
  .section-title {{ font-size:{sizes['step2']}rem; }}
  .palette {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:var(--sp2); }}
  .swatch {{ border-radius:var(--radius); padding:var(--sp3); min-height:118px;
    display:flex; flex-direction:column; justify-content:space-between;
    border:1px solid color-mix(in srgb, var(--text) 10%, transparent); }}
  .swatch-role {{ font-weight:700; text-transform:capitalize; }}
  .swatch-hex {{ font-family:ui-monospace,monospace; font-size:.8rem; opacity:.85; }}
  .badge {{ font-family:ui-monospace,monospace; font-size:.68rem; font-weight:600;
    padding:2px 7px; border-radius:999px; display:inline-block;
    background:color-mix(in srgb, currentColor 14%, transparent); }}
  .type-row {{ display:flex; align-items:baseline; gap:var(--sp4); padding:var(--sp2) 0;
    border-bottom:1px solid color-mix(in srgb, var(--text) 7%, transparent); }}
  .type-meta {{ font-family:ui-monospace,monospace; font-size:.72rem; color:var(--muted);
    min-width:120px; }}
  .type-sample {{ font-family:{head_font}; }}
  .components {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:var(--sp3); }}
  .card {{ background:var(--surface); border-radius:var(--radius); padding:var(--sp4);
    border:1px solid color-mix(in srgb, var(--text) 8%, transparent); }}
  .card h3 {{ font-size:{sizes['step1']}rem; }}
  .chip {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:.78rem; font-weight:600;
    background:var(--accent); color:{text_on(idn,'accent')}; margin:2px; }}
  .input {{ width:100%; padding:var(--sp2) var(--sp3); border-radius:var(--radius);
    border:1.5px solid var(--muted); background:var(--bg); color:var(--text); font-size:1rem; }}
  .scorecard {{ width:100%; border-collapse:collapse; font-size:.86rem; }}
  .scorecard th,.scorecard td {{ text-align:left; padding:8px 10px;
    border-bottom:1px solid color-mix(in srgb, var(--text) 9%, transparent); vertical-align:top; }}
  .scorecard th {{ font-family:{body_font}; text-transform:uppercase; letter-spacing:.1em;
    font-size:.68rem; color:var(--muted); }}
  .scorecard .num {{ font-family:ui-monospace,monospace; text-align:right; white-space:nowrap; }}
  .scorecard .delta {{ color:var(--primary); }}
  .scorecard .why {{ color:var(--muted); font-size:.8rem; }}
  .scorecard tfoot td {{ font-weight:700; border-top:2px solid var(--text); }}
  .meta-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:var(--sp2); }}
  .meta {{ background:var(--surface); border-radius:var(--radius); padding:var(--sp3);
    border:1px solid color-mix(in srgb, var(--text) 8%, transparent); }}
  .meta b {{ display:block; font-family:ui-monospace,monospace; font-size:.74rem; color:var(--muted);
    text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px; }}
  footer {{ color:var(--muted); font-size:.8rem; padding-top:var(--sp4);
    border-top:1px solid color-mix(in srgb, var(--text) 10%, transparent); }}
</style></head>
<body><div class="wrap">

  <div class="eyebrow">art-director · generated identity</div>
  <div class="hero">
    <div class="eyebrow" style="color:var(--accent)">{escape(voice['tone'])}</div>
    <h1>{escape(voice['headline'])}</h1>
    <p>{escape(voice['sub'])} Brief: “{brief_text}”.</p>
    <div class="cta">
      <button class="btn btn-primary">{escape(voice['cta'])}</button>
      <button class="btn btn-secondary">Learn more</button>
    </div>
  </div>

  <section>
    <div class="eyebrow">Palette · contrast measured to WCAG 2.1</div>
    <h2 class="section-title">Color system</h2>
    <div class="palette">{swatches}</div>
  </section>

  <section>
    <div class="eyebrow">Type · {escape(idn.pairing.heading.name)} + {escape(idn.pairing.body.name)} · scale {ratio}</div>
    <h2 class="section-title">Typographic scale</h2>
    {type_specimens}
  </section>

  <section>
    <div class="eyebrow">Components</div>
    <h2 class="section-title">In context</h2>
    <div class="components">
      <div class="card">
        <h3>Card title</h3>
        <p style="color:var(--muted)">Body copy set in {escape(idn.pairing.body.name)}, sized on the modular scale for comfortable measure.</p>
        <button class="btn btn-primary" style="margin-top:var(--sp2)">{escape(voice['cta'])}</button>
      </div>
      <div class="card">
        <h3>Tags &amp; badges</h3>
        <div><span class="chip">new</span><span class="chip">featured</span><span class="chip">pro</span></div>
        <label style="display:block;margin-top:var(--sp3)">
          <input class="input" placeholder="you@example.com" />
        </label>
      </div>
      <div class="card">
        <h3>Tokens</h3>
        <div class="meta-grid">
          <div class="meta"><b>radius</b>{rad}px</div>
          <div class="meta"><b>base space</b>{sp[0]}px</div>
          <div class="meta"><b>scale</b>{ratio}</div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="eyebrow">Why this passes · the critic loop is the product</div>
    <h2 class="section-title">Scorecard</h2>
    {_scorecard(result)}
  </section>

  <footer>
    Generated by <b>art-director</b> from the brief “{brief_text}”.
    Naive single-shot {result.baseline.aggregate:.3f} → critic-directed {result.final.aggregate:.3f}
    over {result.rounds} repair rounds. Every contrast figure is computed to WCAG 2.1; harmony by CIEDE2000.
  </footer>

</div></body></html>"""
