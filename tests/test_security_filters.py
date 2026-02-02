#!/usr/bin/env python3
"""Unit tests for generic security filters."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'filter_plugins'))

from security_filters import (
    sanitize_security,
    mask_ip,
    mask_port,
    mask_email,
    mask_url,
    mask_mac,
    truncate_string,
    truncate_keys_in_string,
    redact_pattern,
)


def test_mask_ip():
    """Test IP address masking."""
    tests = [
        ("[internal-ip]", "***.168.1.100"),
        ("[internal-ip]", "***.0.0.5"),
        ("[internal-ip]", "***.16.0.1"),
        ("255.255.255.255", "***.255.255.255"),
        ("0.0.0.0", "***.0.0.0"),
        ("invalid", "invalid"),  # Invalid IP, should remain unchanged
        ("", ""),  # Empty string
    ]

    passed = 0
    failed = 0

    for input_ip, expected in tests:
        result = mask_ip(input_ip)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: mask_ip('{input_ip}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nmask_ip: {passed} passed, {failed} failed")
    return failed == 0


def test_mask_port():
    """Test port number masking."""
    tests = [
        ("51840", "***1840"),   # Mask first digit, keep rest
        ("8111", "***111"),     # Mask first digit, keep rest
        ("80", "***0"),          # Mask first digit, keep rest
        ("443", "***43"),        # Mask first digit, keep rest
        ("22", "***2"),
        ("1", "1"),             # Single digit, no mask needed
        ("", ""),  # Empty string
    ]

    passed = 0
    failed = 0

    for input_port, expected in tests:
        result = mask_port(input_port)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: mask_port('{input_port}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nmask_port: {passed} passed, {failed} failed")
    return failed == 0


def test_sanitize_security():
    """Test comprehensive security sanitization."""
    tests = [
        # IP:port combinations
        ("[internal-ip]:51840", "***.168.1.100.:***1840"),
        ("[internal-ip]:8111", "***.1.1.1.:***111"),
        ("0.0.0.0:443", "***.0.0.0.:***43"),

        # IP only
        ("[internal-ip]", "***.168.1.100"),
        ("[internal-ip]", "***.0.0.5"),

        # Context-aware ports
        ("listening on port 8111", "listening on port ***111"),
        ("bind 0.0.0.0:51840", "bind ***.0.0.0.:***1840"),
        ("port 443", "port ***43"),
        ("port 51840", "port ***1840"),

        # Multiple IPs and ports
        (
            "Server: [internal-ip]:8111, Peer: [internal-ip]:51840, Port: 8080",
            "Server: ***.1.1.1.:***111, Peer: ***.168.1.100.:***1840, Port: ***080"
        ),

        # URL schemes
        ("tcp://[internal-ip]:80", "tcp://***.168.1.100.:***0"),

        # Invalid IPs (should not match)
        ("invalid IP 300.400.500.600:99999", "invalid IP 300.400.500.600:99999"),

        # Edge cases
        ("", ""),  # Empty string
        (None, None),  # None value
    ]

    passed = 0
    failed = 0

    for input_text, expected in tests:
        result = sanitize_security(input_text)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: sanitize_security('{input_text}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nsanitize_security: {passed} passed, {failed} failed")
    return failed == 0


def test_mask_email():
    """Test email address masking."""
    tests = [
        ("user@example.com", "****@example.com"),
        ("john.doe@company.org", "********@company.org"),  # 8 chars in username (john.doe)
        ("a@b.c", "a@b.c"),  # Invalid email (TLD too short), not matched
        ("", ""),  # Empty string
        ("no email here", "no email here"),  # No email to mask
    ]

    passed = 0
    failed = 0

    for input_email, expected in tests:
        result = mask_email(input_email)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: mask_email('{input_email}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nmask_email: {passed} passed, {failed} failed")
    return failed == 0


def test_mask_url():
    """Test URL masking."""
    tests = [
        ("https://example.com/path", "https://*******.com/path"),  # 'example' = 7 chars
        ("http://test.com", "http://****.com"),  # 'test' = 4 chars
        ("https://example.com/path/to/resource", "https://*******.com/path/to/resource"),
        ("", ""),  # Empty string
        ("no url here", "no url here"),  # No URL to mask
    ]

    passed = 0
    failed = 0

    for input_url, expected in tests:
        result = mask_url(input_url)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: mask_url('{input_url}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nmask_url: {passed} passed, {failed} failed")
    return failed == 0


def test_mask_mac():
    """Test MAC address masking."""
    tests = [
        ("00:11:22:33:44:55", "00:**:**:**:**:55"),
        ("00-11-22-33-44-55", "00-**-**-**-**-55"),
        ("AA:BB:CC:DD:EE:FF", "AA:**:**:**:**:FF"),
        ("", ""),  # Empty string
        ("not a mac", "not a mac"),  # Not a MAC address
    ]

    passed = 0
    failed = 0

    for input_mac, expected in tests:
        result = mask_mac(input_mac)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: mask_mac('{input_mac}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nmask_mac: {passed} passed, {failed} failed")
    return failed == 0


def test_truncate_string():
    """Test string truncation."""
    tests = [
        ("this is a very long string", "this is a very lo..."),  # Default (20 chars with suffix)
        ("short", "short"),  # Shorter than limit
        ("", ""),  # Empty string
        ("123456789012345678901", "12345678901234567..."),  # Exactly at limit (20 chars with suffix)
    ]

    passed = 0
    failed = 0

    for input_text, expected in tests:
        result = truncate_string(input_text)

        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: truncate_string('{input_text}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\ntruncate_string: {passed} passed, {failed} failed")
    return failed == 0


def test_redact_pattern():
    """Test pattern-based redaction.

    Note: redact_pattern replaces ENTIRE match with replacement string.
    To preserve context (like label text), use capturing groups in your pattern.
    """
    tests = [
        # Simple word replacement
        ("secret value", r"\bsecret\b", "[HIDDEN]", "[HIDDEN] value"),
        # Replace entire pattern match
        ("token: xyz789", r"token:\s*\S+", "***", "***"),
        # Replace pattern with prefix
        ("API-KEY-abc123def456", r"API-KEY-\S+", "[REDACTED]", "[REDACTED]"),
        # Empty string
        ("", r".*", "[REDACTED]", ""),
    ]

    passed = 0
    failed = 0

    for input_text, pattern, replacement, expected in tests:
        result = redact_pattern(input_text, pattern, replacement)

        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: redact_pattern('{input_text}', '{pattern}', '{replacement}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\nredact_pattern: {passed} passed, {failed} failed")
    return failed == 0


def test_truncate_keys_in_string():
    """Test key truncation in strings."""
    tests = [
        ("peer: abcdefghijklmnopqrstuvwxyz1234567890=", "peer: abcdefghijklmnopqrst..."),
        ("peer1: XYZABCDEF1234567890ABCDEFGHIJK=", "peer1: XYZABCDEF1234567890A..."),
        ("key1=abc..., key2=xyz...", "key1=abc..., key2=xyz..."),  # Already short
        ("", ""),  # Empty string
        ("no keys here", "no keys here"),  # No keys to truncate
    ]

    passed = 0
    failed = 0

    for input_text, expected in tests:
        result = truncate_keys_in_string(input_text)

        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: truncate_keys_in_string('{input_text}')")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")

    print(f"\ntruncate_keys_in_string: {passed} passed, {failed} failed")
    return failed == 0


def run_all_tests():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Generic Security Filters Unit Tests")
    print("=" * 70)
    print()

    results = {
        "mask_ip": test_mask_ip(),
        "mask_port": test_mask_port(),
        "sanitize_security": test_sanitize_security(),
        "mask_email": test_mask_email(),
        "mask_url": test_mask_url(),
        "mask_mac": test_mask_mac(),
        "truncate_string": test_truncate_string(),
        "truncate_keys_in_string": test_truncate_keys_in_string(),
        "redact_pattern": test_redact_pattern(),
    }

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    total_passed = sum(1 for v in results.values() if v)
    total_failed = sum(1 for v in results.values() if not v)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Total: {total_passed} passed, {total_failed} failed")

    if total_failed == 0:
        print()
        print("All tests passed! ✓")
        return 0
    else:
        print()
        print(f"{total_failed} test(s) failed! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
