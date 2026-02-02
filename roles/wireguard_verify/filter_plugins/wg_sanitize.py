#!/usr/bin/env python3
"""WireGuard Output Sanitization Filters

Filters to mask sensitive data from WireGuard command output for use in Ansible playbooks.
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'filter_plugins'))
from security_filters import sanitize_security, mask_ip, mask_port


def wg_sanitize(text):
    """
    Sanitize WireGuard interface status output by:
    - Completely redacting private keys
    - Truncating public keys to first 20 characters
    - Masking IPs and ports with specific pattern:
      - IP:port: First octet masked, port prefixed with *** (using . separator)
      - Port only: Prefixed with ***
      - IP only: First octet masked
    - Preserving other information

    Example:
        Input: "peer: key1, endpoint: [internal-ip]:51840, peer1: [internal-ip]:8080"
        Output: "peer: key1, endpoint: ***.168.1.100.:***51840, peer1: ***.0.0.5.:***8080"

    Args:
        text: Raw WireGuard output string

    Returns:
        Sanitized output string
    """
    if not text:
        return text

    result = text

    result = re.sub(r'private key: [^\n]+', 'private key: [REDACTED]', result)

    result = re.sub(
        r'public key: ([A-Za-z0-9+/]{20})[A-Za-z0-9+/=]{24}',
        r'public key: \1...[TRUNCATED]',
        result
    )

    result = re.sub(
        r'peer: ([A-Za-z0-9+/]{20})[A-Za-z0-9+/=]{24}',
        r'peer: \1...[TRUNCATED]',
        result
    )

    result = sanitize_security(result)

    return result


def wg_partial_mask(text):
    """
    Partially mask sensitive data while preserving useful information for debugging.
    """
    result = wg_sanitize(text)
    return result


def wg_truncate_key(text):
    """
    Truncate WireGuard public/private keys to 20 characters.
    """
    if not text:
        return text

    result = re.sub(
        r'([A-Za-z0-9+/]{20})[A-Za-z0-9+/=]{24}',
        r'\1...[TRUNCATED]',
        text
    )

    return result


def wg_mask_ips(text, keep_octets=3):
    """
    Partially mask IPv4 addresses.

    Note: This filter now delegates to the generic sanitize_security filter.
    The keep_octets parameter is maintained for backward compatibility but
    is not used (always masks first octet).

    Args:
        text: String containing IP addresses
        keep_octets: Number of octets to keep (default: 3, not used)

    Returns:
        Text with IP addresses partially masked

    Example:
        Input: "[internal-ip]:51840"
        Output: "***.168.1.100.:***51840"
    """
    if not text:
        return text

    return sanitize_security(text)


def wg_mask_ports(text, keep_digits=3):
    """
    Partially mask port numbers.

    Note: This filter now delegates to the generic sanitize_security filter.
    The keep_digits parameter is maintained for backward compatibility but
    is not used (always prefixes all port digits with ***).

    Args:
        text: String containing port numbers
        keep_digits: Number of digits to keep (default: 3, not used)

    Returns:
        Text with port numbers partially masked

    Example:
        Input: "port 51840"
        Output: "port ***51840"
    """
    if not text:
        return text

    return sanitize_security(text)


def wg_mask_interfaces(text):
    """
    Partially mask interface names.

    Args:
        text: String containing interface names

    Returns:
        Text with interface numbers masked
    """
    if not text:
        return text

    result = re.sub(
        r'(wg|utun|tun)(\d+)',
        r'\1**',
        text
    )

    return result


def wg_redact_private_keys(text):
    """
    Remove all private keys from WireGuard output.
    """
    if not text:
        return text

    return re.sub(r'private key: [^\n]+', 'private key: [REDACTED]', text)


def wg_anonymize(text):
    """
    Completely anonymize WireGuard output.
    """
    if not text:
        return text

    result = re.sub(r'private key: [^\n]+', 'private key: [REDACTED]', text)

    result = re.sub(r'public key: [^\n]+', 'public key: [REDACTED]', result)

    result = re.sub(r'peer: [^\n]+', 'peer: [REDACTED]', result)

    result = re.sub(
        r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}):([^:]+)(?=\s|$)',
        '[IP]:[PORT]',
        result
    )

    result = re.sub(r'allowed ips: [^\n]+', 'allowed ips: [CIDR]', result)

    return result


def wg_extract_public_keys(text):
    """
    Extract only public keys (truncated to 20 chars) from WireGuard output.

    Useful for verifying keys without exposing other configuration details.
    """
    if not text:
        return []

    peer_keys = re.findall(r'peer: ([A-Za-z0-9+/]{20})[A-Za-z0-9+/=]{24}', text)

    interface_key = re.findall(r'public key: ([A-Za-z0-9+/]{20})[A-Za-z0-9+/=]{24}', text)

    all_keys = peer_keys + interface_key

    return [f"{key[:20]}..." for key in all_keys]


class FilterModule:
    """Ansible filter plugin for WireGuard output sanitization."""

    def filters(self):
        """Return all filter functions for Ansible."""
        return {
            'wg_sanitize': wg_sanitize,
            'wg_partial_mask': wg_partial_mask,
            'wg_truncate_key': wg_truncate_key,
            'wg_redact_private_keys': wg_redact_private_keys,
            'wg_anonymize': wg_anonymize,

            # Granular filters
            'wg_mask_ips': wg_mask_ips,
            'wg_mask_ports': wg_mask_ports,
            'wg_mask_interfaces': wg_mask_interfaces,

            # Utility filters
            'wg_extract_public_keys': wg_extract_public_keys,
        }
