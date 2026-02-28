# HAProxy Kubernetes API

This role configures HAProxy for Kubernetes API server load balancing,
optional HTTP/HTTPS ingress forwarding, and optional mail server (SMTP/IMAP)
forwarding to the Kubernetes cluster via MetalLB LoadBalancer IPs.

## Purpose

- Configure HAProxy as TCP load balancer for Kubernetes API server
- Support single or multiple control plane nodes
- Health checks for API server backend(s)
- Forward HTTP/HTTPS ingress traffic to a MetalLB BGP VIP (optional)
- Forward SMTP/SMTPS/Submission/IMAPS mail traffic to a MetalLB LB IP (optional)
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

# Mail Server Load Balancing (SMTP/IMAP to Kubernetes via MetalLB)
# Set vault_haproxy_mail_enabled: true to activate; backend IP is the
# MetalLB IP assigned to the stalwart-mail-lb LoadBalancer Service.
vault_haproxy_mail_enabled: false
vault_haproxy_mail_smtp_port: 25
vault_haproxy_mail_smtps_port: 465
vault_haproxy_mail_submission_port: 587
vault_haproxy_mail_imaps_port: 993
vault_haproxy_mail_backend_ip: "[mail-metallb-ip]"
vault_haproxy_mail_backend_smtp_port: 25
vault_haproxy_mail_backend_smtps_port: 465
vault_haproxy_mail_backend_submission_port: 587
vault_haproxy_mail_backend_imaps_port: 993
# vault_haproxy_mail_timeout_client: 300000   # 5 min — SMTP transactions can be slow
# vault_haproxy_mail_timeout_server: 300000
# vault_haproxy_mail_proxy_protocol: false    # Keep false — Stalwart reads client IP natively
```

### PROXY Protocol and externalTrafficPolicy

When `vault_haproxy_ingress_proxy_protocol: true` is set, HAProxy appends a
PROXY v2 header to every ingress connection. Traefik reads this header to
obtain the real client IP.

**Important:** use `vault_traefik_external_traffic_policy: Cluster` (not
`Local`) alongside PROXY Protocol. With `Local`, kube-proxy only forwards
traffic on nodes that host the Traefik pod. The MetalLB VIP subnet
(`[metallb-vip-cidr]`) is routed through WireGuard via the BGP-announcing node,
and that node changes whenever the Traefik pod reschedules. `Cluster` policy
lets any node forward to the Traefik pod regardless of placement, avoiding
silent packet drops. Real client IP is preserved by the PROXY header, not by
`externalTrafficPolicy: Local`.

### Mail PROXY Protocol

`vault_haproxy_mail_proxy_protocol` defaults to `false` and should remain
`false` for Stalwart Mail Server. Stalwart reads the real client IP natively
via the TCP connection; enabling PROXY protocol here would require Stalwart to
be explicitly configured to accept it, and is not needed for correct IP
logging.

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

**Mail Server Forwarding (optional):**

```
Internet (SMTP/SMTPS/Submission/IMAPS)
    → HAProxy ([haproxy-public-ip]:25/465/587/993)
    → MetalLB LoadBalancer IP ([mail-metallb-ip])
    → Stalwart Mail Pod (Kubernetes)
```

- Enabled via `vault_haproxy_mail_enabled: true`
- Backend IP is the MetalLB IP of the `stalwart-mail-lb` LoadBalancer Service
- UFW rules for mail ports are automatically applied when enabled (Debian/Ubuntu)
- Post-deploy verification checks that HAProxy is listening and the backend is reachable
- Deployment order: HAProxy mail config → Stalwart Mail Server in Kubernetes

## Files

- `roles/haproxy_k8s/defaults/main.yaml` - Default variables
- `roles/haproxy_k8s/tasks/main.yaml` - Main tasks
- `roles/haproxy_k8s/templates/haproxy.cfg.j2` - HAProxy config template
- `roles/haproxy_k8s/handlers/main.yaml` - Service handlers
- `roles/haproxy_k8s/meta/main.yaml` - Role metadata
- `haproxy_k8s.yaml` - Main playbook
