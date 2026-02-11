# Ansible Configuration Repository

Ansible playbooks + roles for managing servers and clusters (Kubernetes, WireGuard, DNS, HAProxy, Keepalived, upgrades, workstation setup).

Security is the first constraint in this repo.

- Read and follow `SECURITY.md` before editing or committing.
- Policy highlights: no real SSH usernames, IPs, ports, hostnames, CIDRs, passwords, keys, or tokens (use placeholders).
- Inventory and local config are intentionally gitignored.
- Local topology/scratch docs with real infrastructure values must stay gitignored (for example `docs/*.local.txt`).

## Quick Start

Prereqs:

- Ansible installed
- SSH key-based access to your hosts
- Local inventory file (gitignored) matching your environment
- Vault secrets file created from the example

1) Create vault secrets from the example:

```bash
cp vault_secrets.example.yml vault_secrets.yml
# edit vault_secrets.yml (placeholders -> your real values)
```

2) Ensure vault password tooling is set up (see `SECURITY.md`):

- Default is `vault_password_file = ./vault_password_client.sh` in `ansible.cfg`.

3) Run a playbook:

```bash
ansible-playbook kuber_cluster_deploy.yaml
```

Notes:

- `ansible.cfg` defaults the inventory to `./hosts_bay.ini` (which is gitignored). Override with `-i` as needed.
- Logging is intentionally disabled by default to avoid leaking secrets/topology (see `ansible.cfg` and `SECURITY.md`).

## Common Workflows

- Kubernetes cluster deploy/reset: `kuber_cluster_deploy.yaml`, `kuber_cluster_reset.yaml`
- WireGuard management: `wireguard_manage.yaml`
- BGP HA for MetalLB (FRR + Keepalived): `bgp_ha_deploy.yaml`, `bgp_ha_verify.yaml`, `bgp_ha_test.yaml`, `bgp_ha_remove.yaml`
- DNS deploy/remove: `dns_full_deployment_remove.yaml`, `dns_server_remove.yaml`, `dns_client_remove.yaml`
- HAProxy K8s API load balancer: `playbooks/haproxy_start_and_verify.yaml`, `playbooks/haproxy_verify.yaml`, `haproxy_k8s_remove.yaml`
- PostgreSQL 17 in Docker:
  - Deploy/update: `postgres_docker_manage.yaml`
  - Verify from Kubernetes test pod: `postgres_docker_verify.yaml`
  - Remove: `postgres_docker_remove.yaml`

## PostgreSQL Docker Quick Commands

```bash
# Deploy or update PostgreSQL 17 container
ansible-playbook -i hosts_bay.ini postgres_docker_manage.yaml

# Verify DB connectivity from a Kubernetes test pod
ansible-playbook -i hosts_bay.ini postgres_docker_verify.yaml

# Remove PostgreSQL container (keeps volume data by default)
ansible-playbook -i hosts_bay.ini postgres_docker_remove.yaml
```

Notes:

- PostgreSQL settings come from `vault_secrets.yml` (`vault_postgres_*` keys).
- UFW rules are managed only when UFW is installed and active.
- Keep secrets only in encrypted vault files; never commit real passwords, keys, or host-specific credentials.

## Documentation

- Security and secret handling: `SECURITY.md`
- Kubernetes:
  - Setup guide: `KUBERNETES_SETUP.md`
  - Quick reference: `KUBERNETES_QUICKREF.md`
- HAProxy K8s API load balancer: `HAPROXY_K8S_IMPLEMENTATION.md`, `roles/haproxy_k8s/README.md`, `roles/haproxy_verify/README.md`
- WireGuard:
  - Setup: `WIREGUARD_SETUP.md`
  - Add node: `WIREGUARD_ADD_NODE.md`
  - Full implementation and troubleshooting: `WIREGUARD_IMPLEMENTATION.md`
- BGP HA architecture: `docs/BGP_HA_ARCHITECTURE.md`
- BGP HA operations guide: `docs/BGP_HA_GUIDE.md`
- SSH agent quickref: `SSH_AGENT_QUICKREF.md`

## Contributing / Repo Conventions

- Coding + Ansible conventions: `AGENTS.md`
- Git hooks (sensitive data checks): `scripts/githooks/README.md`
