# Turtle Embroidery Workbench

Prototype embroidery paths with a turtle-style DSL, preview the stitches as SVG, and export PES files—backed by FastAPI and `pyembroidery`.

## How it works
- Frontend: `static/index.html` is a single-page UI with a script editor (tab/auto-indent), a sample octagon script, export + preview controls, a PES download link, and an animated modal that replays stitched segments.
- Backend: `server.py` exposes two POST endpoints:
  - `/export`: accepts validated command lists (`op` + `args`).
  - `/export_script`: parses a tiny turtle-like DSL, then delegates to shared generation helpers.
- Pipeline: script → commands → `TurtleEmbroidery` → `pyembroidery` → SVG preview + PES bytes (base64 for download).
- Static files/images are served automatically when `static/` or `images/` exist.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the backend
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/static/` to open the UI. (Static hosting is mounted at `/static`.)

## Script syntax (Python-like mini DSL)
- Commands must use function-call form: `forward(40)`, `back(10)`, `left(90)`, `right(45)`, `penup()`, `pendown()`, `goto(10, 20)`, `setheading(0)`, helpers `draw_square(40)`, `draw_spiro(R, r, d [, revolutions] [, step_deg])`.
- Loops: `for i in range(8):` with indented blocks (2 spaces or tabs). Example:
  ```
  for i in range(4):
    forward(80)
    left(90)
  ```
  Use 2 spaces (or tabs) for indentation inside `repeat`.

## API quick reference
- `POST /export`
  ```json
  { "commands": [ { "op": "forward", "args": [50] }, { "op": "left", "args": [90] } ], "step": 1.5, "color": "#00aa55" }
  ```
- `POST /export_script`
  ```json
  { "script": "repeat 4:\n  forward 50\n  left 90", "step": 1.5, "color": "#00aa55" }
  ```
Responses include `svg`, `pes_base64`, `pes_filename`, and `point_count` (plus echoed `commands` for `/export_script`).

## Dependencies
`fastapi`, `uvicorn`, `pyembroidery`, `pillow`, `flask` (legacy Flask UI is still available in `app.py`).
