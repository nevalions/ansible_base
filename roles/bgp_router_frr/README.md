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
vault_bgp_router_router_id: "[bay-bgp-wg-ip]"  # Optional if using bgp_routers list
vault_bgp_router_listen_interface: "[wg-interface]"
vault_bgp_router_update_source: "[wg-interface]"

vault_metallb_pool_cidr: "[metallb-pool-cidr]/24"

vault_bgp_router_neighbors:
  - address: "[k8s-node-wg-ip]"
    asn: "[metallb-my-asn]"
```

### Auto-Derived Router ID (BGP HA)

When running multiple BGP routers, you can define a shared `bgp_routers` list in your vault.
The role will automatically derive each router's `router_id` from its `wireguard_ip`:

```yaml
vault_bgp_routers:
  - name: "[bgp-router-1-hostname]"
    wireguard_ip: "[bgp-router-1-wg-ip]"
  - name: "[bgp-router-2-hostname]"
    wireguard_ip: "[bgp-router-2-wg-ip]"
```

The role matches the current host by `inventory_hostname`, `ansible_host`, or group membership,
then uses the corresponding `wireguard_ip` as the BGP router ID. This eliminates the need to
set `vault_bgp_router_router_id` per-host and ensures consistency across HA router pairs.

## Usage

Example playbook: `bgp_router_manage.yaml`

```bash
ansible-playbook -i hosts_bay.ini bgp_router_manage.yaml --tags bgp
```
