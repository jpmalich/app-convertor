"""HTML -> PDF rendering using WeasyPrint.

We reuse the email-safe HTML that the frontend already builds (inline styles,
table layout) — that constraint also produces excellent PDF output.
"""
from io import BytesIO

from weasyprint import HTML


def render_pdf(html: str) -> bytes:
    """Render the given HTML string to PDF bytes."""
    buf = BytesIO()
    HTML(string=html).write_pdf(target=buf)
    return buf.getvalue()


def safe_filename(estimate_number: str | None, customer_name: str | None) -> str:
    """Build a friendly attachment filename, falling back to a generic name."""
    parts = []
    if estimate_number:
        parts.append(str(estimate_number).strip())
    if customer_name:
        # Keep only letters/digits/underscore/dash; collapse spaces
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in customer_name.strip())
        cleaned = "_".join(p for p in cleaned.split("_") if p)
        if cleaned:
            parts.append(cleaned)
    base = "-".join(parts) if parts else "estimate"
    return f"{base}.pdf"
