"""Supplier-admin preview tool for the LP SmartSide AI formula module.

Lets Howard (or whoever holds the `SUPPLIER_ADMIN_TOKEN`) preview how
LP quantities will shift between the legacy `sqft × 0.11` math and
the PDF-accurate per-profile formulas BEFORE flipping the
`LP_AI_FORMULAS_V1` env flag in production.

Endpoint
--------
POST /api/admin/lp-formula-preview
    Header: `X-Admin-Token`
    Body:   {
        "measurements": { ... HOVER-style measurements ... },
        # OR
        "preset":       "campbell" | "shake_heavy" | "bb_heavy" | "lap_only"
    }
    Returns:
    {
        "preset_used": "campbell"|null,
        "measurements": { ... echo back the input ... },
        "diff": [
            {"section":"...", "name":"...", "unit":"PCS",
             "legacy_qty": 110, "pdf_qty": 120,
             "delta_qty": 10, "delta_pct": 9.1},
            ...
        ],
        "summary": {"lines_total":N, "lines_changed":M}
    }

This endpoint runs `_build_lines` twice inside the same request — once
with the flag forced OFF, once forced ON — using
`lp_formulas.override_flag()` so we don't mutate the env. The diff is
LP-tab-only because that's the only tab the new formulas touch.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from deps import check_admin_token
import lp_smartside_formulas as lp_formulas
from routes.hover import _build_lines

router = APIRouter()


# Howard's hand-built sample measurement payloads. Each one targets a
# specific LP scenario so the admin preview surface useful comparison
# data without needing a real HOVER file at hand.
PRESETS: dict[str, dict] = {
    # Mid-size 2-story Campbell-style house. Lap body + shake gable
    # + B&B porch. Numbers are roughly Howard's Campbell takeoff
    # (LETRICK-class job).
    "campbell": {
        "_label": "Campbell-style: 2400 sqft body lap + 400 sqft shake gable + 200 sqft B&B porch",
        "siding_with_openings_sqft": 3000,
        "siding_sqft": 3000,
        "window_count": 14,
        "entry_door_count": 1,
        "patio_door_count": 1,
        "garage_door_count": 1,
        "outside_corner_lf": 80,
        "inside_corner_lf": 24,
        "starter_lf": 180,
        "eaves_lf": 200,
        "rakes_lf": 100,
        "_per_profile_sqft": {"lap": 2400, "shake": 400, "board_batten": 200},
    },
    "shake_heavy": {
        "_label": "Shake-heavy: 1800 sqft shake + 600 sqft lap accent",
        "siding_with_openings_sqft": 2400,
        "siding_sqft": 2400,
        "window_count": 8,
        "entry_door_count": 1,
        "outside_corner_lf": 60,
        "starter_lf": 120,
        "eaves_lf": 140,
        "rakes_lf": 80,
        "_per_profile_sqft": {"shake": 1800, "lap": 600},
    },
    "bb_heavy": {
        "_label": "Board & Batten heavy: 2000 sqft B&B + 400 sqft lap base",
        "siding_with_openings_sqft": 2400,
        "siding_sqft": 2400,
        "window_count": 10,
        "entry_door_count": 1,
        "garage_door_count": 1,
        "outside_corner_lf": 70,
        "starter_lf": 140,
        "eaves_lf": 160,
        "rakes_lf": 90,
        "_per_profile_sqft": {"board_batten": 2000, "lap": 400},
    },
    "lap_only": {
        "_label": "Lap-only single profile: 2200 sqft 8\" Lap (no breakdown)",
        "siding_with_openings_sqft": 2200,
        "siding_sqft": 2200,
        "window_count": 12,
        "entry_door_count": 1,
        "outside_corner_lf": 64,
        "starter_lf": 130,
        "eaves_lf": 150,
        "rakes_lf": 80,
        # No `_per_profile_sqft` — single-profile path uses the default
        # siding row, not _profile_siding_lines.
    },
}


class PreviewIn(BaseModel):
    measurements: Optional[dict] = None
    preset: Optional[str] = None


def _lp_diff(
    legacy_lines: list[dict],
    pdf_lines: list[dict],
) -> tuple[list[dict], dict]:
    """Build the diff array. Lines keyed by (section, name) — that's
    enough since each (section, name) is unique per tab."""
    def _index(lines):
        out = {}
        for ln in lines:
            if ln.get("tab") != "lp_smart":
                continue
            out[(ln["section"], ln["name"])] = ln
        return out

    legacy_idx = _index(legacy_lines)
    pdf_idx = _index(pdf_lines)
    keys = sorted(set(legacy_idx) | set(pdf_idx))

    diff: list[dict] = []
    changed = 0
    for k in keys:
        lo = legacy_idx.get(k)
        new = pdf_idx.get(k)
        legacy_qty = float(lo["qty"]) if lo else 0.0
        pdf_qty = float(new["qty"]) if new else 0.0
        delta = pdf_qty - legacy_qty
        pct = (delta / legacy_qty * 100.0) if legacy_qty > 0 else (100.0 if pdf_qty > 0 else 0.0)
        if abs(delta) > 0.0001:
            changed += 1
        diff.append({
            "section": k[0],
            "name": k[1],
            "unit": (new or lo or {}).get("unit", ""),
            "legacy_qty": round(legacy_qty, 2),
            "pdf_qty": round(pdf_qty, 2),
            "delta_qty": round(delta, 2),
            "delta_pct": round(pct, 1),
            "legacy_note": (lo or {}).get("note", ""),
            "pdf_note": (new or {}).get("note", ""),
        })

    summary = {"lines_total": len(diff), "lines_changed": changed}
    return diff, summary


@router.post("/admin/lp-formula-preview")
async def lp_formula_preview(payload: PreviewIn, request: Request):
    """Return the LP-line side-by-side diff between legacy and PDF
    formulas for the supplied measurement payload (or a named preset).
    """
    check_admin_token(request)

    measurements: Optional[dict] = payload.measurements
    preset_name: Optional[str] = None
    if not measurements and payload.preset:
        preset_name = payload.preset
        preset = PRESETS.get(preset_name)
        if not preset:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown preset '{preset_name}'. Valid: {sorted(PRESETS)}",
            )
        measurements = {k: v for k, v in preset.items() if k != "_label"}

    if not measurements:
        raise HTTPException(
            status_code=400,
            detail="Provide either `measurements` (HOVER-style dict) or `preset`.",
        )

    with lp_formulas.override_flag(False):
        legacy_lines = _build_lines(dict(measurements))
    with lp_formulas.override_flag(True):
        pdf_lines = _build_lines(dict(measurements))

    diff, summary = _lp_diff(legacy_lines, pdf_lines)

    return {
        "preset_used": preset_name,
        "preset_label": (PRESETS.get(preset_name, {}) or {}).get("_label") if preset_name else None,
        "measurements": measurements,
        "diff": diff,
        "summary": summary,
        "flag_currently_enabled": (
            # Show the live env value so the admin knows the production state
            (__import__("os").environ.get("LP_AI_FORMULAS_V1", "").strip().lower()
             in {"1", "true", "yes", "on"})
        ),
    }


@router.get("/admin/lp-formula-preview/presets")
async def lp_formula_presets(request: Request):
    """Lightweight catalog of presets for the admin UI dropdown."""
    check_admin_token(request)
    return {
        "presets": [
            {"key": k, "label": v.get("_label", k)}
            for k, v in PRESETS.items()
        ]
    }
