# Traefik Role

Installs and configures Traefik via Helm.

## TLS: Two Supported Patterns

### 1) Recommended: cert-manager issues certs (no Traefik ACME storage)

In Kubernetes, best practice is to let **cert-manager** obtain/renew certificates and store them as
**Kubernetes TLS Secrets**, and then have Traefik serve those secrets.

Why:
- Traefik OSS ACME storage is file-based (`acme.json`). Without persistence, cert state is lost on pod recreation.
- Traefik OSS does not support distributed ACME storage in Kubernetes; the Traefik docs recommend cert-manager for HA.

How:
- Install cert-manager: `kuber_cert_manager_install.yaml`
- Create `Certificate` resources (or use ingress-shim where appropriate)
- Reference the resulting secret in your `IngressRoute` via `spec.tls.secretName`

Traefik settings:
- Set `vault_traefik_certresolver_enabled: false`

Optional cleanup after switching:
- Ensure Traefik is not configured with any ACME flags/values (no `certResolver`, no `certificatesResolvers.*`).
- This prevents Traefik from trying to manage certificates itself.

### 2) Traefik issues certs itself (ACME)

This is supported, but you must persist `traefik_acme_storage` (default `/data/acme.json`) or you risk
rate-limits/outages on pod reschedule/recreate.

Recommended:
- Enable persistence for `/data` using the Helm chart PVC options (see `vault_traefik_persistence_*`).

## Variables

See `roles/traefik/defaults/main.yaml`.

Key vault variables:

```yaml
# Deployment kind: "Deployment" (default) or "DaemonSet"
# DaemonSet is recommended when using externalTrafficPolicy: Local
# so that every node that BGP-advertises the MetalLB VIP has a local
# Traefik pod (prevents KUBE-SVL packet drops).
vault_traefik_deployment_kind: "DaemonSet"

# Replica count — only applies when vault_traefik_deployment_kind == "Deployment"
vault_traefik_replica_count: 2

# externalTrafficPolicy for the Traefik LoadBalancer service.
vault_traefik_external_traffic_policy: "Local"

# Enable PROXY Protocol v2 support (HAProxy must send send-proxy-v2)
vault_traefik_proxy_protocol_enabled: true

# WireGuard subnet (or any CIDR) that HAProxy connects from
vault_traefik_proxy_protocol_trusted_ips:
  - "[wireguard-network-cidr]"
```

### Deployment kind: Deployment vs DaemonSet

**DaemonSet** (recommended for this cluster):

Use `vault_traefik_deployment_kind: DaemonSet` when `externalTrafficPolicy: Local`
is set. Traefik runs on every worker node. MetalLB (BGP mode) announces the VIP
from every node that has a local Traefik pod — any worker handling the connection
is correct.

The rollout wait task automatically switches to `ds/traefik` instead of
`deploy/traefik` when `DaemonSet` is selected.

**Deployment** (default):

Use when replica scheduling is preferred over per-node presence. With `externalTrafficPolicy: Cluster`
(required for Deployment + PROXY Protocol), kube-proxy forwards to any available
replica regardless of which node received the packet.

### externalTrafficPolicy: Cluster vs Local

**With DaemonSet + Local:**  
Every worker has a Traefik pod. MetalLB announces the VIP from all workers.
WireGuard on HAProxy must route the MetalLB CIDR to one worker peer
(`vault_wg_peers_extra_cidrs`). Worker MASQUERADE rules (PostUp) SNAT
pod reply traffic to the worker's own wg99 IP so HAProxy does not see raw
pod IPs (`10.244.x.x`).

**With Deployment + Cluster (legacy):**  
`externalTrafficPolicy: Cluster` allows any node to receive and proxy the packet.
Real client IP is preserved by the PROXY v2 header, not by `Local`. The MetalLB
pool CIDR must be in a peer's WireGuard AllowedIPs — routing the VIP subnet via
a WireGuard link-route overrides FRR BGP routes (lower administrative distance),
so assignment must target the correct worker.

```
HAProxy → WireGuard (AllowedIPs routes VIP to node A)
         → node A has no local Traefik endpoint (externalTrafficPolicy:Local)
         → KUBE-SVL chain empty → packet dropped   ← avoided with DaemonSet
```
