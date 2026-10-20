"""Comprehensive SSRF defense, network guard, and destination validator."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

# Private, link-local, loopback, carrier-grade NAT, and cloud metadata networks
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (AWS, GCP, Azure, Oracle)
    ipaddress.ip_network("0.0.0.0/8"),         # Broadcast / This network
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("::/128"),            # IPv6 Unspecified
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-local
    ipaddress.ip_network("ff00::/8"),          # IPv6 Multicast
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped IPv6
]

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB maximum allowed page payload
MAX_TIMEOUT_SECONDS = 15.0


def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any blocked or private subnet."""
    # Check for IPv4-mapped IPv6
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        ip_obj = ip_obj.ipv4_mapped

    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
        return True

    for blocked_net in BLOCKED_IP_NETWORKS:
        try:
            if ip_obj in blocked_net:
                return True
        except TypeError:
            continue
    return False


def validate_audit_url(url: str) -> tuple[bool, str]:
    """Validate a target URL for public scanning with defense-in-depth SSRF protection.

    Enforces:
    1. Scheme must be HTTP or HTTPS only.
    2. Credentials embedded in URLs (e.g. user:pass@host) are rejected.
    3. Hostname cannot be 'localhost', intranet names, metadata domains, or empty.
    4. DNS resolution verifies all returned IPv4 and IPv6 addresses against blocked ranges.
    5. Rejects any mixed public/private DNS responses.
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

    # Reject embedded userinfo (credentials)
    if parsed.username or parsed.password:
        return False, "Security violation: Embedded user credentials in target URL are prohibited."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a valid host name."

    hostname_lower = hostname.lower()
    blocked_hosts = {
        "localhost", "127.0.0.1", "::1", "0.0.0.0",
        "metadata.google.internal", "instance-data", "metadata"
    }
    if hostname_lower in blocked_hosts or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, "Auditing of localhost, intranet, or cloud metadata hosts is strictly prohibited."

    # DNS Resolution & IP verification against blocked subnets
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return False, f"Unable to resolve host: '{hostname}'. Ensure domain name is correct and accessible."
    except Exception as exc:
        return False, f"DNS resolution failed: {exc}"

    if not addr_info:
        return False, f"No DNS records returned for '{hostname}'."

    # Verify every resolved address
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                return False, f"Blocked destination: '{hostname}' resolves to restricted IP address ({ip_str})."
        except ValueError:
            return False, f"Invalid resolved IP address: '{ip_str}'."

    return True, "URL validated successfully for public auditing."
