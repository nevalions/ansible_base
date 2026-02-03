# HAProxy Verification Role

Verify HAProxy configuration and service status for Kubernetes API load balancing on `[haproxy-hostname]`.

## Requirements

- Ansible 2.16+
- Target host: `[haproxy-hostname]` ([haproxy-ip])
- HAProxy installed
- UFW firewall (optional, checks if active)

## Role Variables

### Required Variables

None - all variables have defaults.

### Optional Variables

- `haproxy_k8s_frontend_port`: HAProxy frontend port (default: `6443`)
- `vault_k8s_control_planes`: List of control plane backends
- `vault_wg_network_cidr`: WireGuard network CIDR for firewall checks
- `verify_timeout_seconds`: Timeout for checks (default: `30`)
- `verify_retry_count`: Retry count for checks (default: `3`)
- `verify_sleep_seconds`: Sleep between retries (default: `2`)

## Dependencies

None

## Example Usage

### Run Full Verification

```bash
ansible-playbook playbooks/haproxy_verify.yaml --ask-become-pass
```

### Run with Tags

```bash
# Only verify HAProxy service
ansible-playbook playbooks/haproxy_verify.yaml --tags service --ask-become-pass

# Only verify configuration
ansible-playbook playbooks/haproxy_verify.yaml --tags configuration --ask-become-pass

# Only verify firewall
ansible-playbook playbooks/haproxy_verify.yaml --tags firewall --ask-become-pass
```

### With Custom Variables

```bash
ansible-playbook playbooks/haproxy_verify.yaml \
  -e "haproxy_k8s_frontend_port=7443" \
  --ask-become-pass
```

## Checks Performed

### 1. Service Status
- HAProxy systemd service active state
- HAProxy systemd service enabled state
- Service PIDs and details

### 2. Configuration
- Config file exists (`/etc/haproxy/haproxy.cfg`)
- Config syntax valid (`haproxy -c -f /etc/haproxy/haproxy.cfg`)
- Frontend port configured
- Backend servers defined
- Config file permissions

### 3. Listening Port
- HAProxy listening on expected port (default: 6443)
- Binding to all interfaces (0.0.0.0 or *)

### 4. Firewall
- UFW status (active/inactive)
- Port 6443 allowed from WireGuard network
- Port 6443 allowed from localhost

### 5. Backend Connectivity
- TCP connection test to all configured backends
- Ping test to backend hosts
- Summary of reachable/unreachable backends

## Behavior

### Non-Failing Checks
All checks use `ignore_errors: true` and `failed_when: false`. The role will:
- Continue even if a check fails
- Report all findings
- Show a summary at the end
- Never cause playbook failure

This design allows verification even when:
- Kubernetes API is not yet running on backends
- Firewall is temporarily inactive
- Service is in transitional state

### Example Output

```
TASK [Display verification report] ***
ok: [[haproxy-ip]] => 
  msg:
    - ""
    - "=========================================="
    - "  HAProxy Verification Report"
    - "  Host: [haproxy-ip]"
    - "=========================================="
    - ""
    - "Service Status:"
    - "  HAProxy service: ACTIVE (running)"
    - "  HAProxy enabled: YES"
    - ""
    - "Configuration:"
    - "  Config file: EXISTS"
    - "  Config syntax: VALID"
    - "  Frontend port 6443: CONFIGURED"
    - "  Configured backends: 1"
    - ""
    - "Network:"
    - "  Listening on port 6443: YES"
    - "  UFW status: ACTIVE"
    - "  Port 6443 from [vpn-network-cidr]: ALLOWED"
    - "  Port 6443 from localhost: ALLOWED"
    - ""
    - "Backend Connectivity:"
    - "  Total backends: 1"
    - "  Reachable: 0"
    - "  Unreachable: 1"
    - ""
    - "=========================================="
    - "  Summary: 5/6 checks passed"
    - "  Status: WARNINGS"
    - "=========================================="
```

## Tags

- `haproxy`: Main tag for HAProxy operations
- `verify`: Tag for all verification tasks
- `test`: Tag for testing/verification
- `service`: Service status checks
- `configuration`: Configuration validation
- `firewall`: Firewall rule checks

## Troubleshooting

### Backend Unreachable
Normal if Kubernetes API is not running yet. Backends will become reachable when:
- Control plane is initialized with `kubeadm init`
- Kubernetes API server is running on port 6443
- WireGuard network is operational

### UFW Not Active
Verification will continue but firewall checks will show as N/A. This is acceptable if:
- Alternative firewall (iptables, nftables) is used
- Host is in trusted network
- Testing environment without firewall

### Config Syntax Invalid
HAProxy will fail to start with invalid configuration:
- Check template: `roles/haproxy_k8s/templates/haproxy.cfg.j2`
- Run playbook: `ansible-playbook playbooks/haproxy_k8s.yaml`

## License

MIT

## Author

linroot
