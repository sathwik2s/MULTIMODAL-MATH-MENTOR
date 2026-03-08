"""
Multimodal Math Mentor — Visualization Agent

Generates animated math explanations using Manim.
Uses the LLM to create a Manim script from the solution steps,
then renders it to an MP4 video.
"""

from __future__ import annotations

import hashlib
import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.config import get_llm_client
from backend.agents.parser_agent import ParsedProblem
from backend.agents.solver_agent import SolverResult
from backend.agents.explainer_agent import Explanation
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── Ensure ffmpeg is executable (prefer system ffmpeg on hosted platforms) ───
_system_ffmpeg = Path("/usr/bin/ffmpeg")
if _system_ffmpeg.exists():
    ffmpeg_path = str(_system_ffmpeg)
    # Force imageio/manim to use system ffmpeg instead of bundled site-packages binary.
    os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_path)
    os.environ.setdefault("FFMPEG_BINARY", ffmpeg_path)
    if "/usr/bin" not in os.environ.get("PATH", ""):
        os.environ["PATH"] = "/usr/bin" + os.pathsep + os.environ.get("PATH", "")
    logger.info("Using system ffmpeg: %s", ffmpeg_path)
else:
    try:
        import imageio_ffmpeg  # type: ignore
        _ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        # Do not copy/modify binaries under site-packages (read-only on many hosts).
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", str(_ffmpeg_exe))
        _ffmpeg_dir = str(_ffmpeg_exe.parent)
        if _ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        logger.info("Using imageio ffmpeg binary: %s", _ffmpeg_exe)
    except ImportError:
        pass  # Hope ffmpeg is already on system PATH

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VIDEOS_DIR = _PROJECT_ROOT / "outputs" / "videos"
SCRIPTS_DIR = _PROJECT_ROOT / "outputs" / "manim_scripts"

for _d in (VIDEOS_DIR, SCRIPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = """\
You are a Manim Community Edition (v0.18+) animation expert.
Given a solved math problem, generate a Python script that creates
a clean, visually appealing, step-by-step animated explanation.

── STRICT RULES (violating any will break rendering) ──────────────

1. First line of code: `from manim import *`  — NO other imports.
2. Exactly ONE class: `class MathSolution(Scene):` with a `construct` method.
3. Use ONLY these Mobject types:  `Text`, `MathTex`, `Tex`, `VGroup`,
   `SurroundingRectangle`, `Arrow`, `Axes`, `NumberPlane`.
4. Every `MathTex`/`Tex` string MUST be a raw string:  r"...".
5. Keep each `MathTex` expression SHORT (≤ 60 chars).  If an equation is
   long, break it into separate `MathTex` objects and stack them with
   `VGroup(...).arrange(DOWN, buff=0.4)`.
6. Use `.scale(0.7)` or `font_size=36` for any Text/MathTex that could
   overflow the screen.
7. Before showing a new element, `FadeOut` or `Uncreate` the previous one
   so the screen never gets cluttered.
8. Animations to use: `Write`, `FadeIn`, `FadeOut`, `Transform`,
   `ReplacementTransform`, `Create`, `Indicate`.
9. Color scheme: BLUE for formulas, GREEN for final answers, YELLOW for
   highlights, WHITE for plain text.
10. Total animation: 15-30 seconds.  Use `self.wait(1)` between steps,
    `self.wait(2)` at the end.
11. Final answer: show inside a `SurroundingRectangle` with GREEN color.
12. DO NOT use `Title(...)` — use `Text(..., font_size=40)` placed at `UP*3`.
13. DO NOT use `ax.plot()` — use `ax.plot_line_graph` or `ax.get_graph` if
    you need a function graph.
14. DO NOT use `use_container_width` or any Streamlit API.
15. Output ONLY the Python code — no markdown fences, no explanations.

── TEMPLATE STRUCTURE ─────────────────────────────────────────────
from manim import *

class MathSolution(Scene):
    def construct(self):
        # 1. Title
        title = Text("Problem Title Here", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Show problem
        problem = MathTex(r"...", font_size=36).next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(problem))
        self.wait(1)

        # 3. Solution steps (clear previous, show new)
        self.play(FadeOut(problem))
        step1 = MathTex(r"...", font_size=36)
        self.play(Write(step1))
        self.wait(1)

        # ... more steps ...

        # Final answer with box
        answer = MathTex(r"...", color=GREEN, font_size=44)
        box = SurroundingRectangle(answer, color=GREEN, buff=0.2)
        self.play(FadeIn(answer), Create(box))
        self.wait(2)
"""


@dataclass
class VisualizationResult:
    """Output of the visualization agent."""

    video_path: str = ""
    script_path: str = ""
    script_content: str = ""
    success: bool = False
    error: str = ""


def _generate_manim_script(
    parsed: ParsedProblem,
    solver_result: SolverResult,
    explanation: Explanation,
) -> str:
    """Use the LLM to generate a Manim script for the solution."""
    steps_text = ""
    if explanation.steps:
        for step in explanation.steps:
            n = step.get("step_number", "?")
            desc = step.get("description", "")
            formula = step.get("formula_used", "")
            result = step.get("result", "")
            steps_text += f"Step {n}: {desc}"
            if formula:
                steps_text += f" [Formula: {formula}]"
            if result:
                steps_text += f" [Result: {result}]"
            steps_text += "\n"

    user_prompt = textwrap.dedent(f"""\
        Problem: {parsed.problem_text}
        Topic: {parsed.topic}
        Domain: {parsed.topic}

        Solution Steps:
        {steps_text}

        Final Answer: {explanation.final_answer or solver_result.answer}
        LaTeX Answer: {solver_result.latex_answer}

        Generate a Manim animation script for this solution.
    """)

    llm = get_llm_client()
    response = llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
    )

    # Strip markdown fences if the LLM added them
    script = response.strip()
    script = re.sub(r"^```(?:python)?\s*", "", script)
    script = re.sub(r"\s*```$", "", script)
    script = script.strip()

    # ── Auto-fix common LLM mistakes ────────────────────────────────
    script = _sanitize_manim_script(script)

    return script


def _sanitize_manim_script(script: str) -> str:
    """Auto-fix common Manim script issues produced by LLMs."""

    # 1. Replace Title(...) with Text(..., font_size=40).to_edge(UP)
    #    Handles both Title("...") and Title(r"...")
    script = re.sub(
        r'Title\(([^)]+)\)',
        r'Text(\1, font_size=40).to_edge(UP)',
        script,
    )

    # 2. Remove $ and $$ delimiters from inside MathTex/Tex calls
    #    MathTex is ALREADY math mode — dollar signs cause rendering errors
    def _strip_dollars_in_mathtex(m: re.Match) -> str:
        prefix = m.group(1)  # "MathTex(" or "Tex("
        inner = m.group(2)   # everything inside the call
        suffix = m.group(3)  # closing ")"
        # Strip $$ first then $, only from string contents
        inner = re.sub(r'\$\$', '', inner)
        inner = re.sub(r'\$', '', inner)
        return prefix + inner + suffix

    script = re.sub(
        r'((?:MathTex|Tex)\s*\()(.+?)(\))',
        _strip_dollars_in_mathtex,
        script,
    )

    # 3. Replace deprecated ax.plot() with ax.plot_line_graph()
    script = script.replace('.plot(', '.plot_line_graph(')

    # 4. Ensure 'from manim import *' is the first import line
    if 'from manim import' not in script:
        script = 'from manim import *\n\n' + script

    # 5. Remove any accidental streamlit imports
    script = re.sub(r'^.*import streamlit.*$', '', script, flags=re.MULTILINE)

    # 6. Add font_size to MathTex calls that don't have it
    def _add_font_size(m: re.Match) -> str:
        call = m.group(0)
        if 'font_size' in call or 'scale' in call:
            return call
        # Insert font_size before closing paren
        return call[:-1] + ', font_size=36)'

    script = re.sub(
        r'MathTex\([^)]+\)',
        _add_font_size,
        script,
    )

    # 7. Remove any extra import lines (LLM sometimes adds numpy, sympy, etc.)
    script = re.sub(r'^(?!from manim import).*import (?:numpy|sympy|math|matplotlib).*$', '',
                    script, flags=re.MULTILINE)

    return script


def _render_video(script_content: str, script_path: Path) -> Optional[str]:
    """Save the script and run Manim CLI to render it.

    Returns the path to the rendered video, or None on failure.
    """
    import subprocess
    import sys

    script_path.write_text(script_content, encoding="utf-8")
    logger.info("Manim script saved to %s", script_path)

    # Use a dedicated media dir per script to avoid cache-lock conflicts
    media_dir = VIDEOS_DIR / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Run manim rendering
    cmd = [
        sys.executable, "-m", "manim",
        "render",
        "-ql",                          # low quality for speed
        "--format", "mp4",
        "--disable_caching",            # avoid TeX file-lock issues on Windows
        "--media_dir", str(media_dir),
        str(script_path),
        "MathSolution",
    ]

    logger.info("Running Manim: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(script_path.parent),
        env=os.environ.copy(),
    )

    if result.returncode != 0:
        logger.error("Manim render failed:\nstdout: %s\nstderr: %s", result.stdout, result.stderr)
        return None

    # Find the output video: Manim writes to <media>/videos/<script_stem>/480p15/MathSolution.mp4
    video_dir = media_dir / "videos" / script_path.stem / "480p15"
    if video_dir.exists():
        mp4s = list(video_dir.glob("*.mp4"))
        if mp4s:
            return str(mp4s[0])

    # Fallback: search recursively for any mp4 produced recently
    mp4s = list(media_dir.glob("**/*.mp4"))
    if mp4s:
        mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return str(mp4s[0])

    return None


def generate_visualization(
    parsed: ParsedProblem,
    solver_result: SolverResult,
    explanation: Explanation,
) -> VisualizationResult:
    """Generate an animated Manim visualization of the solution.

    Steps:
    1. LLM generates a Manim script.
    2. Script is saved to disk.
    3. Manim CLI renders the video.
    4. Video path is returned.
    """
    # Unique filename based on problem content
    content_hash = hashlib.md5(
        parsed.problem_text.encode(), usedforsecurity=False
    ).hexdigest()[:10]
    script_name = f"solution_{content_hash}.py"
    script_path = SCRIPTS_DIR / script_name

    try:
        # 1. Generate script
        script_content = _generate_manim_script(parsed, solver_result, explanation)
        if not script_content or "class MathSolution" not in script_content:
            return VisualizationResult(
                script_content=script_content,
                success=False,
                error="LLM did not produce a valid Manim script with class MathSolution.",
            )

        # 2. Render video
        video_path = _render_video(script_content, script_path)

        if video_path:
            logger.info("Visualization rendered: %s", video_path)
            return VisualizationResult(
                video_path=video_path,
                script_path=str(script_path),
                script_content=script_content,
                success=True,
            )
        else:
            return VisualizationResult(
                script_path=str(script_path),
                script_content=script_content,
                success=False,
                error="Manim rendering failed. The script may have syntax errors.",
            )

    except Exception as exc:
        logger.error("Visualization agent error: %s", exc)
        return VisualizationResult(
            success=False,
            error=str(exc),
        )
