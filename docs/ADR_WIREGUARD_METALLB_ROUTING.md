# ADR: WireGuard + MetalLB Multi-Site VIP Routing

**Status:** Accepted  
**Date:** 2026-03-06  
**Context:** Multi-site Kubernetes ingress over WireGuard mesh VPN

## Problem

MetalLB assigns VIPs from a shared `/24` pool. Both bay and vas sites have
workers that advertise VIPs via BGP. WireGuard uses AllowedIPs as a
cryptokey routing table with longest-prefix-match (LPM). Without explicit
routing rules, all VIP traffic follows the `/24` catch-all to a single
bay-site worker, even when the VIP belongs to a vas-site service.

### Root cause of the multi-site ingress outage

A bay-site worker had `[metallb-pool-cidr]/24` in its AllowedIPs. This
catch-all captured ALL MetalLB VIP traffic, overriding BGP `/32` routes
for vas-site VIPs. HAProxy could not reach vas Traefik because WireGuard
routed the traffic to the wrong site.

## Decision

Use the **/24 catch-all + /32 override** pattern:

```
Bay worker AllowedIPs:  [worker-vpn-ip]/32, [metallb-pool-cidr]/24
Vas worker AllowedIPs:  [worker-vpn-ip]/32, [vas-metallb-vip]/32
```

### How it works

1. The **first bay-site worker** peer gets the MetalLB pool `/24` as a
   catch-all. This allows WireGuard to route any VIP traffic that doesn't
   have a more specific match.

2. Each **vas-site VIP** gets a `/32` override on the **first vas-site
   worker** peer. WireGuard LPM ensures `/32` beats `/24`, so vas VIPs
   route to the vas worker.

3. **Pod CIDR** is NOT added to any peer. Workers apply iptables
   MASQUERADE (PostUp) which rewrites pod reply source IPs to the
   worker's own WireGuard `/32` IP.

4. The **DB route** is only added to non-DB peers when the DB host has
   no dedicated WireGuard peer entry.

### Routing table example

```
Destination         Peer           Match rule
[vas-metallb-vip]   vas-worker1    /32 override (longest prefix wins)
[bay-metallb-vip]   bay-worker2    /24 catch-all
[any-other-vip]     bay-worker2    /24 catch-all (default path)
```

## Implementation

### Filter plugin: `build_peers_extra_cidrs`

Located at `filter_plugins/wg_routing_filters.py`. Computes per-peer
extra AllowedIPs based on group membership:

- MetalLB `/24` -> first worker peer encountered
- DB route -> non-DB peers when DB has no dedicated peer

Vas VIP `/32` overrides are injected separately in `wireguard_manage.yaml`
using `vault_wg_vas_vip_overrides`.

### Adding a new VIP for a vas-site service

1. Deploy the service on a vas-site worker with MetalLB
2. Note the assigned VIP (e.g., `[new-vip-ip]`)
3. Add `[new-vip-ip]/32` to `vault_wg_vas_vip_overrides` in vault:
   ```yaml
   vault_wg_vas_vip_overrides:
     - "[existing-vas-vip]/32"
     - "[new-vip-ip]/32"     # <-- add this
   ```
4. Run `wireguard_manage.yaml` to apply the new AllowedIPs
5. Run `wireguard_audit.yaml` to verify no conflicts

### Adding a new VIP for a bay-site service

No action needed. The `/24` catch-all already covers all bay-site VIPs.

## Verification

- `wireguard_audit.yaml` — detects AllowedIPs drift, duplicate CIDRs,
  and missing `/32` overrides
- `tests/test_wg_routing_filters.py` — unit tests for the filter plugin
- `wireguard_verify.yaml` — connectivity and handshake health checks

## Consequences

- Every vas-site VIP **must** be added to `vault_wg_vas_vip_overrides`
  or it will silently route to the bay site
- The `build_peers_extra_cidrs` filter assigns MetalLB to the **first**
  worker peer in the list, so peer ordering matters
- The audit playbook catches drift but only when run manually or in CI
