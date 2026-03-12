"""
Multimodal Math Mentor — Image OCR Pipeline

Engine priority (configurable via OCR_ENGINE env var):
  1. Mathpix  — best-in-class math OCR via REST API  (requires MATHPIX_APP_ID + MATHPIX_APP_KEY)
  2. EasyOCR  — local offline fallback
  3. LLM post-correction — reconstruct/clean math notation from raw OCR output
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from backend.config import OCR_CONFIDENCE_THRESHOLD
from backend.utils.confidence import ConfidenceResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── Lazy singletons ───────────────────────────────────────────────────────────
_easy_reader = None
_pix2tex_model = None


def _get_easyocr():
    """Lazy-initialise EasyOCR (offline fallback)."""
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        logger.info("Loading EasyOCR reader …")
        _easy_reader = easyocr.Reader(["en"], gpu=False)
    return _easy_reader


def _get_pix2tex():
    """Lazy-initialise the pix2tex LatexOCR model."""
    global _pix2tex_model
    if _pix2tex_model is None:
        from pix2tex.cli import LatexOCR
        logger.info("Loading pix2tex LatexOCR model …")
        _pix2tex_model = LatexOCR()
    return _pix2tex_model


# ── Engine detection ──────────────────────────────────────────────────────────

def _pix2tex_available() -> bool:
    """Return True when pix2tex is installed."""
    try:
        import pix2tex  # noqa: F401
        return True
    except ImportError:
        return False


def _mathpix_available() -> bool:
    """Return True when real Mathpix credentials are present in the environment."""
    app_id = os.environ.get("MATHPIX_APP_ID", "").strip()
    app_key = os.environ.get("MATHPIX_APP_KEY", "").strip()
    _placeholders = {"", "your_mathpix_app_id", "your_mathpix_app_key"}
    return (
        bool(app_id and app_key)
        and app_id not in _placeholders
        and app_key not in _placeholders
        and not app_id.endswith("...")
        and not app_key.endswith("...")
    )


def _llm_vision_available() -> bool:
    """Return True when the active LLM provider has a real API key set."""
    from backend.config import _is_placeholder_key
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    key_map = {
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    key = os.environ.get(key_map.get(provider, ""), "")
    return not _is_placeholder_key(key)


# ── LLM Vision OCR ────────────────────────────────────────────────────────────

# Vision models used specifically for OCR (may differ from the chat model)
_VISION_MODELS = {
    "openai":    os.getenv("OPENAI_VISION_MODEL",    "gpt-4o"),
    "groq":      os.getenv("GROQ_VISION_MODEL",      "meta-llama/llama-4-maverick-17b-128e-instruct"),
    "anthropic": os.getenv("ANTHROPIC_VISION_MODEL", "claude-3-5-haiku-20241022"),
    "gemini":    os.getenv("GEMINI_VISION_MODEL",    "gemini-1.5-flash"),
}

# Fallback models to try if the primary vision model is unavailable (Groq only)
_GROQ_VISION_FALLBACKS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

_VISION_OCR_PROMPT = """\
You are a math OCR specialist. Your job is to faithfully extract text from an image of a math problem.

The image may contain:
- Typed or printed text (problem statements, instructions)
- Handwritten text or annotations
- Mathematical expressions, equations, or formulas
- Multiple-choice options (A/B/C/D or checkbox lists)
- Diagrams or figures (describe briefly if present)

Strict rules:
1. Read and output ALL the text visible in the image, top to bottom, left to right.
2. For simple arithmetic or word expressions, use plain text (e.g. "x^2 + 3x - 5 = 0").
3. Only use LaTeX for clearly typeset formulas — never hallucinate LaTeX for plain text.
4. For fractions write: (numerator)/(denominator)  or  \\frac{num}{denom}.
5. For powers write: base^exponent.
6. For multiple-choice questions, list every option on its own line prefixed by the label.
7. Percentages, decimals, and words MUST be transcribed as-is (e.g. "10% - 30%").
8. Do NOT invent, add, or rearrange content.
9. If there are squiggles, doodles, or decorative drawings that are not part of the question, ignore them.
10. Output ONLY the extracted problem text — no commentary, no JSON, no LaTeX preamble.

Example output for a multiple-choice probability question:
Question 1: If you guess all 20 questions on this exam, what is the probability that you will pass?
(a) 10% - 30%
(b) 5% - 10%
(c) 1% - 5%
(d) None of the above
"""


def _llm_vision_ocr(pil_img: Image.Image) -> tuple[str, float]:
    """Use a vision-capable LLM to extract math text from an image.

    Works with OpenAI (gpt-4o), Groq (llama-3.2-vision), Anthropic (claude-3),
    and Google Gemini (gemini-1.5-flash).

    Returns
    -------
    (text, confidence)  where confidence is 0.95 on success, 0.3 if no text found.
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    model = _VISION_MODELS.get(provider, "gpt-4o")

    # Encode image to PNG base64
    buf = io.BytesIO()
    img_rgb = pil_img.convert("RGB") if pil_img.mode not in ("RGB", "L") else pil_img
    img_rgb.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("ascii")

    text = ""

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": _VISION_OCR_PROMPT},
                ],
            }],
            max_tokens=1024,
            temperature=0,
        )
        text = resp.choices[0].message.content or ""

    elif provider == "groq":
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
        # Build ordered list: configured model first, then fallbacks (deduped)
        models_to_try = [model] + [m for m in _GROQ_VISION_FALLBACKS if m != model]
        last_exc: Exception | None = None
        for groq_model in models_to_try:
            try:
                resp = client.chat.completions.create(
                    model=groq_model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                            {"type": "text", "text": _VISION_OCR_PROMPT},
                        ],
                    }],
                    max_tokens=1024,
                    temperature=0,
                )
                text = resp.choices[0].message.content or ""
                if groq_model != model:
                    logger.info("Primary Groq model unavailable; used fallback: %s", groq_model)
                break
            except Exception as exc:
                logger.warning("Groq vision model %s failed: %s", groq_model, exc)
                last_exc = exc
                text = ""
        else:
            # All models failed
            raise RuntimeError(f"All Groq vision models failed. Last error: {last_exc}") from last_exc

    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": _VISION_OCR_PROMPT},
                ],
            }],
        )
        text = resp.content[0].text  # type: ignore[union-attr]

    elif provider == "gemini":
        from google import genai as _genai
        from google.genai import types as _gt
        client = _genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        resp = client.models.generate_content(
            model=model,
            contents=[
                _gt.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                _gt.Part.from_text(text=_VISION_OCR_PROMPT),
            ],
            config=_gt.GenerateContentConfig(temperature=0),
        )
        text = resp.text or ""

    else:
        raise ValueError(f"Vision OCR not supported for provider: {provider!r}")

    text = text.strip()
    confidence = 0.95 if len(text) > 10 else 0.3
    logger.info("LLM vision OCR (%s / %s): %d chars extracted", provider, model, len(text))
    return text, confidence


def _pix2tex_output_is_valid(text: str) -> bool:
    """Return False when pix2tex has produced garbled/garbage LaTeX.

    pix2tex is trained on isolated math equations.  When given a full-page
    image with text, MCQ options, or hand-drawn doodles it outputs sequences
    of nonsense LaTeX commands.  We detect this by checking the ratio of
    readable ASCII words vs LaTeX command tokens.
    """
    if not text or len(text) < 3:
        return False
    import re
    # Count LaTeX command tokens (e.g. \\frac, \\sqrt, \\phi …)
    latex_cmds = len(re.findall(r'\\[a-zA-Z]+', text))
    # Count "word" tokens that look like real English or numeric content
    words = len(re.findall(r'\b[a-zA-Z0-9]{2,}\b', text))
    total = latex_cmds + words
    if total == 0:
        return False
    latex_ratio = latex_cmds / total
    # If more than 60% of all tokens are LaTeX commands on a short string it's
    # likely garbage from a text-heavy image
    if latex_ratio > 0.60 and len(text) < 300:
        logger.warning(
            "pix2tex output looks garbled (%.0f%% LaTeX tokens) — will fall back",
            latex_ratio * 100,
        )
        return False
    return True


def _detect_ocr_engine() -> str:
    """Return the engine to use: 'mathpix' | 'llm_vision' | 'easyocr' | 'pix2tex'.

    Auto-priority:
      1. Mathpix  — cloud, best-in-class for printed math
      2. LLM Vision — cloud, excellent for mixed text/MCQ/handwriting
      3. EasyOCR  — local offline general OCR + LLM post-correction
      4. pix2tex  — local, but ONLY reliable on isolated equation crops
    """
    pref = os.environ.get("OCR_ENGINE", "auto").lower()
    if pref == "mathpix":
        return "mathpix"
    if pref in ("easyocr", "easy_ocr"):
        return "easyocr"
    if pref == "llm_vision":
        return "llm_vision"
    if pref == "pix2tex":
        return "pix2tex"
    # Auto: Mathpix → LLM Vision → EasyOCR → pix2tex (last resort)
    if _mathpix_available():
        return "mathpix"
    if _llm_vision_available():
        return "llm_vision"
    try:
        import easyocr  # noqa: F401
        return "easyocr"
    except ImportError:
        pass
    if _pix2tex_available():
        return "pix2tex"
    raise ImportError(
        "No OCR engine available.\n"
        "Option A — LLM Vision (best overall): set GROQ_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY\n"
        "Option B — Mathpix (best for printed math): add MATHPIX_APP_ID and MATHPIX_APP_KEY\n"
        "Option C — EasyOCR (offline, basic): pip install easyocr\n"
        "Option D — pix2tex (isolated equations only): pip install pix2tex[cli]"
    )


# ── Mathpix OCR ──────────────────────────────────────────────────────────────

def _mathpix_ocr(pil_img: Image.Image) -> tuple[str, float]:
    """Send image to Mathpix API and return (latex_text, confidence).

    Mathpix returns LaTeX by default which is perfect for math problems.
    Confidence is derived from the 'confidence' field in the response
    (range 0-1) or 1.0 if the API call succeeded without errors.

    Returns
    -------
    (text, confidence) — text is the extracted math string, confidence in [0, 1].
    Raises RuntimeError on API failure.
    """
    import urllib.request
    import urllib.parse
    import json

    app_id = os.environ.get("MATHPIX_APP_ID", "").strip()
    app_key = os.environ.get("MATHPIX_APP_KEY", "").strip()

    # Encode image to base64 PNG
    buf = io.BytesIO()
    # Ensure RGB for consistent encoding
    if pil_img.mode not in ("RGB", "L"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    data_url = f"data:image/png;base64,{img_b64}"

    payload = json.dumps({
        "src": data_url,
        "formats": ["text", "latex_simplified"],
        "math_inline_delimiters": ["$", "$"],
        "math_display_delimiters": ["$$", "$$"],
        "rm_spaces": True,
        "rm_fonts": True,
        "include_asciimath": True,
        "include_latex": True,
    }).encode("utf-8")

    headers = {
        "app_id": app_id,
        "app_key": app_key,
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        url="https://api.mathpix.com/v3/text",
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8") if exc.fp else ""
        raise RuntimeError(f"Mathpix API error {exc.code}: {err_body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Mathpix request failed: {exc}") from exc

    # Check for API-level errors
    if "error" in body:
        raise RuntimeError(f"Mathpix error: {body['error']}")

    # Prefer 'text' output which includes inline/display math delimiters
    text = body.get("text") or body.get("latex_simplified") or ""
    confidence = float(body.get("confidence", 1.0))
    # Mathpix confidence_rate is per-character, overall confidence may be absent
    confidence_rate = float(body.get("confidence_rate", confidence))
    final_confidence = (confidence + confidence_rate) / 2

    logger.info(
        "Mathpix OCR: %d chars, confidence=%.3f, confidence_rate=%.3f",
        len(text), confidence, confidence_rate,
    )
    return text.strip(), min(final_confidence, 1.0)


# ── Image preprocessing (used for EasyOCR fallback) ───────────────────────────

def _preprocess(pil_img: Image.Image) -> np.ndarray:
    """Apply a sequence of preprocessing steps optimised for math text.

    Steps:
      1. Convert to RGB (drop alpha if present)
      2. Upscale small images so text is ≥ 30 px tall
      3. Convert to grayscale
      4. Enhance contrast (CLAHE-like via PIL)
      5. Sharpen edges
      6. Light denoise via median filter
      7. Return as numpy array ready for EasyOCR
    """
    # 1. Flatten alpha
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")

    # 2. Upscale if image is small (< 800 px wide) — helps with tiny text
    w, h = pil_img.size
    if w < 800:
        scale = 800 / w
        pil_img = pil_img.resize(
            (int(w * scale), int(h * scale)), Image.LANCZOS
        )
        logger.debug("Upscaled image %.1fx to %dx%d", scale, *pil_img.size)

    # 3. Grayscale
    gray = pil_img.convert("L")

    # 4. Contrast enhancement (raises the ratio by 2×)
    gray = ImageEnhance.Contrast(gray).enhance(2.0)

    # 5. Sharpening
    gray = gray.filter(ImageFilter.SHARPEN)
    gray = gray.filter(ImageFilter.SHARPEN)   # double-pass for blurry images

    # 6. Median filter to reduce noise / salt-pepper artefacts
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    return np.array(gray)


# ── LLM post-correction ───────────────────────────────────────────────────────

_OCR_FIX_PROMPT = """\
You are a math OCR correction specialist.

The following text was extracted from an image of a math problem using OCR.
OCR often makes errors with:
- Superscripts/subscripts printed as normal text (e.g. "x3" should be "x³" or "x^3")
- Fractions (e.g. "1 (x-a)3" might be "1/(x-a)^3")
- Greek letters, brackets, minus signs
- Split tokens from the same expression

Your job:
1. Reconstruct the original math problem as faithfully as possible.
2. Use standard math notation: ^ for powers, / for fractions, sqrt() for roots.
3. Fix obvious OCR mis-reads (e.g. capital "O" vs "0", "l" vs "1").
4. Preserve the problem structure (given conditions, question, multiple choice options if any).
5. Output ONLY the corrected problem text — no explanations, no JSON.

Raw OCR output:
"""


def _llm_fix_ocr(raw_text: str) -> str:
    """Use the LLM to correct OCR errors, especially for math notation."""
    try:
        from backend.config import get_llm_client
        llm = get_llm_client()
        corrected = llm(
            system_prompt=_OCR_FIX_PROMPT,
            user_prompt=raw_text,
            temperature=0.0,
        )
        return corrected.strip()
    except Exception as exc:
        logger.warning("LLM OCR correction failed: %s", exc)
        return raw_text  # fall back to raw OCR text


# ── Main entry point ──────────────────────────────────────────────────────────

def extract_text_from_image(
    image_input: Union[str, Path, np.ndarray, Image.Image],
) -> ConfidenceResult:
    """Run the full OCR pipeline on an image.

    Pipeline: preprocess → OCR (PaddleOCR or EasyOCR) → LLM correction

    Parameters
    ----------
    image_input : file path, numpy array, or PIL Image.

    Returns
    -------
    ConfidenceResult  value = corrected problem text,  score = OCR confidence.
    """
    # ── Convert to PIL Image ──────────────────────────────────────────────
    if isinstance(image_input, (str, Path)):
        pil_img = Image.open(str(image_input))
    elif isinstance(image_input, np.ndarray):
        pil_img = Image.fromarray(image_input)
    elif isinstance(image_input, Image.Image):
        pil_img = image_input
    else:
        return ConfidenceResult(value="", score=0.0, reason="Unsupported image type")

    # ── Preprocess ───────────────────────────────────────────────────────
    processed = _preprocess(pil_img)

    # ── OCR — choose engine ──────────────────────────────────────────────
    try:
        engine = _detect_ocr_engine()
    except ImportError as exc:
        return ConfidenceResult(value="", score=0.0, reason=str(exc))

    raw_text = ""
    avg_confidence = 0.0

    if engine == "mathpix":
        try:
            raw_text, avg_confidence = _mathpix_ocr(pil_img)  # send original (not preprocessed)
            logger.debug("Mathpix raw output:\n%s", raw_text)
        except RuntimeError as exc:
            logger.error("Mathpix OCR failed: %s", exc)
            return ConfidenceResult(value="", score=0.0, reason=f"Mathpix error: {exc}")
    elif engine == "pix2tex":
        try:
            model = _get_pix2tex()
            raw_text = model(pil_img)
            raw_text = raw_text.strip() if raw_text else ""
            logger.debug("pix2tex OCR output:\n%s", raw_text)

            # pix2tex produces garbage on text-heavy / MCQ images.
            # If the output looks invalid, fall back to LLM Vision or EasyOCR.
            if not _pix2tex_output_is_valid(raw_text):
                logger.warning("pix2tex output invalid — falling back to LLM Vision / EasyOCR")
                if _llm_vision_available():
                    raw_text, avg_confidence = _llm_vision_ocr(pil_img)
                    engine = "llm_vision"   # so post-correction is skipped below
                else:
                    # EasyOCR fallback
                    try:
                        reader = _get_easyocr()
                        results = reader.readtext(processed, detail=1, paragraph=False)
                        results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
                        raw_text = "\n".join(t.strip() for _, t, _ in results_sorted if t.strip())
                        confs = [float(c) for _, _, c in results_sorted]
                        avg_confidence = sum(confs) / len(confs) if confs else 0.0
                        engine = "easyocr"
                    except Exception as fb_exc:
                        logger.error("EasyOCR fallback failed: %s", fb_exc)
                        raw_text = ""
            else:
                avg_confidence = 0.92 if len(raw_text) > 5 else 0.3
        except Exception as exc:
            logger.error("pix2tex OCR failed: %s", exc)
            return ConfidenceResult(value="", score=0.0, reason=f"pix2tex OCR error: {exc}")
    elif engine == "llm_vision":
        try:
            raw_text, avg_confidence = _llm_vision_ocr(pil_img)
            logger.debug("LLM vision OCR output:\n%s", raw_text)
        except Exception as exc:
            logger.error("LLM vision OCR failed: %s", exc)
            return ConfidenceResult(value="", score=0.0, reason=f"LLM vision OCR error: {exc}")
    else:
        # EasyOCR fallback — uses the preprocessed numpy array
        try:
            reader = _get_easyocr()
            results = reader.readtext(
                processed,
                detail=1,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7,
                text_threshold=0.5,
                low_text=0.3,
            )
            # Sort by vertical then horizontal position
            results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
            texts: list[str] = []
            confidences: list[float] = []
            for _bbox, text, conf in results_sorted:
                texts.append(text.strip())
                confidences.append(float(conf))
            raw_text = "\n".join(t for t in texts if t)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            logger.info("EasyOCR: %d tokens, avg_conf=%.2f", len(texts), avg_confidence)
        except Exception as exc:
            logger.error("EasyOCR failed: %s", exc)
            return ConfidenceResult(value="", score=0.0, reason=f"OCR error: {exc}")

    if not raw_text.strip():
        return ConfidenceResult(value="", score=0.0, reason="No text detected in image")

    logger.debug("Raw OCR text:\n%s", raw_text)

    # ── LLM post-correction (EasyOCR only) ────────────────────────────────────
    # Mathpix, pix2tex, and LLM Vision already produce clean LaTeX — no post-correction needed.
    if engine in ("mathpix", "pix2tex", "llm_vision"):
        corrected_text = raw_text
    else:
        corrected_text = _llm_fix_ocr(raw_text)
    logger.info("Final OCR text (%s):\n%s", engine, corrected_text)

    needs_review = avg_confidence < OCR_CONFIDENCE_THRESHOLD
    reason = "ocr_low_confidence" if needs_review else "ocr_ok"

    return ConfidenceResult(
        value=corrected_text,
        score=round(avg_confidence, 4),
        reason=reason,
    )
