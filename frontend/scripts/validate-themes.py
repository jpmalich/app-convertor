#!/usr/bin/env python3
"""WCAG gate for the theme system (docs/specs/theme-picker.md §7).

Parses the :root and [data-theme=…] token blocks in src/index.css, resolves
each theme against the :root defaults, and checks every contrast gate.
Exit 1 if any theme fails — run before shipping a new or edited theme.
"""
import pathlib
import re
import sys

CSS = pathlib.Path(__file__).resolve().parent.parent / "src" / "index.css"

GATES = [
    # (foreground token, background token, minimum ratio, label)
    ("--ink", "--surface", 4.5, "body text on surface"),
    ("--ink", "--surface-muted", 4.5, "body text on muted surface"),
    ("--ink-2", "--surface", 4.5, "secondary text on surface"),
    ("--muted", "--surface", 4.5, "muted text on surface"),
    ("--brand-text", "--surface", 4.5, "brand as text on surface"),
    ("--on-brand", "--brand", 4.5, "CTA label on brand"),
    ("--on-brand", "--brand-hover", 4.5, "CTA label on brand hover"),
    ("--focus", "--surface", 3.0, "focus indicator on surface"),
    ("--border-strong", "--surface", 3.0, "strong border on surface"),
    ("--bar-ink", "--bar-bg", 4.5, "bar text on bar"),
    ("--bar-muted", "--bar-bg", 4.5, "bar muted text on bar"),
    ("--danger-text", "--surface", 4.5, "danger text on surface"),
    ("--warning-text", "--surface", 4.5, "warning text on surface"),
    ("--hint-ink", "--hint-bg", 4.5, "hint text on hint row"),
    ("--hint-ink-2", "--hint-bg-2", 4.5, "hint badge text"),
]


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def parse_blocks(css: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    for m in re.finditer(r'(:root|\[data-theme="([\w-]+)"\])\s*\{([^}]*)\}', css):
        name = m.group(2) or "orange (default)"
        tokens = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})", m.group(3)))
        if tokens:
            blocks.setdefault(name, {}).update(tokens)
    return blocks


def main() -> None:
    blocks = parse_blocks(CSS.read_text())
    base = blocks.pop("orange (default)")
    failures = 0
    for theme in ["orange (default)", *blocks.keys()]:
        tokens = {**base, **blocks.get(theme, {})}
        print(f"\n== {theme}")
        for fg, bg, minimum, label in GATES:
            if fg not in tokens or bg not in tokens:
                print(f"  SKIP  {label} (token missing)")
                continue
            r = ratio(tokens[fg], tokens[bg])
            ok = r >= minimum
            failures += 0 if ok else 1
            print(f"  {r:5.2f}:1 (need {minimum})  {'PASS' if ok else 'FAIL'}  {label}")
    if failures:
        print(f"\n{failures} gate(s) FAILED")
        sys.exit(1)
    print("\nAll themes pass every gate.")


if __name__ == "__main__":
    main()
