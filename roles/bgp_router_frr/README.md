# bgp_router_frr

Configure a Linux host as a BGP router using FRR.

This role is intended to act as the BGP peer for MetalLB in Kubernetes bare-metal/WireGuard (L3) environments.

## What It Does

- Installs FRR packages
- Enables `zebra` and `bgpd`
- Renders `/etc/frr/frr.conf` with a strict import policy for the MetalLB pool
- Optionally opens TCP/179 with UFW (only when UFW is installed and active)

## Required Variables (vault)

Set these in `vault_secrets.yml` (placeholders shown):

```yaml
vault_bgp_router_asn: "[router-asn]"
vault_bgp_router_router_id: "[bay-bgp-wg-ip]"
vault_bgp_router_listen_interface: "[wg-interface]"
vault_bgp_router_update_source: "[wg-interface]"

vault_metallb_pool_cidr: "[metallb-pool-cidr]/24"

vault_bgp_router_neighbors:
  - address: "[k8s-node-wg-ip]"
    asn: "[metallb-my-asn]"
```

## Usage

Example playbook: `bgp_router_manage.yaml`

```bash
ansible-playbook -i hosts_bay.ini bgp_router_manage.yaml --tags bgp
```
