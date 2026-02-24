# kuber_init

Initialize Kubernetes control plane with kubeadm.

## Overview

This role performs the complete initialization of a Kubernetes control plane node:

- Initializes Kubernetes cluster with kubeadm
- Configures containerd cgroup driver
- Leaves CNI installation to dedicated playbooks (Flannel default)
- Optionally installs Node Feature Discovery (NFD) for node feature labels
- Configures kubeadm API version and control plane endpoint
- Verifies control-plane readiness
- Sets up kubeconfig for admin user

## CNI Workflow (Flannel Default)

This role does not install a CNI plugin. Use dedicated CNI playbooks after init:

```bash
# Default CNI path (recommended)
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel

# Optional legacy path
# ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml --tags calico,bgp
```

For Flannel over WireGuard, keep pod subnet and MTU consistent across kubeadm and Flannel values.

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

### CNI Selection

- `vault_k8s_cni_type` - Active CNI for join/verify checks (default: `flannel`)

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
vault_k8s_cni_type: "flannel"
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
6. Optionally install and verify NFD rollout (run once from the init play)
7. Verify cluster node status
8. Display initialization summary

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

### Legacy Calico Path (optional)

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
- Kubeconfig should be configured at `~/.kube/config`
- Kubernetes API should be accessible via VIP

Then install CNI (Flannel default) and run `kuber_verify.yaml`.

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
