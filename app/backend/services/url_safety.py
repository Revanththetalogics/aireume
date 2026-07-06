"""
SSRF-protection helpers for validating user-supplied URLs before the server
fetches them (JD scraping, video URL processing, webhooks, etc.).

Blocks:
  - non-http(s) schemes (file://, ftp://, gopher://, etc.)
  - hostnames that resolve to private, loopback, link-local, or reserved ranges
  - cloud metadata endpoints (169.254.169.254 and friends)
"""
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a URL is rejected by SSRF validation."""


_ALLOWED_SCHEMES = {"http", "https"}


def _is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """
    Validate that a URL is an http(s) URL whose host resolves only to public IPs.

    Returns the (stripped) URL on success. Raises UnsafeURLError otherwise.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL is required")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURLError("URL must use http:// or https://")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no host")

    # Reject obvious loopback aliases early
    if host.lower() in {"localhost", "ip6-localhost", "metadata.google.internal"}:
        raise UnsafeURLError("URL host is not allowed")

    # Resolve all A/AAAA records and ensure every one is public
    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise UnsafeURLError("URL host could not be resolved")

    resolved_ips = {info[4][0] for info in addr_infos}
    if not resolved_ips:
        raise UnsafeURLError("URL host could not be resolved")

    for ip_str in resolved_ips:
        if not _is_public_ip(ip_str):
            raise UnsafeURLError("URL host resolves to a private or reserved address")

    return url
