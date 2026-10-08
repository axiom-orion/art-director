# Security policy

## Supported versions

Only the `main` branch is supported. There are no maintained release branches; fixes land on `main`.

## Reporting a vulnerability

Please report security issues privately, not in public issues or pull requests:

- Use GitHub's private vulnerability reporting on this repository (**Security → Report a vulnerability**), or
- Email **security@vorion.org**.

Include what you found, how to reproduce it, and the impact you expect. We aim to reply within 7 days.

## Scope

art-director is a local command-line tool and Python library with zero runtime dependencies. It makes no network requests, calls no LLMs, stores no credentials and runs no server. Relevant reports include:

- **HTML output** — brief text or other input reaching the rendered style guide (`render.py`) without escaping, so that opening the generated HTML runs script or injects markup.
- **File writes** — the CLI writes only to the paths given with `--html` and `--tokens`, and `scripts/build_gallery.py` writes only under `gallery/`; anything that makes them write elsewhere.
- **Crafted input** — a brief that causes a crash, hang or runaway resource use.

Note: generated style guides link Google Fonts, so the browser that opens one fetches fonts from Google. That is a property of the output, not a network call by this package. The optional `scripts/shoot_gallery.py` uses Playwright to screenshot local gallery files; Playwright and its browsers are out of scope here.
