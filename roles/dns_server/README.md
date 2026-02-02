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
- DNS resolution testing with `dig`
- Automatic systemd-resolved disable (prevents port 53 conflict)
- Custom resolv.conf with fallback to public DNS (8.8.8.8)

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
dns_upstream_dns:
  - "[dns-server]"
  - "8.8.4.4"
dns_cache_size: 256
dns_do_ipv6: false
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

**Note:** The role automatically disables `systemd-resolved` and creates a custom `/etc/resolv.conf` pointing to Unbound (127.0.0.1) with Google DNS (8.8.8.8) as a fallback for upstream queries.

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

# Test DNS resolution
dig @127.0.0.1 [node-name].[zone-name]

# Example:
dig @127.0.0.1 [cluster-hostname]
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
- ✅ Fallback to public DNS (8.8.8.8) for upstream queries

### Firewall Behavior

- UFW is automatically enabled with logging during installation
- DNS port 53 (UDP/TCP) is opened for configured networks only
- SSH access is preserved from current connecting IP when UFW is enabled
- Existing UFW configurations are respected (no SSH rules added if UFW active)

See `vault_secrets.example.yml` for template structure.

## License

MIT

## Author Information

- [your-username]
