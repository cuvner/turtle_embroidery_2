import tempfile
from flask import Flask, jsonify, render_template_string, request

from embroider_class import TurtleEmbroidery


def render_svg(pattern) -> str:
    """Return SVG data for the given pattern as a UTF-8 string."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        pattern.save(tmp.name, {"svg": None})
        tmp.flush()
        tmp.seek(0)
        svg_bytes = tmp.read()
    return svg_bytes.decode("utf-8")


app = Flask(__name__)


TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Turtle Embroidery Playground</title>
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      padding: 1rem;
      background: #f6f7fb;
    }
    h1 {
      margin-top: 0;
    }
    .app {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 1rem;
      align-items: stretch;
    }
    textarea {
      width: 100%;
      min-height: 320px;
      font-family: 'Fira Code', 'SFMono-Regular', Menlo, monospace;
      font-size: 14px;
      padding: 0.75rem;
      border-radius: 0.5rem;
      border: 1px solid #cbd5e1;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      background: #ffffff;
      resize: vertical;
      tab-size: 4;
      white-space: pre;
      outline: none;
    }
    textarea:focus {
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
    }
    button {
      background: #6366f1;
      border: none;
      color: white;
      padding: 0.6rem 1rem;
      border-radius: 0.5rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
      transition: transform 120ms ease, box-shadow 120ms ease;
    }
    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 8px 26px rgba(99, 102, 241, 0.45);
    }
    button:disabled {
      opacity: 0.6;
      cursor: wait;
      transform: none;
      box-shadow: none;
    }
    .output {
      background: #ffffff;
      border-radius: 0.75rem;
      padding: 0.75rem;
      border: 1px solid #cbd5e1;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      min-height: 320px;
    }
    .output-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .badge {
      background: #e0f2fe;
      color: #0369a1;
      padding: 0.35rem 0.6rem;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .status {
      min-height: 1.2em;
      color: #0f172a;
      font-weight: 600;
    }
    .error {
      color: #b91c1c;
      white-space: pre-wrap;
    }
    #preview-wrapper {
      flex: 1;
      display: grid;
      place-items: center;
      background: repeating-conic-gradient(#f8fafc 0deg 15deg, #f1f5f9 15deg 30deg);
      border-radius: 0.6rem;
      padding: 0.75rem;
      border: 1px dashed #cbd5e1;
    }
    #preview {
      max-width: 100%;
      max-height: 100%;
      background: white;
      border-radius: 0.35rem;
      padding: 0.35rem;
      border: 1px solid #e2e8f0;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }
    @media (max-width: 900px) {
      .app { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <h1>Turtle Embroidery Playground</h1>
  <p>Write Python turtle commands (forward, left, penup, goto, for loops) to generate embroidery stitches.</p>
  <div class="app">
    <div>
      <textarea id="editor" spellcheck="false"></textarea>
      <div style="margin-top: 0.5rem; display:flex; gap:0.5rem; align-items:center;">
        <button id="run">Run pattern</button>
        <span class="status" id="status"></span>
      </div>
    </div>
    <div class="output">
      <div class="output-header">
        <span class="badge">Preview</span>
        <small>Uses default green thread; outputs SVG</small>
      </div>
      <div id="preview-wrapper">
        <div id="preview">Run to see your stitches</div>
      </div>
      <div id="error" class="error"></div>
    </div>
  </div>
  <script>
    const editor = document.getElementById('editor');
    const runBtn = document.getElementById('run');
    const statusEl = document.getElementById('status');
    const errorEl = document.getElementById('error');
    const preview = document.getElementById('preview');

    const starter = `# Tabs are allowed. Press Enter after a ':' to auto-indent.\nfor i in range(24):\n\tforward(120)\n\tleft(150)\n\tforward(60)\n\tleft(10)\n\npenup()\nleft(90)\nforward(40)\npendown()\nfor i in range(36):\n\tforward(80)\n\tleft(170)`;
    editor.value = starter;

    editor.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') {
        event.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + '\t' + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 1;
      } else if (event.key === 'Enter') {
        event.preventDefault();
        const start = editor.selectionStart;
        const before = editor.value.substring(0, start);
        const currentLineStart = before.lastIndexOf('\n') + 1;
        const line = before.substring(currentLineStart);
        const baseIndent = line.match(/^[\t ]*/)[0];
        const needsExtra = line.trimEnd().endsWith(':');
        const indent = baseIndent + (needsExtra ? '\t' : '');
        const insertion = '\n' + indent;
        const after = editor.value.substring(editor.selectionEnd);
        editor.value = before + insertion + after;
        const cursor = before.length + insertion.length;
        editor.selectionStart = editor.selectionEnd = cursor;
      }
    });

    async function runPattern() {
      runBtn.disabled = true;
      statusEl.textContent = 'Running…';
      errorEl.textContent = '';
      preview.textContent = 'Rendering…';
      try {
        const response = await fetch('/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: editor.value })
        });
        const data = await response.json();
        if (data.error) {
          preview.textContent = 'Error';
          errorEl.textContent = data.error;
        } else {
          preview.innerHTML = data.svg;
          statusEl.textContent = 'Rendered ' + data.point_count + ' points';
        }
      } catch (err) {
        preview.textContent = 'Network error';
        errorEl.textContent = err;
      } finally {
        runBtn.disabled = false;
      }
    }

    runBtn.addEventListener('click', runPattern);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(TEMPLATE)


@app.route("/run", methods=["POST"])
def run_code():
    payload = request.get_json(force=True)
    source = payload.get("code", "")

    t = TurtleEmbroidery(color="#00aa55", step=1.5)
    env = {
        "t": t,
        "forward": t.forward,
        "back": t.back,
        "left": t.left,
        "right": t.right,
        "penup": t.penup,
        "pendown": t.pendown,
        "goto": t.goto,
        "setheading": t.setheading,
        "draw_spiro": t.draw_spiro,
        "draw_square": t.draw_square,
        "range": range,
        "math": __import__("math"),
    }

    try:
        exec(source, {"__builtins__": {}}, env)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"{exc.__class__.__name__}: {exc}"})

    pattern = t.finish()
    svg_content = render_svg(pattern)
    return jsonify({
        "svg": svg_content,
        "point_count": len(t.points),
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
