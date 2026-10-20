"""URL validation and SSRF protection security utilities for public auditing."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Private, link-local, loopback, and special use IP networks to block
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-local
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped IPv6
]

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB maximum allowed page payload
MAX_TIMEOUT_SECONDS = 15.0


def validate_audit_url(url: str) -> tuple[bool, str]:
    """Validate a target URL for public scanning.

    Enforces:
    1. Scheme must be HTTP or HTTPS.
    2. Hostname cannot be 'localhost', intranet names, or empty.
    3. Target IP resolution must not resolve to any loopback, private, link-local,
       or cloud metadata IP addresses (SSRF protection).
    """
    if not url or not isinstance(url, str):
        return False, "Target URL cannot be empty."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL format: {exc}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Blocked protocol: '{parsed.scheme}'. Only 'http' and 'https' are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a valid host name."

    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
        return False, "Auditing of localhost and internal hosts is blocked for security."

    # DNS Resolution & IP verification against blocked subnets
    try:
        # Resolve all IPv4 and IPv6 addresses for the host
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return False, f"Unable to resolve host: '{hostname}'. Ensure domain name is correct and accessible."
    except Exception as exc:
        return False, f"DNS resolution failed: {exc}"

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip_obj in blocked_net:
                    return False, f"Blocked destination: '{hostname}' resolves to restricted IP range ({ip_str})."
        except ValueError:
            return False, f"Invalid resolved IP address: '{ip_str}'."

    return True, "URL validated successfully for public auditing."
