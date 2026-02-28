# Kubernetes Cluster Deployment Order

Complete step-by-step guide for deploying a Kubernetes cluster with Flannel CNI over WireGuard VPN.

## Quick Start: Master Playbook

```bash
# Deploy entire cluster from scratch (all phases)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml
```

### Deploy Options

```bash
# Full deployment
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml

# Skip infrastructure (WireGuard + DNS already deployed)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true

# Skip MetalLB/BGP (no LoadBalancer needed)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_metallb=true

# Kubernetes only (skip infra and metallb)
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml -e skip_infrastructure=true -e skip_metallb=true

# Run specific phase only
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase1  # Infrastructure
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase2  # K8s prerequisites
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase3  # K8s cluster
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase4  # MetalLB + BGP
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase5  # Traefik ingress
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml --tags phase6  # cert-manager TLS
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
   [haproxy-spb]    [bay-bgp]       [db]
   WG Server        WG Server       WG Client
   DNS Server       DNS Server      K8s external
   BGP HA           BGP Router
        │               │
        └───────────────┘
                        │
              WireGuard Mesh ([vpn-network-cidr]/24)
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   [bay-plane1]    [vas-plane1]    [workers...]
   K8s Control     K8s Control    K8s Workers
   Plane #1        Plane #2       WG Clients
   WG Server       WG Server
   Keepalived      Keepalived
   MASTER          BACKUP
        │               │
        └──── VIP ───────┘
         [vip-address]:6443
              (wg99)
```

**Why WireGuard must come before DNS:**
DNS records contain WireGuard VPN IPs. DNS servers (dnsmasq) bind to WireGuard interface IPs.
If WireGuard is not up, DNS servers cannot start correctly and DNS records resolve to unreachable addresses.

**Why Keepalived must come before `kubeadm init`:**
`kubeadm init` uses `vault_k8s_api_vip` as the `controlPlaneEndpoint`. The VIP must exist
on the network before the API server certificate is generated — the VIP is embedded in the cert SANs.

## Host Groups Reference

| Group                               | Hosts                                                                                   | Purpose                              |
| ----------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------ |
| `wireguard_servers`                 | [haproxy-hostname], [bgp-router-hostname], [control-plane-1-hostname], [control-plane-2-hostname] | WG servers (accept connections)      |
| `wireguard_clients`                 | [worker-main-hostname], [worker-office-hostname], [worker-super-hostname], [worker-remote-hostname], [worker-remote-office-hostname], [db-hostname] | WG clients                           |
| `wireguard_cluster`                 | All of the above                                                                        | Full WireGuard mesh                  |
| `dns_servers`                       | [haproxy-hostname], [bgp-router-hostname]                                               | dnsmasq DNS servers (bind to WG IPs) |
| `dns_clients`                       | kuber_small_planes, kuber_small_workers, vas_planes_all, vas_workers_all                | DNS clients                          |
| `planes_all` / `kuber_small_planes` | [control-plane-1-hostname], [control-plane-2-hostname]                                  | Kubernetes control planes            |
| `kuber_small_workers`               | [worker-main-hostname], [worker-office-hostname], [worker-super-hostname]               | Kubernetes workers                   |
| `kuber_small_all`                   | planes + workers + vas_workers                                                          | All K8s nodes                        |
| `bgp_routers`                       | [bgp-router-hostname] (via [bgp-router-ha1]), [haproxy-hostname] (via [bgp-router-ha2]) | BGP HA routers                       |

---

## Phase 0: Prerequisites (manual, one-time)

Before running any playbook:

1. **Fix NAT inventory** — hosts behind the same public IP need aliases (see NAT section below)
2. **Generate WireGuard keys:**
   ```bash
   bash generate_wg_keys.sh > wg_keys.yaml
   # Copy generated keys into vault_secrets.yml
   ansible-vault edit vault_secrets.yml
   ```
3. **Populate `vault_secrets.yml`** with all required variables:
   - `vault_wg_*` — WireGuard interface, network, peer keys, peers list
   - `vault_k8s_api_vip`, `vault_k8s_api_port`, `vault_k8s_pod_subnet`, `vault_k8s_service_subnet`
   - `vault_keepalived_vip`, `vault_keepalived_vip_interface`
   - `vault_k8s_control_planes` — list of all control plane entries with `wireguard_ip`
   - `vault_dns_*` — DNS zone, records, servers list
   - CNI vars: `vault_k8s_cni_type`, `vault_k8s_pod_subnet`, `flannel_interface`, `flannel_backend_type`, `flannel_mtu`
   - `vault_metallb_*`, `vault_bgp_*` (for Phase 4)

---

## Phase 1: Infrastructure

> **Order is fixed**: WireGuard → DNS servers → WireGuard verify → DNS clients → DNS verify
>
> DNS server records contain WireGuard IPs and dnsmasq binds to the WireGuard interface.
> WireGuard must be fully up before DNS is deployed.

### Step 1.1: WireGuard VPN

Deploy WireGuard mesh on all nodes. Servers get full configs; clients get peer configs pointing to servers.

```bash
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml
```

**Hosts:** `wireguard_cluster` (all nodes)
**Playbook:** `wireguard_manage.yaml`
**What it does:**

- Installs WireGuard packages
- Generates/deploys server configs on `wireguard_servers`
- Deploys client configs on `wireguard_clients`
- Starts `wg-quick@<interface>` on all nodes
- Restarts dnsmasq if present (after WireGuard interface is up)

### Step 1.2: Verify WireGuard

```bash
ansible-playbook -i hosts_bay.ini wireguard_verify.yaml
```

**Hosts:** `wireguard_cluster`
**Playbook:** `wireguard_verify.yaml`

### Step 1.3: DNS Servers

Deploy dnsmasq on the two DNS servers. These bind to WireGuard IPs — requires Step 1.1 complete.

```bash
ansible-playbook -i hosts_bay.ini dns_server_manage.yaml
```

**Hosts:** `dns_servers` ([haproxy-hostname], [bgp-router-hostname])
**Playbook:** `dns_server_manage.yaml`

### Step 1.4: DNS Clients

Configure all K8s nodes and workers to use internal DNS over WireGuard.

```bash
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml
```

**Hosts:** `dns_clients` (kuber_small_planes, kuber_small_workers, vas_workers_all)
**Playbook:** `dns_client_manage.yaml`

### Step 1.5: Verify DNS

```bash
ansible-playbook -i hosts_bay.ini dns_verify.yaml
```

**Hosts:** `wireguard_cluster`
**Playbook:** `dns_verify.yaml`

---

## Phase 2: Kubernetes Prerequisites

### Step 2.1: Install Kubernetes Packages

Install kubelet, kubeadm, kubectl, containerd, and nfs-common on all cluster nodes.

```bash
ansible-playbook -i hosts_bay.ini kuber.yaml
```

**Hosts:** `kuber_small_all` (both planes + all workers)
**Playbook:** `kuber.yaml`
**What it does:**

- Installs nfs-common, Kubernetes packages, containerd
- Disables swap
- Loads required kernel modules (overlay, br_netfilter) and persists via `/etc/modules-load.d/k8s.conf`
- Configures IP forwarding and bridge networking (iptables + ip6tables)
- Disables UFW (avoids blocking CNI/WireGuard forwarding)
- Runs pre-flight checks (Docker conflicts, port availability, kernel modules)

### Step 2.2: Keepalived VIP

Deploy Keepalived VRRP on **both** control planes to establish the K8s API VIP.
This must run before `kubeadm init` — the VIP is used as the `controlPlaneEndpoint`
and is embedded in the API server TLS certificate SANs.

```bash
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml
```

**Hosts:** `planes_all` ([control-plane-1-hostname], [control-plane-2-hostname])
**Playbook:** `keepalived_manage.yaml`
**VIP:** `vault_keepalived_vip` on `vault_keepalived_vip_interface` (default: `wg99`)
**Result:** One plane holds the VIP as MASTER, the other as BACKUP

---

## Phase 3: Kubernetes Cluster

### Step 3.1: Initialize First Control Plane

Initialize `[control-plane-1-hostname]` only. `kuber_plane_init.yaml` targets `kuber_small_planes` (both planes)
with `serial: 1`, so **limit to the first plane** to avoid attempting to init `[control-plane-2-hostname]`,
which will be joined (not initialized) in Step 3.2.

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml -l [control-plane-1-hostname]
```

**Hosts:** `[control-plane-1-hostname]` (limit explicitly)
**Playbook:** `kuber_plane_init.yaml` → role `kuber_init`
**What it does:**

- Runs `kubeadm init --config=/tmp/kubeadm-config.yaml`
  - `controlPlaneEndpoint`: `vault_k8s_api_vip:vault_k8s_api_port`
  - `advertiseAddress`: WireGuard IP of this node
  - Cert SANs include all control plane WireGuard IPs and DNS names
- Copies `admin.conf` to user `.kube/config`
- Installs Node Feature Discovery (NFD) — optional, for K9s node labels
- Verifies control plane is `Ready`

**After this step:** Cluster has 1 control plane node. VIP is active on `[control-plane-1-hostname]`.

### Step 3.1.5: Install Flannel CNI

Install Flannel before worker join so node CNI checks and pod networking validations pass cleanly.

```bash
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml
```

**Hosts:** `kuber_small_planes`
**Playbook:** `kuber_flannel_install.yaml`
**What it does:**

- Validates Flannel settings (pod CIDR/interface/backend/MTU)
- Applies Flannel manifest with repo-managed values
- Waits for `kube-flannel-ds` rollout
- Fails if Calico daemonset is still present (prevents mixed CNI state)

### Step 3.2: Join Second Control Plane

Join `vas_plane1` as a second control plane. This playbook also reconfigures
Keepalived on both planes and verifies VIP failover.

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_join.yaml
```

**Hosts:** `[control-plane-2-hostname]` (hardcoded in playbook plays 1, 2, 4, 5); `planes_all` (play 3 — Keepalived)
**Playbook:** `kuber_plane_join.yaml` → role `kuber_plane_join`

**Internal plays:**

1. Update WireGuard mesh on `[control-plane-2-hostname]`
2. Verify WireGuard connectivity from `[control-plane-2-hostname]` to existing control plane
3. Reconfigure Keepalived VRRP on **all** `planes_all` (lower priority for `[control-plane-2-hostname]`)
4. Run `kubeadm join --control-plane` on `[control-plane-2-hostname]`
   - Uploads certs from existing plane, generates join token
   - Joins as control plane with `--control-plane --certificate-key`
5. Verify both control planes are `Ready` and VIP is reachable

**Prerequisites for this step (in `vault_secrets.yml`):**

```yaml
vault_wg_peers:
  - name: [control-plane-2-hostname]
    host_group: [control-plane-2-hostname]
    is_server: true
    allowed_ips: "[vas-plane1-wg-ip]/32"
    endpoint: "[control-plane-2-public-ip]:[control-plane-2-wg-port]"

vault_wg_server_ips:
  [control-plane-2-hostname]: "[vas-plane1-wg-ip]"

vault_wg_server_ports:
  [control-plane-2-hostname]: "[vas-plane1-wg-port]"

vault_k8s_control_planes:
  - name: [control-plane-1-hostname] # existing plane must be first
    wireguard_ip: "[bay-plane1-wg-ip]"
    api_port: "[k8s-api-port]"
    priority: 110 # MASTER
  - name: [control-plane-2-hostname]
    wireguard_ip: "[vas-plane1-wg-ip]"
    api_port: "[k8s-api-port]"
    priority: 100 # BACKUP
```

**After this step:** Cluster has 2 control planes. Keepalived VIP fails over between them.

### Step 3.3: Join Worker Nodes

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
```

**Hosts:** `[worker-remote-office-hostname]` (hardcoded — edit playbook `hosts:` to target all workers)
**Playbook:** `kuber_worker_join.yaml` → role `kuber_join`
**What it does:**

- Generates fresh kubeadm join token from control plane (delegates to `planes_all[0]`)
- Runs `kubeadm join --config=/tmp/kube-join.yaml`
- Labels node with `node-role.kubernetes.io/worker`
- Waits for node `Ready`
- Verifies configured CNI daemon pod on worker

> **Note:** `kuber_worker_join.yaml` currently has `hosts: [worker-remote-office-hostname]`.
> To join all workers at once, run with `-l kuber_small_workers` or edit the playbook `hosts:` field.

### Step 3.4: Verify Cluster

```bash
ansible-playbook -i hosts_bay.ini kuber_verify.yaml
```

**Hosts:** `kuber_small_planes`
**Playbook:** `kuber_verify.yaml`
**Checks:** all nodes Ready, Flannel operational, pod-to-pod connectivity, DNS resolution, external access

---

## Phase 4: LoadBalancer (MetalLB with BGP HA)

### Step 4.1: Legacy Calico Path (optional) - Configure Calico BGP Port

Skip this step for the default Flannel path.
Use only if you intentionally run the Legacy Calico Path and need to free TCP/179 for MetalLB.

```bash
# ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml
```

**Hosts:** `kuber_small_all` (legacy only)

### Step 4.2: Deploy BGP HA (FRR + Keepalived)

Deploy FRR BGP router and Keepalived on both BGP HA routers ([bgp-router-hostname] + [haproxy-hostname]).

```bash
ansible-playbook -i hosts_bay.ini bgp_ha_deploy.yaml
```

**Hosts:** `bgp_routers` ([bgp-router-ha1], [bgp-router-ha2])

### Step 4.3: Install MetalLB

```bash
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml
```

**Hosts:** `planes_all`

### Step 4.4: Verify BGP HA

```bash
ansible-playbook -i hosts_bay.ini bgp_ha_verify.yaml
```

### Step 4.5: Verify MetalLB

```bash
ansible-playbook -i hosts_bay.ini kuber_metallb_verify.yaml
```

---

## Phase 5: Ingress Controller (Traefik)

```bash
ansible-playbook -i hosts_bay.ini kuber_traefik_install.yaml
ansible-playbook -i hosts_bay.ini kuber_traefik_verify.yaml
```

---

## Phase 6: TLS (cert-manager)

```bash
ansible-playbook -i hosts_bay.ini kuber_cert_manager_install.yaml
ansible-playbook -i hosts_bay.ini kuber_cert_manager_verify.yaml
```

See [KUBERNETES_SETUP.md](KUBERNETES_SETUP.md) for cert-manager + Traefik TLS details.

---

## Complete Individual Playbook Sequence

```bash
# ── Phase 1: Infrastructure ──────────────────────────────────────────────────
# WireGuard MUST come before DNS: DNS records contain WG IPs,
# dnsmasq binds to the WireGuard interface.
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml
ansible-playbook -i hosts_bay.ini wireguard_verify.yaml
ansible-playbook -i hosts_bay.ini dns_server_manage.yaml
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml
ansible-playbook -i hosts_bay.ini dns_verify.yaml

# ── Phase 2: Kubernetes prerequisites ────────────────────────────────────────
ansible-playbook -i hosts_bay.ini kuber.yaml
# Keepalived MUST come before kubeadm init: VIP is the controlPlaneEndpoint
# and is embedded in API server cert SANs.
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml

# ── Phase 3: Kubernetes cluster ───────────────────────────────────────────────
# Limit to [control-plane-1-hostname] only — [control-plane-2-hostname] joins in the next step, not init.
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml -l [control-plane-1-hostname]
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_join.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
ansible-playbook -i hosts_bay.ini kuber_verify.yaml

# ── Phase 4: LoadBalancer ─────────────────────────────────────────────────────
# Optional legacy only: ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml
ansible-playbook -i hosts_bay.ini bgp_ha_deploy.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml
ansible-playbook -i hosts_bay.ini bgp_ha_verify.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_verify.yaml

# ── Phase 5: Ingress ──────────────────────────────────────────────────────────
ansible-playbook -i hosts_bay.ini kuber_traefik_install.yaml
ansible-playbook -i hosts_bay.ini kuber_traefik_verify.yaml

# ── Phase 6: TLS ──────────────────────────────────────────────────────────────
ansible-playbook -i hosts_bay.ini kuber_cert_manager_install.yaml
ansible-playbook -i hosts_bay.ini kuber_cert_manager_verify.yaml
```

---

## Playbook Summary Table

### Master Playbooks

| Playbook                    | Purpose               | Key Options                                                                                                                     |
| --------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `kuber_cluster_deploy.yaml` | Deploy entire cluster | `-e skip_infrastructure=true`, `-e skip_metallb=true`, `-e skip_helm=true`, `-e skip_traefik=true`, `-e skip_cert_manager=true` |
| `kuber_cluster_reset.yaml`  | Reset entire cluster  | `-e reset_mode=soft`, `-e cleanup_metallb=true`, `-e cleanup_bgp=true`                                                          |

### Individual Playbooks — Deployment Order

| Step | Playbook                              | Hosts                | Purpose                                |
| ---- | ------------------------------------- | -------------------- | -------------------------------------- |
| 1.1  | `wireguard_manage.yaml`               | `wireguard_cluster`  | Deploy WireGuard mesh VPN              |
| 1.2  | `wireguard_verify.yaml`               | `wireguard_cluster`  | Verify WireGuard peers                 |
| 1.3  | `dns_server_manage.yaml`              | `dns_servers`        | Deploy dnsmasq (binds to WG IPs)       |
| 1.4  | `dns_client_manage.yaml`              | `dns_clients`        | Configure nodes to use internal DNS    |
| 1.5  | `dns_verify.yaml`                     | `wireguard_cluster`  | Verify DNS resolution                  |
| 2.1  | `kuber.yaml`                          | `kuber_small_all`    | Install K8s packages + containerd      |
| 2.2  | `keepalived_manage.yaml`              | `planes_all`         | VIP on both planes before init         |
| 3.1  | `kuber_plane_init.yaml -l [control-plane-1-hostname]` | `[control-plane-1-hostname]` | Init first control plane               |
| 3.2  | `kuber_flannel_install.yaml`          | `kuber_small_planes` | Install Flannel CNI                    |
| 3.3  | `kuber_plane_join.yaml`               | `[control-plane-2-hostname]` | Join second control plane + Keepalived |
| 3.4  | `kuber_worker_join.yaml`              | workers              | Join worker nodes                      |
| 3.5  | `kuber_verify.yaml`                   | `kuber_small_planes` | Full cluster health check              |
| 4.1  | `calico_bgp_manage.yaml`              | `kuber_small_all`    | Legacy Calico Path (optional) BGP tuning |
| 4.2  | `bgp_ha_deploy.yaml`                  | `bgp_routers`        | Deploy FRR + Keepalived HA             |
| 4.3  | `kuber_metallb_install.yaml`          | `planes_all`         | Install MetalLB                        |
| 4.4  | `bgp_ha_verify.yaml`                  | `bgp_routers`        | Verify BGP HA                          |
| 4.5  | `kuber_metallb_verify.yaml`           | `planes_all`         | Verify MetalLB                         |
| 5.1  | `kuber_traefik_install.yaml`          | `planes_all`         | Install Traefik ingress                |
| 5.2  | `kuber_traefik_verify.yaml`           | `planes_all`         | Verify Traefik                         |
| 6.1  | `kuber_cert_manager_install.yaml`     | `planes_all`         | Install cert-manager                   |
| 6.2  | `kuber_cert_manager_verify.yaml`      | `planes_all`         | Verify cert-manager                    |

---

## Reset / Rebuild Sequences

### Full Reset and Rebuild

```bash
ansible-playbook -i hosts_bay.ini kuber_cluster_reset.yaml -e cleanup_metallb=true -e cleanup_bgp=true
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml
```

### Kubernetes-Only Reset (keep WireGuard + DNS)

```bash
# Reset workers first, then control planes
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml

# Rebuild
ansible-playbook -i hosts_bay.ini keepalived_manage.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml -l [control-plane-1-hostname]
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_join.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
# Optional legacy only: ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml
ansible-playbook -i hosts_bay.ini bgp_ha_deploy.yaml
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml
```

### Soft Reset (keep packages, reset cluster state only)

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_soft_reset.yaml
ansible-playbook -i hosts_bay.ini kuber_plane_soft_reset.yaml

ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml -l [control-plane-1-hostname]
ansible-playbook -i hosts_bay.ini kuber_plane_join.yaml
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
```

---

## Reset / Cleanup Playbooks Reference

| Playbook                                       | Hosts                 | Purpose                              |
| ---------------------------------------------- | --------------------- | ------------------------------------ |
| `kuber_worker_reset.yaml`                      | `kuber_small_workers` | Full worker reset (removes packages) |
| `kuber_plane_reset.yaml`                       | `kuber_small_planes`  | Full control plane reset             |
| `kuber_worker_soft_reset.yaml`                 | `kuber_small_workers` | Soft reset (keep packages)           |
| `kuber_plane_soft_reset.yaml`                  | `kuber_small_planes`  | Soft reset (keep packages)           |
| `kuber_metallb_remove.yaml`                    | `planes_all`          | Remove MetalLB                       |
| `bgp_ha_remove.yaml`                           | `bgp_routers`         | Remove BGP HA (FRR + Keepalived)     |
| `bgp_router_remove.yaml`                       | `bgp_routers`         | Remove standalone BGP router config  |
| `wireguard_manage.yaml -e wg_operation=remove` | `wireguard_cluster`   | Remove WireGuard                     |
| `dns_server_remove.yaml`                       | `dns_servers`         | Remove DNS servers                   |
| `dns_client_remove.yaml`                       | `dns_clients`         | Remove DNS client config             |

---

## Dependency Graph

```
WireGuard VPN
    │
    ├─→ WireGuard Verify
    │
    └─→ DNS Servers  (bind to WireGuard IPs, records use WG IPs)
            │
            └─→ DNS Clients
                    │
                    └─→ DNS Verify
                            │
                            └─→ Kubernetes Packages (kuber.yaml)
                                    │
                                    └─→ Keepalived VIP (required before kubeadm init)
                                            │
                                            └─→ Control Plane Init ([control-plane-1-hostname] -l)
                                                    │
                                                    └─→ Control Plane Join (vas_plane1)
                                                            │
                                                            └─→ Worker Join
                                                                    │
                                                                    └─→ Cluster Verify
                                                                            │
                                                                            └─→ Flannel Install
                                                                                    │
                                                                                    └─→ BGP HA Deploy
                                                                                            │
                                                                                            └─→ MetalLB
                                                                                                    │
                                                                                                    ├─→ Traefik
                                                                                                    │
                                                                                                    └─→ cert-manager
```

---

## NAT Inventory: Hosts Sharing a Public IP

Some hosts sit behind NAT and share public IP.
Ansible deduplicates hosts by `inventory_hostname`, so bare IPs collapse to one host.
Use aliases with `ansible_host` + `ansible_port` inline:

```ini
# Correct — three distinct inventory hostnames
[some_plane1]
some-plane1 ansible_host=[ip] ansible_port=[port]
```

---

## Critical vault_secrets.yml Settings

```yaml
# WireGuard + Flannel VXLAN (default baseline)
vault_k8s_cni_type: "flannel"
flannel_interface: "wg99"
flannel_backend_type: "vxlan"
flannel_mtu: 1360 # 1420 (WG) - 50 (VXLAN) - 10 (safety)

# WireGuard interface used for node IP detection
vault_interface: "wg99"

# Kubernetes API — VIP must exist before kubeadm init
vault_k8s_api_vip: "[vip-address]"
vault_k8s_api_port: "[k8s-api-port]"

# Control planes list — [control-plane-1-hostname] must be first (used as join delegate)
vault_k8s_control_planes:
  - name: [control-plane-1-hostname]
    wireguard_ip: "[bay-plane1-wg-ip]"
    api_port: "[k8s-api-port]"
    priority: 110
  - name: [control-plane-2-hostname]
    wireguard_ip: "[vas-plane1-wg-ip]"
    api_port: "[k8s-api-port]"
    priority: 100

# Pod and service CIDRs
vault_k8s_pod_subnet: "[pod-network-cidr]"
vault_k8s_service_subnet: "[service-network-cidr]"

# MetalLB BGP
vault_metallb_pool_cidr: "[metallb-pool-cidr]/24"
vault_metallb_bgp_my_asn: "[metallb-my-asn]"
vault_bgp_router_asn: "[router-asn]"
```

---

## Troubleshooting

See [KUBERNETES_SETUP.md](KUBERNETES_SETUP.md#troubleshooting) for detailed troubleshooting:

- Flannel daemonset not ready (`kube-flannel-ds` rollout incomplete)
- MetalLB speaker crashes (orphaned process)
- BGP peering not establishing (reachability/firewall mismatch)
- MTU fragmentation issues
- UFW blocking pod egress (DNS/ACME failures)
- IPv6 AAAA record failures (`ImagePullBackOff`)

### Keepalived split-brain (both planes show MASTER)

Symptom: `ip addr show wg99 | grep <vip>` returns true on both control planes.

Root cause: VRRP unicast packets cannot reach the peer because WireGuard tunnel between
the two planes is not passing traffic in one or both directions.

Diagnosis:

```bash
# Test tunnel connectivity from each plane
ansible -i hosts_bay.ini [control-plane-1-hostname] -m shell -a "ping -c 3 <vas-plane1-wg-ip>"
ansible -i hosts_bay.ini [control-plane-2-hostname] -m shell -a "ping -c 3 <bay-plane1-wg-ip>"

# Capture ICMP inside tunnel (no packets = WG not decrypting)
ansible -i hosts_bay.ini [control-plane-2-hostname] -m shell -a "timeout 5 tcpdump -i wg99 icmp -c 5"

# Check actual WireGuard endpoint vs configured endpoint
ansible -i hosts_bay.ini [control-plane-1-hostname] -m shell -a "wg show wg99 | grep -A6 '<vas-plane1-pubkey>'"
# endpoint: field shows the live NAT-mapped port (may differ from static config)
```

Common cause — NAT port-forward missing or wrong:

- `vault_wg_peers[[control-plane-2-hostname]].endpoint` = `<nat-ip>:<external-port>` must be forwarded by
  the NAT device to `[control-plane-2-hostname]:<wg_listen_port>` (default `vault_wg_server_port`).
- If the external port in the vault does not match the actual NAT forward rule, `[control-plane-1-hostname]`
  sends WireGuard packets to a port the NAT device does not route to `[control-plane-2-hostname]`.
- Fix: update the NAT router's port-forward rule, or update the endpoint port in vault.

After fixing the tunnel, restart Keepalived on both planes to clear stale state:

```bash
ansible -i hosts_bay.ini keepalived_vip_servers -m systemd \
  -a "name=keepalived state=restarted" --extra-vars "@vault_secrets.yml"
```
