import base64
import os
import re
import tempfile
from typing import Iterable, List, Literal, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from pyembroidery import write_pes, write_svg

from embroider_class import TurtleEmbroidery


# ---------- Pydantic models ----------


AllowedOp = Literal[
    "forward",
    "back",
    "left",
    "right",
    "penup",
    "pendown",
    "goto",
    "setheading",
    "draw_square",
    "draw_spiro",
]


class Command(BaseModel):
    op: AllowedOp = Field(..., description="Turtle operation name")
    args: List[float] = Field(default_factory=list, description="Arguments for the operation")

    @validator("args", pre=True, each_item=True)
    def _coerce_float(cls, value):
        try:
            return float(value)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Argument {value!r} is not a number") from exc


class ExportRequest(BaseModel):
    commands: List[Command]
    step: float = Field(1.5, gt=0.01, description="Maximum stitch step length")
    color: str = Field("#00aa55", description="Hex thread colour")


class ExportScriptRequest(BaseModel):
    script: str = Field(..., description="Tiny turtle-like DSL lines")
    step: float = Field(1.5, gt=0.01)
    color: str = Field("#00aa55")


# ---------- Helpers ----------


def _render_svg(pattern) -> str:
    """Write to temp SVG and return the text."""
    fd, path = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    try:
        write_svg(pattern, path)
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    finally:
        if os.path.exists(path):
            os.remove(path)


def _render_pes_bytes(pattern) -> bytes:
    """Write to temp PES and return bytes."""
    fd, path = tempfile.mkstemp(suffix=".pes")
    os.close(fd)
    try:
        write_pes(pattern, path)
        with open(path, "rb") as handle:
            return handle.read()
    finally:
        if os.path.exists(path):
            os.remove(path)


def _apply_command(turtle: TurtleEmbroidery, command: Command):
    """Dispatch a validated command to the turtle instance."""
    op = command.op
    args = command.args

    # simple arity validation
    expected: dict[str, Iterable[int] | int] = {
        "forward": 1,
        "back": 1,
        "left": 1,
        "right": 1,
        "penup": 0,
        "pendown": 0,
        "goto": 2,
        "setheading": 1,
        "draw_square": 1,
        "draw_spiro": (3, 4, 5),
    }

    allowed_counts = expected[op]
    if isinstance(allowed_counts, int):
        allowed_counts = (allowed_counts,)
    if len(args) not in allowed_counts:
        raise ValueError(f"{op} expects {allowed_counts} args, got {len(args)}")

    if op == "forward":
        turtle.forward(args[0])
    elif op == "back":
        turtle.back(args[0])
    elif op == "left":
        turtle.left(args[0])
    elif op == "right":
        turtle.right(args[0])
    elif op == "penup":
        turtle.penup()
    elif op == "pendown":
        turtle.pendown()
    elif op == "goto":
        turtle.goto(args[0], args[1])
    elif op == "setheading":
        turtle.setheading(args[0])
    elif op == "draw_square":
        turtle.draw_square(args[0])
    elif op == "draw_spiro":
        turtle.draw_spiro(*args)
    else:  # pragma: no cover - exhaustive
        raise ValueError(f"Unsupported command: {op}")


def build_pattern(commands: List[Command], *, step: float, color: str):
    """Run command list through TurtleEmbroidery and produce outputs."""
    turtle = TurtleEmbroidery(color=color, step=step)
    for command in commands:
        _apply_command(turtle, command)

    pattern = turtle.finish()
    svg_content = _render_svg(pattern)
    pes_bytes = _render_pes_bytes(pattern)
    return {
        "pattern": pattern,
        "svg": svg_content,
        "pes_bytes": pes_bytes,
        "point_count": len(turtle.points),
    }


def _parse_line_to_command(line: str) -> Command:
    """Parse a single Python-ish call (forward(10), penup(), goto(10, 20))."""
    stripped = line.strip()
    if not stripped:
        raise ValueError("Empty command")

    if "(" not in stripped or not stripped.endswith(")"):
        raise ValueError(f"Commands must use function syntax like forward(10): '{line}'")

    op_part, rest = stripped.split("(", 1)
    op = op_part.strip().lower()
    arg_str = rest[:-1]  # drop trailing ')'
    arg_tokens = [tok for tok in re.split(r"[,\s]+", arg_str.strip()) if tok]

    numeric_args = []
    for arg in arg_tokens:
        try:
            numeric_args.append(float(arg))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not parse argument {arg!r} on line '{line}'") from exc
    return Command(op=op, args=numeric_args)


def _parse_script_block(lines: List[str], start: int, indent: int) -> Tuple[List[Command], int]:
    """
    Recursively parse indented lines into commands.
    Supports:
      repeat N:
        forward 10
        left 90
    """
    commands: List[Command] = []
    i = start
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        leading_spaces = len(raw) - len(raw.lstrip(" "))
        if leading_spaces < indent:
            break
        if leading_spaces > indent:
            raise ValueError(f"Unexpected indentation on line: {raw.strip()}")

        stripped = raw.strip()
        lowered = stripped.lower()
        for_match = re.match(r"for\s+\w+\s+in\s+range\(\s*([0-9]+)\s*\)\s*:\s*$", stripped, re.IGNORECASE)
        if for_match:
            count = int(for_match.group(1))
            block_start = i + 1
            block_indent = indent + 2
            block_commands, consumed = _parse_script_block(lines, block_start, block_indent)
            for _ in range(count):
                commands.extend(block_commands)
            i = consumed
            continue

        commands.append(_parse_line_to_command(stripped))
        i += 1

    return commands, i


def parse_script(script: str) -> List[Command]:
    """Turn the tiny DSL into a validated command list."""
    normalized = script.replace("\t", "  ").splitlines()
    commands, consumed = _parse_script_block(normalized, 0, 0)
    if consumed < len(normalized):
        # extra dedent handled by parser, no-op
        pass
    return commands


# ---------- FastAPI wiring ----------

app = FastAPI(title="Embroidery Exporter", version="1.0.0")


@app.post("/export")
def export_pattern(payload: ExportRequest):
    try:
        result = build_pattern(payload.commands, step=payload.step, color=payload.color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pes_base64 = base64.b64encode(result["pes_bytes"]).decode("ascii")
    return JSONResponse({
        "svg": result["svg"],
        "pes_base64": pes_base64,
        "pes_filename": "turtle_pattern.pes",
        "point_count": result["point_count"],
    })


@app.post("/export_script")
def export_script(payload: ExportScriptRequest):
    try:
        commands = parse_script(payload.script)
        result = build_pattern(commands, step=payload.step, color=payload.color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pes_base64 = base64.b64encode(result["pes_bytes"]).decode("ascii")
    return JSONResponse({
        "svg": result["svg"],
        "pes_base64": pes_base64,
        "pes_filename": "turtle_pattern.pes",
        "point_count": result["point_count"],
        "commands": [c.dict() for c in commands],
    })


# serve /static and /images when present
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.isdir("images"):
    app.mount("/images", StaticFiles(directory="images"), name="images")


@app.get("/")
def root():
    """Serve the SPA entrypoint or redirect if missing."""
    index_path = os.path.join("static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
