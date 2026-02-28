# Kubernetes Cluster Setup with Ansible

> **Quick Start:** For complete deployment order from scratch, see [KUBERNETES_DEPLOYMENT_ORDER.md](KUBERNETES_DEPLOYMENT_ORDER.md)

## Overview

This Ansible project provides automated Kubernetes cluster setup over WireGuard VPN.
The current default CNI is Flannel. Legacy Calico Path (optional) is kept for compatibility.

## Architecture

The Kubernetes cluster uses a Virtual IP (VIP) for high availability:

```
Workers → VIP:[k8s-api-port]
           ↓
Keepalived on [haproxy-hostname] (VIP management + DNAT)
           ↓ DNAT: [vip-address]:[k8s-api-port] → [control-plane-wg-ip]:[haproxy-frontend-port]
HAProxy on [plane-hostname] (WireGuard IP: [control-plane-wg-ip]:[haproxy-frontend-port])
           → localhost:[haproxy-backend-port]
Kubernetes API server (port [haproxy-backend-port])
```

**Components:**
- **Keepalived**: Manages VIP failover and performs health checks on control planes
- **HAProxy**: Load balances Kubernetes API requests on each control plane
- **WireGuard**: Provides secure mesh network for inter-plane communication
- **VIP**: Virtual IP ([vip-address]) that workers connect to
- **Flannel CNI**: Pod networking with VXLAN encapsulation over WireGuard

**Scalability:**
- Start with single control plane ([plane-hostname])
- Add additional control planes by updating `vault_k8s_control_planes`
- Keepalived automatically detects healthy planes and routes traffic accordingly

---

## WireGuard + Flannel VXLAN Network Requirements

Running Kubernetes with Flannel CNI over WireGuard requires consistent pod CIDR and MTU values.

### Critical Configuration

| Setting | Required Value | Why |
|---------|---------------|-----|
| `vault_k8s_cni_type` | `flannel` | Keeps join/verify checks aligned with active CNI |
| `vault_k8s_pod_subnet` | cluster pod CIDR | Must match kubeadm pod subnet and Flannel manifest |
| `flannel_interface` | `wg99` | Ensures overlay uses WireGuard underlay |
| `flannel_backend_type` | `vxlan` | Recommended baseline for mixed networks |
| `flannel_mtu` | `1360` | WireGuard (1420) - VXLAN (50) - safety (10) |

### Network Flow

```
Pod ([pod-network-cidr]) -> Flannel VXLAN -> WireGuard ([vpn-network-cidr]) -> Remote Node
```

### Flannel Install/Remove

Flannel is managed as a dedicated step and is not installed by `kuber_plane_init.yaml`.

```bash
# Install Flannel CNI
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel

# Remove Flannel CNI
ansible-playbook -i hosts_bay.ini kuber_flannel_remove.yaml --tags flannel
```

## Playbooks

### 1. kuber.yaml - Install Kubernetes Packages
**Purpose:** Install Kubernetes components (kubelet, kubeadm, kubectl, containerd) and configure system prerequisites

**Hosts:** `[workers_super]` (currently targets [worker-super-ip])

**Tags:** `kubernetes`, `k8s`, `install`, `cluster`

**What it does:**

**Pre-flight Validation (NEW):**
- Checks if Kubernetes is already installed (fails if detected)
- Validates system is ready for installation
- Checks for Docker installation (fails if Docker is installed - conflicts with containerd)
- Checks for Docker daemon running (fails if active)
- Checks for conflicting container runtimes (dockerd, cri-o, crictl)
- Validates port availability (API server, etcd, kubelet, scheduler, controller manager)
- Detects existing CNI configurations (warns if found)
- Checks for running Kubernetes processes from previous installations
- Validates kernel module availability (overlay, br_netfilter)
- Warns about swap status (swap will be disabled during install)

**Installation:**
- Updates package lists
- Adds Kubernetes GPG key and repository
- Installs kubelet, kubeadm, kubectl, containerd
- Holds Kubernetes packages to prevent automatic updates
- Disables swap
- Loads required kernel modules (overlay, br_netfilter) and persists via `/etc/modules-load.d/k8s.conf`
- Configures IP forwarding and bridge networking (iptables + ip6tables)
- Configures containerd cgroup driver (systemd)
- Disables UFW on Kubernetes nodes (to avoid CNI/WireGuard forwarding issues)

---

## TLS Certificates (Traefik)

This repository supports two approaches:

### Recommended: cert-manager issues certs (no Traefik ACME storage)

Use cert-manager to obtain/renew certificates and store them as Kubernetes TLS Secrets.
Traefik then serves those secrets.

Why this is recommended:
- Traefik OSS ACME storage is file-based (`acme.json`). Without persistence, certs/state disappear when the Traefik pod is recreated.
- Traefik docs recommend cert-manager for Kubernetes HA scenarios.

Steps:
```bash
# Install cert-manager and ClusterIssuer
ansible-playbook -i hosts_bay.ini kuber_cert_manager_install.yaml

# Install/upgrade Traefik (with Traefik ACME disabled)
# In vault_secrets.yml: vault_traefik_certresolver_enabled: false
ansible-playbook -i hosts_bay.ini kuber_traefik_install.yaml
```

Optional cleanup after the switch:
- Keep `vault_traefik_certresolver_enabled: false`
- Ensure Traefik is not configured with:
  - `--entryPoints.websecure.http.tls.certResolver=...`
  - `--certificatesresolvers.*.acme.*`

In this repo, those values are only rendered when `vault_traefik_certresolver_enabled: true`.

Example `Certificate` + `IngressRoute` (placeholders):
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: butakov-su
  namespace: web-test
spec:
  secretName: butakov-su-tls
  issuerRef:
    kind: ClusterIssuer
    name: letsencrypt-prod
  dnsNames:
    - example.com

---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: butakov-https
  namespace: web-test
spec:
  entryPoints:
    - websecure
  routes:
    - kind: Rule
      match: Host(`example.com`)
      services:
        - name: nginx-test-svc
          port: 80
  tls:
    secretName: butakov-su-tls
```

### Alternative: Traefik issues certs itself (ACME)

If you enable Traefik ACME (`vault_traefik_certresolver_enabled: true`), you should also persist
`/data/acme.json` using a PVC (see Traefik role persistence variables).

**Pre-flight Variables** (roles/kuber/defaults/main.yaml):
```yaml
k8s_preflight_skip_docker_check: false
k8s_preflight_skip_swap_check: false
k8s_preflight_skip_port_check: false
k8s_preflight_skip_cni_check: false
k8s_preflight_skip_container_runtime_check: false
k8s_preflight_skip_process_check: false
k8s_preflight_fail_on_warnings: false
```

Configure in `vault_secrets.yml`:
```yaml
vault_k8s_preflight_skip_docker_check: false
vault_k8s_preflight_skip_swap_check: false
vault_k8s_preflight_skip_port_check: false
vault_k8s_preflight_skip_cni_check: false
vault_k8s_preflight_skip_container_runtime_check: false
vault_k8s_preflight_skip_process_check: false
vault_k8s_preflight_fail_on_warnings: false
```

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes
```

**Pre-flight Validation Behavior:**
- Critical errors (Docker installed/running, conflicting runtimes) will fail by default
- Warnings (swap enabled, existing CNI, existing K8s processes) will be displayed but won't fail
- Set `k8s_preflight_fail_on_warnings: true` to fail on warnings
- Skip individual checks by setting the corresponding `vault_k8s_preflight_skip_*_check: true`

---

### 2. kuber_plane_init.yaml - Initialize Control Plane
**Purpose:** Initialize Kubernetes control plane with kubeadm

**Hosts:** `[planes]` ([control-plane-ip])

**Tags:** `kubernetes`, `k8s`, `init`, `plane`, `cni`, `nfd`, `node_info`, `k9s`

**What it does:**
- Checks if cluster is already initialized
- Copies kubeadm configuration (template with dynamic IPs)
- Runs `kubeadm init --config=kubeadm-config.yaml`
- Copies admin.conf to user's .kube/config
- Installs Node Feature Discovery (NFD) for node feature labels (optional)
- Waits for NFD master deployment and worker DaemonSet rollout
- **VERIFICATION:** Validates control plane is Ready
- **VERIFICATION:** Displays sample NFD node label output
- **VERIFICATION:** Displays initialization summary

**Variables** (roles/kuber_init/defaults/main.yaml):
```yaml
kubeadm_pod_subnet: "[pod-network-cidr]"
kubeadm_service_subnet: "[service-network-cidr]"
kubeadm_control_plane_endpoint: "{{ ansible_default_ipv4.address }}:{{ vault_haproxy_k8s_backend_port | default('[haproxy-backend-port]') }}"
kubeadm_api_server_advertise_address: "{{ ansible_default_ipv4.address }}"
kubeadm_kubelet_extra_args:
  node-ip: "{{ ansible_default_ipv4.address }}"
kubeadm_api_version: "v1beta4"
k8s_node_info_enabled: true
nfd_version: "v0.18.2"
nfd_kustomize_ref: "https://github.com/kubernetes-sigs/node-feature-discovery/deployment/overlays/default?ref={{ nfd_version }}"
```

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
```

**Verification included:**
✓ Control plane node Ready status
✓ Kubernetes API reachable
✓ Optional NFD rollout status

### 2.5. kuber_flannel_install.yaml - Install Flannel CNI
**Purpose:** Install Flannel CNI (VXLAN over WireGuard)

**Hosts:** `kuber_small_planes`

**Tags:** `kubernetes`, `k8s`, `flannel`, `cni`, `addon`

**What it does:**
- Validates Flannel prerequisites (pod subnet/interface/backend)
- Ensures base CNI plugins exist
- Applies Flannel manifest with repo-driven values
- Waits for Flannel daemonset rollout on nodes
- Prevents mixed CNI state by failing if Calico daemonset still exists

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel
```

---

### 3. kuber_worker_join.yaml - Join Worker Nodes
**Purpose:** Join worker nodes to the Kubernetes cluster

**Hosts:** `[workers_all]` (all worker nodes in inventory)

**Tags:** `kubernetes`, `k8s`, `join`, `worker`

**What it does:**
- Checks if node is already joined
- Generates fresh kubeadm join token from control plane
- Parses token and CA cert hash from join command
- Displays join information (control plane IP, token, hash)
- Copies kubeadm join configuration (template)
- Runs `kubeadm join --config=kube-join.yaml`
- Waits for kubelet to be active
- **VERIFICATION:** Confirms node is visible from control plane
- **VERIFICATION:** Waits for node to be Ready
- **VERIFICATION:** Checks configured CNI daemon pod on worker
- **VERIFICATION:** Displays join summary

**Variables** (roles/kuber_join/defaults/main.yaml):
```yaml
kuber_join_control_plane_host: "VIP"
kuber_join_control_plane_ip: "[vip-address]"  # VIP address
kuber_join_api_port: "[k8s-api-port]"
```

**Verification included:**
✓ Node visibility from control plane
✓ Node Ready status
✓ CNI daemon pod on worker node
✓ Join summary

---

### 4. kuber_verify.yaml - Full Cluster Health Check
**Purpose:** Comprehensive verification of Kubernetes cluster health, CNI networking, and worker connectivity

**Hosts:** `[planes]` ([control-plane-ip])

**Tags:** `kubernetes`, `k8s`, `verify`, `test`

**What it does:**

#### Control Plane Verification
- Gets all cluster nodes
- Checks control plane node Ready status
- Detects configured CNI type (Flannel/Calico)
- Gets active CNI daemon pods
- Waits for CNI daemon pods to be Running
- Displays cluster info

#### Worker Verification
- Gets all worker nodes
- Counts worker nodes
- Checks if all worker nodes are Ready
- Gets CNI daemon pods on all nodes
- Verifies CNI daemon pod count matches cluster nodes
- Describes each worker node

#### Network Verification
- Creates test namespace (`kuber-verify-test`)
- Deploys 2 test pods (nginx:alpine)
- Deploys 1 DNS test pod
- Waits for test pods to be Ready
- Displays test pods status and IPs
- **TESTS pod-to-pod connectivity** between test pods
- **TESTS DNS resolution** ([k8s-service])
- **TESTS external connectivity** ([your-username].google.com)
- Gets pod logs and describe for troubleshooting
- Cleans up test namespace

**Variables** (roles/kuber_verify/defaults/main.yaml):
```yaml
verify_test_namespace: "kuber-verify-test"
verify_test_pod_image: "nginx:alpine"
verify_test_pod_port: "80"
verify_timeout_seconds: "300"
verify_sleep_seconds: "5"
verify_retry_count: "20"
```

**Usage:**
```bash
# Full verification
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify

# Run after control plane init
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify

# Run after worker join
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify
```

**Verification Report:**
```
=== Kubernetes Cluster Verification Report ===
Control Plane: Ready
Flannel CNI: Operational
Worker Nodes: X joined
Networking: Functional/Issues detected
DNS: Functional/Issues detected
============================================
```

---

### 5. kuber_plane_reset.yaml - Reset Control Plane
**Purpose:** Clean Kubernetes control plane for fresh setup

**Hosts:** `[masters]` ([control-plane-ip])

**Tags:** `kubernetes`, `k8s`, `reset`, `cleanup`, `master`

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml --tags reset
```

---

### 6. kuber_worker_reset.yaml - Reset Worker Nodes
**Purpose:** Clean Kubernetes worker nodes for fresh join

**Hosts:** `[workers_all]`

**Tags:** `kubernetes`, `k8s`, `reset`, `cleanup`, `worker`

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --tags reset
```

---

## Complete Setup Workflow

### First-Time Setup (Single Control Plane)

```bash
# 1. Install packages on all nodes
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes

# 2. Initialize control plane ([control-plane-ip])
# Includes automatic control-plane checks
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init

# 2.5 Install Flannel CNI (required before worker CNI checks are expected to pass)
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel

# 3. Join workers (all 4 workers)
# Includes automatic verification of each worker
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join

# 3.5 (Optional) Configure BGP router and install MetalLB (LoadBalancer)
# Recommended for WireGuard/L3 clusters.
#
# 1) Configure FRR on the BGP router host (e.g., [bgp-router-hostname])
ansible-playbook -i hosts_bay.ini bgp_router_manage.yaml --tags bgp
#
# 2) Install and configure MetalLB (BGP mode)
ansible-playbook -i hosts_bay.ini kuber_metallb_install.yaml --tags metallb

# Remove MetalLB (cleanup)
ansible-playbook -i hosts_bay.ini kuber_metallb_remove.yaml --tags remove

# Remove BGP router configuration (cleanup)
ansible-playbook -i hosts_bay.ini bgp_router_remove.yaml --tags remove

# 4. Full cluster verification (optional but recommended)
# Tests pod-to-pod connectivity, DNS, external access
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify
```

### Rolling Updates or Reconfiguration

```bash
# Reset control plane
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml --tags reset

# Reset specific workers
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_main --tags reset

# Re-run setup steps
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit workers_main --tags join
```

---

## Inventory Groups (hosts_bay.ini)

- `[planes]` - Control plane nodes ([control-plane-ip])
- `[workers_all]` - All worker nodes ([worker-main-ip], [worker-office-ip], [worker-super-ip])
- `[workers_main]` - Main workers ([worker-main-ip])
- `[workers_office]` - Office workers ([worker-office-ip])
- `[workers_super]` - Super workers ([worker-super-ip])
- `[workers_longhorn]` - Longhorn storage workers ([worker-longhorn-ip])
- `[masters]` - Master nodes (same as planes)

---

## Roles Structure

### roles/kuber_init/
Control plane initialization role with built-in verification
- `tasks/main.yaml` - Init and control-plane verification tasks
- `defaults/main.yaml` - Variables (pod CIDR, service CIDR, kubeadm settings)
- `templates/kubeadm-config.yaml.j2` - Dynamic kubeadm config
- `handlers/main.yaml` - Service restart handlers
- `meta/main.yaml` - Role metadata

### roles/kuber_join/
Worker node joining role with built-in verification
- `tasks/main.yaml` - Token generation, join, verification tasks
- `defaults/main.yaml` - Variables (control plane IP, port)
- `templates/kube-join.yaml.j2` - Dynamic join config
- `meta/main.yaml` - Role metadata

### roles/kuber_verify/
Comprehensive cluster verification role
- `tasks/main.yaml` - Main verification orchestration
- `tasks/verify_control_plane.yaml` - Control plane health checks
- `tasks/verify_workers.yaml` - Worker node status checks
- `tasks/verify_networking.yaml` - Network and DNS tests
- `defaults/main.yaml` - Verification configuration
- `meta/main.yaml` - Role metadata

---

## Verification Summary

### Automatic Verification
All playbooks include built-in verification steps:

**kuber_plane_init.yaml:**
✓ Control plane Ready status
✓ Kubernetes API access

**kuber_flannel_install.yaml:**
✓ Flannel daemonset rollout
✓ No mixed-CNI state

**kuber_worker_join.yaml:**
✓ Node visibility from control plane
✓ Node Ready status
✓ CNI daemon pod on worker

**kuber_verify.yaml:**
✓ Control plane health
✓ Worker node status
✓ Pod-to-pod connectivity
✓ DNS resolution
✓ External connectivity

### Manual Verification Commands
Run on control plane ([control-plane-ip]):

```bash
# Check cluster nodes
kubectl get nodes

# Check Flannel pods
kubectl get pods -n kube-flannel -l app=flannel

# Test network connectivity
kubectl run test-pod --image=nginx:alpine --restart=Never
kubectl exec test-pod -- wget -q -O- http://[your-username].google.com --spider
kubectl delete pod test-pod
```

---

## Troubleshooting

### Common Issues

**1. Control Plane Not Ready**
- Check Flannel pods: `kubectl get pods -n kube-flannel -l app=flannel`
- View logs: `kubectl logs -n kube-flannel -l app=flannel --tail=80`
- Reset and reinit: `kuber_plane_reset.yaml` → `kuber_plane_init.yaml`

**2. Worker Not Ready**
- Check worker node: `kubectl get node <worker-name> -o wide`
- Check Flannel pod on worker: `kubectl get pods -n kube-flannel -l app=flannel -o wide`
- View kubelet logs: `journalctl -u kubelet -f`
- Reset and rejoin: `kuber_worker_reset.yaml` → `kuber_worker_join.yaml`

**3. Network Issues**
- Run full verification: `kuber_verify.yaml`
- Check Flannel daemonset: `kubectl -n kube-flannel get ds kube-flannel-ds -o wide`
- Check CNI interfaces on node: `ip link show cni0 && ip link show flannel.1`
- Test DNS: `kubectl run dns-test --image=busybox --rm -it -- nslookup [k8s-service]`

**3.1 Kubernetes + WireGuard: UFW blocks pod egress (DNS/ACME fails)**

**Symptoms:**
- Traefik serves `TRAEFIK DEFAULT CERT`
- CoreDNS logs timeouts to upstream DNS over WireGuard
- Pod DNS lookups to upstream DNS over WireGuard time out while node `dig` works

**Root cause:** UFW (or a default FORWARD drop) blocks forwarded pod traffic (`cali*` interfaces) to `wg99`.

**Fix (repo default):** disable UFW on all Kubernetes nodes (planes + workers). The `kuber` role does this best-effort.

**Quick check (on the affected node):**
```bash
sudo systemctl is-active ufw || true
sudo iptables -S FORWARD
sudo iptables -L FORWARD -v -n --line-numbers
```

**3.2 ImagePullBackOff / ACME failures due to AAAA records (no IPv6 route)**

**Symptoms:**
- Pods cannot start because images fail to pull (e.g. `busybox`, `nginx`)
- containerd/crictl errors show `dial tcp [2600:...]:443: network is unreachable`
- ACME clients may fail if they pick IPv6 first

**Root cause:** upstream DNS returns AAAA records, but nodes do not have working IPv6 egress.
Some clients do not fall back cleanly to IPv4.

**Fix (recommended in this repo):** enable node-local dnsmasq on the node's `wg99` IP with `filter-AAAA`, and point
the node `/etc/resolv.conf` at that node IP. This is Kubernetes-safe when CoreDNS runs with `dnsPolicy: Default`
(CoreDNS forwards using the node's resolv.conf).

**Apply:**
```bash
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns

# CoreDNS pods need a restart to pick up updated node resolv.conf
kubectl -n kube-system rollout restart deploy/coredns
kubectl -n kube-system rollout status deploy/coredns
```

**Verify:**
```bash
sudo crictl pull docker.io/library/busybox:1.36

# Get CoreDNS (kube-dns) ClusterIP and query through it
KUBEDNS_IP=$(kubectl -n kube-system get svc kube-dns -o jsonpath='{.spec.clusterIP}')
dig +short @${KUBEDNS_IP} registry-1.docker.io AAAA   # should be empty after filtering
```

**4. Token Issues**
- Join playbook generates fresh token automatically
- No manual token management required
- Token is generated from control plane and used immediately

### Legacy Calico Path (optional)

**5. calico-typha CrashLoopBackOff - Port Already in Use**

**Symptoms:**
```
[PANIC] Failed to open listen socket error=listen tcp :5473: bind: address already in use
```

**Cause:** Multiple Typha pods scheduled on same node (autoscaler override or missing anti-affinity)

**Fix:**
```bash
# Check typha pods
kubectl get pods -n calico-system -o wide | grep typha

# Patch installation with required anti-affinity (already in playbooks)
kubectl patch installation default --type=merge -p '{"spec":{"typhaDeployment":{"spec":{"template":{"spec":{"affinity":{"podAntiAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":[{"labelSelector":{"matchLabels":{"k8s-app":"calico-typha"}},"topologyKey":"kubernetes.io/hostname"}]}}}}}}}}'

# Kill orphaned typha process if stuck
ssh <node> "pgrep -a typha"
ssh <node> "sudo kill -9 <pid>"
```

**6. Pods Cannot Reach Kubernetes API - Timeout**

**Symptoms:**
```
dial tcp [k8s-api-vip]:443: i/o timeout
```

**Cause:** `natOutgoing: Disabled` in Calico IPPool - pods can't reach node WireGuard IPs

**Fix:**
```bash
# Enable NAT outgoing
kubectl patch ippool default-ip4-ippool --type=merge -p '{"spec":{"natOutgoing":true}}'

# Verify
kubectl get ippool -o yaml | grep natOutgoing

# Test from a pod
kubectl run test --image=busybox --rm -it -- wget -qO- --timeout=5 https://[k8s-api-vip]:443/healthz
```

**7. metallb-speaker CrashLoopBackOff - Port Already in Use**

**Symptoms:**
```
failed to create memberlist: listen tcp [node-ip]:[metallb-memberlist-port]: bind: address already in use
```

**Cause:** Orphaned speaker process from previous crashed pod

**Fix:**
```bash
# Find orphaned speaker process
ssh <node> "pgrep -a speaker"

# Kill it
ssh <node> "sudo kill -9 <pid>"

# Delete crashed pod to trigger restart
kubectl delete pod -n metallb-system <speaker-pod> --force --grace-period=0
```

**8. MetalLB/FRR BGP peers not establishing**

**Symptoms:**
```
metallb-speaker: failed to establish BGP session to peer [bgp-router-wg-ip]
```

**Cause:** WireGuard path down, firewall blocking TCP/179, or FRR neighbor mismatch

**Fix:**
```bash
# Check WireGuard connectivity
wg show wg99

# Check MetalLB speakers
kubectl -n metallb-system get pods -o wide
kubectl -n metallb-system logs -l component=speaker --tail=80

# Confirm MetalLB BGP peers and advertisements
kubectl get bgppeers.metallb.io -A -o yaml
kubectl get bgpadvertisements.metallb.io -A -o yaml

# Test BGP port from a Kubernetes node to FRR peer
nc -zv [bgp-router-wg-ip] 179

# On FRR router host, verify neighbors
vtysh -c "show bgp summary"
```

**9. MTU Issues - Packet Fragmentation**

**Symptoms:**
- Slow network performance
- Large file transfers fail
- TCP connections hang

**Cause:** MTU too high for WireGuard + VXLAN encapsulation

**Fix:**
```bash
# Check current MTU
kubectl get installation default -o jsonpath='{.spec.calicoNetwork.mtu}'

# Should start at 1360 for WireGuard + VXLAN
# WireGuard: 1420, VXLAN: -50, safety: -10 = 1360

# Patch if needed
kubectl patch installation default --type=merge -p '{"spec":{"calicoNetwork":{"mtu":1360}}}'
```

---

## Security Notes

- SSH access required to all nodes
- Root/ sudo access required for package installation and system configuration
- Flannel manifest is managed by `kuber_flannel_install.yaml`
- Join tokens are generated dynamically (ttl=0 for one-time use)
- No hardcoded tokens in playbooks

---

## Testing

### Unit Tests
```bash
# Test variable definitions
ansible-playbook tests/unit/test_kuber_init_variables.yaml
ansible-playbook tests/unit/test_kuber_join_variables.yaml
ansible-playbook tests/unit/test_kuber_verify_variables.yaml
```

### Integration Tests
```bash
# Syntax check
ansible-playbook --syntax-check kuber_plane_init.yaml
ansible-playbook --syntax-check kuber_worker_join.yaml
ansible-playbook --syntax-check kuber_verify.yaml

# Lint
ansible-lint kuber_plane_init.yaml
ansible-lint kuber_worker_join.yaml
ansible-lint kuber_verify.yaml
```

### Dry Run
```bash
# Check mode (no changes made)
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --check
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --check
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --check
```

---

## Tags Reference

All playbooks support the following tags for selective execution:

- `kubernetes` - All Kubernetes-related tasks
- `k8s` - Shorthand for kubernetes
- `init` - Control plane initialization
- `join` - Worker node joining
- `verify` - Cluster health verification
- `test` - Network and DNS testing
- `plane` - Control plane operations
- `worker` - Worker node operations
- `cni` - CNI-related tasks
- `nfd` - Node Feature Discovery installation
- `node_info` - Node metadata labeling tasks
- `k9s` - Node metadata tasks for K9s visibility/filtering
- `metallb` - MetalLB install/config (LoadBalancer)
- `bgp` - BGP router configuration
- `reset` - Reset/cleanup operations

---

## Additional Information

- Kubernetes version: v1.35 (from pkgs.k8s.io)
- Container runtime: containerd with systemd cgroup driver
- CNI default: Flannel (Legacy Calico Path (optional))
- Pod CIDR: [internal-ip]/16
- Service CIDR: [internal-ip]/16
- Ansible version: 2.16+
- OS: Debian bullseye/bookworm, Ubuntu focal/jammy
