# CLAUDE.md — art-director

Orientation for future Claude Code sessions. Keep this short and true.

## What this is

**"Taste, made computable."** A one-line brief (e.g. *"a calm fintech app for nurses"*,
*"a brutalist record label"*) becomes a complete visual identity — a roled color palette,
a typeface pairing, a spacing scale, a corner radius, and a voice. A panel of **critics**
then scores that identity against measurable rubrics and a **repair loop** fixes what
fails, rendering the result as a live, art-directed HTML style guide.

The point the repo makes and measures: most of "good design" people call subjective is
actually checkable. Contrast is a number (WCAG 2.1); color harmony is geometry plus a
perceptual distance metric (CIEDE2000); type pairing is a small set of encoded rules;
brief-fit is the distance between what was asked and what the artifact measures.

**Headline result:** across 12 briefs, naive single-shot generation passes WCAG AA
contrast on **12%** of text pairings; the same generator inside the critic loop reaches
**92%**. Numbers are produced by `eval/run_eval.py`, not asserted.

## Constraints (do not break these)

- **Pure Python standard library** for the engine and critics — the "measured taste"
  claim must not depend on a heavy numeric stack. `dependencies = []` in `pyproject.toml`.
  (Only `pytest`/`ruff` as dev extras, `playwright` as an optional `shots` extra for the
  gallery screenshots.)
- **Deterministic + reproducible** eval. CI guards the invariant: the critic loop must
  hold **≥85% AA pass-rate** and beat the naive baseline by **≥0.2 aggregate**, and must
  never ship a result worse than where it started.

## Layout

- `src/art_director/` — `brief` (parse), `color` (LCh / CIEDE2000), `typography`,
  `identity` (assembly), `loop` (generate → critique → repair), `render` (HTML style guide)
- `src/art_director/critics/` — `accessibility` (WCAG 2.1), `harmony`, `typography_critic`,
  `brief_fit`, over a `base` interface
- `eval/` — deterministic ablation harness + `briefs.jsonl` + results
- `gallery/` — rendered style guides (HTML) and screenshots
- `scripts/` — `build_gallery.py`, `shoot_gallery.py` (Playwright)
- `tests/` — 59 tests incl. the Sharma et al. CIEDE2000 reference set

## Commands

```bash
pip install -e ".[dev]"      # or: PYTHONPATH=src
pytest -q                    # full suite (59 tests, pure stdlib)
python -m art_director "a calm fintech app for nurses"   # CLI: brief -> identity
python eval/run_eval.py      # reproduce the ablation table
```

## Through-line

Part of **axiom-orion** — small, eval-driven engineering pieces that each turn one
hand-waved claim into a reproducible number. The generate-then-critique loop here is the
same principle the **Vorion** (`@vorionsys`) governed-AI platform applies to autonomous
agents: don't trust a single shot — hold the output to account and repair what fails.
Built by Ryan Cason.

## Provenance / history (2026-06-15)

- Originally developed on branch `courier/art-director` of the **`genealogy-graphrag`**
  repo (commit `3463bd1`, tree `5ac2cb5`).
- Migrated here as an **exact tree snapshot** (verified identical hash) — the unrelated
  genealogy history was intentionally **not** carried over, keeping this repo clean.
- Landed via **PR #1** (merge commit `58b8619`); the README "Context" section was added
  in `9076715`.

## Known leftover cleanup (as of 2026-06-15)

These branches are redundant (content is in `main`) and safe to delete — they could not
be removed from a web session because the git proxy blocks branch deletions:
- `claude/courier-art-director-migration-LqoPA` (merged via PR #1)
- `claude/courier-art-director-merge-h3WyP` (a parallel migration; subset of `main`)
