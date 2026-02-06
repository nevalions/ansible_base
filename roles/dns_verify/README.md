# DNS Verification Role

Verify DNS infrastructure health including servers, clients, WireGuard connectivity, and DNS resolution.

## Requirements

- Debian/Ubuntu system
- Ansible 2.16+
- `become: true` privileges
- WireGuard VPN configured and running
- DNS servers deployed and operational

## What This Role Does

### DNS Server Verification (`verify_servers.yaml`)

Checks on hosts in `dns_servers` group:

1. **unbound service status** - Verifies Unbound DNS server is running
2. **Port 53 listening** - Checks if Unbound is listening on UDP/TCP port 53
3. **Configuration validity** - Validates `/etc/unbound/unbound.conf` with `unbound-checkconf`
4. **Local DNS resolution** - Tests DNS resolution to localhost

**Failure behavior:** 
- CRITICAL issues (service not running, port not accessible) trigger immediate failure when `verify_fail_immediately: true`

### WireGuard Verification (`verify_wireguard.yaml`)

Checks on hosts in `wireguard_cluster`:

1. **Interface existence** - Verifies WireGuard interface exists
2. **Interface status** - Checks if WireGuard interface is UP
3. **VPN IP assignment** - Retrieves VPN IP address from peer configuration
4. **DNS server pings** - From clients to primary/secondary DNS servers via VPN

**Failure behavior:**
- WireGuard interface DOWN or missing triggers immediate failure
- Ping failures counted as critical issues

### DNS Client Verification (`verify_clients.yaml`)

Checks on hosts in `dns_clients` group:

1. **systemd-resolved status** - Verifies systemd-resolved is disabled (warning if running)
2. **resolv.conf existence** - Checks if `/etc/resolv.conf` exists (critical)
3. **Ansible management** - Verifies `/etc/resolv.conf` is Ansible-managed (warning if not)
4. **DNS servers configured** - Validates correct DNS servers in `/etc/resolv.conf` (warning if incorrect)

**Failure behavior:**
- Missing `/etc/resolv.conf` triggers immediate failure
- All other issues are warnings

### DNS Resolution Tests (`verify_dns_resolution.yaml`)

Tests from DNS clients:

**Internal DNS (cluster.local):**
- Resolve `[dns-server-1].[search-domain]` → VPN IP
- Resolve `[dns-server-2].[search-domain]` → VPN IP
- Resolve `[client-hostname-1].[search-domain]` → VPN IP
- Resolve `[client-hostname-2].[search-domain]` → VPN IP

**External DNS:**
- Resolve `google.com` via primary DNS server
- Resolve `google.com` via secondary DNS server
- Resolve `example.com` via primary DNS server
- Resolve `example.com` via secondary DNS server

**Failure behavior:**
- Internal DNS resolution failures trigger immediate failure
- External DNS resolution failures trigger immediate failure
- Warnings for secondary DNS server issues

### Verification Report (`generate_report.yaml`)

Generates comprehensive health report:

**Per-Host Summary:**
- Hostname (masked IPs)
- Host type (Server/Client)
- WireGuard status (UP/DOWN)
- VPN IP address
- Test results (total, passed, failed, warnings)
- Health status (HEALTHY/DEGRADED/CRITICAL)

**Overall Cluster Summary:**
- Total hosts checked
- WireGuard cluster status
- DNS servers health
- DNS clients connection status
- DNS resolution status

## Role Variables

### Required Vault Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `vault_dns_server_primary` | Primary DNS server VPN IP | `[primary-dns-server-vpn-ip]` |
| `vault_dns_server_secondary` | Secondary DNS server VPN IP | `[secondary-dns-server-vpn-ip]` |
| `vault_wg_interface` | WireGuard interface name | `wg99` |
| `vault_wg_peers` | WireGuard peers configuration | See vault example |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `verify_ping_count` | Number of ping packets | `3` |
| `verify_ping_timeout` | Ping timeout in seconds | `2` |
| `verify_dns_timeout` | DNS query timeout in seconds | `5` |
| `verify_dns_retry` | DNS query retry attempts | `2` |
| `verify_internal_test_records` | Internal DNS test targets (defaults from `vault_dns_records`/`vault_dns_zone`) | See defaults |
| `verify_external_test_hosts` | External DNS test targets | See defaults |
| `verify_fail_immediately` | Fail on critical errors | `true` |

## Dependencies

- `vault_secrets.yml` with DNS and WireGuard configuration
- WireGuard VPN operational
- DNS servers deployed and running

## Usage

### Using the provided playbook:

```bash
# Verify DNS infrastructure (check mode)
ansible-playbook -i hosts_bay.ini dns_verify.yaml --check

# Verify DNS infrastructure (run actual tests)
ansible-playbook -i hosts_bay.ini dns_verify.yaml

# Verify specific hosts
ansible-playbook -i hosts_bay.ini dns_verify.yaml --limit wireguard_clients

# Verify only DNS servers
ansible-playbook -i hosts_bay.ini dns_verify.yaml --limit dns_servers
```

### Using the role directly:

```yaml
---
- name: Verify DNS infrastructure
  hosts: wireguard_cluster
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    verify_fail_immediately: true
    verify_ping_count: 5

  roles:
    - dns_verify
```

## Exit Codes

- **0**: All critical checks passed, cluster is HEALTHY or DEGRADED
- **1**: Critical failures detected when `verify_fail_immediately: true`

## Health Status Definitions

- **HEALTHY**: All critical checks passed, no warnings
- **DEGRADED**: All critical checks passed, but warnings detected
- **CRITICAL**: One or more critical checks failed

## Troubleshooting

### DNS server checks fail:

1. Verify Unbound service is running:
   ```bash
   systemctl status unbound
   ```

2. Check port 53 listening:
   ```bash
   ss -ulnp | grep ":53"
   ```

3. Validate configuration:
   ```bash
   unbound-checkconf /etc/unbound/unbound.conf
   ```

### WireGuard checks fail:

1. Verify WireGuard interface exists:
   ```bash
   ip link show wg99
   ```

2. Check WireGuard status:
   ```bash
   wg show wg99
   ```

3. Verify VPN connectivity:
    ```bash
    ping [primary-dns-server-vpn-ip]  # Primary DNS server
    ```

### DNS resolution checks fail:

1. Test DNS resolution manually:
    ```bash
    nslookup [dns-record].[search-domain] [primary-dns-server-vpn-ip]
    nslookup google.com [primary-dns-server-vpn-ip]
    ```

2. Check DNS server logs:
   ```bash
   journalctl -u unbound -n 50
   ```

3. Verify firewall allows DNS queries:
   ```bash
   ufw status | grep 53
   ```

## Security Considerations

- All IP addresses and ports in output are masked using `sanitize_security` filter
- DNS queries use `nslookup` (non-privileged)
- No secrets are logged or displayed
- Requires `become: true` for service checks

## Example Output

```
=== DNS Infrastructure Verification Report ===
=========================================
Run Date: 2026-02-02 11:54:01
Total Hosts Checked: 4
Overall Status: ✅ HEALTHY
=========================================

=== Overall Cluster Health ===
WireGuard Cluster: UP
DNS Servers: All healthy
DNS Clients: All connected
DNS Resolution: Working
========================================
```

## License

MIT
