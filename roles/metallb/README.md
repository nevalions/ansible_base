# metallb

Install and configure MetalLB for Kubernetes clusters.

This repository primarily targets WireGuard/L3 clusters, so the default/recommended mode is BGP.

## What It Does

- Applies the upstream MetalLB manifest (pinned by version)
- Waits for controller and speaker to be Ready
- Applies:
  - `IPAddressPool`
  - `BGPPeer` and `BGPAdvertisement` (BGP mode)
  - or `L2Advertisement` (layer2 mode)

## Required Variables (vault)

Set these in `vault_secrets.yml` (placeholders shown):

```yaml
vault_metallb_enabled: true
vault_metallb_version: "v0.14.9"
vault_metallb_mode: "bgp"

vault_metallb_pool_name: "wg-lb-pool"
vault_metallb_pool_cidr: "[metallb-pool-cidr]/24"

vault_metallb_bgp_my_asn: "[metallb-my-asn]"
vault_metallb_bgp_peers:
  - name: "bgp-router-1"
    peer_address: "[bay-bgp-wg-ip]"
    peer_asn: "[router-asn]"

# Optional: also advertise an aggregate prefix (e.g., /24) in addition to per-service /32
vault_metallb_bgp_advertise_per_service: true
vault_metallb_bgp_aggregate_enabled: true
vault_metallb_bgp_aggregate_length_v4: 24
```

## Usage

Example playbook: `kuber_metallb_install.yaml`

```bash
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml --tags metallb
```
