#!/usr/bin/env python3
"""Generic Security Filters for Ansible

Filters to mask sensitive data from command output for use in Ansible playbooks.
Supports IP addresses, ports, and other network data with context-aware masking.
"""

import re


IP_PORT_RE = re.compile(
    r"\b(?P<ip>(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})"
    r"(?::(?P<port>\d{1,5}))?\b"
)

PORT_CTX_RE = re.compile(
    r"\b(?:port|ports|listen(?:ing)?|bind|binds|tcp|udp)\s*(?::)?\s*(?P<port>\d{1,5})\b",
    re.IGNORECASE
)


def mask_ip(ip: str) -> str:
    """
    Mask the first octet of an IPv4 address.

    Example:
        "[internal-ip]" -> "***.168.1.100"
        "[internal-ip]" -> "***.0.0.5"

    Args:
        ip: IPv4 address string

    Returns:
        IP address with first octet masked
    """
    parts = ip.split(".")
    if len(parts) == 4:
        return "***." + ".".join(parts[1:])
    return ip


def mask_port(port: str, mask_char: str = "*") -> str:
    """
    Mask a port number by masking first digit and keeping rest.

    Example:
        "51840" -> "***1840"
        "8111" -> "***111"
        "80" -> "***80"
        "443" -> "***443"

    Args:
        port: Port number as string
        mask_char: Character to use for masking (default: *)

    Returns:
        Port number with first digit masked
    """
    if not port:
        return port

    mask_prefix = mask_char * 3

    if len(port) <= 1:
        return port
    else:
        return mask_prefix + port[1:]


def sanitize_security(text: str, mask_char: str = "*") -> str:
    """
    Sanitize network data with context-aware masking.

    Masks:
    - IP:port combinations (e.g., "[internal-ip]:51840" -> "***.168.1.100.:***51840")
    - IP addresses only (e.g., "[internal-ip]" -> "***.168.1.100")
    - Context-aware ports (e.g., "port 8080" -> "port ***8080")

    Port masking is context-aware and only triggers near keywords:
    - port, ports, listen, listening, bind, binds, tcp, udp

    Example:
        "Server: [internal-ip]:8111, Peer: [internal-ip]:51840, port: 8080"
        -> "Server: ***.1.1.1.:***8111, Peer: ***.168.1.100.:***51840, port: ***8080"

    Args:
        text: Text to sanitize
        mask_char: Character to use for masking (default: *)

    Returns:
        Sanitized text with IPs and ports masked
    """
    if text is None:
        return text

    mask_prefix = mask_char * 3

    def repl_ip_port(m: re.Match) -> str:
        ip = m.group("ip")
        port = m.group("port")
        if port:
            masked_ip = mask_ip(ip) + "."
            masked_port = mask_port(port, mask_char)
            return f"{masked_ip}:{masked_port}"
        return mask_ip(ip)

    out = IP_PORT_RE.sub(repl_ip_port, str(text))

    def repl_port_ctx(m: re.Match) -> str:
        port = m.group("port")
        masked_port = mask_port(port, mask_char)
        return m.group(0).replace(port, masked_port)

    out = PORT_CTX_RE.sub(repl_port_ctx, out)
    return out


def mask_email(text: str, mask_char: str = "*") -> str:
    """
    Mask email addresses while preserving domain.

    Example:
        "user@example.com" -> "****@example.com"
        "john.doe@company.org" -> "*********@company.org"

    Args:
        text: Text containing email addresses
        mask_char: Character to use for masking (default: *)

    Returns:
        Text with email usernames masked
    """
    if not text:
        return text

    email_pattern = r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"

    def mask_email_match(m):
        username = m.group(1)
        domain = m.group(2)
        masked_len = len(username)
        if masked_len > 0:
            return f"{mask_char * masked_len}@{domain}"
        return m.group(0)

    return re.sub(email_pattern, mask_email_match, text)


def mask_url(text: str, mask_hostname: bool = True, mask_path: bool = False, mask_char: str = "*") -> str:
    """
    Mask URLs with optional hostname and path masking.

    Example (mask_hostname=True):
        "https://example.com/path" -> "https://*****.com/path"

    Args:
        text: Text containing URLs
        mask_hostname: Mask the hostname (default: True)
        mask_path: Mask the path (default: False)
        mask_char: Character to use for masking (default: *)

    Returns:
        Text with URLs masked
    """
    if not text:
        return text

    url_pattern = r"(https?://)([^/:]+)(:[0-9]+)?(/[^\\s]*)?"

    def mask_url_match(m):
        protocol = m.group(1)
        hostname = m.group(2)
        port = m.group(3)
        path = m.group(4)

        if mask_hostname:
            hostname_parts = hostname.split('.')
            if len(hostname_parts) > 1:
                masked_hostname = mask_char * len('.'.join(hostname_parts[:-1])) + '.' + hostname_parts[-1]
            else:
                masked_hostname = mask_char * len(hostname)
        else:
            masked_hostname = hostname

        if mask_path and path:
            masked_path = mask_char * len(path)
        else:
            masked_path = path if path else ""

        return f"{protocol}{masked_hostname}{port or ''}{masked_path}"

    return re.sub(url_pattern, mask_url_match, text)


def truncate_string(text: str, length: int = 20, suffix: str = "...") -> str:
    """
    Truncate a string to specified length with optional suffix.

    Example:
        "this is a very long string" -> "this is a very lon..."

    Args:
        text: String to truncate
        length: Maximum length (default: 20)
        suffix: Suffix to add when truncated (default: "...")

    Returns:
        Truncated string
    """
    if not text or len(text) <= length:
        return text

    return text[:length - len(suffix)] + suffix


def redact_pattern(text: str, pattern: str, replacement: str = "[REDACTED]") -> str:
    r"""
    Redact text matching a regex pattern.

    Replaces the ENTIRE pattern match with the replacement string.
    To preserve context (like label text), use capturing groups in your pattern.

    Example (simple replacement):
        "secret value" (pattern=r"\bsecret\b")
        -> "[HIDDEN] value"

    Example (with capturing groups to preserve prefix):
        "API-KEY-abc123def456" (pattern=r"API-KEY-(\S+)")
        -> "API-KEY-[REDACTED]"

    Args:
        text: Text to redact
        pattern: Regex pattern to match
        replacement: Replacement string (default: "[REDACTED]")

    Returns:
        Text with pattern matches redacted
    """
    if not text:
        return text

    return re.sub(pattern, replacement, text)


def mask_mac(text: str, mask_char: str = "*") -> str:
    """
    Mask MAC addresses while preserving format.

    Example:
        "00:11:22:33:44:55" -> "00:**:**:**:**:55"
        "00-11-22-33-44-55" -> "00-**-**-**-**-55"

    Args:
        text: Text containing MAC addresses
        mask_char: Character to use for masking (default: *)

    Returns:
        Text with MAC addresses masked
    """
    if not text:
        return text

    mac_pattern = r"\b([0-9A-Fa-f]{2}[:-]){2}([0-9A-Fa-f]{2}[:-]){3}([0-9A-Fa-f]{2})\b"

    def mask_mac_match(m):
        mac = m.group(0)
        parts = re.split("[:-]", mac)

        if len(parts) != 6:
            return mac

        mask_middle = mask_char * 2
        separator = ":" if ":" in mac else "-"

        return f"{parts[0]}{separator}{mask_middle}{separator}{mask_middle}{separator}{mask_middle}{separator}{mask_middle}{separator}{parts[5]}"

    return re.sub(mac_pattern, mask_mac_match, text)


def truncate_keys_in_string(text: str, key_length: int = 20, suffix: str = "...") -> str:
    """
    Truncate all WireGuard keys (Base64) found in text to specified length.

    Finds Base64-like keys and truncates them to first N characters.

    Example:
        "peer: key1=abc..., peer2=xyz..." -> "peer: key1=abc..., peer2=xyz..."
        (with key_length=5, suffix='...')

    Args:
        text: Text containing keys
        key_length: Maximum length for each key (default: 20)
        suffix: Suffix to add when truncated (default: "...")

    Returns:
        Text with all keys truncated
    """
    if not text:
        return text

    key_pattern = r"([A-Za-z0-9+/]{" + str(key_length) + r"}[A-Za-z0-9+/=]{0,})"
    
    def truncate_key_match(m):
        return m.group(0)[:key_length] + suffix

    return re.sub(key_pattern, truncate_key_match, str(text))


class FilterModule:
    """Ansible filter plugin for security sanitization."""

    def filters(self):
        """Return all filter functions for Ansible."""
        return {
            # Network masking filters
            "sanitize_security": sanitize_security,
            "mask_ip": mask_ip,
            "mask_port": mask_port,

            # Additional security filters
            "mask_email": mask_email,
            "mask_url": mask_url,
            "mask_mac": mask_mac,

            # Utility filters
            "truncate_string": truncate_string,
            "truncate_keys_in_string": truncate_keys_in_string,
            "redact_pattern": redact_pattern,
        }
