"""Unit tests for the HOVER window-style guessing heuristic.

HOVER PDF reports give us the rough opening dimensions (W × H) per window
but NEVER tell us if the window is double-hung, slider, casement, or
picture. `_guess_vero_product_type` picks a sensible default from those
two numbers. Contractors override per-opening on the preview modal.

Iter 78y (2026-02-13): Vero collapsed to 3 product types (DH, 2-Lite
Slider, Patio Door). Casement / 3-Lite Slider / Picture were removed —
the heuristic now picks between DH and 2-Lite Slider only.
"""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "vinyl_estimator")

import pytest

from routes.hover import _guess_vero_product_type as g


@pytest.mark.parametrize("w,h,expected", [
    # Small openings (kitchen above-sink, bath transom) → DH (no Casement anymore)
    (24, 36, "Vero Double Hung"),
    (22, 30, "Vero Double Hung"),
    (28, 36, "Vero Double Hung"),
    # Classic DH proportions (taller than wide, < 40")
    (29, 51, "Vero Double Hung"),
    (30, 60, "Vero Double Hung"),
    (24, 47, "Vero Double Hung"),
    (31, 65, "Vero Double Hung"),
    # Tall narrow DH-ish (h > w) — even if w >= 40
    (40, 60, "Vero Double Hung"),
    (49, 62, "Vero Double Hung"),
    # 2-Lite slider: wider than tall, ≥ 40" wide
    (48, 36, "Vero 2-Lite Slider"),
    (40, 30, "Vero 2-Lite Slider"),
    (50, 40, "Vero 2-Lite Slider"),
    # Very wide windows used to route to 3-Lite Slider — now 2-Lite
    (60, 36, "Vero 2-Lite Slider"),
    (72, 48, "Vero 2-Lite Slider"),
    (66, 49, "Vero 2-Lite Slider"),
    # Large square windows used to route to Picture — now DH (height ≥ width)
    (60, 60, "Vero Double Hung"),
    (72, 72, "Vero Double Hung"),
    (50, 50, "Vero Double Hung"),
    # Degenerates
    (0, 0, "Vero Double Hung"),
    (None, 50, "Vero Double Hung"),  # type: ignore
])
def test_guess_vero_product_type(w, h, expected):
    assert g(w, h) == expected


def test_guess_handles_string_input():
    """Defensive — JSON sometimes serialises numbers as strings."""
    assert g("48", "36") == "Vero 2-Lite Slider"
