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
   NEVER put $ or $$ inside a MathTex string — it's already in math mode.
5. Keep each `MathTex` expression SHORT (≤ 60 chars).  If an equation is
   long, break it into SEPARATE `MathTex` objects stacked with
   `VGroup(...).arrange(DOWN, buff=0.4)`.
6. Use `font_size=36` on every `MathTex`, and `font_size=32` on every `Text`
   that is not a title.  Every title must use `font_size=40`.
7. For parentheses INSIDE a MathTex LaTeX string always use
   `\\left(` and `\\right)` — e.g. r"\\left(x + 1\\right)^2".
   NEVER write bare ( ) characters inside a MathTex string argument.
8. Before showing a new element, `FadeOut` the previous one so the screen
   never gets cluttered.
9. Animations to use: `Write`, `FadeIn`, `FadeOut`, `Transform`,
   `ReplacementTransform`, `Create`, `Indicate`.
10. Color scheme: BLUE for formulas, GREEN for final answers, YELLOW for
    highlights, WHITE for plain text.
    Color constants are ALL CAPS: BLUE, GREEN, YELLOW, WHITE, RED, ORANGE.
    NEVER use quoted color strings like color="blue" — always color=BLUE.
11. Total animation: 15-30 seconds.  Use `self.wait(1)` between steps,
    `self.wait(2)` at the end.
12. Final answer: show inside a `SurroundingRectangle` with GREEN color.
13. DO NOT use `Title(...)` — use `Text("...", font_size=40).to_edge(UP)`.
14. For function curves: `axes.plot(lambda x: expression, x_range=[a, b])`.
    For discrete point sets: `axes.plot_line_graph(x_values=[...], y_values=[...])`.
15. DO NOT import or use any Streamlit API.
16. Output ONLY the Python code — no markdown fences, no explanations.

── TEMPLATE STRUCTURE ─────────────────────────────────────────────
from manim import *

class MathSolution(Scene):
    def construct(self):
        # 1. Title (always text, never Title class)
        title = Text("Problem Title Here", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Show problem statement
        problem = MathTex(r"ax^2 + bx + c = 0", font_size=36).next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(problem))
        self.wait(1)

        # 3. Solution steps — clear previous before showing next
        self.play(FadeOut(problem))
        step1 = MathTex(r"x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}", font_size=36)
        self.play(Write(step1))
        self.wait(1)

        # ... more steps following the same fade-out / show pattern ...

        # Final answer with surrounding box
        self.play(FadeOut(step1))
        answer = MathTex(r"x = 2, \\quad x = 3", color=GREEN, font_size=44)
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
    render_stderr: str = ""  # Manim process output for debugging


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

    # 1. Ensure 'from manim import *' is present (rule 1)
    if 'from manim import' not in script:
        script = 'from manim import *\n\n' + script

    # 2. Replace Title(...) with Text(..., font_size=40).to_edge(UP)
    #    Only when the title argument has no nested parentheses to be safe.
    script = re.sub(
        r'\bTitle\(([^()]+)\)',
        r'Text(\1, font_size=40).to_edge(UP)',
        script,
    )

    # 3. Remove $ and $$ delimiters from MathTex/Tex string args.
    #    MathTex is already in LaTeX math mode — dollar signs cause errors.
    #    We scan character-by-character to handle nested parens correctly.
    def _strip_dollars_from_mathtex(script: str) -> str:
        result: list[str] = []
        i = 0
        pattern = re.compile(r'\b(MathTex|Tex)\s*\(')
        while i < len(script):
            m = pattern.search(script, i)
            if not m:
                result.append(script[i:])
                break
            result.append(script[i:m.end()])  # everything up to and including the opening (
            # Now find the matching closing paren using a depth counter
            depth = 1
            j = m.end()
            while j < len(script) and depth > 0:
                if script[j] == '(':
                    depth += 1
                elif script[j] == ')':
                    depth -= 1
                j += 1
            # script[m.end():j-1] is the content inside MathTex(...)
            inner = script[m.end():j - 1]
            inner = inner.replace('$$', '').replace('$', '')
            result.append(inner + ')')
            i = j
        return ''.join(result)

    script = _strip_dollars_from_mathtex(script)

    # 4. Fix color='string' → color=UPPER_CONSTANT (e.g., color='blue' → color=BLUE)
    def _fix_color_string(m: re.Match) -> str:
        return f', color={m.group(1).upper()}'

    script = re.sub(r',\s*color=["\']([A-Za-z_]+)["\']', _fix_color_string, script)

    # 5. Remove any accidental streamlit imports
    script = re.sub(r'^.*import streamlit.*$', '', script, flags=re.MULTILINE)

    # 6. Remove extra non-Manim imports (numpy, sympy, etc. — not permitted by rule 1)
    script = re.sub(
        r'^(?!from manim import).*\bimport (?:numpy|sympy|math|matplotlib)\b.*$',
        '',
        script,
        flags=re.MULTILINE,
    )

    return script


def _ensure_ffmpeg_in_env(env: dict) -> None:
    """Add ffmpeg to the subprocess environment PATH so Manim can combine frames."""
    import shutil

    if shutil.which("ffmpeg", path=env.get("PATH")):
        return  # already available

    # Try imageio_ffmpeg (bundled with Manim's dependencies)
    try:
        import imageio_ffmpeg  # type: ignore
        ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if ffmpeg_exe.exists():
            ffmpeg_dir = str(ffmpeg_exe.parent)
            env["IMAGEIO_FFMPEG_EXE"] = str(ffmpeg_exe)
            env["FFMPEG_BINARY"] = str(ffmpeg_exe)
            if ffmpeg_dir not in env.get("PATH", ""):
                env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
            logger.info("Using imageio ffmpeg: %s", ffmpeg_exe)
            return
    except (ImportError, Exception):
        pass

    # Common Windows installation paths
    for candidate_dir in [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
        r"C:\tools\ffmpeg\bin",
    ]:
        candidate = Path(candidate_dir) / "ffmpeg.exe"
        if candidate.exists():
            env["PATH"] = candidate_dir + os.pathsep + env.get("PATH", "")
            env["IMAGEIO_FFMPEG_EXE"] = str(candidate)
            env["FFMPEG_BINARY"] = str(candidate)
            logger.info("Found Windows ffmpeg at: %s", candidate)
            return


def _find_manim_python() -> str:
    """Return a Python executable path that has `manim` importable.

    Tries sys.executable first (venv), then common system Python locations on
    Windows so rendering still works even if manim is installed globally.
    """
    import subprocess
    import sys

    candidates = [sys.executable]

    # System Python 3.x installs on Windows that may have manim globally
    for drive in [r"C:", r"D:"]:
        for ver in ["313", "312", "311", "310", "39"]:
            candidates.append(rf"{drive}\Python{ver}\python.exe")
    # User-installed via Microsoft Store / AppData
    candidates.append(
        str(Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python313" / "python.exe")
    )

    for py in candidates:
        if not Path(py).exists():
            continue
        try:
            result = subprocess.run(
                [py, "-c", "import manim"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("Manim found with Python: %s", py)
                return py
        except Exception:
            continue

    # Last resort — hope 'python' on PATH has it
    return sys.executable


def _render_video(script_content: str, script_path: Path) -> tuple[Optional[str], str]:
    """Save the script and run Manim CLI to render it.

    Returns (video_path_or_None, combined_stdout_stderr).
    """
    import subprocess

    script_path.write_text(script_content, encoding="utf-8")
    logger.info("Manim script saved to %s", script_path)

    media_dir = VIDEOS_DIR / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Build subprocess env with ffmpeg on PATH
    env = os.environ.copy()
    _ensure_ffmpeg_in_env(env)

    python_exe = _find_manim_python()
    cmd = [
        python_exe, "-m", "manim",
        "render",
        "-ql",                   # 480p15 — fast render
        "--format", "mp4",
        "--disable_caching",     # avoid TeX file-lock races on Windows
        "--media_dir", str(media_dir),
        str(script_path),
        "MathSolution",
    ]

    logger.info("Running Manim: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(script_path.parent),
            env=env,
        )
    except subprocess.TimeoutExpired:
        msg = "Manim rendering timed out after 180 seconds."
        logger.error(msg)
        return None, msg

    combined = f"=== STDOUT ===\n{proc.stdout}\n=== STDERR ===\n{proc.stderr}"

    # IMPORTANT: always look for the video FIRST before trusting the exit code.
    # Manim exits with code 1 on non-fatal warnings (e.g. MiKTeX update notices)
    # even when the video was successfully written.
    video_dir = media_dir / "videos" / script_path.stem / "480p15"
    if video_dir.exists():
        mp4s = sorted(video_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            logger.info("Manim video ready: %s (exit code %d)", mp4s[0], proc.returncode)
            return str(mp4s[0]), combined

    # Fallback: most-recently-modified mp4 anywhere under media_dir
    all_mp4s = sorted(media_dir.glob("**/*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if all_mp4s:
        logger.info("Manim video (fallback): %s (exit code %d)", all_mp4s[0], proc.returncode)
        return str(all_mp4s[0]), combined

    # No video found — now the exit code matters
    if proc.returncode != 0:
        logger.error("Manim render failed (exit %d):\n%s", proc.returncode, combined)
    else:
        logger.error("Manim exited 0 but no .mp4 was found.\n%s", combined)
    return None, combined


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
        # 1. Generate script via LLM
        script_content = _generate_manim_script(parsed, solver_result, explanation)
        if not script_content or "class MathSolution" not in script_content:
            return VisualizationResult(
                script_content=script_content,
                success=False,
                error="LLM did not produce a valid Manim script with class MathSolution.",
            )

        # 2. Render video
        video_path, render_stderr = _render_video(script_content, script_path)

        if video_path:
            logger.info("Visualization rendered: %s", video_path)
            return VisualizationResult(
                video_path=video_path,
                script_path=str(script_path),
                script_content=script_content,
                success=True,
                render_stderr=render_stderr,
            )
        else:
            return VisualizationResult(
                script_path=str(script_path),
                script_content=script_content,
                success=False,
                error="Manim rendering failed. Check the details below.",
                render_stderr=render_stderr,
            )

    except Exception as exc:
        logger.error("Visualization agent error: %s", exc)
        return VisualizationResult(
            success=False,
            error=str(exc),
        )
