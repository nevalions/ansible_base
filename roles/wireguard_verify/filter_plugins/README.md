# WireGuard Sanitization Filters

Custom Ansible filter plugins to protect sensitive WireGuard data in logs.

## Installation

The filters are automatically available when using the `wireguard_verify` role:
- Location: `roles/wireguard_verify/filter_plugins/wg_sanitize.py`
- No additional configuration required

## Available Filters

### `wg_sanitize`

**Purpose:** Sanitize full WireGuard `wg show` output by:
- Completely redacting private keys
- Truncating public keys to first 20 characters
- Partially masking IPv4 addresses (first 3 octets)
- Partially masking ports (first 3 digits)
- Partially masking interface names
- **Masks only first and last IPs/ports per line** (middle ones visible)
- Preserving connectivity status and transfer statistics

**Usage:**
```yaml
- name: Display WireGuard interface status
  ansible.builtin.command: wg show {{ vault_wg_interface }}
  register: wg_interface_status
  no_log: true
  changed_when: false
  ignore_errors: true

- name: Display sanitized output
  ansible.builtin.debug:
    msg: "{{ wg_interface_status.stdout | wg_sanitize }}"
```

**Example Output:**
```yaml
Input:
  private key: 4G39cPf90ljxuGW0Uqt1gb79p1gh/trPhxYUUiWxkXo=
  public key: kdaFtITs4I+HlCUCFxH9IzciOgVRTxGqo/74dQxk7hw=
  listening port: 51840
  peer: vuxT/gHyTD7tlHNPxY1NppEOChqi0GRSS4AI55yub3s=

Output:
  private key: [REDACTED]
  public key: kdaFtITs4I+HlCUCFxH...[TRUNCATED]
  listening port: 518***
  peer: vuxT/gHyTD7tlHNPx...[TRUNCATED]
  endpoint: 192.168.1.***:518***
```

---

### `wg_partial_mask`

**Purpose:** Partially mask sensitive network data while preserving useful information for debugging.

This function provides middle-ground security:
- Shows first parts of IPs for network identification
- Shows first digits of ports for service identification
- Shows interface prefix but masks numbers
- Truncates keys as in `wg_sanitize`
- **Masks only first and last IPs/ports per line** (middle ones visible)

Use this when you need to debug connectivity issues without full exposure.

**Usage:**
```yaml
- name: Display with partial masking
  ansible.builtin.debug:
    msg: "{{ wg_output | wg_partial_mask }}"
```

**Example Output:**
```yaml
Input:
  endpoint: [internal-ip]:51840, peer: [internal-ip]:8080, server: [internal-ip]:51842
  peer: kdaFtITs4I+HlCUCFxH9IzciOgVRTxGqo/74dQxk7hw=

Output:
  endpoint: 192.168.1.***:518***, peer: [internal-ip]:80**, server: 192.168.1.***:518***
  peer: kdaFtITs4I+HlCUCFxH...[TRUNCATED]
```

---

### `wg_mask_ips`

**Purpose:** Partially mask IPv4 addresses while keeping specified number of octets.

**Parameters:**
- `keep_octets`: Number of octets to keep (default: 3)
  - 3: `192.168.1.***` (recommended)
  - 2: `192.168.***.***`
  - 1: `192.***.***.***`
- `first_last_only`: Only mask first and last IPs per line (default: True)
  - `True`: Mask first and last, keep middle visible (recommended)
  - `False`: Mask all IPs

**Usage:**
```yaml
- name: Mask IPs with 3 octets visible
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_ips(3) }}"

- name: Mask IPs with 2 octets visible
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_ips(2) }}"

- name: Mask ALL IPs (not first/last only)
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_ips(3, false) }}"
```

**Example Output:**
```yaml
Input:  "Server: [internal-ip]:51840, Peer: [internal-ip]:8080, Server: [internal-ip]:51842"
Output (keep_octets=3, first_last_only=True): "Server: 192.168.1.***:51840, Peer: [internal-ip]:8080, Server: 192.168.1.***:51842"
Output (keep_octets=2, first_last_only=True): "Server: 192.168.***.***:51840, Peer: [internal-ip]:8080, Server: 192.168.***.***:51842"
Output (keep_octets=3, first_last_only=False): "Server: 192.168.1.***:51840, Peer: 10.0.0.***:8080, Server: 192.168.1.***:51842"
```

---

### `wg_mask_ports`

**Purpose:** Partially mask port numbers while keeping specified number of digits.

**Parameters:**
- `keep_digits`: Number of digits to keep (default: 3)
  - 3: `518***` (recommended)
  - 2: `51****`
  - 1: `5*****`
- `first_last_only`: Only mask first and last ports per line (default: True)
  - `True`: Mask first and last, keep middle visible (recommended)
  - `False`: Mask all ports

**Usage:**
```yaml
- name: Mask ports with 3 digits visible
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_ports(3) }}"

- name: Mask ALL ports (not first/last only)
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_ports(3, false) }}"
```

**Example Output:**
```yaml
Input:  "endpoint: [internal-ip]:51840, :8080, :51841"
Output (keep_digits=3, first_last_only=True): "endpoint: [internal-ip]:518***, :8080, :518***"
Output (keep_digits=2, first_last_only=True): "endpoint: [internal-ip]:51****, :8080, :51****"
Output (keep_digits=3, first_last_only=False): "endpoint: [internal-ip]:518***, :8080, :518***"
```

---

### `wg_mask_interfaces`

**Purpose:** Partially mask network interface names while preserving type.

Masks numeric suffix of interface names while keeping the prefix.

**Usage:**
```yaml
- name: Mask interface names
  ansible.builtin.debug:
    msg: "{{ config_text | wg_mask_interfaces }}"
```

**Example Output:**
```yaml
Input:  "interface: wg99"
Output: "interface: wg**"

Input:  "interface: utun0"
Output: "interface: utun**"

Input:  "interface: tun10"
Output: "interface: tun**"
```

---

### `wg_truncate_key`

**Purpose:** Truncate WireGuard public/private keys to prevent full key exposure while preserving identification.

**Usage:**
```yaml
- name: Display peer keys
  ansible.builtin.debug:
    msg: "{{ wg_keys_output | wg_truncate_key }}"
```

**Example Output:**
```yaml
Input:  "kdaFtITs4I+HlCUCFxH9IzciOgVRTxGqo/74dQxk7hw="
Output: "kdaFtITs4I+HlCUCFxH...[TRUNCATED]"
```

---

### `wg_redact_private_keys`

**Purpose:** Remove all private keys while leaving all other data intact.

**Usage:**
```yaml
- name: Display config without private keys
  ansible.builtin.debug:
    msg: "{{ wg_config | wg_redact_private_keys }}"
```

**Example Output:**
```yaml
Input:  "private key: 4G39cPf90ljxuGW0Uqt1gb79p1gh/trPhxYUUiWxkXo=\npublic key: kdaFt..."
Output: "private key: [REDACTED]\npublic key: kdaFt..."
```

---

### `wg_anonymize`

**Purpose:** Completely anonymize WireGuard output by removing ALL sensitive information:
- All keys (private and public)
- IP addresses and endpoints
- Allowed IPs

**Usage:**
```yaml
- name: Display fully anonymized output
  ansible.builtin.debug:
    msg: "{{ wg_output | wg_anonymize }}"
```

**Example Output:**
```yaml
Input:
  endpoint: [internal-ip]:[vpn-port]
  allowed ips: [vpn-network-cidr]

Output:
  endpoint: [IP]:[PORT]
  allowed ips: [CIDR]
```

---

### `wg_extract_public_keys`

**Purpose:** Extract only public keys for debugging/troubleshooting (each truncated to 20 chars).

**Usage:**
```yaml
- name: Extract and display peer keys
  ansible.builtin.debug:
    msg: "Peer keys: {{ wg_output | wg_extract_public_keys }}"
```

**Example Output:**
```yaml
Input:  "peer: kdaFtITs4I+HlCUCFxH9IzciOgVRTxGqo/74dQxk7hw=\npeer: vuxT/..."
Output: ["kdaFtITs4I+HlCUCFxH...", "vuxT/gHyTD7tlHNPx..."]
```

---

## Best Practices

### 1. Always Use `no_log: true` for Sensitive Commands

When running `wg show` or reading WireGuard config files, always use `no_log: true`:

```yaml
- name: Get WireGuard status
  ansible.builtin.command: wg show {{ vault_wg_interface }}
  register: wg_status
  changed_when: false
  no_log: true  # CRITICAL: Prevents logging of raw output
  ignore_errors: true

- name: Display sanitized status
  ansible.builtin.debug:
    msg: "{{ wg_status.stdout | wg_sanitize }}"
```

### 2. Choose the Right Filter

| Filter | Use Case | Security Level | IP Mask | Port Mask | First/Last Only |
|--------|----------|----------------|-----------|-----------|-----------------|
| `wg_sanitize` | Displaying `wg show` output | High | Partial | Partial | Yes |
| `wg_partial_mask` | Debugging with context | High | Partial | Partial | Yes |
| `wg_mask_ips` | Granular IP control | Custom | Custom | None | Optional |
| `wg_mask_ports` | Granular port control | Custom | None | Custom | Optional |
| `wg_mask_interfaces` | Granular interface control | Custom | None | None | None |
| `wg_truncate_key` | Peer key lists | Medium | None | None | None |
| `wg_redact_private_keys` | Config files without private keys | High | None | None | None |
| `wg_anonymize` | Public logs/monitoring | Maximum | Full | Full | None |
| `wg_extract_public_keys` | Debugging key issues | Low | None | None | None |

### 3. Use in Verification Playbooks

```yaml
# Interface verification
- name: Check WireGuard interface
  command: wg show {{ vault_wg_interface }}
  register: wg_interface
  no_log: true
  changed_when: false

- name: Display interface status (sanitized)
  debug:
    msg: "{{ wg_interface.stdout | wg_sanitize }}"

# Key verification
- name: Display peer keys (truncated)
  debug:
    msg: "Peer {{ item.name }}: {{ item.public_key | wg_truncate_key }}"
  loop: "{{ peers }}"

# Connectivity testing
- name: Show transfer stats
  debug:
    msg: "{{ wg_transfer.stdout | wg_truncate_key }}"
```

### 4. Reuse in Other Playbooks

The filters are available to any playbook that includes the `wireguard_verify` role or places the filter in a global location:

```yaml
---
- name: Custom WireGuard Management
  hosts: wireguard_servers
  vars_files:
    - vault_secrets.yml
  roles:
    - wireguard_verify  # Makes filters available

  tasks:
    - name: Display keys safely
      debug:
        msg: "{{ wg_output | wg_sanitize }}"
```

---

## Reusing Filters in Other Roles

To use these filters in other roles:

### Option 1: Import the Role

```yaml
roles:
  - wireguard_verify  # Makes filters available
  - your_other_role
```

### Option 2: Copy to Global Location

```bash
# Copy to project-level filter_plugins directory
mkdir -p filter_plugins
cp roles/wireguard_verify/filter_plugins/wg_sanitize.py filter_plugins/
```

Then the filters are available globally without importing the role.

---

## Security Considerations

### What Gets Protected

- **Private Keys:** Always completely redacted
- **Public Keys:** Truncated to 20 characters (out of 44)
- **IPv4 Addresses:** Partially masked
  - First and last IPs per line masked (default behavior)
  - Middle IPs visible for debugging context
  - Can be configured to mask all IPs
- **Port Numbers:** Partially masked
  - First and last ports per line masked (default behavior)
  - Middle ports visible for debugging context
  - Can be configured to mask all ports
- **Interface Names:** Prefix visible, numbers masked
- **Endpoints/IPs:** Fully protected in `wg_anonymize` mode
- **Configuration:** Sanitized while maintaining readability

### What Remains Visible (in `wg_sanitize` / `wg_partial_mask` mode)

- **Network segments:** First 3 octets of IPs (e.g., 192.168.1.*)
- **Middle IPs:** Fully visible when there are multiple IPs in a line (e.g., [internal-ip])
- **Port ranges:** First 3 digits (e.g., 518**)
- **Middle ports:** Fully visible when there are multiple ports in a line
- **Interface types:** Prefix (e.g., wg**)
- **Connection status:** All status information
- **Handshake timestamps:** All timestamps
- **Transfer statistics:** All statistics (without keys)
- **Allowed IP ranges:** CIDR notation (e.g., 9.11.0.***/24)

### First/Last Masking Behavior

The default behavior of `wg_sanitize`, `wg_partial_mask`, `wg_mask_ips` (with `first_last_only=True`), and `wg_mask_ports` (with `first_last_only=True`) is:

- **Single occurrence:** Mask it
- **Multiple occurrences:** Mask first and last, keep middle visible

**Example:**
```
Input:  "Server: [internal-ip]:51840, Peer: [internal-ip]:8080, Server: [internal-ip]:51842"
Output: "Server: 192.168.1.***:518***, Peer: [internal-ip]:80**, Server: 192.168.1.***:518***"
```

This provides debugging context while protecting sensitive endpoints.

### Truncated Keys Are Still Unique

The 20-character prefix of WireGuard Base64 keys provides sufficient entropy for:
- Identifying which key is being referenced
- Debugging key mismatches
- Verification that keys haven't changed

But prevents:
- Reconstructing the full key
- Using truncated keys for authentication
- Full exposure in logs

---

## Troubleshooting

### Filter Not Found Error

If you get `filter 'wg_sanitize' not found`:

1. Ensure you've imported the `wireguard_verify` role:
   ```yaml
   roles:
     - wireguard_verify
   ```

2. Or copy the filter to a global `filter_plugins/` directory.

3. Check file permissions: `chmod 644 filter_plugins/wg_sanitize.py`

### Python Path Issues

If filters don't load, check Ansible can find Python filters:

```bash
ansible-config dump | grep FILTER_PLUGINS
```

Expected output should include your filter paths.

---

## Examples

### Complete Verification Task

```yaml
- name: Verify WireGuard configuration
  block:
    - name: Get WireGuard status
      ansible.builtin.command: wg show {{ vault_wg_interface }}
      register: wg_status
      no_log: true
      changed_when: false
      ignore_errors: true

    - name: Display sanitized status
      ansible.builtin.debug:
        msg: "{{ wg_status.stdout | wg_sanitize }}"

    - name: Verify server key
      ansible.builtin.assert:
        that:
          - wg_status.stdout | regex_search('public key: ' + vault_wg_server_public_key[:20])
        success_msg: "Server public key verified (truncated)"
        fail_msg: "Server public key mismatch"
```

### Peer Key Comparison

```yaml
- name: Display peer key mapping
  ansible.builtin.debug:
    msg:
      - "Peer: {{ item.name }}"
      - "Expected: {{ vault_wg_peer_public_keys[item.name] | wg_truncate_key }}"
      - "Running: {{ item.public_key | wg_truncate_key }}"
  loop: "{{ vault_wg_peers }}"
```

---

## Contributing

When adding new filters:

1. Follow the naming convention: `wg_*`
2. Add comprehensive docstrings
3. Include usage examples
4. Test with both valid and invalid inputs
5. Update this README.md

---

## License

Same as the wireguard_verify role (MIT).
