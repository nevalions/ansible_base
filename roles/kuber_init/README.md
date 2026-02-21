# kuber_init

Initialize Kubernetes control plane with kubeadm and Calico CNI.

## Overview

This role performs the complete initialization of a Kubernetes control plane node:

- Initializes Kubernetes cluster with kubeadm
- Configures containerd cgroup driver
- Installs Calico CNI with Tigera Operator
- Optionally installs Node Feature Discovery (NFD) for node feature labels
- Configures Typha deployment with required anti-affinity
- Configures kubeadm API version and control plane endpoint
- Verifies cluster readiness and Calico installation
- Sets up kubeconfig for admin user

## WireGuard + Calico IPIP Requirements

When running Kubernetes over WireGuard VPN, specific Calico settings are required:

| Setting | Value | Description |
|---------|-------|-------------|
| `natOutgoing` | `true` | **CRITICAL**: Pods must NAT to reach WireGuard IPs |
| `vault_ipPools_encapsulation` | `IPIP` | Required for L3 networks |
| `mtu` | `1380` | WireGuard (1420) - IPIP (20) - safety (20) |
| `vault_calico_typha_replicas` | `1` | Prevents port conflicts |

### Typha Anti-Affinity

This role configures **required** pod anti-affinity for Typha to prevent port 5473 conflicts:

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

Without this, multiple Typha pods can be scheduled on the same node, causing CrashLoopBackOff.

## Requirements

- Kubernetes packages installed (kubelet, kubeadm, kubectl)
- Containerd configured and running
- Network firewall configured for Kubernetes ports
- WireGuard VPN configured and connected
- Vault variables defined in `vault_secrets.yml`

## Role Variables

### Network Configuration (from vault)

- `kubeadm_pod_subnet` - Pod network CIDR (e.g., `10.244.0.0/16`)
- `kubeadm_service_subnet` - Service network CIDR (e.g., `10.96.0.0/12`)
- `kubeadm_control_plane_endpoint` - Control plane endpoint (VIP address:port)
- `kubeadm_api_server_advertise_address` - WireGuard IP for API server

### Calico CNI Configuration

- `calico_version` - Calico version (default: `v3.31.3`)
- `calico_ippool_name` - IP pool name (default: `default-ipv4-ippool`)
- `calico_ippool_cidr` - IP pool CIDR (uses pod subnet)
- `calico_encapsulation` - Encapsulation type (default: `IPIP` for WireGuard)
- `calico_nat_outgoing` - NAT outgoing traffic (default: `true`) **CRITICAL for WireGuard**
- `calico_node_selector` - Node selector for Calico (default: `all()`)
- `calico_block_size` - IP block size (default: `26`)
- `calico_mtu` - MTU size (default: `1380` for WireGuard + IPIP)
- `calico_node_address_interface` - Network interface (default: `wg99`)
- `calico_typha_replicas` - Typha replicas (default: `1` for small clusters)

### Kubeconfig Configuration

- `kubeconfig_user` - Admin user (default: current user)
- `kubeconfig_user_home` - User home directory
- `kubeconfig_path` - Kubeconfig path (default: `~/.kube/config`)

### API Version

- `kubeadm_api_version` - kubeadm API version (default: `v1beta4`)

### Node Feature Discovery (NFD)

- `k8s_node_info_enabled` - Enable NFD install during init (default: `true`)
- `nfd_version` - NFD version (default: `v0.18.2`)
- `nfd_kustomize_ref` - NFD kustomize ref URL
- `nfd_namespace` - NFD namespace (default: `node-feature-discovery`)
- `nfd_master_deployment_name` - NFD master deployment name (default: `nfd-master`)
- `nfd_worker_daemonset_name` - NFD worker daemonset name (default: `nfd-worker`)

## Vault Variables

Required in `vault_secrets.yml`:

```yaml
vault_k8s_pod_subnet: "10.244.0.0/16"
vault_k8s_service_subnet: "10.96.0.0/12"
vault_k8s_api_vip: "[vip-address]"
vault_k8s_api_port: "[k8s-api-port]"
vault_k8s_control_planes:
  - name: "control-plane-1"
    wireguard_ip: "[control-plane-wg-ip]"
  - name: "control-plane-2"
    wireguard_ip: "[control-plane-wg-ip-2]"
vault_calico_version: "v3.31.3"
vault_interface: "wg99"
vault_admin_user: "[admin-username]"
```

## Usage

### Playbook

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml
```

### Direct role usage

```yaml
- hosts: control_planes
  roles:
    - kuber_init
```

## Tasks

1. Check if Kubernetes is already initialized
2. Configure containerd cgroup driver
3. Create kubeadm configuration
4. Initialize cluster with kubeadm
5. Set up kubeconfig for admin user
6. Install Calico Tigera Operator
7. Configure Calico IP pool
8. Wait for Calico pods to be ready
9. Optionally install and verify NFD rollout (run once from the init play)
10. Verify cluster node status
11. Verify Tigera Operator is running
12. Display initialization summary

## Troubleshooting

### Common Issues

**Felix (Calico node agent) crashes with OOM:**
- **Symptoms:** calico-node pods in CrashLoopBackOff, BIRD/BGP instability
- **Root Cause:** Felix has no memory limits; kernel OOM killer terminates it
- **Solution:** Added Felix resource limits in calico-custom-resources.yaml.j2
  - Memory request: 256Mi, limit: 2048Mi
  - CPU request: 100m, limit: 500m
  - Applied via `componentResources.node` in Installation CRD

**BGP connection failures:**
- **Symptoms:** metallb-speaker crashes, calico-typha can't connect to Felix
- **Root Cause:** UFW INPUT chain default DROP policy blocks BGP port 179
- **Solution:** Disable UFW during CNI setup or configure UFW to allow BGP
  - Implemented via `Disable UFW` task after Calico installation

**CSI node driver socket connection failures:**
- **Symptoms:** csi-node-driver pods with Exit Code 2, socket connection refused
- **Root Cause:** Temporary instability after Felix/BIRD crashes
- **Solution:** Ensure Felix has stable resource limits before CSI starts

### WireGuard + Calico IPIP Issues

**Typha CrashLoopBackOff - Port 5473 in use:**
- **Symptoms:** `listen tcp :5473: bind: address already in use`
- **Root Cause:** Multiple Typha pods on same node (autoscaler or missing anti-affinity)
- **Solution:** This role now includes required anti-affinity in Installation CR
  ```bash
  # Kill orphaned process if needed
  ssh <node> "pgrep -a typha && sudo kill -9 $(pgrep typha)"
  ```

**Pods cannot reach Kubernetes API:**
- **Symptoms:** `dial tcp 10.96.0.1:443: i/o timeout`
- **Root Cause:** `natOutgoing: Disabled` - pods can't reach WireGuard IPs
- **Solution:** Ensure `natOutgoing: true` in vault_secrets.yml
  ```bash
  kubectl patch ippool default-ip4-ippool --type=merge -p '{"spec":{"natOutgoing":true}}'
  ```

**MetalLB speaker port conflict:**
- **Symptoms:** `listen tcp [node-ip]:7946: bind: address already in use`
- **Root Cause:** Orphaned speaker process from crashed pod
- **Solution:** Kill orphaned process and restart pod
  ```bash
  ssh <node> "pgrep -a speaker && sudo kill -9 $(pgrep speaker)"
  kubectl delete pod -n metallb-system <speaker-pod> --force
  ```

### Remediation Commands

```bash
# Fix Felix OOM crashes by adding resource limits
kubectl patch ds calico-node -n calico-system -p '{"spec":{"template":{"spec":{"containers":[{"name":"calico-node","resources":{"limits":{"memory":"2048Mi","cpu":"500m"},"requests":{"memory":"256Mi","cpu":"100m"}}]}}}'

# Disable UFW to allow BGP
sudo systemctl stop ufw && sudo systemctl disable ufw

# Check Felix resource usage
kubectl top pod -n calico-system calico-node --containers

# Monitor BGP status
kubectl logs -n calico-system calico-node-<pod> -c calico-node --tail=50 | grep -iE 'BGP|bird|mesh'

# Fix NAT outgoing for WireGuard
kubectl patch ippool default-ip4-ippool --type=merge -p '{"spec":{"natOutgoing":true}}'

# Add Typha anti-affinity (already in playbooks)
kubectl patch installation default --type=merge -p '{"spec":{"typhaDeployment":{"spec":{"template":{"spec":{"affinity":{"podAntiAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":[{"labelSelector":{"matchLabels":{"k8s-app":"calico-typha"}},"topologyKey":"kubernetes.io/hostname"}]}}}}}}}}'
```

## Verification

After running this role:

- Control plane node should be Ready
- Calico pods should be Running
- Tigera Operator should be Running
- Kubeconfig should be configured at `~/.kube/config`
- Kubernetes API should be accessible via VIP

Run `kuber_verify.yaml` for full cluster health check.

## Dependencies

- `kuber` role (installs Kubernetes packages)
- `wireguard` role (WireGuard VPN for VIP)

## Tags

- `kubernetes` - Kubernetes-related tasks
- `k8s` - Kubernetes tasks (alias)
- `init` - Control plane initialization
- `plane` - Control plane tasks
- `cni` - CNI installation tasks
- `addon` - Optional addon installation tasks
- `nfd` - Node Feature Discovery tasks
- `node_info` - Node metadata collection tasks
- `k9s` - Node metadata tasks relevant for K9s filtering/viewing
