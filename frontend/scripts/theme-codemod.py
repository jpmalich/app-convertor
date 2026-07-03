#!/usr/bin/env python3
"""One-shot codemod: migrate hardcoded Tailwind hex classes to semantic
CSS-variable tokens (docs/specs/theme-picker.md Phase 1).

Only rewrites bracketed utility classes (text-[#…], bg-[#…], …) and the
plain `bg-white` class — inline styles and JS color strings (canvas/SVG
drawing colors) are untouched by design.

Customer-facing document surfaces are excluded: they keep the neutral
document style regardless of the contractor's UI theme.
"""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"

EXCLUDE = {
    "lib/emailQuote.js",      # homeowner email HTML
    "lib/materialList.js",    # printable material list
    "lib/printTakeoff.js",    # printable takeoff
    "pages/AcceptPage.jsx",   # public homeowner accept page
    "components/QuoteModal.jsx",  # quote document preview
}

# Ordered: context-sensitive rules first, then generic.
RULES = [
    # --- on-brand labels: black text paired with an orange bg on the same line
    ("ONBRAND-op", None, None),   # handled specially below
    # --- focus indicators before generic brand
    (r"focus:border-\[#F97316\]", "focus:border-[var(--focus)]", None),
    (r"focus:ring-\[#F97316\]", "focus:ring-[var(--focus)]", None),
    (r"outline-\[#F97316\]", "outline-[var(--focus)]", None),
    # --- brand family
    (r"bg-\[#F97316\]", "bg-[var(--brand)]", None),
    (r"text-\[#F97316\]", "text-[var(--brand)]", None),
    (r"border-\[#F97316\]", "border-[var(--brand)]", None),
    (r"accent-\[#F97316\]", "accent-[var(--brand)]", None),
    (r"decoration-\[#F97316\]", "decoration-[var(--brand)]", None),
    (r"ring-\[#F97316\]", "ring-[var(--brand)]", None),
    (r"bg-\[#EA580C\]", "bg-[var(--brand-hover)]", None),
    (r"text-\[#EA580C\]", "text-[var(--brand-hover)]", None),
    (r"border-\[#EA580C\]", "border-[var(--brand-hover)]", None),
    (r"bg-\[#C2410C\]", "bg-[var(--brand-hover)]", None),
    (r"text-\[#C2410C\]", "text-[var(--brand-text)]", None),
    (r"border-\[#C2410C\]", "border-[var(--brand-text)]", None),
    # --- ink family (after on-brand pass)
    (r"bg-\[#09090B\]", "bg-[var(--bar-bg)]", None),
    (r"text-\[#09090B\]", "text-[var(--ink)]", None),
    (r"border-\[#09090B\]", "border-[var(--border-strong)]", None),
    (r"text-\[#52525B\]", "text-[var(--ink-2)]", None),
    (r"border-\[#52525B\]", "border-[var(--ink-2)]", None),
    (r"bg-\[#52525B\]", "bg-[var(--ink-2)]", None),
    (r"text-\[#71717A\]", "text-[var(--muted)]", None),
    (r"border-\[#71717A\]", "border-[var(--muted)]", None),
    (r"bg-\[#71717A\]", "bg-[var(--muted)]", None),
    # #A1A1AA text sits on fixed dark chrome (post contrast-sweep invariant)
    (r"text-\[#A1A1AA\]", "text-[var(--bar-muted)]", None),
    (r"border-\[#A1A1AA\]", "border-[var(--muted)]", None),
    (r"bg-\[#A1A1AA\]", "bg-[var(--muted)]", None),
    # --- surfaces & lines
    (r"(?<![\w/-])bg-white(?![\w/-])", "bg-[var(--surface)]", None),
    (r"hover:bg-white(?![\w/-])", "hover:bg-[var(--surface)]", None),
    (r"bg-\[#FFFFFF\]", "bg-[var(--surface)]", None),
    (r"bg-\[#F4F4F5\]", "bg-[var(--bg-app)]", None),
    (r"bg-\[#FAFAFA\]", "bg-[var(--surface-muted)]", None),
    (r"bg-\[#E4E4E7\]", "bg-[var(--table-header)]", None),
    (r"border-\[#E4E4E7\]", "border-[var(--border)]", None),
    (r"text-\[#E4E4E7\]", "text-[var(--border)]", None),
    (r"divide-\[#E4E4E7\]", "divide-[var(--border)]", None),
    # --- AI accent
    (r"text-\[#7C3AED\]", "text-[var(--ai)]", None),
    (r"border-\[#7C3AED\]", "border-[var(--ai)]", None),
    (r"bg-\[#7C3AED\]", "bg-[var(--ai)]", None),
    (r"ring-\[#7C3AED\]", "ring-[var(--ai)]", None),
    (r"bg-\[#F5F3FF\]", "bg-[var(--ai-soft)]", None),
    (r"bg-\[#EDE9FE\]", "bg-[var(--ai-soft)]", None),
    # --- status
    (r"text-\[#DC2626\]", "text-[var(--danger-text)]", None),
    (r"text-\[#EF4444\]", "text-[var(--danger)]", None),
    (r"border-\[#EF4444\]", "border-[var(--danger)]", None),
    (r"bg-\[#EF4444\]", "bg-[var(--danger)]", None),
    (r"bg-\[#FEF2F2\]", "bg-[var(--danger-soft)]", None),
    (r"text-\[#16A34A\]", "text-[var(--success)]", None),
    (r"border-\[#16A34A\]", "border-[var(--success)]", None),
    (r"bg-\[#16A34A\]", "bg-[var(--success)]", None),
    (r"text-\[#059669\]", "text-[var(--profit)]", None),
    (r"text-\[#10B981\]", "text-[var(--success)]", None),
    (r"text-\[#92400E\]", "text-[var(--warning-text)]", None),
    (r"text-\[#B45309\]", "text-[var(--warning-text)]", None),
    # --- lightbulb hint rows
    (r"(?<![\w/-])bg-yellow-50(?![\w/-])", "bg-[var(--hint-bg)]", None),
    (r"(?<![\w/-])bg-yellow-100(?![\w/-])", "bg-[var(--hint-bg-2)]", None),
    (r"border-yellow-400", "border-[var(--hint-line)]", None),
    (r"text-yellow-700", "text-[var(--hint-ink)]", None),
    (r"text-yellow-900", "text-[var(--hint-ink-2)]", None),
]

ONBRAND_LINE = re.compile(r"bg-\[#F97316\]")


def migrate(text: str) -> tuple[str, int]:
    count = 0
    lines = text.split("\n")
    # Pass 1: on-brand labels — black text on the same line as an orange bg.
    for i, line in enumerate(lines):
        if ONBRAND_LINE.search(line):
            new = line.replace("text-[#09090B]/80", "text-[var(--on-brand)] opacity-80")
            new = new.replace("text-[#09090B]", "text-[var(--on-brand)]")
            if new != line:
                count += 1
                lines[i] = new
    text = "\n".join(lines)
    # Pass 2: ordered generic rules.
    for pattern, repl, _ in RULES:
        if repl is None:
            continue
        text, n = re.subn(pattern, repl, text)
        count += n
    return text, count


def main() -> None:
    total = 0
    touched = 0
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in (".jsx", ".js") or "components/ui/" in str(path):
            continue
        rel = str(path.relative_to(SRC))
        if rel in EXCLUDE:
            continue
        text = path.read_text()
        new, n = migrate(text)
        if n:
            path.write_text(new)
            touched += 1
            total += n
            print(f"{n:4d}  {rel}")
    print(f"\n{total} replacements across {touched} files")


if __name__ == "__main__":
    main()
