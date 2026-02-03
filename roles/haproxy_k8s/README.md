# HAProxy Kubernetes API

This role configures HAProxy for Kubernetes API server load balancing.

## Purpose

- Configure HAProxy as TCP load balancer for Kubernetes API server
- Support single or multiple control plane nodes
- Health checks for API server backend(s)

## Variables

All sensitive variables are stored in `vault_secrets.yml`:

```yaml
# HAProxy Kubernetes API Configuration
vault_haproxy_k8s_frontend_port: "[haproxy-frontend-port]"
vault_haproxy_k8s_backend_port: "[haproxy-backend-port]"
vault_haproxy_k8s_backend_ip: "[control-plane-ip]"

# Kubernetes Network Configuration
vault_k8s_pod_subnet: "[pod-network-cidr]"
vault_k8s_service_subnet: "[service-network-cidr]"
```

## Usage

```bash
# Configure HAProxy for Kubernetes API
ansible-playbook -i hosts_bay.ini haproxy_k8s.yaml --tags haproxy

# Full deployment sequence:
# 1. Install Kubernetes packages
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes

# 2. Configure HAProxy
ansible-playbook -i hosts_bay.ini haproxy_k8s.yaml

# 3. Initialize control plane
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml

# 4. Join workers
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml

# 5. Verify cluster
ansible-playbook -i hosts_bay.ini kuber_verify.yaml
```

## Architecture

**Multi-Control Plane with VIP:**
- Workers connect to VIP: `[vip-address]:6443`
- Keepalived on [haproxy-hostname] manages VIP failover
- DNAT: VIP:6443 → active plane's HAProxy:7443
- Each control plane has HAProxy:7443 → localhost:6443
- All communication via WireGuard network

**Adding More Control Planes:**
1. Add new control plane to inventory (`[planes_all]`)
2. Add WireGuard peer configuration
3. Update `vault_k8s_control_planes` in vault_secrets.yml
4. Re-run `keepalived_manage.yaml` and `haproxy_k8s.yaml`

## Files

- `roles/haproxy_k8s/defaults/main.yaml` - Default variables
- `roles/haproxy_k8s/tasks/main.yaml` - Main tasks
- `roles/haproxy_k8s/templates/haproxy.cfg.j2` - HAProxy config template
- `roles/haproxy_k8s/handlers/main.yaml` - Service handlers
- `roles/haproxy_k8s/meta/main.yaml` - Role metadata
- `haproxy_k8s.yaml` - Main playbook
