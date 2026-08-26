#!/usr/bin/env python3
"""Render docs/demo.svg — the animated terminal demo shown in the README.

Runs the demo commands for real in a throwaway directory, captures their
actual stdout and exit codes, and renders the session as a self-contained
animated SVG. Nothing in the output is hand-transcribed: if the CLI's
behaviour changes, re-running this script changes the demo.

    uv run python scripts/make_demo_svg.py

The animation is pure CSS keyframes on a stack of frame groups, so the file
needs no scripts or external assets and renders inline in a GitHub README.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

# --- terminal geometry -------------------------------------------------------

COLS = 88
ROWS = 23
CHAR_W = 8.4
LINE_H = 19.0
PAD_X = 14.0
PAD_TOP = 40.0  # room for the window chrome
PAD_BOTTOM = 12.0
FONT_SIZE = 14

WIDTH = COLS * CHAR_W + PAD_X * 2
HEIGHT = ROWS * LINE_H + PAD_TOP + PAD_BOTTOM

# --- palette -----------------------------------------------------------------

BG = "#0f1117"
CHROME = "#191c25"
FG = "#c9d1d9"
DIM = "#6e7681"
GREEN = "#7ee787"
RED = "#ff7b72"
YELLOW = "#e3b341"
WHITE = "#e6edf3"

# --- timing (milliseconds) ---------------------------------------------------

TYPE_MS = 55  # per typed chunk
CHUNK = 2  # characters revealed per typing frame
AFTER_ENTER_MS = 180
HOLD_SHORT = 900
HOLD_LONG = 1900
END_HOLD = 2600

Span = tuple[str, str]  # (text, colour)
Line = list[Span]


@dataclass
class Frame:
    duration: int
    lines: list[Line] = field(default_factory=list)


# --- demo definition ---------------------------------------------------------

PROMPT = "❯ "  # noqa: RUF001 - deliberate prompt glyph, not a stray '>'

STEPS: list[tuple[str | None, str, int]] = [
    # (narration comment, command, hold after output)
    (
        "start a project — it becomes a packet of files on disk",
        "swarmlord new csv-linter --summary 'Catch malformed CSV rows'",
        HOLD_SHORT,
    ),
    ("the backlog, with every packet's stage", "swarmlord list", HOLD_LONG),
    ("what should I work on, and what is the next action?", "swarmlord next", HOLD_LONG),
    (
        "promoting runs typed gates against files on disk",
        "swarmlord promote 2026-08-csv-linter --to discovery",
        HOLD_SHORT,
    ),
    (None, "swarmlord promote 2026-08-csv-linter --to spec_ready", HOLD_LONG),
    (
        "gates that aren't satisfied refuse the promotion",
        "swarmlord promote 2026-08-csv-linter --to build_ready",
        HOLD_LONG,
    ),
    (None, "echo $?", END_HOLD),
]


def colourise(text: str) -> Line:
    """Assign a colour to a line of captured CLI output."""
    stripped = text.strip()
    if stripped.startswith("gates failed") or stripped.startswith("error:"):
        return [(text, RED)]
    if stripped.startswith("- ") and "unresolved" in stripped:
        return [(text, RED)]
    if stripped.startswith("ok "):
        return [(text, GREEN)]
    if stripped.startswith("promoted"):
        return [(text, GREEN)]
    if stripped.startswith("created"):
        return [(text, GREEN)]
    if stripped.startswith("next:"):
        return [(text, YELLOW)]
    # Rich's box drawing and table rules read better dimmed.
    if text and all(c in "┏┓┗┛┡┩━│┃┃╇╈┳┻┫┣┼─└┘┌┐ " for c in text):
        return [(text, DIM)]
    if text.startswith("│") or text.startswith("┃"):
        out: Line = []
        for ch in text:
            out.append((ch, DIM if ch in "│┃" else FG))
        return _merge(out)
    return [(text, FG)]


def _merge(spans: Line) -> Line:
    """Collapse adjacent spans that share a colour."""
    merged: Line = []
    for text, colour in spans:
        if merged and merged[-1][1] == colour:
            merged[-1] = (merged[-1][0] + text, colour)
        else:
            merged.append((text, colour))
    return merged


def run_demo() -> list[Frame]:
    # A fixed path, not mkdtemp: the packet path appears in `swarmlord new`'s
    # output, so a random directory would make every regeneration produce a
    # spurious diff in the committed SVG.
    workdir = Path(tempfile.gettempdir()) / "swarmlord-demo"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    env = {
        **os.environ,
        "COLUMNS": str(COLS),
        "TERM": "dumb",
        "NO_COLOR": "1",
    }

    history: list[Line] = []
    frames: list[Frame] = []

    def snapshot(duration: int, current: Line | None = None) -> None:
        lines = list(history)
        if current is not None:
            lines.append(current)
        frames.append(Frame(duration, lines[-ROWS:]))

    snapshot(700)

    last_rc = 0
    for comment, command, hold in STEPS:
        if comment:
            history.append([(PROMPT, GREEN), (f"# {comment}", DIM)])
            snapshot(1100)

        # Type the command out.
        for i in range(0, len(command) + 1, CHUNK):
            snapshot(TYPE_MS, [(PROMPT, GREEN), (command[:i], WHITE)])
        typed: Line = [(PROMPT, GREEN), (command, WHITE)]
        history.append(typed)
        snapshot(AFTER_ENTER_MS)

        if command == "echo $?":
            output, rc = str(last_rc), 0
        else:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
            )
            output = (proc.stdout + proc.stderr).rstrip("\n")
            rc = proc.returncode
            last_rc = rc

        for raw in output.split("\n"):
            if len(raw) > COLS:
                raw = raw[: COLS - 1] + "…"
            history.append(colourise(raw))
        snapshot(hold)

    shutil.rmtree(workdir, ignore_errors=True)
    return frames


# --- SVG emission ------------------------------------------------------------


def render(frames: list[Frame]) -> str:
    total = sum(f.duration for f in frames)
    parts: list[str] = []
    keyframes: list[str] = []
    groups: list[str] = []

    elapsed = 0
    for idx, frame in enumerate(frames):
        start = elapsed / total * 100
        end = (elapsed + frame.duration) / total * 100
        elapsed += frame.duration

        if idx == 0:
            kf = (
                f"@keyframes f{idx}{{0%{{visibility:visible}}"
                f"{end:.4f}%{{visibility:hidden}}100%{{visibility:hidden}}}}"
            )
        else:
            kf = (
                f"@keyframes f{idx}{{0%{{visibility:hidden}}"
                f"{start:.4f}%{{visibility:visible}}"
                f"{end:.4f}%{{visibility:hidden}}100%{{visibility:hidden}}}}"
            )
        keyframes.append(kf)

        rows: list[str] = []
        for row, line in enumerate(frame.lines):
            y = PAD_TOP + (row + 1) * LINE_H
            col = 0
            tspans: list[str] = []
            for text, colour in line:
                if text:
                    x = PAD_X + col * CHAR_W
                    width = len(text) * CHAR_W
                    tspans.append(
                        f'<tspan x="{x:.2f}" textLength="{width:.2f}" '
                        f'lengthAdjust="spacingAndGlyphs" fill="{colour}">'
                        f"{escape(text)}</tspan>"
                    )
                col += len(text)
            if tspans:
                # xml:space is load-bearing: without it the renderer collapses
                # runs of spaces, and textLength then stretches the surviving
                # glyphs across the full column width.
                rows.append(f'<text xml:space="preserve" y="{y:.1f}">{"".join(tspans)}</text>')
        groups.append(f'<g class="f" id="f{idx}">{"".join(rows)}</g>')

    css = (
        f"#screen{{font-family:'DejaVu Sans Mono','SFMono-Regular',Menlo,Consolas,"
        f"'Liberation Mono',monospace;font-size:{FONT_SIZE}px;"
        "white-space:pre;dominant-baseline:middle}"
        f".f{{visibility:hidden;animation-duration:{total}ms;"
        "animation-iteration-count:infinite;animation-timing-function:steps(1,end)}"
        + "".join(f"#f{i}{{animation-name:f{i}}}" for i in range(len(frames)))
        + "".join(keyframes)
    )

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" '
        f'width="{WIDTH:.0f}" height="{HEIGHT:.0f}" role="img" '
        f'aria-label="Terminal recording of the swarmlord CLI creating a packet, '
        f'listing the backlog, and having a stage promotion refused by its gates">'
    )
    parts.append(f"<style>{css}</style>")
    parts.append(f'<rect width="{WIDTH:.0f}" height="{HEIGHT:.0f}" rx="8" fill="{BG}"/>')
    parts.append(
        f'<path d="M0 8a8 8 0 0 1 8-8h{WIDTH - 16:.0f}a8 8 0 0 1 8 8v20H0z" fill="{CHROME}"/>'
    )
    for i, colour in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        parts.append(f'<circle cx="{18 + i * 18}" cy="14" r="5.5" fill="{colour}"/>')
    parts.append(
        f'<text x="{WIDTH / 2:.0f}" y="18" fill="{DIM}" font-size="11" '
        f'text-anchor="middle" font-family="system-ui,sans-serif">swarmlord</text>'
    )
    parts.append(f'<g id="screen">{"".join(groups)}</g>')
    parts.append("</svg>")
    return "".join(parts)


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "docs" / "demo.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = run_demo()
    svg = render(frames)
    out.write_text(svg, encoding="utf-8")
    total = sum(f.duration for f in frames)
    print(f"wrote {out} — {len(frames)} frames, {total / 1000:.1f}s loop, {len(svg) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
