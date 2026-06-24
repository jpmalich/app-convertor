"""HOVER per-elevation vision verification — Iter 78p (Phase 2 of 3).

Renders the elevation-drawing pages from a HOVER PDF, sends each one to
Claude Opus 4.5 Vision, and compares the drawing-extracted area to the
text-extracted `per_elevation_siding` (when HOVER broke it out) or to the
overall `siding_sqft` (when it didn't).

Returns Phase 1-shaped warning dicts so the same yellow banner in the
preview modal surfaces both rule-based AND vision-based discrepancies.

Cost: one Claude Opus 4.5 vision call per elevation page found (typically
4-6 pages). Caps at 6 pages to bound spend.

Phase 3 ("Deep Verify") will reuse `_render_pdf_pages` from this module.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
from typing import Optional

import fitz  # PyMuPDF — already imported elsewhere in hover.py
from emergentintegrations.llm.chat import (
    ImageContent,
    LlmChat,
    UserMessage,
)

logger = logging.getLogger(__name__)

# Same model as the existing HOVER text extraction + AI Measure flows.
MODEL_NAME = "claude-opus-4-5-20251101"
MAX_ELEVATION_PAGES = 6   # Hard cap on vision calls per HOVER (cost control)
RENDER_DPI = 144          # Crisp enough for Claude to read dim callouts,
                          # not so high it blows the token budget
DELTA_PCT_THRESHOLD = 12  # Drawing-vs-text delta % above which we warn.
                          # 12% absorbs scale-bar rounding + drawing
                          # generalization without missing real mis-reads.

# Elevation page detector — match the text on the rendered PDF page
# against any of these prefix tokens. HOVER reports use exactly these
# labels ("Front Elevation", "Left Elevation", etc.).
_ELEV_LABELS = ("Front", "Back", "Rear", "Left", "Right",
                "Side A", "Side B", "Side C", "Side D")
_ELEV_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _ELEV_LABELS) + r")\s+Elevation\b",
    re.IGNORECASE,
)


VISION_PROMPT = """\
You are looking at a single ELEVATION page from a HOVER measurement report.
This page shows a 2D drawing of one face of a residential home with labeled
dimensions, a scale bar, and rectangles for every window/door opening.

Return ONE JSON object (no markdown, no commentary):
{
  "elevation_label": "<Front | Back | Left | Right | Side A | ...>",
  "facade_width_ft": <number>,           // wall width along the eave
  "facade_height_ft": <number>,          // ground to peak (or eave if flat)
  "gross_wall_sqft": <number>,           // width × height (gross, before openings)
  "opening_count": <integer>,            // total windows + doors on this face
  "siding_sqft": <number | null>,        // net of openings if shown on the page;
                                         // null if only gross is labeled
  "confidence": "high" | "medium" | "low",
  "notes": "<one short string explaining anomalies if confidence is low>"
}

CRITICAL RULES:
- Use ONLY the numbers visible on this drawing. Do NOT calculate using
  outside knowledge of typical homes.
- If a dimension is partially obscured or your read is uncertain, set
  `confidence` to medium/low and surface the issue in `notes`.
- If the page is NOT an elevation drawing (e.g. roof view, summary table,
  cover page), return: {"elevation_label": "NOT_AN_ELEVATION", ...zeros}
- `siding_sqft` should be NET when the drawing explicitly shows a net
  number; otherwise null. NEVER guess net by subtracting an assumed
  opening size — only report what's labeled.
"""


def _render_pdf_pages(pdf_bytes: bytes, max_pages: int = MAX_ELEVATION_PAGES) -> list[dict]:
    """Open the HOVER PDF, locate elevation pages by their on-page text,
    render each one at `RENDER_DPI` as PNG bytes. Returns up to
    `max_pages` page records: `{page_num, label, png_bytes}`."""
    out: list[dict] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.warning("Iter 78p: PyMuPDF could not open HOVER PDF: %s", e)
        return out

    try:
        for page_num in range(doc.page_count):
            if len(out) >= max_pages:
                break
            page = doc.load_page(page_num)
            text = page.get_text("text") or ""
            match = _ELEV_RE.search(text)
            if not match:
                continue
            label = match.group(1).title()
            try:
                pix = page.get_pixmap(dpi=RENDER_DPI)
                png_bytes = pix.tobytes("png")
            except Exception as e:
                logger.warning("Iter 78p: page %d render failed: %s", page_num, e)
                continue
            # Sanity cap on image size — emergentintegrations chokes on
            # very large payloads. ~1.5MB is plenty for a 144-DPI page.
            if len(png_bytes) > 2_500_000:
                logger.info("Iter 78p: page %d image %.1fMB, skipping",
                            page_num, len(png_bytes) / 1e6)
                continue
            out.append({"page_num": page_num + 1, "label": label,
                        "png_bytes": png_bytes})
    finally:
        doc.close()
    return out


def _json_from_reply(reply: str) -> dict:
    """Strip code fences and parse the first JSON object Claude returned.
    Same shape as the helper in `ai_measure.py` but lighter-weight."""
    if not reply:
        return {}
    s = reply.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)
    # Find first {…} object — handles Claude's occasional preface text
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return {}


async def _read_one_elevation(
    page: dict,
    api_key: str,
    session_id: str,
) -> Optional[dict]:
    """Send a single rendered PDF page to Claude Vision. Returns the parsed
    JSON or None if the call/parse failed (silent — never raises)."""
    chat = LlmChat(
        api_key=api_key,
        session_id=f"{session_id}-p{page['page_num']}",
        system_message=VISION_PROMPT,
    ).with_model("anthropic", MODEL_NAME)
    msg = UserMessage(
        text=(
            f"Hint: this is most likely the '{page['label']} Elevation' page. "
            f"Extract per the JSON schema above."
        ),
        file_contents=[ImageContent(
            image_base64=base64.b64encode(page["png_bytes"]).decode("ascii"),
        )],
    )
    try:
        reply = await chat.send_message(msg)
    except Exception as e:
        logger.warning("Iter 78p: vision call failed on page %d: %s",
                       page["page_num"], e)
        return None
    parsed = _json_from_reply(reply or "")
    if not parsed or parsed.get("elevation_label") == "NOT_AN_ELEVATION":
        return None
    parsed["__page_num"] = page["page_num"]
    parsed["__expected_label"] = page["label"]
    return parsed


def _pct_delta(a: float, b: float) -> float:
    if a == 0 and b == 0:
        return 0.0
    if a == 0 or b == 0:
        return 100.0
    return abs(a - b) / max(abs(a), abs(b)) * 100.0


def _build_warnings(
    vision_results: list[dict],
    measurements: dict,
) -> list[dict]:
    """Compare each elevation's drawing-extracted area to the text-extracted
    siding total. Builds Phase 1-shaped warning dicts (same banner)."""
    warnings: list[dict] = []
    text_per_elev = measurements.get("per_elevation_siding") or {}
    total_siding = float(measurements.get("siding_sqft") or 0)
    drawing_total = 0.0
    elev_lines: list[str] = []

    for vr in vision_results:
        label = vr.get("elevation_label") or vr.get("__expected_label") or "?"
        drawing_net = vr.get("siding_sqft")
        drawing_gross = float(vr.get("gross_wall_sqft") or 0)
        # Prefer net (siding) — fall back to gross when HOVER drawing
        # didn't label a net.
        drawing_area = float(drawing_net) if drawing_net not in (None, 0) else drawing_gross
        drawing_total += drawing_area

        # Per-elevation comparison if text has it broken out
        text_area_raw = text_per_elev.get(label) or text_per_elev.get(label.lower())
        if isinstance(text_area_raw, dict):
            text_area = float(
                text_area_raw.get("siding_sqft")
                or text_area_raw.get("net")
                or text_area_raw.get("gross")
                or 0
            )
        else:
            text_area = float(text_area_raw or 0)
        if text_area > 0 and drawing_area > 0:
            delta = _pct_delta(text_area, drawing_area)
            if delta > DELTA_PCT_THRESHOLD:
                warnings.append({
                    "code": f"vision_elev_delta_{label.lower().replace(' ', '_')}",
                    "level": "warn",
                    "message": (
                        f"{label} Elevation: drawing area looks "
                        f"{'high' if drawing_area > text_area else 'low'} vs text"
                    ),
                    "detail": (
                        f"Drawing ≈ {drawing_area:.0f} ft² · Text {text_area:.0f} ft² · "
                        f"Δ = {delta:.0f}% · confidence={vr.get('confidence', '?')}"
                    ),
                })
        elev_lines.append(f"{label}: {drawing_area:.0f} ft²")

    # Overall: drawing-total vs text siding_sqft
    if drawing_total > 0 and total_siding > 0:
        delta = _pct_delta(total_siding, drawing_total)
        if delta > DELTA_PCT_THRESHOLD:
            warnings.append({
                "code": "vision_total_delta",
                "level": "warn",
                "message": (
                    f"Total siding from drawings ({drawing_total:.0f} ft²) "
                    f"differs from text ({total_siding:.0f} ft²) by {delta:.0f}%"
                ),
                "detail": " · ".join(elev_lines) if elev_lines else None,
            })
    elif drawing_total > 0:
        # Info-only: drawings gave us a number, text didn't.
        warnings.append({
            "code": "vision_drawings_sum_info",
            "level": "info",
            "message": (
                f"Drawings sum to ≈ {drawing_total:.0f} ft² of siding "
                f"(per-elevation: {', '.join(elev_lines)})"
            ),
        })
    return warnings


async def run_vision_pass(
    pdf_bytes: bytes,
    measurements: dict,
    api_key: str,
    session_id: str = "hover-vision",
    cache_key: Optional[str] = None,
    cache_writer=None,
) -> tuple[list[dict], dict]:
    """Public entrypoint. Renders elevation pages, runs Claude Vision on
    each, returns `(warnings, per_elevation_drawing_data)`.

    `per_elevation_drawing_data` is the raw per-elevation dict
    `{label: {gross, siding_sqft, opening_count, confidence}}` ready to
    stash on the estimate for the Per-Elevation Breakdown card.

    If `cache_key` and `cache_writer` are provided, the rendered PNG of
    each elevation is stashed via `cache_writer(cache_key, label, png_b64)`
    so Phase 3 Deep Verify can replay the same image without re-uploading
    the PDF. Cache writes happen even when vision parsing fails.
    """
    pages = _render_pdf_pages(pdf_bytes)
    if not pages:
        logger.info("Iter 78p: no elevation pages detected — skipping vision pass")
        return [], {}

    # Iter 78q — stash the rendered PNGs for Phase 3 Deep Verify before
    # we hit the LLM. Even if every vision call fails, the contractor can
    # still trigger Deep Verify manually on a flagged elevation.
    if cache_key and cache_writer:
        try:
            for p in pages:
                png_b64 = base64.b64encode(p["png_bytes"]).decode("ascii")
                await cache_writer(cache_key, p["label"], png_b64, p["page_num"])
        except Exception as e:
            logger.warning("Iter 78q: page cache write failed: %s", e)

    logger.info("Iter 78p: running vision pass on %d elevation pages", len(pages))
    # Parallelize the vision calls — they're network-bound (~30-60s each)
    # so running 4-6 in parallel takes the same wall-time as one.
    results = await asyncio.gather(
        *(_read_one_elevation(p, api_key, session_id) for p in pages),
        return_exceptions=False,
    )
    results = [r for r in results if r]
    if not results:
        logger.info("Iter 78p: no vision results returned (all calls failed/empty)")
        return [], {}

    warnings = _build_warnings(results, measurements)
    per_elev: dict = {}
    for r in results:
        lbl = (r.get("elevation_label") or r.get("__expected_label") or "?").title()
        per_elev[lbl] = {
            "gross_wall_sqft": r.get("gross_wall_sqft"),
            "siding_sqft": r.get("siding_sqft"),
            "facade_width_ft": r.get("facade_width_ft"),
            "facade_height_ft": r.get("facade_height_ft"),
            "opening_count": r.get("opening_count"),
            "confidence": r.get("confidence"),
            "source": "claude_vision",
            "page_num": r.get("__page_num"),
        }
    return warnings, per_elev


# =============================================================================
# Iter 78q — Phase 3: Deep Verify (scale-bar measurement)
# =============================================================================

DEEP_VERIFY_PROMPT = """\
You are looking at a single ELEVATION drawing from a HOVER measurement report.
This is a SECOND-OPINION verification pass. Your job is to measure the
facade using ONLY the visible scale bar — IGNORE the labeled dimension
callouts entirely.

Methodology:
1. Find the scale bar on the drawing. Read its labeled length (e.g. "20 ft").
2. Measure that scale bar's pixel length on the image (use the leftmost
   and rightmost endpoints).
3. Compute the ft-per-pixel ratio.
4. Measure the eave run (top horizontal of the wall) in pixels.
5. Measure the facade height (ground line to eave) in pixels.
6. Multiply by the ft-per-pixel ratio.

Return ONE JSON object (no markdown, no commentary):
{
  "scale_bar_label_ft": <number>,            // e.g. 20
  "scale_bar_pixels": <number>,
  "ft_per_pixel": <number>,                  // = label / pixels
  "measured_width_ft": <number>,             // eave run × ft_per_pixel
  "measured_height_ft": <number>,            // ground-to-eave × ft_per_pixel
  "measured_gross_wall_sqft": <number>,      // width × height
  "scale_bar_found": <true | false>,
  "confidence": "high" | "medium" | "low",
  "notes": "<string — anomalies, occluded scale bar, unusual roof shape, etc>"
}

CRITICAL RULES:
- Do NOT use any number from a labeled dim callout.
- If the scale bar is missing/illegible, set `scale_bar_found: false`,
  confidence "low", and leave measurements as best-effort estimates.
- This is a cross-check; precision matters more than speed.
"""


async def deep_verify_elevation(
    png_b64: str,
    label: str,
    api_key: str,
    session_id: str = "hover-deep-verify",
) -> dict:
    """Run the Phase 3 scale-bar prompt on a single elevation image."""
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=DEEP_VERIFY_PROMPT,
    ).with_model("anthropic", MODEL_NAME)
    msg = UserMessage(
        text=(
            f"Verify the '{label} Elevation' by independently measuring "
            f"against the scale bar. Return JSON only."
        ),
        file_contents=[ImageContent(image_base64=png_b64)],
    )
    try:
        reply = await chat.send_message(msg)
    except Exception as e:
        logger.warning("Iter 78q: Deep Verify call failed: %s", e)
        return {"ok": False, "error": str(e)}
    parsed = _json_from_reply(reply or "")
    parsed["ok"] = True
    parsed["label"] = label
    return parsed


def reconcile_deep_verify(
    deep_result: dict,
    measurements: dict,
    phase2_drawing: dict,
) -> dict:
    """Compare the Deep Verify (scale-bar) numbers to the Phase 2 numbers
    AND the text-extracted numbers. Returns a verdict block the frontend
    renders in the modal as a three-way comparison panel."""
    label = deep_result.get("label") or "?"
    measured = float(deep_result.get("measured_gross_wall_sqft") or 0)
    phase2_gross = float(phase2_drawing.get("gross_wall_sqft") or 0)
    phase2_net = float(phase2_drawing.get("siding_sqft") or 0)
    text_per_elev = measurements.get("per_elevation_siding") or {}
    text_raw = text_per_elev.get(label) or text_per_elev.get(label.lower())
    if isinstance(text_raw, dict):
        text_area = float(text_raw.get("siding_sqft") or text_raw.get("net")
                          or text_raw.get("gross") or 0)
    else:
        text_area = float(text_raw or 0)

    def _verdict_pct(a: float, b: float) -> str:
        if a == 0 or b == 0:
            return "—"
        d = abs(a - b) / max(abs(a), abs(b)) * 100
        return f"Δ {d:.0f}%"

    return {
        "label": label,
        "scale_bar_found": deep_result.get("scale_bar_found", False),
        "scale_bar_label_ft": deep_result.get("scale_bar_label_ft"),
        "measured_width_ft": deep_result.get("measured_width_ft"),
        "measured_height_ft": deep_result.get("measured_height_ft"),
        "measured_gross_wall_sqft": measured,
        "phase2_gross_wall_sqft": phase2_gross,
        "phase2_net_siding_sqft": phase2_net,
        "text_area_sqft": text_area,
        "confidence": deep_result.get("confidence"),
        "notes": deep_result.get("notes"),
        "delta_vs_phase2": _verdict_pct(measured, phase2_gross or phase2_net),
        "delta_vs_text": _verdict_pct(measured, text_area),
    }
