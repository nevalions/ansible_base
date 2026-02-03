# Keepalived

This role configures Keepalived for Virtual IP (VIP) management and automatic failover.

## Purpose

- Manages Virtual IP address for Kubernetes API high availability
- Automatic failover between control plane nodes
- Health checks on HAProxy and Kubernetes API
- VRRP-based VIP assignment and removal

## Variables

All sensitive variables are stored in `vault_secrets.yml`:

```yaml
# Keepalived Configuration
keepalived_vip: "[vip-address]"
keepalived_vip_cidr: 32
keepalived_vip_interface: "[vip-interface]"
keepalived_vip_port: "[k8s-api-port]"
keepalived_password: "[keepalived-password]"
keepalived_router_id: 51
keepalived_check_interval: 2000
keepalived_check_rise: 2
keepalived_check_fall: 3
keepalived_priority: 100

# Control Planes for DNAT
keepalived_control_planes:
  - name: "[control-plane-hostname]"
    wireguard_ip: "[control-plane-wg-ip]"
    api_port: 7443
    backend_port: 7443
```

## Features

- **VIP Management**: Automatic assignment on WireGuard interface
- **VRRP Protocol**: Industry-standard for VIP failover
- **Health Checks**: Monitors HAProxy and Kubernetes API
- **DNAT Support**: Maps VIP port to HAProxy backend port
- **MASQUERADE**: Automatic NAT for DNAT traffic
- **UFW Integration**: Firewall rules for VIP and WireGuard
- **Multi-Control Plane**: Supports HA across multiple control planes

## Usage

```bash
# Deploy Keepalived on HAProxy host
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml

# With tags
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml --tags keepalived
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml --tags verify

# Limit to specific host
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml --limit [haproxy-hostname]
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  WireGuard Network                │
│                                                      │
│  ┌──────────────┐          ┌──────────────┐ │
│  │ Control      │          │   Control    │ │
│  │ Plane 1     │          │   Plane 2    │ │
│  │              │          │              │ │
│  │ HAProxy      │          │   HAProxy    │ │
│  │ :7443        │          │   :7443      │ │
│  │              │          │              │ │
│  │ Keepalived   │◄───────┤ Keepalived   │ │
│  │              │   VIP    │              │ │
│  │              │  [vip-addr]│              │ │
│  └──────────────┘          └──────────────┘ │
│                      │                      │
│  ◄──────────────Workers                │
│     connect to [vip-address]:[k8s-api-port] │
└─────────────────────────────────────────────────────┘
```

**DNAT Flow:**
```
VIP:[k8s-api-port] → Keepalived selects active plane
     ↓
DNAT to [control-plane-wg-ip]:[haproxy-backend-port]
     ↓
HAProxy backend :[haproxy-backend-port] → localhost:[k8s-api-port]
```

**Failover Process:**
1. Keepalived health check fails on active plane
2. VRRP priority determines new master
3. VIP moves to new control plane
4. DNAT updates to new plane's WireGuard IP
5. Workers seamlessly reconnect to VIP

## Files

- `roles/keepalived/defaults/main.yaml` - Default variables
- `roles/keepalived/tasks/main.yaml` - Main tasks (install, configure, verify)
- `roles/keepalived/handlers/main.yaml` - Service handlers
- `roles/keepalived/templates/keepalived.conf.j2` - Keepalived config template
- `roles/keepalived/meta/main.yaml` - Role metadata

## Adding More Control Planes

1. Add new control plane to inventory (`[planes_all]`)
2. Add WireGuard peer configuration
3. Update `vault_secrets.yml`:
   ```yaml
   keepalived_control_planes:
     - name: "[control-plane-hostname-2]"
       wireguard_ip: "[control-plane-wg-ip-2]"
       api_port: 7443
       backend_port: 7443
       priority: 99
   ```
4. Re-run playbooks:
   ```bash
   ansible-playbook -i hosts_bay.ini keepalived_manage.yaml
   ansible-playbook -i hosts_bay.ini haproxy_k8s.yaml
   ```

## Health Checks

Keepalived tracks health of both HAProxy and Kubernetes API:

**HAProxy Health Check:**
```bash
/bin/bash -c 'timeout 2 /usr/bin/nc -z [control-plane-wg-ip] 7443'
```
- Returns: success (0) or failure (1)
- Checks every 2 seconds
- Weight: 20 (less than API check)

**Kubernetes API Health Check:**
```bash
/bin/bash -c 'timeout 2 /usr/bin/nc -z [control-plane-wg-ip] 6443'
```
- Returns: success (0) or failure (1)
- Checks every 2 seconds
- Weight: 10 (more critical)

**Priority:**
- Active master: priority 100
- Backup planes: priority 99 (or lower)
- Priority determines VRRP master election

## Security

- All IPs, ports, hostnames encrypted in `vault_secrets.yml`
- VRRP authentication with encrypted password
- WireGuard network isolation for VIP traffic
- No hardcoded values in playbooks
- UFW firewall rules restrict access to WireGuard network only

## Troubleshooting

### VIP not assigned
```bash
# Check Keepalived status
sudo systemctl status keepalived

# Check VIP assignment
ip addr show [vip-interface]

# Check VRRP status
sudo keepalived -d -D

# Check for interface issues
ip link show [vip-interface]
```

### Failover not working
```bash
# Verify VRRP authentication
grep -r "auth_pass" /etc/keepalived/keepalived.conf

# Check priority values
grep -r "priority" /etc/keepalived/keepalived.conf

# Test health checks manually
timeout 2 /usr/bin/nc -z [control-plane-wg-ip] 7443
timeout 2 /usr/bin/nc -z [control-plane-wg-ip] 6443

# Check Keepalived logs
sudo journalctl -u keepalived -n 50
```

### Workers cannot connect
```bash
# Check VIP is active
ip addr show | grep [vip-address]

# Check port is listening
sudo netstat -tlnp | grep [k8s-api-port]
sudo ss -tlnp | grep [k8s-api-port]

# Test from worker
nc -zv [vip-address] [k8s-api-port]

# Check firewall rules
sudo iptables -t nat -L -n -v | grep [vip-address]
sudo iptables -t filter -L INPUT -n -v | grep [k8s-api-port]
```

## Requirements

- **System**: Debian 11 (bullseye) or Ubuntu 20.04+ (jammy)
- **Privileges**: sudo/root access
- **WireGuard**: Configured and operational
- **HAProxy**: Installed and configured on control planes
- **Network**: WireGuard interface (e.g., wg99)

## Integration with HAProxy K8s

This role works with `haproxy_k8s` for complete VIP architecture:

1. Deploy HAProxy: `ansible-playbook -i hosts_bay.ini haproxy_k8s.yaml`
2. Deploy Keepalived: `ansible-playbook -i hosts_bay.ini keepalived_manage.yaml`
3. Verify setup:
   ```bash
   # Check VIP assignment
   ansible-playbook -i hosts_bay.ini keepalived_manage.yaml --tags verify
   
   # Test VIP connectivity
   nc -zv [vip-address] [k8s-api-port]
   ```

See `VIP_IMPLEMENTATION_SUMMARY.md` for complete architecture guide.
