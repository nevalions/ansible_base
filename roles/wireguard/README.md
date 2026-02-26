# WireGuard Role

Manage WireGuard VPN network with automatic peer configuration, NAT support, and optional UFW firewall integration.

## Overview
This role manages WireGuard VPN with a hybrid topology:
- **Full Mesh**: Servers directly connect to all other servers
- **Multi-Server Peers**: Clients connect to ALL servers for redundancy

## Network Architecture

### Current Setup
- **VPN Network**: [vpn-network-cidr]
- **Interface**: wg99
- **Servers (3)**: Full mesh topology
  - [server-name-a] ([vpn-ip-a]): [public-ip-a]:[port-a]
  - [server-name-b] ([vpn-ip-b]): [public-ip-b]:[port-b] (NAT)
  - [server-name-c] ([vpn-ip-c]): [public-ip-c]:[port-c] (NAT)
- **Clients**: Multi-server connections
  - [client-name] ([client-vpn-ip]): Connects to all 3 servers

### Topology Diagram
```
Servers (Full Mesh):
[server-name-a] ←→ [server-name-b]
      ↑                  ↑
      └──→ [server-name-c] ←─┘

Clients (Multi-Server):
[client-name] → [server-name-a] (primary)
[client-name] → [server-name-b] (backup)
[client-name] → [server-name-c] (backup)
```

## Requirements

- Ansible 2.16+
- Debian/Ubuntu hosts
- WireGuard package available in repository
- UFW firewall (optional)

## Role Variables

### Network Configuration

| Variable | Description |
|----------|-------------|
| `vault_wg_interface` | WireGuard interface name (e.g., `wg0`) |
| `vault_wg_network_cidr` | VPN network CIDR (from vault) |
| `vault_wg_server_ip` | WireGuard server IP |
| `vault_wg_server_port` | WireGuard server UDP port |
| `vault_wg_client_default_port` | Default client listen port |
| `vault_wg_client_port_start` | Start of NAT port range |
| `vault_wg_client_port_end` | End of NAT port range |
| `vault_wg_dns_primary` | DNS server for VPN clients |
| `vault_k8s_api_vip` | Kubernetes API VIP used for routed /32 |
| `vault_metallb_pool_cidr` | MetalLB subnet routed through WireGuard |
| `vault_db_wg_route_cidr` | Optional DB endpoint route for non-DB peers (`[db-wg-ip]/32`) |

### Keys (Auto-generated)

| Variable | Description |
|----------|-------------|
| `vault_wg_peer_private_keys` | Dictionary of peer private keys (all nodes) |
| `vault_wg_peer_public_keys` | Dictionary of peer public keys (all nodes) |

### Peer Configuration

| Variable | Description |
|----------|-------------|
| `vault_wg_peers` | List of peer configurations |
| `vault_wg_server_ips` | Per-host server IP addresses for mesh |
| `vault_wg_peers_extra_cidrs` | Dict of `peer_name → [CIDRs]` for explicit per-peer AllowedIPs (authoritative; replaces legacy `is_server` + `vault_wg_routed_cidrs`) |
| `vault_wg_routed_cidrs` | Legacy: CIDRs added to all `is_server: true` peers. Set to `[]` in current playbook. |
| `wg_postup_rules` | List of PostUp iptables rules rendered into wg99.conf (e.g. MASQUERADE for worker nodes) |
| `wg_predown_rules` | List of PreDown iptables rules rendered into wg99.conf (cleanup of MASQUERADE rules) |

Each peer requires:
```yaml
- name: "[peer-name]"              # Peer name (must match key dict)
  host_group: "[ansible-host-group]" # Ansible host group for auto-deployment
  allowed_ips: "[peer-vpn-ip]/32"  # Peer's VPN IP
  endpoint: "[peer-public-ip]:[port]" # Peer's public endpoint
  client_listen_port: "[port]"     # Optional: unique port for NAT peers
```

### Firewall Configuration

| Variable | Description |
|----------|-------------|
| `vault_wg_allowed_networks` | Networks allowed to connect to WireGuard |

## Configuration

### Peer Configuration
Peers connect to ALL servers for redundancy:
- Each peer has a `[Peer]` section for each server
- `AllowedIPs` uses specific server VPN IPs (e.g., `[vpn-ip.100]/32`)
- `PersistentKeepalive = 25` maintains connections

### NAT Port Forwarding
For servers behind NAT with shared public IP:
1. Configure public endpoint: `[public-ip]:PORT`
2. Forward UDP port to internal server:
   - [public-ip]:[port-a] → [internal-ip-a]:[port-a]
   - [public-ip]:[port-b] → [internal-ip-b]:[port-b]
3. Update `vault_wg_peers` with NAT endpoint
4. Peers use public endpoints with unique ports

### Interface Address Drift Detection

When WireGuard configuration changes and the interface IP address changes (e.g., different server IP assignment), the role:

1. Detects address drift by comparing current interface IP with desired IP
2. Automatically restarts WireGuard service when drift is detected
3. Uses `wg syncconf` for zero-downtime updates when address hasn't changed

**Why this matters:**
- Address changes require service restart (syncconf doesn't update interface IP)
- Automatic detection prevents stale configurations after IP changes
- Preserves connections when only peer configuration changes

### AllowedIPs Configuration

**Why use specific server IPs instead of network CIDR?**

**Broken (routing conflicts):**
```ini
[Peer]
AllowedIPs = [vpn-network-cidr]  # All peers get same route
```

**Correct (no conflicts):**
```ini
[Peer]
AllowedIPs = [server-vpn-ip]/32  # Only routes to this server
```

**Benefits:**
- No routing conflicts between multiple peer connections
- Clear traffic routing per server
- Supports multi-server redundancy
- Automatic deduplication of AllowedIPs across peers (prevents duplicate routes)
- Smart CIDR routing: server peers get routed CIDRs (e.g., MetalLB pools), but API VIP is excluded for non-plane peers

### Per-peer explicit CIDR routing (current, authoritative)

`vault_wg_peers_extra_cidrs` maps each peer name to a list of additional CIDRs
appended to that peer's `AllowedIPs`. This is the **authoritative** mechanism.

```yaml
# In wireguard_manage.yaml, built automatically by build_peers_extra_cidrs filter:
vault_wg_peers_extra_cidrs:
  bay_worker2: ["11.11.0.0/24"]   # MetalLB pool — first worker peer owns it
  # Pod CIDR (10.244.0.0/16) intentionally omitted — MASQUERADE on workers rewrites src
```

Ownership rules computed by `filter_plugins/wg_routing_filters.py`:

| CIDR | Assigned to | Why |
|------|-------------|-----|
| MetalLB pool (`vault_metallb_pool_cidr`) | First worker peer in `vault_wg_peers` | Traefik DaemonSet runs on every worker; one peer must own the CIDR for outbound routing |
| Pod CIDR (`vault_k8s_pod_subnet`) | **Not assigned** | Workers apply MASQUERADE PostUp — replies arrive from worker /32 IPs, already in AllowedIPs |
| DB WG route (`vault_db_wg_route_cidr`) | Non-DB peers, only when DB has no dedicated peer entry | Avoids AllowedIPs conflict with existing /32 peer entry |

### PostUp / PreDown rules for worker MASQUERADE

When Traefik uses `externalTrafficPolicy: Local`, kube-proxy does not SNAT external
traffic. Pod reply packets carry source IPs in `10.244.0.0/16` (pod CIDR). HAProxy
cannot route those back — it only knows worker WG IPs.

Workers apply an iptables MASQUERADE rule on wg99 PostUp:

```
iptables -t nat -A POSTROUTING -s <pod_cidr> -d <haproxy_wg_ip> -j MASQUERADE
```

This is set automatically in `wireguard_manage.yaml` via `wg_worker_postup_rules`
and `wg_worker_predown_rules` (passed to the role as `wg_postup_rules` /
`wg_predown_rules`). The rules are rendered into wg99.conf by the templates.

### Legacy: Routed CIDRs for is_server peers (deprecated)

The `vault_wg_routed_cidrs` + `is_server: true` mechanism is still supported
but is now a no-op in `wireguard_manage.yaml` (`wg_routed_cidrs: []`).

Prefer `vault_wg_peers_extra_cidrs` for explicit per-peer control. The legacy
path exists for backward compatibility with existing vault configurations.

### BGP Router Peer Routing Exception

When both the current host and a peer are members of the `bgp_routers` inventory group,
routed CIDRs via the legacy `is_server` path are **not** added to `AllowedIPs` for that peer.

**Why:** BGP routers learn routes dynamically via BGP sessions. Adding static WireGuard
routes for the same prefixes would conflict with or duplicate the BGP-learned routes.

This logic is automatic and applies to both the legacy and explicit routing paths.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Manage WireGuard network
  hosts: wireguard_servers
  become: true
  gather_facts: true
  serial: 1
  vars_files:
    - vault_secrets.yml
  tags:
    - wireguard
    - vpn
  vars:
    wg_operation: "install"

  tasks:
    - name: Apply WireGuard role
      ansible.builtin.include_role:
        name: wireguard
```

## Usage

### Install WireGuard

```bash
# Deploy to all WireGuard hosts
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard

# Deploy to specific server
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [server-host]

# Deploy to specific client
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [client-host]
```

### Remove WireGuard

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml -e "wg_operation=remove" --tags wireguard
```

### Rotate Keys

```bash
ansible-playbook wireguard_rotate_keys.yaml -i [inventory-file] --tags wireguard,rotate
```

### Check Mode (Dry Run)

```bash
ansible-playbook wireguard_manage.yaml -i [inventory-file] --check
```

### Custom Interface Name

```bash
ansible-playbook wireguard_manage.yaml -i [inventory-file] -e "vault_wg_interface=wg98,vault_wg_network_cidr=[internal-ip]/24"
```

### Management

```bash
# View WireGuard status on host
sudo wg show

# Restart WireGuard service
sudo systemctl restart wg-quick@wg99

# View current configuration
sudo cat /etc/wireguard/wg99.conf
```

## Troubleshooting

### Extra CIDRs missing from AllowedIPs
**Symptoms:** WireGuard handshakes work, but traffic to MetalLB pool or DB route does not flow.

**With explicit routing (current):**
1. Check `wg_computed_peers_extra_cidrs` in the debug task output — confirm the expected CIDR appears for the correct peer.
2. Verify the target peer appears **before** any competing peer in `vault_wg_peers` (WireGuard silently deduplicates identical CIDRs at the kernel level; first peer wins).
3. Re-run: `ansible-playbook wireguard_manage.yaml --vault-password-file vault_password_client.sh --limit <host> --diff`

**With legacy is_server routing:**
1. Confirm the peer entry in `vault_wg_peers` includes `is_server: true`.
2. Confirm `vault_wg_routed_cidrs` is non-empty.
3. Note: `wireguard_manage.yaml` sets `wg_routed_cidrs: []` — the legacy path is disabled. Use `vault_wg_peers_extra_cidrs` instead.

### Pods cannot reach DB over WireGuard

**Symptoms:** node-to-DB connectivity works, but pods cannot reach DB endpoint.

**Checks:**
1. If using legacy Calico, ensure SNAT (`natOutgoing`) is enabled on the pod IPPool.
   - Flannel default path in this repo does not require this setting.
2. Ensure workers have DB WG route in `AllowedIPs` (for example `vault_db_wg_route_cidr`).
3. Validate route on worker: `ip route get [db-wg-ip]` should use `wg99`.

### No Handshake with Peer
**Symptoms:** `latest handshake` not updating, 0 B received

**Solutions:**
1. Check firewall allows WireGuard port (UDP):
   ```bash
   sudo ufw status verbose | grep [wg-port]
   ```
2. Verify server is listening:
   ```bash
   sudo ss -ulnp | grep [wg-port]
   ```
3. Check NAT port forwarding (if applicable):
   ```bash
   # On NAT gateway
   iptables -t nat -L -n -v | grep [wg-port]
   ```
4. Test UDP connectivity:
   ```bash
   nc -u -z <server_ip> <port>
   ```

### Routing Conflicts
**Symptoms:** Peers connect but can't reach all servers

**Solution:** Verify each peer uses specific `AllowedIPs`:
```ini
[Peer]
AllowedIPs = [server-vpn-ip]/32  # Correct: /32 for specific server
# NOT: [vpn-network-cidr]  # Wrong: Full network CIDR
```

### All Servers Unreachable
**Symptoms:** Client can't ping any VPN IPs

**Solutions:**
1. Restart WireGuard:
   ```bash
   sudo wg-quick down wg99
   sudo wg-quick up wg99
   ```
2. Check interface is up:
   ```bash
   ip addr show wg99
   ```
3. Verify routing table:
   ```bash
   ip route show | grep [vpn-network]
   ```
4. Check private key matches vault:
   ```bash
   # Compare with vault_wg_peer_private_keys
   sudo grep PrivateKey /etc/wireguard/wg99.conf
   ```

### NAT Hairpin Issues

**Symptoms:** Peers on same network can't connect via public IP when servers share NAT IP

**Scenario:**
- Server A: [server-name-a] at [internal-ip-a] (NAT: [public-ip]:[port-a])
- Server B: [server-name-b] at [internal-ip-b] (NAT: [public-ip]:[port-b])
- Client: [client-name] at [internal-ip-client] (NAT: [public-ip]:[port-client])

**Problem:** Client can't connect to Server B via public IP [public-ip]:[port-b] because:
1. NAT doesn't support "hairpin NAT" (NAT routing to local hosts)
2. Client's NAT router blocks outgoing traffic to its own public IP

**Solutions:**

**Option 1: Use Internal IPs (Recommended for local clients)**
```yaml
# In vault_wg_peers, use internal IPs for servers on same local network
- name: "[server-name-a]"
  endpoint: "[internal-ip-a]:[port-a]"  # Internal IP for local clients
- name: "[server-name-b]"
  endpoint: "[internal-ip-b]:[port-b]"   # Internal IP for local clients
- name: "[server-name-c]"
  endpoint: "[public-ip-remote]:[port-c]"  # Public IP (remote server)
```

**Option 2: Configure NAT Hairpin on Router**
On the NAT gateway ([public-ip]):
```
# Enable NAT loopback (hairpin NAT)
iptables -t nat -A POSTROUTING -d [public-ip] -j MASQUERADE

# Or configure in router settings
# Enable "NAT Loopback" or "Hairpin NAT" feature
```

**Option 3: Use Different NAT Ports**
Each server gets unique NAT port to prevent conflicts:
```yaml
# Router port forwarding:
[public-ip]:[port-a] → [internal-ip-a]:[port-a]  # [server-name-a]
[public-ip]:[port-b] → [internal-ip-b]:[port-b]   # [server-name-b]
[public-ip]:[port-c] → [internal-ip-client]:[port-c]   # [client-name] (client)
```

**Recommendation:** Use Option 1 (Internal IPs) for local clients to avoid NAT complexity.

### Verify Full Mesh
**Test server-to-server connectivity:**
```bash
# From any server
ping -c 3 [vpn-ip-a]  # [server-name-a]
ping -c 3 [vpn-ip-b]  # [server-name-b]
ping -c 3 [vpn-ip-c]   # [server-name-c]
```

**Test client-to-server connectivity:**
```bash
# From client (should reach all servers)
sudo wg show  # Should show 3 peers with handshakes
ping -c 3 [vpn-ip-a]
ping -c 3 [vpn-ip-b]
ping -c 3 [vpn-ip-c]
```

## Security

### Key Management
- Private keys stored in encrypted `vault_secrets.yml`
- Never commit vault files to git
- Rotate keys if compromised: regenerate with `wg genkey`

### Firewall Requirements
```bash
# Allow WireGuard UDP ports
sudo ufw allow [port-a]/udp from <network>
sudo ufw allow [port-b]/udp from <network>
sudo ufw allow [port-c]/udp from <network>

# Allow VPN forwarding
sudo ufw route allow in on wg99 from [vpn-network-cidr]
sudo ufw route allow out on wg99 to [vpn-network-cidr]
```

## Vault Variables

### vault_wg_peers Structure
```yaml
vault_wg_peers:
  - name: "server_name"           # Unique identifier
    host_group: "inventory_group"  # Maps to inventory
    allowed_ips: "[vpn-ip.X]/32"  # Server's VPN IP
    endpoint: "IP:PORT"          # Public or internal IP with port
    client_listen_port: "PORT"     # UDP port for incoming connections
```

### Example: Adding New Peer
1. Generate keys:
   ```bash
   wg genkey > peer_private.txt
   cat peer_private.txt | wg pubkey > peer_public.txt
   ```
2. Add to `vault_wg_peers`:
   ```yaml
   - name: "new_peer"
     host_group: "new_peer"
     allowed_ips: "[vpn-ip.50]/32"
     endpoint: "[public-ip]:[port]"
     client_listen_port: "[port]"
   ```
3. Add keys to `vault_wg_peer_private_keys` and `vault_wg_peer_public_keys`
4. Encrypt vault:
   ```bash
   ansible-vault encrypt vault_secrets.yml
   ```
5. Deploy:
   ```bash
   ansible-playbook wireguard_manage.yaml -i [inventory-file] --tags wireguard --limit new_peer
   ```

## Multi-Server HA

This role supports multiple WireGuard servers for high availability. All servers use:
- Same network CIDR
- Same server keypair (simplifies client config)
- Same configuration deployed to all servers

Clients will connect to all servers in `[Peer]` sections for automatic failover.

## Key Management

### First Deployment

Keys are auto-generated on first run and stored in Ansible facts. To persist keys:

1. After first deployment, copy keys from output to `vault_secrets.yml`
2. Encrypt vault with `ansible-vault encrypt vault_secrets.yml`

### Key Rotation

Use rotation playbook to regenerate all keys:

```bash
ansible-playbook wireguard_rotate_keys.yaml -i [inventory-file]
```

After rotation, update `vault_secrets.yml` with new keys.

## Firewall Configuration

This role can configure UFW rules, but it does not enable UFW automatically.

Kubernetes note:
- For Kubernetes-over-WireGuard clusters (Flannel default; Legacy Calico Path (optional)), avoid UFW on Kubernetes nodes unless you are explicitly managing FORWARD rules.

### Server Side
- Opens `vault_wg_server_port` for all WireGuard connections
- Opens unique ports for NAT peers
- Opens SSH port from current connecting IP

### Client Side
- Opens client listen port
- Allows outbound connections to WireGuard servers
- Opens SSH port from current connecting IP

## Backups

All configuration changes are backed up to `/etc/wireguard/backups/` with timestamps:

```
/etc/wireguard/backups/[interface].conf.backup.[timestamp]
```

## Support

### Useful Commands
```bash
# WireGuard
sudo wg show                    # View status
sudo wg-quick up wg99          # Start interface
sudo wg-quick down wg99        # Stop interface

# Network
ip addr show wg99              # Show interface
ip route show | grep wg99     # Show routes
ss -ulnp | grep wg99         # Show listening ports

# Firewall
sudo ufw status verbose        # Show rules
sudo ufw allow <port>/udp     # Allow port
```

## License

MIT
