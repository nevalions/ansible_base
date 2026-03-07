# DNS Server Role

Configures Unbound DNS server for Kubernetes cluster with encrypted vault variables.

## Overview

This role installs and configures Unbound as a DNS server for Kubernetes cluster management. All sensitive data (IPs, hostnames, ports) is stored encrypted in Ansible Vault.

## Features

- Unbound DNS server installation and configuration
- DNS zone management with encrypted records
- High availability across multiple servers (rolling updates with `serial: 1`)
- Firewall rules for DNS (UDP/TCP port 53) with UFW enablement
- SSH access preservation when enabling UFW (prevents lockout)
- Supports multiple networks for DNS queries (physical, VPN, cloud)
- Check mode support for safe dry-run testing
- Supports both node hostname resolution and Kubernetes service DNS
- All IPs encrypted in Ansible Vault (zero hardcoded values)
- Configuration validation with `unbound-checkconf`
- DNS resolution testing with `dig` (internal zone, external registry, CNAME-chase)
- `unbound-control` enabled for live cache management (flush stale entries without restart)
- Automatic systemd-resolved disable (prevents port 53 conflict)
- Custom resolv.conf with fallback to first configured upstream forwarder
- Forwarding hardening: `so-reuseport: no` prevents orphaned processes from stealing queries
- Forwarding hardening: `qname-minimisation: no` prevents NS referral cache poisoning in forwarding mode
- Cache safety: `serve-expired` and `prefetch` disabled by default to prevent stale NS referral amplification
- DNSSEC validation delegated to upstream resolvers (no local validator by default to avoid TLD NS referral caching)
- Optional local DNSSEC validation (`dns_dnssec_validation: true`) with trust anchor management
- Removes Ubuntu package `root-auto-trust-anchor-file.conf` that re-enables DNSSEC validator behind the scenes
- Disables resolvconf hook that overrides forwarders on DHCP events
- Systemd watchdog timer: periodic external resolution health check with escalating recovery (flush → retry → restart)
- DNSSEC root key refresh timer: daily `unbound-anchor` run (active when `dns_dnssec_validation: true`)

## Requirements

- Debian 11 (bullseye) or 12 (bookworm)
- Ubuntu 20.04 (focal), 22.04 (jammy), or 24.04 (noble)
- Sudo privileges
- Vault secrets configured in `vault_secrets.yml`

## Variables

### Default Variables

All default variables are in `defaults/main.yaml`:

```yaml
dns_listen_interface: "0.0.0.0"
dns_operation: "install"
# Dynamic: uses vault_dns_upstream_dns_by_host[inventory_hostname] if set,
# otherwise falls back to vault_dns_upstream_dns (default: ['77.88.8.8', '1.1.1.1', '9.9.9.9']).
# Per-host overrides live in vault_secrets.yml under vault_dns_upstream_dns_by_host.
dns_upstream_dns: "{{ vault_dns_upstream_dns_by_host[inventory_hostname] | default(vault_dns_upstream_dns) }}"
dns_cache_size: 256
dns_do_ipv6: false

# Forwarding hardening
dns_so_reuseport: false             # prevent orphaned processes binding to :53
dns_qname_minimisation: false       # prevent NS referral caching in forwarding mode
dns_serve_expired: false             # disabled: amplifies NS referral cache poisoning
dns_serve_expired_ttl: 86400        # max TTL for expired entries (seconds)
dns_prefetch: false                  # disabled: prefetch races can cache NS referrals
dns_dnssec_validation: false        # delegate DNSSEC to upstream resolvers

# Watchdog timer (external resolution health check)
dns_watchdog_enabled: true
dns_watchdog_interval: "60s"
dns_watchdog_test_domains:          # list — ANY domain resolving = healthy
  - "google.com"
  - "ghcr.io"
dns_watchdog_timeout: 5             # dig timeout per attempt (seconds)
dns_watchdog_tries: 2               # dig retry count per domain
dns_watchdog_cooldown_seconds: 120  # seconds after restart before re-checking

# DNSSEC root key refresh timer (active when dns_dnssec_validation: true)
dns_anchor_refresh_enabled: true
```

### Vault Variables (Required)

Sensitive variables must be encrypted in `vault_secrets.yml`:

```yaml
vault_dns_zone: "cluster.local"

vault_dns_servers:
  - "[primary-dns-server-ip]"
  - "[secondary-dns-server-ip]"

vault_dns_records:
  # Node hostnames
  - type: "A"
    name: "[plane1-hostname]"
    ip: "[plane1-ip]"
  - type: "A"
    name: "[worker1-hostname]"
    ip: "[worker1-ip]"
  
  # Kubernetes services (external ingress/LoadBalancer)
  - type: "A"
    name: "[ingress-hostname]"
    ip: "[ingress-ip]"
  
  # Infrastructure services
  - type: "A"
    name: "[nfs-hostname]"
    ip: "[nfs-ip]"

vault_dns_allowed_networks:
  # Add all networks that should be able to query DNS
  # This list supports multiple networks for flexible deployment
  # - Always include localhost for local queries
  - "[physical-network-cidr]"
  - "[vpn-network-cidr]"
  - "[cloud-network-cidr]"
  - "127.0.0.0/8"
```

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Manage DNS server
  hosts: dns_servers
  become: true
  gather_facts: true
  serial: 1
  vars_files:
    - vault_secrets.yml
  tags:
    - dns
    - server
    - manage
  vars:
    dns_operation: "install"
    dns_records: "{{ vault_dns_records }}"
    dns_zone: "{{ vault_dns_zone }}"
    dns_servers_list: "{{ vault_dns_servers }}"

  tasks:
    - name: Apply DNS server role
      ansible.builtin.include_role:
        name: dns_server
```

## Usage

### Installation

1. Configure vault secrets in `vault_secrets.yml` (all IPs, hostnames, ports)
2. Create inventory file with `dns_servers` group
3. Run playbook:

**Note:** The role automatically disables `systemd-resolved` and creates a custom `/etc/resolv.conf` pointing to Unbound (127.0.0.1) with the first configured upstream forwarder as a fallback.

```bash
ansible-playbook -i hosts_dns.ini dns_server_manage.yaml
```

### Removal

Set `dns_operation: "remove"` to uninstall:

```bash
ansible-playbook -i hosts_dns.ini dns_server_manage.yaml -e dns_operation=remove
```

### Check Mode

Run in check mode for dry-run:

```bash
ansible-playbook -i hosts_dns.ini dns_server_manage.yaml --check
```

## Inventory Configuration

Example inventory file (`hosts_dns.ini`):

```ini
[dns_servers]
[[dns-server-ip]]
[[dns-server-ip]]

[dns_servers:vars]
ansible_user=[username]
ansible_port=[ssh-port]
ansible_become=true
ansible_become_method=sudo
```

## Verification

After deployment, verify DNS resolution:

```bash
# Check Unbound service status
systemctl status unbound

# Validate configuration
unbound-checkconf /etc/unbound/unbound.conf

# Test internal zone DNS resolution
dig @127.0.0.1 [node-name].[zone-name]

# Test external registry resolution (must return at least one A record)
dig @127.0.0.1 registry-1.docker.io A +short

# Test CNAME-chase resolution (auth.docker.io -> cdn.cloudflare.net)
# Must return at least one A record, not just a CNAME
dig @127.0.0.1 auth.docker.io A +short

# Flush stale cache entries without restarting Unbound
sudo unbound-control flush auth.docker.io.cdn.cloudflare.net
sudo unbound-control flush auth.docker.io

# Verify no TLD NS referrals in cache (should return empty)
sudo unbound-control dump_cache | grep -E '(com|io|net|org)\.\s.*IN\s+NS'

# Check serve-expired and prefetch are disabled (default)
sudo unbound-control get_option serve-expired   # should be: no
sudo unbound-control get_option prefetch         # should be: no
```

### Watchdog Timer

When `dns_watchdog_enabled: true` (the default), the role deploys a systemd timer
that runs every `dns_watchdog_interval` (default: 60s). The watchdog tests whether
Unbound can resolve **any** domain in `dns_watchdog_test_domains` (default:
`google.com`, `ghcr.io`). If at least one domain resolves, the check passes
(ANY-pass logic). On total failure it applies escalating recovery:

1. Flush the Unbound cache (`unbound-control flush_zone .`)
2. Retry resolution
3. Restart the Unbound service if still failing
4. Enter a cooldown period (`dns_watchdog_cooldown_seconds`, default: 120s) to let
   the cache warm before the next check

The watchdog also detects **orphaned Unbound processes** (zombie `unbound -d` debug
instances that survived a service restart) and kills them before recovery, preventing
the `SO_REUSEPORT` kernel load-balancing split described in the troubleshooting
section below.

```bash
# Check watchdog timer status
systemctl status unbound-watchdog.timer

# View recent watchdog runs
journalctl -u unbound-watchdog.service --no-pager -n 20

# Disable watchdog (set dns_watchdog_enabled: false and re-run the role)
```

### DNSSEC Validation

By default (`dns_dnssec_validation: false`), DNSSEC validation is **delegated to
upstream resolvers** (77.88.8.8, 1.1.1.1, 9.9.9.9 all perform DNSSEC validation).
Unbound runs with `module-config: "iterator"` only.

**Why local DNSSEC is disabled by default:** The validator module performs iterative
DS/DNSKEY chain lookups that populate Unbound's cache with TLD NS referrals (e.g.
`com. NS`, `io. NS`) with long TTLs (~86400s). When a forwarding query to an upstream
resolver times out, Unbound serves these cached NS referrals as the answer (NOERROR
with ANSWER:0), breaking resolution for all domains under that TLD. This was the root
cause of intermittent DNS failures for ghcr.io, docker.io, and google.com.

**To enable local DNSSEC validation** (e.g. in environments without trusted upstreams),
set `dns_dnssec_validation: true`. The role will then deploy trust anchors and the
daily refresh timer:

```bash
# Check anchor refresh timer status (only when dns_dnssec_validation: true)
systemctl status unbound-anchor-refresh.timer

# Force manual anchor refresh
sudo unbound-anchor -a /var/lib/unbound/root.key
```

## Security

- ✅ All IPs, hostnames, and ports encrypted in `vault_secrets.yml`
- ✅ No hardcoded values in playbooks or templates
- ✅ Vault password protected with GPG
- ✅ Access control lists restrict DNS queries to allowed networks
- ✅ SSH access automatically configured when enabling UFW (prevents lockout)
- ✅ Example file uses `[placeholder]` format
- ✅ systemd-resolved is disabled to prevent port 53 conflicts
- ✅ Custom resolv.conf ensures DNS queries use Unbound
- ✅ Fallback to first configured upstream forwarder for `/etc/resolv.conf`
- ✅ DNSSEC validated by upstream resolvers (local validation optional via `dns_dnssec_validation`)
- ✅ `so-reuseport: no` prevents orphaned processes from silently stealing DNS queries
- ✅ `qname-minimisation: no` prevents TLD NS referral cache poisoning in forwarding mode
- ✅ Watchdog timer detects and auto-recovers from resolution failures between deploys

### Firewall Behavior

- UFW is automatically enabled with logging during installation
- DNS port 53 (UDP/TCP) is opened for configured networks only
- SSH access is preserved from current connecting IP when UFW is enabled
- Existing UFW configurations are respected (no SSH rules added if UFW active)

See `vault_secrets.example.yml` for template structure.

## Troubleshooting

### External registry domains return SERVFAIL or empty answer

**Symptoms:** `dig @127.0.0.1 registry-1.docker.io` returns `SERVFAIL` or no answer.
ImagePullBackOff on cluster nodes whose dnsmasq forwards to this resolver.

**Common causes:**
1. TLD NS referral cached (see "TLD NS cache poisoning" section below)
2. Upstream forwarder unreachable (WireGuard tunnel down during resolver restart)
3. Unbound cache poisoned with a negative TTL entry from a transient failure

**Fix:**
```bash
# 1. Flush cache and restart
sudo unbound-control flush_zone .
sudo systemctl restart unbound

# 2. Verify
dig @127.0.0.1 registry-1.docker.io A +short
```

### CNAME-chase returns empty answer (ANSWER:0)

**Symptoms:** `dig @127.0.0.1 auth.docker.io` returns only a CNAME with no A record.
Kubernetes pods fail with `ImagePullBackOff` because containerd cannot authenticate
with Docker Hub (`failed to fetch anonymous token: no such host`).

**Cause:** Unbound's cache holds a stale referral for the CNAME target domain
(e.g. `*.cdn.cloudflare.net`). The forwarder returns the cached NS referral instead
of chasing the CNAME through upstream.

**Fix:**
```bash
# Flush the stale CNAME target and source entries
sudo unbound-control flush auth.docker.io.cdn.cloudflare.net
sudo unbound-control flush auth.docker.io

# Verify resolution recovers
dig @127.0.0.1 auth.docker.io A +short  # should now return IPs
```

If `unbound-control` is not available (pre-remote-control config), restart the service:
```bash
sudo systemctl restart unbound
```

### Unbound service not starting after config change

```bash
# Check config syntax
sudo unbound-checkconf /etc/unbound/unbound.conf

# Check journal
sudo journalctl -xeu unbound --no-pager -n 40
```

### DNS resolution works but DNSSEC validation fails

**Note:** With the default configuration (`dns_dnssec_validation: false`), DNSSEC
validation is handled by the upstream resolvers. If you have enabled local validation
(`dns_dnssec_validation: true`) and see DNSSEC errors, the anchor file may be stale:

```bash
sudo unbound-anchor -v -a /var/lib/unbound/root.key
# rc=0: up to date | rc=1: updated | rc>1: error
```

### Domains return ANSWER:0 with NS referrals (TLD NS cache poisoning)

**Symptoms:** `dig @127.0.0.1 ghcr.io` returns `NOERROR` with `ANSWER: 0` and
`AUTHORITY` section containing TLD nameservers (e.g. `io. NS a0.nic.io.`).
Some domains work while others under the same TLD consistently fail.

**Cause:** An upstream resolver (e.g. 8.8.8.8 from certain NAT source IPs) intermittently
returns NS referrals instead of A records. Unbound caches these referrals with long
TTLs (~86400s). With `serve-expired: yes`, stale referrals persist indefinitely. Other
triggers include DNSSEC validator iterative lookups and qname-minimisation partial
lookups — both populate the cache with TLD NS records.

**Fix (already prevented by default config):**
```bash
# Flush the affected TLD zone and all subdomains
sudo unbound-control flush_zone io.
sudo unbound-control flush_zone com.

# Or restart Unbound to fully clear internal cache
sudo systemctl restart unbound
```

**Prevention:** The role applies five layers of defense against TLD NS referral caching:
1. `dns_serve_expired: false` — the **primary fix**. `serve-expired: yes` amplifies
   transient failures by serving stale NS referral cache entries (with ~86400s TTL)
   indefinitely instead of forwarding fresh queries. The stable haproxy_spb server
   runs with `serve-expired: no` and never exhibits this problem.
2. `dns_prefetch: false` — prefetch races can cache NS referral responses during
   transient upstream issues.
3. `dns_dnssec_validation: false` → `module-config: "iterator"` (no validator module
   that would do iterative DS/DNSKEY lookups)
4. Removes `/etc/unbound/unbound.conf.d/root-auto-trust-anchor-file.conf` — the Ubuntu
   package ships this file which re-enables the validator module by adding
   `auto-trust-anchor-file`, overriding `module-config: "iterator"` in the main config
5. Disables `/etc/resolvconf/update.d/unbound` hook — prevents DHCP lease events from
   running `unbound-control forward <dhcp-nameservers>` which can replace the configured
   forwarders with unreachable DHCP-provided nameservers

### Orphaned Unbound process stealing queries (SO_REUSEPORT split)

**Symptoms:** ~50% of DNS queries return empty answers (`ANSWER: 0`) with NS referrals
(e.g. `com.` TLD servers) instead of actual A records. ImagePullBackOff in Kubernetes.
Restarting Unbound does not fix the problem; it recurs within seconds.

**Cause:** A debug Unbound process (typically started with `unbound -d -p -dddd`) is
still running alongside the real systemd-managed Unbound. Both bind to `0.0.0.0:53`
with `SO_REUSEPORT`, so the Linux kernel load-balances ~50% of incoming queries to
the zombie process, which has a stale config and/or empty cache. Because `SO_REUSEPORT`
distributes by source-port hash, the failure appears intermittent and random.

**Detection:**
```bash
# List all processes bound to port 53
ss -tlnp sport = :53
ss -ulnp sport = :53

# Check for multiple Unbound PIDs (should be exactly one main + workers)
pgrep -a unbound

# Look for debug instances (contain -d flag)
pgrep -af 'unbound -d'
```

**Fix:**
```bash
# Kill all orphaned Unbound processes (the systemd service will remain)
sudo pkill -x unbound
sudo systemctl restart unbound

# Verify only one set of PIDs remains
pgrep -a unbound
```

**Prevention:** The role applies three layers of orphan defense:
1. `so-reuseport: no` in unbound.conf prevents any second process from binding to port 53
2. Systemd `ExecStartPre` override kills stray processes before starting the service
3. The watchdog detects and kills orphans during its health check cycle

To prevent accidental debug processes, avoid running `unbound -d` directly; use
`unbound-control` or `journalctl -u unbound` for debugging instead.

## License

MIT

## Author Information

- [your-username]
