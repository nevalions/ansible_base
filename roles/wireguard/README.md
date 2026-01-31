# WireGuard Role

Manage WireGuard VPN network with automatic peer configuration, NAT support, and UFW firewall integration.

## Requirements

- Ansible 2.16+
- Debian/Ubuntu hosts
- WireGuard package available in repository
- UFW firewall (optional but recommended)

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

### Keys (Auto-generated)

| Variable | Description |
|----------|-------------|
| `vault_wg_server_private_key` | Server private key (auto-generated) |
| `vault_wg_server_public_key` | Server public key (auto-generated) |
| `vault_wg_peer_private_keys` | Dictionary of peer private keys |
| `vault_wg_peer_public_keys` | Dictionary of peer public keys |

### Peer Configuration

| Variable | Description |
|----------|-------------|
| `vault_wg_peers` | List of peer configurations |

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
ansible-playbook wireguard_manage.yaml -i hosts_bay.ini --tags wireguard
```

### Remove WireGuard

```bash
ansible-playbook wireguard_manage.yaml -i hosts_bay.ini -e "wg_operation=remove" --tags wireguard
```

### Rotate Keys

```bash
ansible-playbook wireguard_rotate_keys.yaml -i hosts_bay.ini --tags wireguard,rotate
```

### Check Mode (Dry Run)

```bash
ansible-playbook wireguard_manage.yaml -i hosts_bay.ini --check
```

### Custom Interface Name

```bash
ansible-playbook wireguard_manage.yaml -i hosts_bay.ini -e "vault_wg_interface=wg98,vault_wg_network_cidr=[internal-ip]/24"
```

## NAT Configuration

For peers behind NAT, configure port forwarding on your router:

```
NAT Router: [public-ip]

Peer: [peer-name] (internal IP: [internal-ip])
  Forward: UDP [external-port] → [internal-ip]:[internal-port]
```

Then update `vault_wg_peers` with the correct endpoints:

```yaml
- name: "[peer-name]"
  host_group: "[ansible-host-group]"
  allowed_ips: "[peer-vpn-ip]/32"
  endpoint: "[public-ip]:[external-port]"
  client_listen_port: "[internal-port]"
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

Use the rotation playbook to regenerate all keys:

```bash
ansible-playbook wireguard_rotate_keys.yaml -i hosts_bay.ini
```

After rotation, update `vault_secrets.yml` with new keys.

## Firewall Configuration

This role automatically configures UFW:

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

## License

MIT
