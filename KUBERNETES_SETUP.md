# Kubernetes Cluster Setup with Ansible

## Overview

This Ansible project provides automated Kubernetes cluster setup with Calico CNI networking.

## Playbooks

### 1. kuber.yaml - Install Kubernetes Packages
**Purpose:** Install Kubernetes components (kubelet, kubeadm, kubectl, containerd) and configure system prerequisites

**Hosts:** `[workers_super]` (currently targets [worker-super-ip])

**Tags:** `kubernetes`, `k8s`, `install`, `cluster`

**What it does:**
- Updates package lists
- Adds Kubernetes GPG key and repository
- Installs kubelet, kubeadm, kubectl, containerd
- Holds Kubernetes packages to prevent automatic updates
- Disables swap
- Loads required kernel modules (overlay, br_netfilter)
- Configures IP forwarding and bridge networking
- Configures containerd cgroup driver (systemd)
- Configures UFW firewall with required ports
- Enables UFW

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes
```

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
- Applies Calico custom resources (from `/home/[your-username]/kuber-bay/kube/calico/`)
- Waits for Calico pods to be ready
- **VERIFICATION:** Validates control plane is Ready
- **VERIFICATION:** Checks Tigera Operator is Running
- **VERIFICATION:** Displays Calico IP pools
- **VERIFICATION:** Displays initialization summary

**Variables** (roles/kuber_init/defaults/main.yaml):
```yaml
kubeadm_pod_subnet: "[internal-ip]/16"
kubeadm_service_subnet: "[internal-ip]/16"
kubeadm_control_plane_endpoint: "{{ ansible_default_ipv4.address }}:6443"
kubeadm_api_server_advertise_address: "{{ ansible_default_ipv4.address }}"
calico_tigera_operator_url: "https://raw.githubusercontent.com/projectcalico/calico/v3.28.1/manifests/tigera-operator.yaml"
calico_custom_resources_src: "/home/[your-username]/kuber-bay/kube/calico/2-custom-resources.yaml"
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
kuber_join_control_plane_host: "{{ groups['planes'][0] }}"
kuber_join_control_plane_ip: "{{ hostvars[kuber_join_control_plane_host]['ansible_default_ipv4']['address'] }}"
kuber_join_api_port: "6443"
kuber_join_token_ttl: "0"
```

**Usage:**
```bash
# Join all workers
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join

# Join specific worker groups
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit workers_main --tags join
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit workers_office --tags join
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

# 3. Join workers (all 4 workers)
# Includes automatic verification of each worker
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join

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

**4. Token Issues**
- Join playbook generates fresh token automatically
- No manual token management required
- Token is generated from control plane and used immediately

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
- `reset` - Reset/cleanup operations

---

## Additional Information

- Kubernetes version: v1.30 (from pkgs.k8s.io)
- Container runtime: containerd with systemd cgroup driver
- CNI: Calico v3.28.1 (Tigera Operator)
- Pod CIDR: [internal-ip]/16
- Service CIDR: [internal-ip]/16
- Ansible version: 2.16+
- OS: Debian bullseye/bookworm, Ubuntu focal/jammy
