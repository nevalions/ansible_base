# BGP HA Kubernetes Cluster Architecture

This document describes the high-availability architecture for the Kubernetes cluster with BGP-based load balancing.

Operational steps (deploy/verify/test/remove) are documented in `docs/BGP_HA_GUIDE.md`.

## Network Topology

```
                                    INTERNET
                                        |
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    |           EXTERNAL NETWORK            |
                    |                                       |
                    +-------------------+-------------------+
                                        |
            +-----------+---------------+---------------+-----------+
            |           |                               |           |
            v           v                               v           v
    +---------------+  +---------------+       +---------------+  +---------------+
    |  BGP Router 1 |  |  BGP Router 2 |       |   HAProxy 1   |  |   HAProxy 2   |
    |  (MASTER)     |  |  (BACKUP)     |       |   (MASTER)    |  |   (BACKUP)    |
    |               |  |               |       |               |  |               |
    | FRR + Keepalived | FRR + Keepalived     | Keepalived    |  | Keepalived    |
    | VIP: [bgp-vip]|  |               |       | VIP:[api-vip] |  |               |
    +-------+-------+  +-------+-------+       +-------+-------+  +-------+-------+
            |                  |                       |                  |
            |                  |                       |                  |
            +------------------+-----------------------+------------------+
                               |
                               | WireGuard VPN (wg99)
                               | Network: [vpn-network-cidr]
                               |
    +----------+---------------+---------------+---------------+----------+
    |          |               |               |               |          |
    v          v               v               v               v          v
+--------+ +--------+     +--------+     +---------+     +---------+ +---------+
| Control| | Control|     | Worker |     | Worker  |     | Worker  | | Worker  |
| Plane 1| | Plane 2|     | Node 1 |     | Node 2  |     | Node 3  | | Node N  |
|        | |        |     |        |     |         |     |         | |         |
|Keepalived|Keepalived    |MetalLB |     |MetalLB  |     |MetalLB  | |MetalLB  |
|VIP:[api]| |        |     |Speaker |     |Speaker  |     |Speaker  | |Speaker  |
+----+---+ +----+---+     +----+---+     +----+----+     +----+----+ +----+----+
     |          |              |              |              |            |
     +----------+--------------+--------------+--------------+------------+
                               |
                      Kubernetes Cluster
                      Pod Network: [pod-network-cidr]
                      Service Network: [service-network-cidr]
```

## Component Overview

### BGP Routers (HA Pair)

| Component | Description |
|-----------|-------------|
| FRR | Free Range Routing - BGP daemon peering with MetalLB speakers |
| Keepalived | VRRP for floating VIP between BGP routers |
| BGP VIP | Floating IP for external access to LoadBalancer services |
| ASN | Local AS number for BGP peering |

**Failover behavior:**
- MASTER router holds the BGP VIP
- BACKUP router monitors MASTER via VRRP
- On MASTER failure, BACKUP takes over VIP within seconds
- BGP sessions re-establish automatically

### Kubernetes Control Plane (HA)

| Component | Description |
|-----------|-------------|
| kube-apiserver | Kubernetes API server (multiple instances) |
| etcd | Distributed key-value store (stacked or external) |
| Keepalived | VRRP for floating API VIP |
| API VIP | Floating IP for kubectl and cluster access |

### Worker Nodes

| Component | Description |
|-----------|-------------|
| kubelet | Node agent managing pods |
| MetalLB Speaker | BGP speaker advertising LoadBalancer IPs |
| Calico | CNI for pod networking (IPIP mode over WireGuard) |
| WireGuard | Encrypted tunnel for cross-network communication |

### WireGuard VPN Mesh

| Component | Description |
|-----------|-------------|
| wg99 | WireGuard interface on all cluster nodes |
| Peer IPs | Each node has a unique VPN IP |
| Routed CIDRs | API VIP and BGP VIP routed through tunnel |

## Network Flows

### 1. External Traffic to LoadBalancer Service

```
Client -> BGP VIP -> BGP Router (MASTER) -> WireGuard -> Worker Node -> Pod
                          |
                     FRR routes to
                     MetalLB speaker
                     via BGP learned
                     routes
```

### 2. kubectl Access to API Server

```
Admin -> API VIP -> Control Plane (MASTER) -> kube-apiserver
              |
         Keepalived
         VRRP failover
```

### 3. Pod-to-Pod Communication (Cross-Node)

```
Pod A -> Calico (IPIP) -> tunl0 -> WireGuard (wg99) -> Node B -> Calico -> Pod B
```

### 4. MetalLB BGP Advertisement

```
MetalLB Speaker -> BGP (ASN [k8s-asn]) -> FRR Router (ASN [router-asn])
                          |
                     Advertises:
                     - LoadBalancer IPs
                     - Service pool CIDR
```

## IP Address Allocation

| Resource | CIDR/Address | Description |
|----------|--------------|-------------|
| WireGuard Network | [vpn-network-cidr] | VPN overlay network |
| Pod Network | [pod-network-cidr] | Kubernetes pod IPs |
| Service Network | [service-network-cidr] | ClusterIP services |
| MetalLB Pool | [metallb-pool-cidr] | LoadBalancer external IPs |
| API VIP | [api-vip-address] | Kubernetes API floating IP |
| BGP VIP | [bgp-vip-address] | BGP router floating IP |

## High Availability Summary

| Component | HA Method | Failover Time |
|-----------|-----------|---------------|
| Kubernetes API | Keepalived VRRP | 1-3 seconds |
| BGP Routers | Keepalived VRRP + FRR | 1-5 seconds |
| etcd | Raft consensus | Automatic |
| MetalLB | Multiple speakers | Automatic |
| WireGuard | Mesh topology | N/A (no single point) |

## Playbooks

| Playbook | Purpose |
|----------|---------|
| `bgp_ha_deploy.yaml` | Deploy FRR + Keepalived on BGP routers |
| `bgp_ha_verify.yaml` | Verify BGP HA status and VIP reachability |
| `bgp_ha_test.yaml` | Test end-to-end connectivity |
| `wireguard_manage.yaml` | Manage WireGuard VPN mesh |
| `kuber_metallb_install.yaml` | Install/configure MetalLB |

## Troubleshooting

### Check BGP Status
```bash
# On BGP router
vtysh -c "show bgp summary"
vtysh -c "show ip route bgp"
```

### Check Keepalived Status
```bash
# On any HA node
systemctl status keepalived
ip addr show wg99 | grep -E "inet.*secondary"
```

### Check MetalLB
```bash
# On control plane
kubectl get bgppeer -A
kubectl get ipaddresspool -A
kubectl logs -n metallb-system -l component=speaker
```

### Check WireGuard
```bash
# On any node
wg show wg99
ping [peer-vpn-ip]
```
