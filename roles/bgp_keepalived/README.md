# bgp_keepalived

Keepalived VRRP for FRR BGP router high availability.

This role provides a floating VIP between two FRR BGP routers using VRRP, enabling seamless failover for BGP peering with MetalLB in Kubernetes clusters.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │            Upstream Gateway                 │
                    │     Routes to BGP VIP: [bgp-vip-address]    │
                    └──────────────────────┬──────────────────────┘
                                           │
                                           ▼
                         ┌─────────────────────────────────────┐
                         │      Floating BGP VIP (VRRP)        │
                         │        [bgp-vip-address]            │
                         └─────────────────┬───────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
                    ▼                                             ▼
         ┌──────────────────────┐                   ┌──────────────────────┐
         │   FRR Router #1      │                   │   FRR Router #2      │
         │   [bgp-router-1-ip]  │◄────VRRP────────►│   [bgp-router-2-ip]  │
         │   Priority: 150      │                   │   Priority: 100      │
         │   State: MASTER      │                   │   State: BACKUP      │
         └──────────┬───────────┘                   └──────────┬───────────┘
                    │                                          │
                    │         eBGP Peering (TCP/179)           │
                    └──────────────────┬───────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
     ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
     │ K8s Plane   │            │ K8s Worker1 │            │ K8s Worker2 │
     │ MetalLB     │            │ MetalLB     │            │ MetalLB     │
     │ Speaker     │            │ Speaker     │            │ Speaker     │
     └─────────────┘            └─────────────┘            └─────────────┘
```

## What It Does

- Installs keepalived
- Deploys a BGP health check script (`/usr/local/bin/check_bgp.sh`)
- Configures VRRP between BGP routers with BGP session tracking
- VIP floats to healthy router when BGP sessions fail
- Supports WireGuard interfaces (unicast VRRP)

## Required Variables (vault)

Set these in `vault_secrets.yml` (placeholders shown):

```yaml
# BGP Router VIP Configuration
vault_bgp_keepalived_vip: "[bgp-vip-address]"
vault_bgp_keepalived_vip_cidr: "32"
vault_bgp_keepalived_vip_interface: "wg99"
vault_bgp_keepalived_password: "[bgp-keepalived-password]"
vault_bgp_keepalived_router_id: "52"  # Must differ from K8s VIP router_id
vault_bgp_keepalived_script_user: "[admin-username]"

# BGP Routers list
vault_bgp_routers:
  - name: "[bgp-router-1-hostname]"
    wireguard_ip: "[bgp-router-1-wg-ip]"
    priority: 150  # Higher = MASTER
  - name: "[bgp-router-2-hostname]"
    wireguard_ip: "[bgp-router-2-wg-ip]"
    priority: 100  # Lower = BACKUP
```

## Health Check

The role deploys `/usr/local/bin/check_bgp.sh` which:
1. Verifies `bgpd` process is running
2. Checks for at least one Established BGP session via `vtysh`
3. Returns exit code 0 (healthy) or 1 (unhealthy)

Keepalived uses this script to track BGP health:
- If BGP sessions fail, priority drops by `weight` (-50 default)
- VIP moves to the other router if its priority becomes higher

## Failover Behavior

| Scenario | Result |
|----------|--------|
| FRR Router 1 fails | VIP moves to Router 2 (BGP check fails, priority drops) |
| FRR Router 2 fails | VIP stays on Router 1 (already MASTER) |
| BGP sessions down on Router 1 | VIP moves to Router 2 |
| Both routers fail | No external connectivity (rare) |

## Usage

Deploy with `bgp_ha_deploy.yaml` playbook:

```bash
ansible-playbook -i hosts_bay.ini bgp_ha_deploy.yaml --tags bgp_ha
```

## Dependencies

- `bgp_router_frr` role (installs FRR and configures BGP)

## Important Notes

1. **Router ID**: Use a different `vault_bgp_keepalived_router_id` (e.g., 52) than the K8s API VIP (51) to avoid VRRP conflicts
2. **WireGuard**: Automatically uses unicast VRRP when interface starts with `wg`
3. **MetalLB Peers**: MetalLB should peer with both router IPs (not the VIP) for redundancy
4. **Upstream Gateway**: Configure your upstream to route MetalLB pool traffic to the BGP VIP
