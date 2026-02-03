# HAProxy for Kubernetes API - Implementation Summary

**Date:** 2026-02-03  
**Status:** ✅ Complete

---

## Overview

Configured HAProxy load balancer on `[load-balancer-hostname]` to serve Kubernetes API traffic for cluster.

---

## Changes Made

### 1. Vault Configuration

Updated `vault_secrets.yml`:
- **Changed `vault_haproxy_k8s_frontend_port` from "[old-api-port]" to "[k8s-api-port]"
- **Changed `vault_k8s_control_planes[0].backend_port` from "[old-api-port]" to "[k8s-api-port]"
- **Backend:** `[control-plane-hostname]` ([control-plane-ip]:[k8s-api-port])

### 2. Nginx Port Changes

Moved nginx to different ports on `[load-balancer-hostname]` to free up standard HTTP/HTTPS ports for HAProxy usage:
- HTTP: standard port → custom port
- HTTPS: standard port → custom port

### 3. HAProxy Configuration

Deployed `/etc/haproxy/haproxy.cfg` with:
- Frontend listening on port **[k8s-api-port]** (all interfaces)
- Backend: `[control-plane-hostname]` via WireGuard IP ([control-plane-ip]:[k8s-api-port])
- Load balancing: round-robin
- Health checks enabled (TCP)

### 5. Service Configuration

- HAProxy service: **enabled** and **running**
- BIRD routing services: **stopped** and **disabled**

---

## Files Created

### Playbooks

1. **playbooks/haproxy_k8s.yaml**
   - Original playbook for HAProxy configuration
   - Targets: `[load-balancer-hostname]`
   - Deploys haproxy_k8s role

2. **playbooks/haproxy_verify.yaml**
   - Verification playbook for HAProxy status
   - Targets: `[load-balancer-hostname]`
   - Runs haproxy_verify role

3. **playbooks/haproxy_start_and_verify.yaml** ⭐ NEW
   - **Parallel playbook** that:
     - Configures HAProxy (first play)
     - Verifies setup (second play)
   - Single command: `ansible-playbook playbooks/haproxy_start_and_verify.yaml --ask-become-pass`

### Roles

**roles/haproxy_verify/** (NEW)**
```
roles/haproxy_verify/
├── defaults/main.yaml
├── meta/main.yaml
├── README.md
└── tasks/
    ├── main.yaml
    ├── verify_service.yaml
    ├── verify_configuration.yaml
    ├── verify_listening.yaml
    ├── verify_firewall.yaml
    └── verify_backend_connectivity.yaml
```

**tasks files:**
- `verify_service.yaml` - Checks HAProxy systemd status
- `verify_configuration.yaml` - Validates haproxy.cfg syntax and content
- `verify_listening.yaml` - Verifies port [k8s-api-port] binding
- `verify_firewall.yaml` - Checks UFW rules for port [k8s-api-port]
- `verify_backend_connectivity.yaml` - Tests TCP connectivity to all backends

### Unit Tests

**tests/unit/test_haproxy_verify_variables.yaml**
- Validates all verification role variables
- Tests default values and types

### Role Variables (group_vars/[load-balancer-hostname].yml)

```yaml
haproxy_k8s_frontend_port: "[k8s-api-port]"
haproxy_k8s_backend_port: "[k8s-api-port]"

vault_k8s_control_planes:
  - name: "[control-plane-hostname]"
    wireguard_ip: "[control-plane-ip]"
    backend_port: "[k8s-api-port]"
    api_port: "[k8s-api-port]"
    priority: 100

vault_wg_network_cidr: "[vpn-network-cidr]"
```

---

## Current State

### HAProxy Service

- **Status:** Active (running)
- **Enabled:** Yes
- **PID:** 760667
- **Listening:** Port [k8s-api-port] (0.0.0.0:[k8s-api-port], :::[k8s-api-port])
| **Backend:** `[control-plane-hostname]` ([control-plane-ip]:[k8s-api-port]) - **REACHABLE**

### Network Services

**WireGuard ([vpn-interface]):**
- Interface IP: [vpn-interface-ip]
- Status: UP
- Connected: `[router-hostname]`, `[control-plane-hostname]`, `[worker-hostname]`

**Nginx:**
- Status: Active (running)
- Listening: custom HTTP (HTTP), custom HTTPS (HTTPS)
- Serving: `[service-domain]`

**UFW:**
- Status: Active
- Port [k8s-api-port]: ALLOWED from [vpn-network-cidr]
- Port [k8s-api-port]: ALLOWED from 127.0.0.1

### BIRD Services (Disabled)

- bird.service: Stopped, Disabled
- bird6.service: Stopped, Disabled

---

## Usage

### Run Start & Verify

```bash
# Run both HAProxy setup and verification in parallel
ansible-playbook playbooks/haproxy_start_and_verify.yaml --ask-become-pass
```

### Run Verification Only

```bash
# Verify HAProxy status without making changes
ansible-playbook playbooks/haproxy_verify.yaml --tags haproxy,verify --ask-become-pass

# Run specific checks
ansible-playbook playbooks/haproxy_verify.yaml --tags service --ask-become-pass
ansible-playbook playbooks/haproxy_verify.yaml --tags configuration --ask-become-pass
ansible-playbook playbooks/haproxy_verify.yaml --tags firewall --ask-become-pass
```

### Run Unit Tests

```bash
ansible-playbook tests/unit/test_haproxy_verify_variables.yaml
```

---

## Verification Report

All checks passed (6/6):

| Check | Status | Details |
|-------|--------|---------|
| Service Active | ✅ | HAProxy running |
| Service Enabled | ✅ | HAProxy enabled on boot |
| Config File | ✅ | /etc/haproxy/haproxy.cfg exists |
| Config Syntax | ✅ | `haproxy -c -f` passes |
| Frontend Configured | ✅ | Port [k8s-api-port] configured |
| Backend Reachable | ✅ | `[control-plane-hostname]` ([control-plane-ip]:[k8s-api-port]) reachable |
| Listening on Port | ✅ | HAProxy bound to 0.0.0.0:[k8s-api-port] |
| Firewall Rules | ✅ | Port [k8s-api-port] allowed from VPN and localhost |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                       │
│                                                             │
│  ┌────────────┐                                         │
│  │  [control-plane-hostname] │                                         │
│  │ ([control-plane-ip]) │ ◄── WireGuard Network ──┤       │
│  │  K8s API:[k8s-api-port]│    ([vpn-network-cidr])        │
│  └────────────┘                                         │
│          ▲                                            │
│          │                                            │
└──────────┼──────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────┐
    │  [load-balancer-hostname]    │
    │  HAProxy          │
    │  Frontend: [k8s-api-port]   │
    │  Backend: [control-plane-ip]│
    └─────────────────────┘
           │
           ▼
    ┌─────────────────────┐
    │   k8s_workers     │
    │   k8s_clients     │
    │  kubectl connect   │
    └─────────────────────┘
```

**Flow:**
1. k8s clients connect to `[load-balancer-hostname]:[k8s-api-port]`
2. HAProxy load balances to `[control-plane-hostname]:[k8s-api-port]` via WireGuard
3. `[control-plane-hostname]` processes Kubernetes API requests

---

## Design Decisions

### Why Port [k8s-api-port]?

- Standard Kubernetes API port
- No need to configure kubectl or other tools
- Industry standard for Kubernetes API access

### Why Parallel Playbook?

- Single command to setup and verify
- Immediate feedback on configuration issues
- Reduces manual steps

### Why Non-Failing Verification?

- Backend may not be running during initial setup
- Allows verification in pre-production state
- Shows warnings but doesn't block CI/CD pipelines

### Why Check All Backends?

- Supports future expansion (multi-control-plane setups)
- Ensures connectivity to all configured backends
- Helpful for troubleshooting

---

## Troubleshooting

### Backend Unreachable

If backend shows as unreachable:
1. Check WireGuard status: `ssh [load-balancer-hostname] "wg show"`
2. Ping backend: `ping [control-plane-ip]`
3. Check backend port: `nc -zv [control-plane-ip] [k8s-api-port]`
4. Verify Kubernetes API is running on control plane

### Port Conflicts

If you see port binding errors:
1. Check nginx is on 8080/8443: `netstat -tln | grep nginx`
2. Check for other services on [k8s-api-port]: `netstat -tln | grep [k8s-api-port]`
3. Review UFW rules: `ufw status | grep [k8s-api-port]`

### Configuration Not Applied

If HAProxy config doesn't update:
1. Check vault variables: `ansible-playbook playbooks/haproxy_k8s.yaml --check`
2. Validate group_vars/[load-balancer-hostname].yml
3. Verify vault_secrets.yml is accessible

---

## Migration Notes

### For Existing Users

1. **Update kubectl config:**
   ```bash
   # Old (if using port 7443 or local IP)
   kubectl config set-cluster [cluster-name] --server=https://[old-address]:[old-api-port]
   
   # New
   kubectl config set-cluster [cluster-name] --server=https://[load-balancer-hostname]:[k8s-api-port]
   ```

2. **Update application configs:**
   - Change API server endpoint to `[load-balancer-hostname]:[k8s-api-port]`
   - Update load balancer IPs in config files

3. **Update DNS/Load Balancers:**
   - Point k8s-api DNS to `[load-balancer-hostname]` public IP
   - Update external load balancer targets

---

## Backup Files

HAProxy creates backups automatically:
- `/etc/haproxy/haproxy.cfg.backup.[timestamp]`

To restore:
```bash
sudo cp /etc/haproxy/haproxy.cfg.backup.<timestamp> /etc/haproxy/haproxy.cfg
sudo systemctl restart haproxy
```

---

## Security Considerations

### ✅ Implemented

- UFW restricts port [k8s-api-port] to WireGuard network only
- No direct exposure to public internet
- Config file permissions: 0640 (root:haproxy)

### ⚠️ Notes

- WireGuard network ([vpn-network-cidr]) is trusted
- Control plane IP ([control-plane-ip]) is only accessible via VPN
- TLS termination happens at control plane (not at HAProxy)
- HAProxy performs TCP passthrough (no SSL inspection)

---

## Performance Tuning

Current configuration includes:
- Max connections: 1000
- Timeout connect: 5000ms
- Timeout client: 30000ms
- Timeout server: 30000ms
- Health check interval: 2000ms

Adjustments available in `roles/haproxy_k8s/defaults/main.yaml`:
```yaml
haproxy_k8s_maxconn: 1000  # Increase for high traffic
haproxy_k8s_timeout_client: 30000  # Adjust for slow clients
haproxy_k8s_check_interval: 2000  # Health check frequency
```

---

## Monitoring

### HAProxy Stats Socket

Access stats:
```bash
sudo socat readline /run/haproxy/admin.sock
echo "show stat" | sudo socat readline /run/haproxy/admin.sock
```

### Systemd Status

```bash
systemctl status haproxy
journalctl -u haproxy -f
```

### Verification Playbook

Run periodic checks:
```bash
ansible-playbook playbooks/haproxy_verify.yaml --tags verify --ask-become-pass
```

---

## Tags

All playbooks support tags:

- `haproxy` - HAProxy operations
- `kubernetes` - Kubernetes setup
- `loadbalancer` - Load balancing
- `verify` - Verification tasks
- `test` - Testing/verification

---

## Future Enhancements

Possible improvements:

1. **Add Prometheus metrics**
   - Export HAProxy metrics to Prometheus
   - Use HAProxy exporter sidecar

2. **Add health check endpoint**
   - HTTP endpoint for load balancer health
   - Example: `http://[load-balancer-hostname]:[k8s-api-port]/healthz`

3. **Add alerting**
   - Email/webhook alerts on backend failures
   - Integration with existing monitoring

4. **Multi-master support**
   - Add `[secondary-control-plane-hostname]` to `vault_k8s_control_planes`
   - HAProxy will automatically load balance across all

5. **TLS termination at HAProxy**
   - Offload SSL from control planes
   - Reduces control plane CPU usage

---

## Related Documentation

- **AGENTS.md** - Ansible best practices and conventions
- **playbooks/haproxy_verify.yaml** - Verification playbook
- **roles/haproxy_k8s/README.md** - HAProxy role documentation
- **roles/haproxy_verify/README.md** - Verification role documentation

---

## Rollback

To revert changes:

1. **Restore original vault variables** (if you have backup):
   - Change ports back to [old-api-port] if needed
   - Revert control plane configurations

2. **Stop HAProxy:**
   ```bash
   sudo systemctl stop haproxy
   sudo systemctl disable haproxy
   ```

3. **Move nginx back to original ports:**
   ```bash
   # Update nginx config
   sed -i 's/custom HTTP port/standard HTTP port/g' /etc/nginx/sites-enabled/[service-domain]
   sed -i 's/custom HTTPS port/standard HTTPS port/g' /etc/nginx/sites-enabled/[service-domain]
   sudo systemctl restart nginx
   ```

3. **Move nginx back to original ports:**
   ```bash
   # Update nginx config
   sed -i 's/custom HTTP port/standard HTTP port/g' /etc/nginx/sites-enabled/[service-domain]
   sed -i 's/custom HTTPS port/standard HTTPS port/g' /etc/nginx/sites-enabled/[service-domain]
   sudo systemctl restart nginx
   ```

3. **Move nginx back to original ports:**
   ```bash
   # Update nginx config
   sed -i 's/[nginx-http-port]/[standard-http-port]/g' /etc/nginx/sites-enabled/[service-domain]
   sed -i 's/[nginx-https-port]/[standard-https-port]/g' /etc/nginx/sites-enabled/[service-domain]
   sudo systemctl restart nginx
   ```

4. **Restore old HAProxy config:**
   ```bash
   sudo cp /etc/haproxy/haproxy.cfg.backup.* /etc/haproxy/haproxy.cfg
   sudo systemctl restart haproxy
   ```

---

## Support

For issues or questions:

1. Check verification playbook output
2. Review logs: `journalctl -u haproxy -n 100`
3. Check connectivity: `nc -zv [control-plane-ip] [k8s-api-port]`
4. Review documentation in `roles/haproxy_k8s/README.md`

---

**End of Documentation**
