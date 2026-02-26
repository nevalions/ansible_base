# DNS Client Role

Configure DNS client settings on Debian/Ubuntu systems by managing `/etc/resolv.conf`.

## Requirements

- Debian/Ubuntu system
- Ansible 2.16+
- `become: true` privileges

## Role Variables

### Required Vault Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `vault_dns_server_primary` | Primary DNS server IP | `[primary-dns-server-ip]` |
| `vault_dns_server_secondary` | Secondary DNS server IP | `[secondary-dns-server-ip]` |
| `vault_dns_zone` | DNS search domain | `[search-domain]` |

### Optional Vault Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_dns_client_options` | List of resolv.conf options | `["timeout:2", "attempts:3", "rotate"]` |

### Kubernetes / dnsmasq (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_dns_client_node_local_enabled` | Enable node-local `dnsmasq` on Kubernetes nodes | Auto-enabled for k8s inventory groups |
| `vault_dns_client_filter_aaaa` | Drop AAAA answers — eliminates AAAA-first timeouts when node has no IPv6 egress | `false` (set `true` for WG-client nodes) |
| `vault_dns_client_primary_only_domains` | Domains routed exclusively to the primary upstream (secondary is rate-limited for these) | `pkg.dev`, `googleusercontent.com`, `amazonaws.com`, `registry.k8s.io` |
| `vault_dns_client_ci_domains` | CI/CD and container registry domains routed across **all** upstreams with round-robin failover — never pinned to a single upstream | `githubusercontent.com`, `github.com`, `ghcr.io`, `docker.io`, etc. |

## Dependencies

None

## Example Playbook

### Install DNS Client Configuration

```yaml
---
- name: Configure DNS on WireGuard clients
  hosts: wireguard_clients
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    dns_operation: "install"

  roles:
    - dns_client
```

### Remove DNS Client Configuration

```yaml
---
- name: Restore default DNS configuration
  hosts: wireguard_clients
  become: true
  vars:
    dns_operation: "remove"

  roles:
    - dns_client
```

## Usage

### Using the provided playbook:

```bash
# Install on all dns_clients
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns

# VAS workers only (targeted re-apply without touching bay-* nodes)
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags vas_dns

# Install on specific hosts
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --limit wireguard_clients

# Remove DNS client configuration (restore systemd-resolved)
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml -e dns_operation=remove --tags dns
```

### Using the role directly:

```bash
ansible-playbook your_playbook.yaml
```

## What This Role Does

### On Install:

1. Stops and disables `systemd-resolved` (Debian/Ubuntu only)
2. Removes systemd-resolved stub `/etc/resolv.conf`
3. Backs up original `/etc/resolv.conf` to `/etc/resolv.conf.original`
4. Optionally configures node-local `dnsmasq` to forward DNS and filter AAAA responses (Kubernetes-friendly)
   - Creates systemd override to ensure dnsmasq starts after WireGuard interface
   - Uses `bind-dynamic` mode to tolerate interfaces appearing after service start
   - Automatically restarts dnsmasq after WireGuard configuration changes (when listen IP becomes available)
5. Deploys a new `/etc/resolv.conf` with your custom DNS settings
6. Tests DNS resolution to verify connectivity
7. Asserts that DNS is working correctly

### On Remove:

1. Restores the original `/etc/resolv.conf` from backup (if it exists)
2. Removes the Ansible-managed `/etc/resolv.conf` if no backup exists
3. Re-enables and starts `systemd-resolved`
4. Cleans up backup files

## Inventory Setup

No special inventory groups are required. You can target any hosts:

```ini
# In hosts_bay.ini
[dns_clients:children]
wireguard_clients
# Or add specific hosts as needed
```

## Vault Configuration

The DNS client role reuses existing DNS server variables from `vault_secrets.yml`:

**Required (existing variables):**
```yaml
# DNS Server Configuration
vault_dns_zone: "cluster.local"
vault_dns_server_primary: "[primary-dns-server-ip]"
vault_dns_server_secondary: "[secondary-dns-server-ip]"
```

**Optional:**
```yaml
# DNS Client Options (for resolv.conf settings)
vault_dns_client_options:
  - "timeout:2"
  - "attempts:3"
  - "rotate"
```

## Testing DNS Resolution

The role automatically tests DNS resolution during installation. To manually test:

```bash
# From a client host
nslookup google.com [dns-server-vpn-ip]

# Or use dig
dig @[dns-server-vpn-ip] google.com
```

## DNS reliability architecture

The full chain for Kubernetes pod DNS queries is:

```
Pod → CoreDNS → node /etc/resolv.conf → dnsmasq (wg99 IP) → Unbound DNS servers
```

dnsmasq on each node manages two upstream lists:

**`dns_client_dnsmasq_primary_only_domains`** — sent only to the primary Unbound server.
Used for Google/AWS CDN domains where the secondary resolver is known to be rate-limited.

**`dns_client_dnsmasq_ci_domains`** — sent to **all** configured upstreams with round-robin.
Used for CI/CD and container registry domains (GitHub, Docker, ghcr.io, etc.) so that
a brief WireGuard path degradation on the primary does not return SERVFAIL and stall jobs.
This is the fix for the intermittent 100-second OAuth timeout on vas-worker1.

For nodes on a separate network segment (VAS workers on `9.11.0.x`):
- Set `vault_dns_client_filter_aaaa: true` in `group_vars/workers_vas.yml` to drop AAAA
  answers at the dnsmasq layer — eliminates 30–90 s AAAA-first timeouts.
- The `--tags vas_dns` target lets you re-apply dnsmasq config on VAS workers only.

## Troubleshooting

### dnsmasq fails to start on boot
**Symptoms:** dnsmasq service fails during system startup with "address not available" errors

**Cause:** WireGuard interface isn't ready when dnsmasq tries to bind to its listen IP

**Solution:**
- This role automatically creates a systemd override: `/etc/systemd/system/dnsmasq.service.d/10-wireguard-ordering.conf`
- The override ensures dnsmasq starts after `wg-quick@wg99.service`
- Uses `bind-dynamic` mode which tolerates interfaces appearing after service start
- Manually verify:
  ```bash
  # Check override exists
  cat /etc/systemd/system/dnsmasq.service.d/10-wireguard-ordering.conf

  # Reload systemd if needed
  sudo systemctl daemon-reload

  # Restart dnsmasq
  sudo systemctl restart dnsmasq
  ```

### DNS resolution fails:

1. Verify WireGuard VPN is running and connected
2. Check that DNS servers are accessible via VPN:
   ```bash
   ping [primary-dns-server-vpn-ip]
   ping [secondary-dns-server-vpn-ip]
   ```
3. Verify DNS server is running:
   ```bash
   systemctl status unbound
   ```
4. Check `/etc/resolv.conf` contains correct nameservers:
   ```bash
   cat /etc/resolv.conf
   ```

### Kubernetes nodes can resolve, but containerd/ACME/GitHub Actions fails (AAAA selected)

If your nodes have no IPv6 default route but your upstream resolver returns AAAA records,
some clients (containerd pulls, ACME, GitHub Actions runners) may try IPv6 first and time
out (30–90 s) before falling back to IPv4.

Enable node-local dnsmasq AAAA filtering — set `vault_dns_client_filter_aaaa: true` in
`vault_secrets.yml` or in `group_vars/workers_vas.yml` for VAS-segment nodes only.
This drops AAAA answers at the dnsmasq layer so both the node and CoreDNS (when using
`dnsPolicy: Default`) get IPv4-only upstream answers.

### GitHub Actions runner times out resolving `actions.githubusercontent.com`

This is the intermittent SERVFAIL caused by `githubusercontent.com` being pinned to a
single upstream with no fallback. As of v1.9.0 this is fixed: CI/CD domains are in
`dns_client_dnsmasq_ci_domains` and routed across all upstreams.

If you see this on a fresh deploy, ensure `group_vars/workers_vas.yml` exists (copy from
`workers_vas.example.yml`) with `vault_dns_client_filter_aaaa: true`, and re-run:

```bash
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags vas_dns
ansible-playbook -i hosts_bay.ini kuber_coredns_install.yaml
```

### systemd-resolved keeps taking over:

If `systemd-resolved` is interfering:
```bash
# Stop and disable
systemctl stop systemd-resolved
systemctl disable systemd-resolved

# Remove stub file
rm /etc/resolv.conf

# Run this playbook again to deploy custom configuration
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns
```

## Security Considerations

- This role requires `become: true` (root privileges)
- `/etc/resolv.conf` is a system-critical file - test in non-production first
- Original configuration is backed up before changes

## License

MIT
