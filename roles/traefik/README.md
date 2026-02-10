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
