# BGP HA Operations Guide (FRR + Keepalived)

This guide explains how to deploy, verify, test, and remove the BGP high-availability (HA) pair used for MetalLB BGP peering.

For architecture and traffic flows, see `docs/BGP_HA_ARCHITECTURE.md`.

## Overview

This repository supports running two BGP routers with:

- FRR for BGP peering with MetalLB speakers
- Keepalived (VRRP) to float a BGP VIP between the routers

MetalLB peers with both router *node IPs* (not the VIP). Upstream traffic targets the VIP.

## Inventory Requirements

- `[bgp_routers]` group with both BGP router hosts
- Kubernetes groups used by verification/testing:
  - `planes_all`
  - `workers_all`

These are inventory group names (safe to reference in playbooks).

## Vault Variables

Start from `vault_secrets.example.yml` and provide real values in your local `vault_secrets.yml`.

Minimum required for deployment:

- `vault_bgp_router_asn`
- `vault_bgp_router_router_id`
- `vault_bgp_router_neighbors`
- `vault_bgp_keepalived_vip`
- `vault_bgp_routers`

MetalLB should be configured to peer with both routers (see `vault_metallb_bgp_peers` in `vault_secrets.example.yml`).

## Deploy

Deploy FRR + Keepalived (serially, one router at a time):

```bash
ansible-playbook -i [your-inventory] bgp_ha_deploy.yaml
```

Target only one component if needed:

```bash
ansible-playbook -i [your-inventory] bgp_ha_deploy.yaml --tags frr
ansible-playbook -i [your-inventory] bgp_ha_deploy.yaml --tags keepalived
```

## Verify

Run full verification (routers + K8s node reachability to VIP):

```bash
ansible-playbook -i [your-inventory] bgp_ha_verify.yaml
```

Only test K8s node connectivity to the VIP:

```bash
ansible-playbook -i [your-inventory] bgp_ha_verify.yaml --tags k8s_connectivity
```

Router-side commands you will commonly use:

```bash
vtysh -c "show bgp summary"
vtysh -c "show ip route bgp"
systemctl status keepalived
ip addr show [wg-interface]
```

## Test (End-to-End)

Run the connectivity test suite:

```bash
ansible-playbook -i [your-inventory] bgp_ha_test.yaml
```

Notes:

- The test suite expects MetalLB to be installed and at least one LoadBalancer service to exist.
- Some tests run from a host/group intended to represent an "external client". Adjust the inventory target in `bgp_ha_test.yaml` to match your environment.

## Remove

Remove Keepalived and FRR configuration:

```bash
ansible-playbook -i [your-inventory] bgp_ha_remove.yaml
```

Optional removal flags:

```bash
ansible-playbook -i [your-inventory] bgp_ha_remove.yaml -e remove_packages=true
ansible-playbook -i [your-inventory] bgp_ha_remove.yaml -e keep_frr=true
```

## Common Failure Modes

- VIP not reachable from K8s nodes: WireGuard allowed-ips/routing missing; run `wireguard_manage.yaml`.
- No established BGP sessions: verify MetalLB BGP configuration and neighbor addressing.
- VRRP flaps: ensure router IDs/passwords and unicast peer addresses are correct; verify both routers can reach each other on the VRRP path.
