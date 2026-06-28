"""HTML -> PDF rendering using WeasyPrint.

We reuse the email-safe HTML that the frontend already builds (inline styles,
table layout) — that constraint also produces excellent PDF output.

SEC-002 — Iter 78z+++: WeasyPrint ships with a default URL fetcher that
happily follows `file://` URLs and any HTTP(S) target the server can
reach. Quote HTML is contractor-supplied; a malicious value could
embed `<img src="file:///etc/passwd">` or cloud-metadata IPs and
exfiltrate the result via the rendered PDF. We override the fetcher
to refuse anything that's not HTTPS to a public IP.
"""
import ipaddress
import socket
from io import BytesIO
from urllib.parse import urlparse

from weasyprint import HTML, default_url_fetcher


def _is_public_ip(host: str) -> bool:
    """True only when the host resolves to a public, routable IP. Blocks
    loopback, link-local, private nets, multicast, cloud metadata."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except (ValueError, IndexError):
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
        # AWS/GCP/Azure metadata service
        if str(ip) in {"169.254.169.254", "fd00:ec2::254"}:
            return False
    return True


def _safe_url_fetcher(url: str, *args, **kwargs):
    """Custom WeasyPrint fetcher. Allowlists data: and https:// to
    public-IP hosts only. Refuses file://, http:// (downgrade-attack
    surface), and any host that resolves to a private/link-local/
    metadata address.
    """
    if url.startswith("data:"):
        return default_url_fetcher(url, *args, **kwargs)
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Refusing to fetch non-https URL: {parsed.scheme}://...")
    host = parsed.hostname or ""
    if not host or not _is_public_ip(host):
        raise ValueError(f"Refusing to fetch private/local host: {host}")
    return default_url_fetcher(url, *args, **kwargs)


def render_pdf(html: str) -> bytes:
    """Render the given HTML string to PDF bytes."""
    buf = BytesIO()
    HTML(string=html, url_fetcher=_safe_url_fetcher).write_pdf(target=buf)
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
