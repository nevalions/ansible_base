# WireGuard Verification Role

Automated verification playbook for WireGuard VPN network health, connectivity, and configuration.

## Security Features

### Log Sanitization

This role includes custom filter plugins to protect sensitive WireGuard data in logs:
- **Private keys**: Completely redacted
- **Public keys**: Truncated to 20 characters (out of 44)
- **Endpoints/IPs**: Optional anonymization

See [filter_plugins/README.md](filter_plugins/README.md) for detailed usage.

## Usage

### Run full verification
```bash
./ansible_with_agent.sh -i hosts_bay.ini wireguard_verify.yaml --tags verify
```

### Run with verbosity
```bash
./ansible_with_agent.sh -i hosts_bay.ini wireguard_verify.yaml --tags verify -v
```

### Verify specific hosts only
```bash
# Verify only WireGuard servers
./ansible_with_agent.sh -i hosts_bay.ini wireguard_verify.yaml --limit wireguard_servers --tags verify

# Verify only WireGuard clients
./ansible_with_agent.sh -i hosts_bay.ini wireguard_verify.yaml --limit wireguard_clients --tags verify
```

### Run in check mode (no changes)
```bash
./ansible_with_agent.sh -i hosts_bay.ini wireguard_verify.yaml --tags verify --check
```

## Verification Checks

### 1. Interface Verification (`verify_interface.yaml`)
- Checks if WireGuard interface exists (`wg show`)
- Verifies interface link status
- Displays interface IP address
- Verifies WireGuard service is active
- Validates IP is in expected network CIDR

### 2. Keys Verification (`verify_keys.yaml`)
- Verifies server public key matches vault configuration
- Lists configured peers
- Verifies peer public keys are properly configured
- Checks peer handshake status
- Displays peer transfer statistics

### 3. Connectivity Verification (`verify_connectivity.yaml`)
- Pings server's own WireGuard IP
- Pings each peer's VPN IP from server
- Pings server from each client
- Tests bidirectional peer-to-peer connectivity
- Counts failed connectivity tests

### 4. Firewall Verification (`verify_firewall.yaml`)
- Checks UFW firewall status
- Verifies WireGuard port is allowed (servers)
- Checks allowed networks configuration
- Verifies WireGuard interface firewall rules
- Confirms WireGuard service can bind to port

## Variables

All sensitive configuration is loaded from `vault_secrets.yml`:

- `vault_wg_interface` - WireGuard interface name (e.g., wg99)
- `vault_wg_network_cidr` - VPN network CIDR (e.g., 9.11.0.0/24)
- `vault_wg_server_ip` - Server VPN IP address
- `vault_wg_server_port` - WireGuard listen port
- `vault_wg_peers` - List of peer configurations
- `vault_wg_server_public_key` - Server public key
- `vault_wg_peer_public_keys` - Peer public keys
- `vault_wg_allowed_networks` - Allowed firewall networks

## Verification Settings

Configurable in `defaults/main.yaml`:

- `verify_ping_count` - Number of ping packets (default: 3)
- `verify_ping_timeout` - Ping timeout in seconds (default: 2)
- `verify_retry_count` - Number of retries (default: 5)
- `verify_sleep_seconds` - Sleep between retries (default: 5)
- `verify_timeout_seconds` - Operation timeout (default: 30)

## Output

The playbook provides a comprehensive verification report with:

- Interface status (UP/DOWN)
- Server public key (truncated)
- Number of configured peers
- Connectivity status (Functional/Issues detected)
- Firewall status (Configured/Issues detected)

## Requirements

- Ansible 2.16+
- WireGuard installed on target hosts
- UFW firewall (Debian/Ubuntu)
- vault_secrets.yml configured with WireGuard variables
- Inventory groups: `wireguard_servers`, `wireguard_clients`

## Notes

- All commands use `ignore_errors: true` and `changed_when: false`
- Playbook is read-only (no changes made to hosts)
- Uses vault variables for all sensitive data (no hardcoded IPs/ports)
- Follows same pattern as `kuber_verify` role
