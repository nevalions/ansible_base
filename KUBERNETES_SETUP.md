# Kubernetes Cluster Setup with Ansible

> **Quick Start:** For complete deployment order from scratch, see [KUBERNETES_DEPLOYMENT_ORDER.md](KUBERNETES_DEPLOYMENT_ORDER.md)

## Overview

This Ansible project provides automated Kubernetes cluster setup with Calico CNI networking over WireGuard VPN.

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
- **Calico CNI**: Pod networking with IPIP encapsulation over WireGuard

**Scalability:**
- Start with single control plane ([plane-hostname])
- Add additional control planes by updating `vault_k8s_control_planes`
- Keepalived automatically detects healthy planes and routes traffic accordingly

---

## WireGuard + Calico IPIP Network Requirements

Running Kubernetes with Calico CNI over WireGuard requires specific configuration to ensure proper pod networking.

### Critical Configuration

| Setting | Required Value | Why |
|---------|---------------|-----|
| `natOutgoing` | `true` | Pods must NAT to reach node WireGuard IPs ([vpn-network-cidr]) |
| `vault_ipPools_encapsulation` | `IPIP` | Required for L3 WireGuard networks |
| `mtu` | `1380` | WireGuard (1420) - IPIP (20) - safety (20) |
| `vault_calico_typha_replicas` | `1` | Prevents port conflicts on small clusters |

### Network Flow

```
Pod ([pod-network-cidr]) → IPIP Tunnel → WireGuard ([vpn-network-cidr]) → Remote Node
                      ↓
              NAT (MASQUERADE)
                      ↓
           Source becomes node's WireGuard IP
```

### Why natOutgoing is Critical

Without `natOutgoing: true`:
- Pods can reach other pods via IPIP tunnels ✓
- Pods CANNOT reach node WireGuard IPs ([vpn-network-cidr]) ✗
- Pods CANNOT reach Kubernetes API ([kube-service-cidr] → [control-plane-wg-ip]:6443) ✗
- MetalLB controller crashes with API timeout ✗

### Typha Anti-Affinity

Calico Typha uses `hostNetwork: true` and binds to port 5473. Without proper anti-affinity, multiple Typha pods can be scheduled on the same node, causing:

```
[PANIC] Failed to open listen socket error=listen tcp :5473: bind: address already in use
```

The playbooks now configure **required** pod anti-affinity:

```yaml
typhaDeployment:
  spec:
    template:
      spec:
        affinity:
          podAntiAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              - labelSelector:
                  matchLabels:
                    k8s-app: calico-typha
                topologyKey: kubernetes.io/hostname
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
- Loads required kernel modules (overlay, br_netfilter)
- Configures IP forwarding and bridge networking
- Configures containerd cgroup driver (systemd)
- Disables UFW on Kubernetes nodes (to avoid Calico/WireGuard forwarding issues)

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
**Purpose:** Initialize Kubernetes control plane with kubeadm and install Calico CNI

**Hosts:** `[planes]` ([control-plane-ip])

**Tags:** `kubernetes`, `k8s`, `init`, `plane`, `cni`

**What it does:**
- Checks if cluster is already initialized
- Copies kubeadm configuration (template with dynamic IPs)
- Runs `kubeadm init --config=kubeadm-config.yaml`
- Copies admin.conf to user's .kube/config
- Installs Calico Tigera Operator
- Waits for Tigera Operator to be ready
 - Applies Calico custom resources (from `/path/to/calico/custom-resources.yaml`)
 - Waits for Calico pods to be ready
- **VERIFICATION:** Validates control plane is Ready
- **VERIFICATION:** Checks Tigera Operator is Running
- **VERIFICATION:** Displays Calico IP pools
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
calico_version: "v3.31.3"
calico_tigera_operator_url: "https://raw.githubusercontent.com/projectcalico/calico/{{ calico_version }}/manifests/tigera-operator.yaml"
calico_custom_resources_src: "/path/to/calico/custom-resources.yaml"
```

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
```

**Verification included:**
✓ Control plane node Ready status
✓ Tigera Operator Running status
✓ Calico pods status
✓ Calico IP pools configuration

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
- **VERIFICATION:** Checks Calico pod on worker
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
✓ Calico pod on worker node
✓ Join summary

---

### 4. kuber_verify.yaml - Full Cluster Health Check
**Purpose:** Comprehensive verification of Kubernetes cluster health, Calico networking, and worker connectivity

**Hosts:** `[planes]` ([control-plane-ip])

**Tags:** `kubernetes`, `k8s`, `verify`, `test`

**What it does:**

#### Control Plane Verification
- Gets all cluster nodes
- Checks control plane node Ready status
- Gets all Calico node pods
- Gets Tigera Operator pods
- Verifies Tigera Operator is Running
- Waits for all Calico node pods to be Running
- Displays cluster info
- Gets Calico Installation status
- Gets Calico FelixConfiguration
- Gets Calico IP pools

#### Worker Verification
- Gets all worker nodes
- Counts worker nodes
- Checks if all worker nodes are Ready
- Gets Calico pods on all nodes
- Verifies Calico pods count matches cluster nodes
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
Calico CNI: Operational
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
# Includes automatic verification of control plane and Calico
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init

# 2.5 (Optional) Move Calico BGP off TCP/179 (needed for MetalLB BGP)
# Calico (BIRD) binds TCP/179 by default; MetalLB BGP also needs TCP/179.
ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml --tags calico,bgp

# 3. Join workers (all 4 workers)
# Includes automatic verification of each worker
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join

# 3.5 (Optional) Configure BGP router and install MetalLB (LoadBalancer)
# Recommended for WireGuard/L3 clusters. Keeps Calico IPIP unchanged.
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
- `tasks/main.yaml` - Init, Calico install, verification tasks
- `defaults/main.yaml` - Variables (pod CIDR, service CIDR, Calico version)
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
✓ Tigera Operator Running status
✓ Calico pods status
✓ Calico IP pools

**kuber_worker_join.yaml:**
✓ Node visibility from control plane
✓ Node Ready status
✓ Calico pod on worker

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

# Check Calico pods
kubectl get pods -n kube-system -l k8s-app=calico-node

# Check Tigera Operator
kubectl get pods -n tigera-operator

# Check Calico IP pools
kubectl get ippool -o wide

# Check Calico configuration
kubectl get installation -o yaml
kubectl get felixconfiguration default -o yaml

# Test network connectivity
kubectl run test-pod --image=nginx:alpine --restart=Never
kubectl exec test-pod -- wget -q -O- http://[your-username].google.com --spider
kubectl delete pod test-pod
```

---

## Troubleshooting

### Common Issues

**1. Control Plane Not Ready**
- Check Calico pods: `kubectl get pods -n kube-system -l k8s-app=calico-node`
- Check Tigera Operator: `kubectl get pods -n tigera-operator`
- View logs: `kubectl logs -n tigera-operator <pod-name>`
- Reset and reinit: `kuber_plane_reset.yaml` → `kuber_plane_init.yaml`

**2. Worker Not Ready**
- Check worker node: `kubectl get node <worker-name> -o wide`
- Check Calico pod on worker: `kubectl get pods -n kube-system -l k8s-app=calico-node -o wide`
- View kubelet logs: `journalctl -u kubelet -f`
- Reset and rejoin: `kuber_worker_reset.yaml` → `kuber_worker_join.yaml`

**3. Network Issues**
- Run full verification: `kuber_verify.yaml`
- Check Calico IP pools: `kubectl get ippool -o wide`
- Check Calico configuration: `kubectl get installation -o yaml`
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

### WireGuard + Calico IPIP Issues

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

**8. BGP Peers Not Establishing**

**Symptoms:**
```
BIRD is not ready: BGP not established with [node-ip-1],[node-ip-2]
```

**Cause:** WireGuard tunnel not up, firewall blocking, or BGP port conflict

**Fix:**
```bash
# Check WireGuard connectivity
wg show wg99

# Test BGP port from node
nc -zv [node-ip] [bgp-port]

# Check Calico BGP config
kubectl get bgpconfigurations default -o yaml

# If Calico BGP conflicts with MetalLB, move Calico to different port
kubectl patch bgpconfigurations default --type=merge -p '{"spec":{"listenPort":178}}'
```

**9. MTU Issues - Packet Fragmentation**

**Symptoms:**
- Slow network performance
- Large file transfers fail
- TCP connections hang

**Cause:** MTU too high for WireGuard + IPIP encapsulation

**Fix:**
```bash
# Check current MTU
kubectl get installation default -o jsonpath='{.spec.calicoNetwork.mtu}'

# Should be 1380 for WireGuard + IPIP
# WireGuard: 1420, IPIP: -20, safety: -20 = 1380

# Patch if needed
kubectl patch installation default --type=merge -p '{"spec":{"calicoNetwork":{"mtu":1380}}}'
```

---

## Security Notes

- SSH access required to all nodes
- Root/ sudo access required for package installation and system configuration
- Calico custom resources file must be accessible on Ansible controller
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
- `cni` - Calico CNI installation
- `metallb` - MetalLB install/config (LoadBalancer)
- `bgp` - BGP router configuration
- `reset` - Reset/cleanup operations

---

## Additional Information

- Kubernetes version: v1.35 (from pkgs.k8s.io)
- Container runtime: containerd with systemd cgroup driver
- CNI: Calico v3.31.3 (Tigera Operator)
- Pod CIDR: [internal-ip]/16
- Service CIDR: [internal-ip]/16
- Ansible version: 2.16+
- OS: Debian bullseye/bookworm, Ubuntu focal/jammy
