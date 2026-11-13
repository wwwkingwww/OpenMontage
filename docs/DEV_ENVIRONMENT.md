# Development Environment Dependencies

Extra tools needed beyond the Python package install, so local contract tests
can run without environment-driven skips.

## mermaid-cli (`mmdc`)

| Field | Value |
| --- | --- |
| Tool | `@mermaid-js/mermaid-cli` (CLI binary: `mmdc`) |
| Install | `npm install -g "@mermaid-js/mermaid-cli"` |
| Verify | `mmdc --version` (must print a version in a fresh shell) |
| Purpose | Renders Mermaid diagram definitions to images for `DiagramGen` |
| Consumed by | `tools/graphics/diagram_gen.py` (`shutil.which("mmdc")`) |
| Tests that need it | `tests/contracts/test_phase2_contracts.py` → `TestDiagramGenUnit` (`test_render_box_diagram`, `test_render_mermaid_fallback`). `DiagramGen.get_status()` is `AVAILABLE` only when mermaid **and** Pillow backends (flowchart/boxes) are all present; without `mmdc` those two tests skip with `No diagram renderer available`. |

Notes:

- Node.js / npm must already be on `PATH` (this repo’s reference setup: Node 24, npm 11).
- First install downloads Chromium via puppeteer’s postinstall; wait until it finishes.
- Global npm packages are machine-local and are not committed to git.
- Pillow (Python) covers flowchart/boxes rendering; install separately in the project venv if missing (`pip install Pillow`).

## Playwright (Chromium)

| Field | Value |
| --- | --- |
| Tool | `playwright` (Python package) + Chromium browser binary |
| Install package | `.venv/Scripts/python.exe -m pip install playwright` (also listed in `requirements-dev.txt`) |
| Install browser | `.venv/Scripts/python.exe -m playwright install chromium` (~150MB; wait until finished) |
| Verify | `.venv/Scripts/python.exe -c "from playwright.sync_api import sync_playwright; print('ok')"` |
| Purpose | Drives a real Chromium browser for Backlot local board UI bug-bash |
| Consumed by | `tests/backlot/test_ui_bug_bash.py` (`pytest.importorskip("playwright.sync_api")`) |
| Tests that need it | `tests/backlot/test_ui_bug_bash.py` — without the package those tests skip; without Chromium they fail at browser launch |

Notes:

- Browser binaries live under the Playwright cache on the machine and are **not** committed to git.
- Re-run `playwright install chromium` after upgrading the `playwright` package if browser launch fails.
