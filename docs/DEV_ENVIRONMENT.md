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
