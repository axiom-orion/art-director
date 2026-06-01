# Ablation results

_12 briefs · seed 7 · scores in [0,1], higher is better. Produced by `eval/run_eval.py`._

| configuration | accessibility | harmony | typography | brief_fit | **aggregate** | **WCAG AA pass** |
|---|---|---|---|---|---|---|
| naive (single-shot) | 0.223 | 0.888 | 0.690 | 0.617 | 0.558 | 0.125 (12/96) |
| + brief-steered generator | 0.834 | 0.909 | 0.904 | 0.827 | 0.862 | 0.875 (84/96) |
| **+ critic loop** | 0.864 | 0.925 | 0.904 | 0.828 | **0.876** | **0.917** (88/96) |

## What moves

- **Accessibility** is where ungoverned generation fails hardest: naive lands **12%** of text pairings at WCAG AA (12/96); the critic loop reaches **92%** (88/96) by measuring every pairing and repairing lightness until it clears the threshold.
- **Aggregate quality** rises 0.558 → 0.876 across 12 briefs, in a mean of 5.2 repair rounds.
- The **brief-steered generator alone** (middle row) already recovers most of the harmony and brief-fit gap; the critic loop's distinct contribution is closing the *accessibility* gap that generation-by-taste leaves open — you cannot eyeball a 4.5:1 contrast ratio, you have to compute it.

## Honest notes

- Scores are **rubric scores, not human ratings.** They measure conformance to encoded design rules (WCAG contrast, CIEDE2000 separation, type-pairing heuristics, brief-fit). They are a proxy for taste, not taste itself; the rules are defensible and inspectable, which is the point.
- The **naive baseline is not a strawman**: it samples plausible colors near the brief hue, exactly as an ungoverned single-shot generator does. Its failure mode is the real one — text a touch too light, brand colors that collide, buttons whose white label misses AA.
- Brief-fit is measured from the **rendered artifact** (re-derived warmth, chroma, contrast, etc.), independent of the generator's inputs, so it catches drift between intent and output.
