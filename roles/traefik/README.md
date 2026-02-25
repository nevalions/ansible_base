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
# externalTrafficPolicy for the Traefik LoadBalancer service.
# Must be "Cluster" when PROXY Protocol is enabled — see note below.
vault_traefik_external_traffic_policy: "Cluster"

# Enable PROXY Protocol v2 support (HAProxy must send send-proxy-v2)
vault_traefik_proxy_protocol_enabled: true

# WireGuard subnet (or any CIDR) that HAProxy connects from
vault_traefik_proxy_protocol_trusted_ips:
  - "9.11.0.0/24"
```

### externalTrafficPolicy: Cluster vs Local

When Traefik runs behind HAProxy with PROXY Protocol enabled, set
`vault_traefik_external_traffic_policy: Cluster`.

**Why not `Local`?**  
With `Local`, MetalLB only announces the VIP from nodes where Traefik has a
local endpoint. The MetalLB VIP subnet is routed through WireGuard to
whichever node BGP-advertises it. If that BGP peer's WireGuard AllowedIPs
for the VIP subnet does not match the node Traefik currently runs on, packets
are silently dropped:

```
HAProxy → WireGuard (AllowedIPs routes VIP to node A)
         → node A has no local Traefik endpoint (externalTrafficPolicy:Local)
         → KUBE-SVL chain empty → packet dropped
```

With `Cluster`, any node (including the one WireGuard routes to) forwards
the packet to the Traefik pod via the pod overlay network. Real client IP is
preserved by the PROXY v2 header, not by `externalTrafficPolicy: Local`.
