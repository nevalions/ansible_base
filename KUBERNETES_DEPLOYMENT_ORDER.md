# Kubernetes Cluster Deployment Order

Complete step-by-step guide for deploying a Kubernetes cluster with Calico CNI over WireGuard VPN.

## Quick Start: Master Playbooks

Two master playbooks handle the entire cluster lifecycle:

```bash
# Deploy entire cluster from scratch (all phases)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml

# Reset entire cluster (workers first, then control plane)
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml
```

### Deploy Options

```bash
# Full deployment
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml

# Skip infrastructure (DNS/WireGuard already deployed)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true

# Skip MetalLB/BGP (no LoadBalancer needed)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_metallb=true

# Kubernetes only (skip infra and metallb)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true -e skip_metallb=true

# Run specific phase only
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase1  # Infrastructure
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase2  # K8s packages
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase3  # K8s cluster
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase4  # MetalLB
```

### Reset Options

```bash
# Full reset (remove packages)
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml

# Soft reset (keep packages, just reset cluster state)
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml -e reset_mode=soft

# Full cleanup (MetalLB + BGP + Kubernetes)
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml -e cleanup_metallb=true -e cleanup_bgp=true
```

---

## Architecture Overview

```
                    Internet
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   [dns-server-1]   [bgp-router]    [worker-host-1]
   DNS Server      DNS Server     K8s Worker
   WG Server       WG Server      WG Client
        │               │               │
        └───────────────┼───────────────┘
                        │
              WireGuard Mesh ([vpn-network-cidr]/24)
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   [control-plane-1]     │          [worker-host-2]
   K8s Control      Keepalived     K8s Worker
   Plane            VIP            WG Client
    WG Server        [vip-address]
        │
   Calico CNI (IPIP over WireGuard)
   MetalLB (BGP to [bgp-router])
```

## Host Groups Reference

| Group | Hosts | Purpose |
|-------|-------|---------|
| `dns_servers` | [dns-server-1], [bgp-router] | DNS servers (unbound) |
| `dns_clients` | [control-plane-1], [worker-host-2], [worker-host-1] | DNS clients |
| `wireguard_servers` | [dns-server-1], [bgp-router], [control-plane-1] | WG servers (accept connections) |
| `wireguard_clients` | [worker-host-2], [worker-host-1] | WG clients (connect to servers) |
| `wireguard_cluster` | All WG nodes | Full WireGuard mesh |
| `planes_all` / `kuber_small_planes` | [control-plane-1] | Kubernetes control plane |
| `kuber_small_workers` | [worker-host-2], [worker-host-1] | Kubernetes workers |
| `kuber_small_all` | All K8s nodes | Full Kubernetes cluster |
| `bgp_routers` | [bgp-router] | BGP router for MetalLB |

---

## Phase 1: Infrastructure Setup

### Step 1.1: DNS Servers
Deploy DNS servers first - required for hostname resolution.

```bash
# Deploy DNS servers (unbound on [dns-server-1] and [bgp-router])
ansible-playbook -i hosts_bay.ini dns_server_manage.yaml --tags dns
```

**Hosts:** `dns_servers` ([dns-server-1], [bgp-router])
**Playbook:** `dns_server_manage.yaml`

### Step 1.2: WireGuard VPN
Deploy WireGuard mesh network - required for all inter-node communication.

```bash
# Generate WireGuard keys (first time only)
bash generate_wg_keys.sh > wg_keys.yaml
# Update vault_secrets.yml with generated keys

# Deploy WireGuard on all nodes
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard
```

**Hosts:** `wireguard_cluster` (all nodes)
**Playbook:** `wireguard_manage.yaml`

### Step 1.3: Verify WireGuard
```bash
# Verify WireGuard connectivity
ansible-playbook -i hosts_bay.ini wireguard_verify.yaml --tags wireguard
```

**Playbook:** `wireguard_verify.yaml`

### Step 1.4: DNS Clients
Configure DNS clients on Kubernetes nodes.

```bash
# Configure DNS clients
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns
```

**Hosts:** `dns_clients` (kuber_small_planes, kuber_small_workers)
**Playbook:** `dns_client_manage.yaml`

### Step 1.5: Verify DNS
```bash
# Verify DNS resolution
ansible-playbook -i hosts_bay.ini dns_verify.yaml --tags dns
```

**Playbook:** `dns_verify.yaml`

---

## Phase 2: Kubernetes Prerequisites

### Step 2.1: Install Kubernetes Packages
Install kubelet, kubeadm, kubectl, containerd on all cluster nodes.

```bash
# Install Kubernetes packages on all nodes
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes
```

**Hosts:** `kuber_small_all` ([control-plane-1], [worker-host-2], [worker-host-1])
**Playbook:** `kuber.yaml`

### Step 2.2: Keepalived VIP
Deploy Keepalived for Kubernetes API VIP on control plane.

```bash
# Configure Keepalived VIP
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml --tags keepalived
```

**Hosts:** `planes_all` ([control-plane-1])
**Playbook:** `keepalived_manage.yaml`
**VIP:** `[vip-address]` on `wg99` interface

---

## Phase 3: Kubernetes Cluster

### Step 3.1: Initialize Control Plane
Initialize Kubernetes control plane with Calico CNI.

```bash
# Initialize control plane
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
```

**Hosts:** `kuber_small_planes` ([control-plane-1])
**Playbook:** `kuber_plane_init.yaml`

**What it does:**
- Runs `kubeadm init` with WireGuard-aware config
- Installs Tigera Operator
- Configures Calico with:
  - IPIP encapsulation
  - `natOutgoing: true` (critical for WireGuard)
  - MTU: 1380
  - Typha anti-affinity (prevents port conflicts)
- Optionally installs Node Feature Discovery (NFD) to label node system features for K9s filtering/views

**Optional NFD-only run:**

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags nfd
```

### Step 3.2: Join Worker Nodes
Join worker nodes to the cluster.

```bash
# Join all workers
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join
```

**Hosts:** `kuber_small_workers` ([worker-host-2], [worker-host-1])
**Playbook:** `kuber_worker_join.yaml`

### Step 3.3: Verify Cluster
Run full cluster verification.

```bash
# Verify cluster health
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify
```

**Playbook:** `kuber_verify.yaml`

---

## Phase 4: LoadBalancer (MetalLB with BGP)

### Step 4.1: Configure Calico BGP Port
Move Calico BGP to non-standard port (avoids conflict with MetalLB).

```bash
# Move Calico BGP from port 179 to 178
ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml --tags calico,bgp
```

**Hosts:** `kuber_small_all`
**Playbook:** `calico_bgp_manage.yaml`

### Step 4.2: Configure BGP Router
Set up FRR BGP router for MetalLB advertisements.

```bash
# Configure BGP router
ansible-playbook -i hosts_bay.ini bgp_router_manage.yaml --tags bgp
```

**Hosts:** `bgp_routers`
**Playbook:** `bgp_router_manage.yaml`

### Step 4.3: Install MetalLB
Install and configure MetalLB in BGP mode.

```bash
# Install MetalLB
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml --tags metallb
```

**Hosts:** `planes_all` ([control-plane-1])
**Playbook:** `kuber_metallb_install.yaml`

### Step 4.4: Verify MetalLB and BGP
```bash
# Verify BGP router
ansible-playbook -i hosts_bay.ini bgp_router_verify.yaml --tags bgp

# Verify MetalLB
ansible-playbook -i hosts_bay.ini kuber_metallb_verify.yaml --tags metallb
```

---

## Quick Reference: Master Playbooks vs Individual

### Using Master Playbooks (Recommended)

```bash
# Full deployment from scratch
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml

# Full reset and rebuild
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml -e cleanup_metallb=true
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml

# Soft reset and rebuild (keep packages)
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml -e reset_mode=soft
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true

# Kubernetes only (no infra, no metallb)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true -e skip_metallb=true
```

### Using Individual Playbooks

<details>
<summary>Click to expand individual playbook commands</summary>

#### Fresh Install (All Steps)

```bash
# Phase 1: Infrastructure
ansible-playbook -i hosts_bay.ini dns_server_manage.yaml
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml
ansible-playbook -i hosts_bay.ini wireguard_verify.yaml
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml
ansible-playbook -i hosts_bay.ini dns_verify.yaml

# Phase 2: Kubernetes Prerequisites
ansible-playbook -i hosts_bay.ini kuber.yaml
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml

# Phase 3: Kubernetes Cluster
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
ansible-playbook -i hosts_bay.ini kuber_verify.yaml

# Phase 4: LoadBalancer
ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml
ansible-playbook -i hosts_bay.ini bgp_router_manage.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml
ansible-playbook -i hosts_bay.ini bgp_router_verify.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_verify.yaml
```

#### Reset and Rebuild Kubernetes Only

```bash
# Reset workers first, then control plane
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml

# Rebuild
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml
```

#### Soft Reset (Keep Packages)

```bash
# Soft reset - keeps packages, removes cluster state
ansible-playbook -i hosts_bay.ini kuber_worker_soft_reset.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_soft_reset.yaml

# Rebuild
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
```

</details>

---

## Playbook Summary Table

### Master Playbooks

| Playbook | Purpose | Key Options |
|----------|---------|-------------|
| `kuber_cluster_deploy.yaml` | Deploy entire cluster | `-e skip_infrastructure=true`, `-e skip_metallb=true` |
| `kuber_cluster_reset.yaml` | Reset entire cluster | `-e reset_mode=soft`, `-e cleanup_metallb=true`, `-e cleanup_bgp=true` |

### Individual Playbooks

| Order | Playbook | Hosts | Purpose | Tags |
|-------|----------|-------|---------|------|
| 1.1 | `dns_server_manage.yaml` | dns_servers | Deploy DNS servers | dns, server |
| 1.2 | `wireguard_manage.yaml` | wireguard_cluster | Deploy WireGuard VPN | wireguard, vpn |
| 1.3 | `wireguard_verify.yaml` | wireguard_cluster | Verify WireGuard | wireguard |
| 1.4 | `dns_client_manage.yaml` | dns_clients | Configure DNS clients | dns, client |
| 1.5 | `dns_verify.yaml` | dns_clients | Verify DNS | dns |
| 2.1 | `kuber.yaml` | kuber_small_all | Install K8s packages | kubernetes |
| 2.2 | `keepalived_manage.yaml` | planes_all | Configure VIP | keepalived |
| 3.1 | `kuber_plane_init.yaml` | kuber_small_planes | Init control plane | init, cni, nfd, node_info, k9s |
| 3.2 | `kuber_worker_join.yaml` | kuber_small_workers | Join workers | join |
| 3.3 | `kuber_verify.yaml` | planes_all | Verify cluster | verify |
| 4.1 | `calico_bgp_manage.yaml` | kuber_small_all | Configure Calico BGP | calico, bgp |
| 4.2 | `bgp_router_manage.yaml` | bgp_routers | Configure BGP router | bgp |
| 4.3 | `kuber_metallb_install.yaml` | planes_all | Install MetalLB | metallb |
| 4.4 | `bgp_router_verify.yaml` | bgp_routers | Verify BGP | bgp |
| 4.5 | `kuber_metallb_verify.yaml` | planes_all | Verify MetalLB | metallb |

---

## Reset/Cleanup Playbooks

| Playbook | Hosts | Purpose |
|----------|-------|---------|
| `kuber_worker_reset.yaml` | kuber_small_workers | Full worker reset |
| `kuber_plane_reset.yaml` | kuber_small_planes | Full control plane reset |
| `kuber_worker_soft_reset.yaml` | kuber_small_workers | Soft reset (keep packages) |
| `kuber_plane_soft_reset.yaml` | kuber_small_planes | Soft reset (keep packages) |
| `kuber_metallb_remove.yaml` | planes_all | Remove MetalLB |
| `bgp_router_remove.yaml` | bgp_routers | Remove BGP router config |

---

## Critical Configuration (vault_secrets.yml)

### WireGuard + Calico IPIP Requirements

```yaml
# CRITICAL: Must be true for pods to reach WireGuard IPs
natOutgoing: true

# REQUIRED: IPIP encapsulation for L3 WireGuard networks
vault_ipPools_encapsulation: "IPIP"

# MTU: WireGuard (1420) - IPIP (20) - safety (20) = 1380
mtu: 1380

# Prevents Typha port conflicts on small clusters
vault_calico_typha_replicas: 1

# WireGuard interface for node IP detection
vault_interface: "wg99"
```

### Key Variables

```yaml
# Kubernetes API VIP (managed by Keepalived)
vault_k8s_api_vip: "[vip-address]"
vault_k8s_api_port: "[k8s-api-port]"

# Pod and Service CIDRs
vault_k8s_pod_subnet: "[pod-network-cidr]"
vault_k8s_service_subnet: "[service-network-cidr]"

# MetalLB BGP Configuration
vault_metallb_pool_cidr: "[metallb-pool-cidr]/24"
vault_metallb_bgp_my_asn: "[metallb-my-asn]"
vault_bgp_router_asn: "[router-asn]"
```

---

## Troubleshooting

See [KUBERNETES_SETUP.md](KUBERNETES_SETUP.md#troubleshooting) for detailed troubleshooting, including:

- Calico Typha port conflicts
- Pods cannot reach Kubernetes API
- MetalLB speaker crashes
- BGP peering issues
- MTU problems

---

## Dependencies

```
DNS Servers
    │
    └─→ WireGuard VPN
            │
            ├─→ DNS Clients
            │
            └─→ Kubernetes Packages
                    │
                    └─→ Keepalived VIP
                            │
                            └─→ Control Plane Init
                                    │
                                    ├─→ Worker Join
                                    │
                                    └─→ Calico BGP Config
                                            │
                                            ├─→ BGP Router
                                            │
                                            └─→ MetalLB
```
