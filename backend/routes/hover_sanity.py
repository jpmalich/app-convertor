"""HOVER reasonableness checks — Iter 78o (Phase 1 of 3 of the AI verification stack).

Pure deterministic rules that run on the text-extracted measurements right
after Claude returns them. Each rule that triggers produces a warning the
frontend renders in the preview modal so the contractor sees discrepancies
BEFORE they apply the takeoff.

No LLM calls, no PDF parsing — just math + construction-physics constants.

Phase 2 (per-elevation vision pass) + Phase 3 (scale-bar Deep Verify) will
add additional warning sources but reuse the same `Warning` shape returned
from this module so the frontend banner stays unified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


# Construction-physics constants — tuned to typical residential homes in
# Howard's Pittsburgh / Cleveland markets. Slight regional variance exists
# but these envelopes are conservative enough not to false-flag normal
# variation while still catching genuine HOVER mis-reads.
TYPICAL_WINDOW_PERIM_LF = 14.0     # 3'0" × 4'0" replacement window
TYPICAL_ENTRY_DOOR_PERIM_LF = 19.0  # 3'0" × 6'8"
TYPICAL_PATIO_DOOR_PERIM_LF = 22.0  # 6'0" × 6'8" (panels share jamb)
TYPICAL_GARAGE_DOOR_PERIM_LF = 32.0  # 9'0" × 7'0"


@dataclass
class Warning:
    """One sanity-check finding. `level` drives the banner color; `code` is
    a stable id for filtering/dedup; `detail` carries optional structured
    data (rendered as a small mono-num row under the message)."""
    code: str
    level: str  # "warn" | "info"
    message: str
    detail: Optional[str] = None


def _pct_delta(a: float, b: float) -> float:
    """Symmetric % difference between two non-zero values. 0 when both 0."""
    if a == 0 and b == 0:
        return 0.0
    if a == 0 or b == 0:
        return 100.0
    return abs(a - b) / max(abs(a), abs(b)) * 100.0


def run_checks(m: dict) -> list[dict]:
    """Run every rule and return the list of warnings (as plain dicts so
    Pydantic round-trips cleanly). Empty list = report looks consistent."""
    findings: list[Warning] = []
    if not isinstance(m, dict):
        return []

    eaves = float(m.get("eaves_lf") or 0)
    rakes = float(m.get("rakes_lf") or 0)
    siding = float(m.get("siding_sqft") or 0)
    soffit = float(m.get("soffit_sqft") or 0)
    overhang_in = float(m.get("overhang_in") or 12.0)
    overhang_ft = overhang_in / 12.0
    win_count = int(m.get("window_count") or 0)
    door_count = int(m.get("door_count") or 0)
    entry_n = int(m.get("entry_door_count") or 0)
    patio_n = int(m.get("patio_door_count") or 0)
    garage_n = int(m.get("garage_door_count") or 0)
    opening_perim = float(m.get("opening_perimeter_lf") or 0)
    out_corner_n = int(m.get("outside_corner_count") or 0)
    in_corner_n = int(m.get("inside_corner_count") or 0)

    # ────── Rule 1: Soffit area should equal eaves × overhang (±15%) ──────
    # Most reliable cross-check in a HOVER report — the soffit is just the
    # underside of the eave so the area is geometrically determined.
    if eaves > 0 and soffit > 0 and overhang_ft > 0:
        expected_soffit = eaves * overhang_ft
        delta = _pct_delta(expected_soffit, soffit)
        if delta > 15:
            findings.append(Warning(
                code="soffit_area_mismatch",
                level="warn",
                message=(
                    f"Soffit area looks {'high' if soffit > expected_soffit else 'low'} "
                    f"vs eaves × overhang"
                ),
                detail=(
                    f"Reported {soffit:.0f} ft² · Expected ≈ {expected_soffit:.0f} ft² "
                    f"({eaves:.0f} LF eaves × {overhang_ft:.2f} ft overhang) · "
                    f"Δ = {delta:.0f}%"
                ),
            ))

    # ────── Rule 2: Rakes-to-eaves ratio sanity envelope (0.5–1.4) ──────
    # Rectangular gable-roof homes land near 1.0; complex hip/dormer roofs
    # can push higher. Outside this envelope usually means HOVER mis-labeled
    # a roof edge or dropped one entirely.
    if eaves > 0 and rakes > 0:
        ratio = rakes / eaves
        if ratio < 0.5 or ratio > 1.4:
            findings.append(Warning(
                code="rake_eave_ratio",
                level="warn",
                message=(
                    f"Rakes-to-eaves ratio {ratio:.2f}× is outside the typical 0.5–1.4× range"
                ),
                detail=(
                    f"Rakes {rakes:.0f} LF · Eaves {eaves:.0f} LF · "
                    f"a {'low' if ratio < 0.5 else 'high'} ratio often means HOVER "
                    f"missed a {'rake' if ratio < 0.5 else 'eave'} run"
                ),
            ))

    # ────── Rule 3: Opening perimeter consistency vs counts ──────
    # If HOVER reported a lumped opening perimeter, it should be within
    # ±25% of the count-based estimate using typical sizes. Wide envelope
    # because window sizes legitimately vary 6'–20' perimeter.
    if opening_perim > 0 and (win_count + entry_n + patio_n + garage_n) > 0:
        est = (
            win_count * TYPICAL_WINDOW_PERIM_LF
            + entry_n * TYPICAL_ENTRY_DOOR_PERIM_LF
            + patio_n * TYPICAL_PATIO_DOOR_PERIM_LF
            + garage_n * TYPICAL_GARAGE_DOOR_PERIM_LF
        )
        delta = _pct_delta(est, opening_perim)
        if delta > 30:
            findings.append(Warning(
                code="opening_perim_mismatch",
                level="warn",
                message=(
                    f"Opening perimeter ({opening_perim:.0f} LF) doesn't match the opening count"
                ),
                detail=(
                    f"Estimated ≈ {est:.0f} LF from "
                    f"{win_count} win × 14 + {entry_n} entry × 19 + "
                    f"{patio_n} patio × 22 + {garage_n} garage × 32 · "
                    f"Δ = {delta:.0f}%"
                ),
            ))

    # ────── Rule 4: door_count schema integrity ──────
    sum_doors = entry_n + patio_n + garage_n
    if door_count > 0 and sum_doors > 0 and door_count != sum_doors:
        findings.append(Warning(
            code="door_count_mismatch",
            level="warn",
            message=(
                f"Total door_count ({door_count}) doesn't equal "
                f"entry + patio + garage ({sum_doors})"
            ),
            detail=(
                f"Entry {entry_n} + Patio {patio_n} + Garage {garage_n} = {sum_doors} "
                f"vs reported door_count {door_count}"
            ),
        ))

    # ────── Rule 5: Corner count plausibility ──────
    # Outside corners scale with footprint complexity. Rectangle = 4
    # corners; L-shape = 6; U-shape = 8. > 12 on a residence is suspicious.
    if out_corner_n > 12:
        findings.append(Warning(
            code="too_many_outside_corners",
            level="warn",
            message=f"Outside corner count ({out_corner_n}) is unusually high",
            detail=(
                "Most homes land at 4 (rectangle), 6 (L), or 8 (U). "
                "Values > 12 often mean HOVER counted bay-window returns "
                "or chimney chases as corners — review before quoting."
            ),
        ))

    # ────── Rule 6: Inside corners > outside corners ──────
    # Geometrically every inside corner shares an outside corner pair on
    # the opposite wall, so inside should always be ≤ outside on a single-
    # story residence. (Multi-story with cantilevered second floors can
    # violate this — info-level, not warn.)
    if in_corner_n > out_corner_n and out_corner_n > 0:
        findings.append(Warning(
            code="inside_gt_outside_corners",
            level="info",
            message=(
                f"Inside corners ({in_corner_n}) exceed outside corners "
                f"({out_corner_n}) — possible on cantilevered or recessed entries, "
                "but unusual otherwise."
            ),
        ))

    # ────── Rule 7: Siding sqft sanity vs footprint estimate ──────
    # Crude lower bound: siding ≥ 0.5 × eaves × wall_height (assume 9 ft).
    # Catches catastrophic mis-reads where Claude grabbed soffit instead of
    # siding, etc.
    if siding > 0 and eaves > 0:
        min_siding_estimate = eaves * 9 * 0.5  # half-perimeter × 9 ft
        if siding < min_siding_estimate:
            findings.append(Warning(
                code="siding_low_vs_footprint",
                level="warn",
                message=(
                    f"Siding area ({siding:.0f} ft²) looks low for {eaves:.0f} LF of eaves"
                ),
                detail=(
                    f"Lower-bound estimate ≈ {min_siding_estimate:.0f} ft² "
                    f"(½ × {eaves:.0f} LF × 9 ft wall). "
                    "If correct, the home has a very short or partial siding footprint."
                ),
            ))

    return [asdict(w) for w in findings]
