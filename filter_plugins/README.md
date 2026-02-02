# Security Filter Plugins

Generic Ansible filter plugins for masking sensitive data in command output and logs.

## Installation

The filters are automatically available when placed in the `filter_plugins/` directory at project root.

**No additional configuration required** - Ansible automatically discovers filters in this directory.

## Quick Start

```yaml
- name: Get system status
  ansible.builtin.command: some_command_with_sensitive_data
  register: status
  no_log: true
  changed_when: false

- name: Display sanitized output
  ansible.builtin.debug:
    msg: "{{ status.stdout | sanitize_security }}"
```

## Available Filters

### Network Masking

#### `sanitize_security`

**Purpose**: Sanitize network data with context-aware masking

**Masks:**
- IP:port combinations: `[internal-ip]:51840` → `***.168.1.100.:***51840`
- IP addresses only: `[internal-ip]` → `***.168.1.100`
- Context-aware ports: `port 8080` → `port ***8080`

**Context-aware port detection:**
Only masks ports near these keywords:
- `port`, `ports`, `listen`, `listening`, `bind`, `binds`, `tcp`, `udp`

**Usage:**
```yaml
- debug:
    msg: "{{ output | sanitize_security }}"

- debug:
    msg: "{{ output | sanitize_security(mask_char='#') }}"
```

**Examples:**
```yaml
Input:  "Server: [internal-ip]:8111, Peer: [internal-ip]:51840, port: 8080"
Output: "Server: ***.1.1.1.:***8111, Peer: ***.168.1.100.:***51840, port: ***8080"

Input:  "binding to 0.0.0.0:443"
Output: "binding to ***.***0.0.0.:***443"

Input:  "listening on port 22"
Output: "listening on port ***22"
```

---

#### `mask_ip`

**Purpose**: Mask the first octet of an IPv4 address

**Usage:**
```yaml
- debug:
    msg: "{{ ip_address | mask_ip }}"
```

**Examples:**
```yaml
Input:  "[internal-ip]"
Output: "***.168.1.100"

Input:  "[internal-ip]"
Output: "***.0.0.5"
```

---

#### `mask_port`

**Purpose**: Mask a port number by adding prefix (keeps all digits)

**Usage:**
```yaml
- debug:
    msg: "{{ port_number | mask_port }}"

- debug:
    msg: "{{ port_number | mask_port(mask_char='#') }}"
```

**Examples:**
```yaml
Input:  "51840"
Output: "***51840"

Input:  "80"
Output: "***80"

Input:  "443"
Output: "***443"
```

---

### Additional Security Filters

#### `mask_email`

**Purpose**: Mask email addresses while preserving domain

**Usage:**
```yaml
- debug:
    msg: "{{ user_email | mask_email }}"
```

**Examples:**
```yaml
Input:  "user@example.com"
Output: "****@example.com"

Input:  "john.doe@company.org"
Output: "*********@company.org"
```

---

#### `mask_url`

**Purpose**: Mask URLs with optional hostname and path masking

**Parameters:**
- `mask_hostname`: Mask the hostname (default: True)
- `mask_path`: Mask the path (default: False)
- `mask_char`: Character to use for masking (default: *)

**Usage:**
```yaml
- debug:
    msg: "{{ url | mask_url }}"

- debug:
    msg: "{{ url | mask_url(mask_path=true) }}"
```

**Examples:**
```yaml
Input:  "https://example.com/path"
Output: "https://*****.com/path"

Input:  "https://example.com/path" (mask_path=true)
Output: "https://*****.com/****"
```

---

#### `mask_mac`

**Purpose**: Mask MAC addresses while preserving format

**Usage:**
```yaml
- debug:
    msg: "{{ mac_address | mask_mac }}"
```

**Examples:**
```yaml
Input:  "00:11:22:33:44:55"
Output: "00:**:**:**:**:55"

Input:  "00-11-22-33-44-55"
Output: "00-**-**-**-**-55"
```

---

### Utility Filters

#### `truncate_string`

**Purpose**: Truncate a string to specified length with optional suffix

**Parameters:**
- `length`: Maximum length (default: 20)
- `suffix`: Suffix to add when truncated (default: "...")

**Usage:**
```yaml
- debug:
    msg: "{{ long_string | truncate_string }}"

- debug:
    msg: "{{ long_string | truncate_string(length=10, suffix=' [more]') }}"
```

**Examples:**
```yaml
Input:  "this is a very long string"
Output: "this is a very lon..."

Input:  "this is a very long string" (length=10)
Output: "this is a [more]"
```

---

#### `redact_pattern`

**Purpose**: Redact text matching a regex pattern

**Parameters:**
- `pattern`: Regex pattern to match
- `replacement`: Replacement string (default: "[REDACTED]")

**Usage:**
```yaml
- debug:
    msg: "{{ output | redact_pattern('API key: \\S+') }}"

- debug:
    msg: "{{ output | redact_pattern('password:\\s*\\S+', '[HIDDEN]') }}"
```

**Examples:**
```yaml
Input:  "API key: abc123def456"
Output: "API key: [REDACTED]"

Input:  "password: secret123"
Output: "password: [HIDDEN]"
```

---

## Best Practices

### 1. Always Use `no_log: true` for Sensitive Commands

```yaml
- name: Get sensitive data
  ansible.builtin.command: sensitive_command
  register: result
  no_log: true  # CRITICAL: Prevents logging of raw output
  changed_when: false

- name: Display sanitized output
  debug:
    msg: "{{ result.stdout | sanitize_security }}"
```

### 2. Choose the Right Filter

| Filter | Use Case | Masking Pattern |
|--------|----------|----------------|
| `sanitize_security` | Network data (IPs, ports) | Context-aware |
| `mask_ip` | IP addresses only | First octet |
| `mask_port` | Port numbers only | Prefix mask |
| `mask_email` | Email addresses | Username only |
| `mask_url` | URLs | Hostname/path optional |
| `mask_mac` | MAC addresses | Middle octets |
| `truncate_string` | Long strings | Length limit |
| `redact_pattern` | Custom patterns | Regex-based |

### 3. Use in Verification Playbooks

```yaml
- name: Verify network connectivity
  block:
    - name: Test connectivity
      ansible.builtin.command: ping -c 3 {{ target_ip }}
      register: ping_result
      no_log: true
      changed_when: false

    - name: Display sanitized result
      debug:
        msg: "{{ ping_result.stdout | sanitize_security }}"
```

### 4. Chain Multiple Filters

```yaml
- name: Sanitize and truncate
  debug:
    msg: "{{ long_sensitive_output | sanitize_security | truncate_string(length=50) }}"
```

---

## Security Considerations

### What Gets Protected

- **IPv4 Addresses**: First octet masked (e.g., `***.168.1.100`)
- **IP:Port Combinations**: First octet + port prefix (e.g., `***.168.1.100.:***51840`)
- **Port Numbers**: Prefix added only near context keywords
- **Email Addresses**: Username masked (e.g., `****@example.com`)
- **URLs**: Hostname optionally masked (e.g., `https://*****.com`)
- **MAC Addresses**: Middle octets masked (e.g., `00:**:**:**:**:55`)

### What Remains Visible

- **Network segments**: Last 3 octets of IPs (e.g., `***.168.1.100`)
- **Port ranges**: All digits (e.g., `***51840`)
- **Service identification**: Context words (port, listen, bind, etc.)
- **Connection status**: All status information
- **Debugging context**: Sufficient for troubleshooting

### Masking Approach

- **Consistent**: Always uses the same masking pattern
- **Non-reversible**: Cannot reconstruct original values
- **Context-aware**: Port detection reduces false positives
- **Flexible**: Configurable mask character

---

## Configuration

### Custom Mask Character

All filters accept `mask_char` parameter:

```yaml
# Use different mask character
- debug:
    msg: "{{ output | sanitize_security(mask_char='#') }}"

- debug:
    msg: "{{ ip | mask_ip(mask_char='X') }}"
```

### Filter Plugin Path

If filters are not automatically discovered, add to `ansible.cfg`:

```ini
[defaults]
filter_plugins = ./filter_plugins
```

---

## Migration from WireGuard Filters

### Old Way (WireGuard-specific)

```yaml
- debug:
    msg: "{{ wg_output | wg_mask_ips(3) }}"
```

### New Way (Generic)

```yaml
- debug:
    msg: "{{ output | sanitize_security }}"
```

### Backward Compatibility

WireGuard-specific filters (`wg_mask_*`) are still available and will be maintained for backward compatibility until at least 2026.

Gradually migrate to generic filters for new playbooks and existing ones during maintenance windows.

---

## Troubleshooting

### Filter Not Found Error

If you get `filter 'sanitize_security' not found`:

1. Ensure `filter_plugins/` directory exists in project root
2. Check file permissions: `chmod 644 filter_plugins/*.py`
3. Verify Ansible can find filters:
   ```bash
   ansible-config dump | grep FILTER_PLUGINS
   ```

### Unexpected Masking Behavior

If masks aren't working as expected:

1. Check your IP format - only IPv4 is supported
2. Verify context keywords for port masking
3. Test with simple examples first
4. Enable debug mode to see filter output

### Performance Considerations

- Filters run on the control node, not target hosts
- Regex patterns are pre-compiled for performance
- Large outputs may take longer to process

---

## Examples

### Complete Verification Task

```yaml
- name: Verify network configuration
  block:
    - name: Get network status
      ansible.builtin.command: ip addr show
      register: network_status
      no_log: true
      changed_when: false

    - name: Display sanitized status
      debug:
        msg: "{{ network_status.stdout | sanitize_security }}"

    - name: Verify specific IP
      ansible.builtin.assert:
        that:
          - network_status.stdout is regex('***\\.' + expected_network)
        success_msg: "Network verified (sanitized)"
        fail_msg: "Network mismatch"
```

### Email Redaction

```yaml
- name: Display user info (sanitized)
  debug:
    msg:
      name: "{{ user.name }}"
      email: "{{ user.email | mask_email }}"
      phone: "{{ user.phone | truncate_string(length=7) }}"
```

### API Key Redaction

```yaml
- name: Display API response
  debug:
    msg: "{{ api_response | redact_pattern('\"api_key\":\\s*\"[^\"]+\"') }}"
```

---

## Contributing

When adding new filters:

1. Follow naming convention: `mask_*` or `sanitize_*`
2. Add comprehensive docstrings
3. Include usage examples in this README
4. Test with valid and invalid inputs
5. Update this README.md

---

## License

Same as the parent project (MIT).

---

## Version History

- **v1.0.0** (2025-02-01): Initial release
  - `sanitize_security` - Network data masking
  - `mask_ip` - IP address masking
  - `mask_port` - Port number masking
  - `mask_email` - Email masking
  - `mask_url` - URL masking
  - `mask_mac` - MAC address masking
  - `truncate_string` - String truncation
  - `redact_pattern` - Pattern-based redaction
