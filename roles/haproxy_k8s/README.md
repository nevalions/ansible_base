# HAProxy Kubernetes API

This role configures HAProxy for Kubernetes API server load balancing and
optional HTTP/HTTPS ingress forwarding to the Kubernetes cluster via a
MetalLB BGP VIP.

## Purpose

- Configure HAProxy as TCP load balancer for Kubernetes API server
- Support single or multiple control plane nodes
- Health checks for API server backend(s)
- Forward HTTP/HTTPS ingress traffic to a MetalLB BGP VIP (optional)
- Support PROXY Protocol v2 for real client IP preservation (optional)

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

# Ingress forwarding (HTTP/HTTPS → MetalLB BGP VIP)
vault_haproxy_ingress_enabled: true
vault_haproxy_ingress_backend_ip: "[bgp-vip-address]"
vault_haproxy_ingress_http_port: 80
vault_haproxy_ingress_https_port: 443
vault_haproxy_ingress_backend_http_port: 80
vault_haproxy_ingress_backend_https_port: 443

# PROXY Protocol v2 — send real client IP to Traefik
# Requires Traefik to be configured with vault_traefik_proxy_protocol_enabled: true
# and vault_traefik_external_traffic_policy: Cluster
vault_haproxy_ingress_proxy_protocol: true
```

### PROXY Protocol and externalTrafficPolicy

When `vault_haproxy_ingress_proxy_protocol: true` is set, HAProxy appends a
PROXY v2 header to every ingress connection. Traefik reads this header to
obtain the real client IP.

**Important:** use `vault_traefik_external_traffic_policy: Cluster` (not
`Local`) alongside PROXY Protocol. With `Local`, kube-proxy only forwards
traffic on nodes that host the Traefik pod. The MetalLB VIP subnet
(`11.11.0.0/24`) is routed through WireGuard via the BGP-announcing node,
and that node changes whenever the Traefik pod reschedules. `Cluster` policy
lets any node forward to the Traefik pod regardless of placement, avoiding
silent packet drops. Real client IP is preserved by the PROXY header, not by
`externalTrafficPolicy: Local`.

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
