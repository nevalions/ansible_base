# kuber_join

Join worker nodes to Kubernetes cluster using kubeadm.

## Overview

This role joins worker nodes to an existing Kubernetes cluster:

- Generates join token from control plane
- Joins worker node to cluster with kubeadm
- Configures kubelet node IP for WireGuard network
- Verifies node is visible from control plane
- Supports both VIP and direct control plane endpoints
- Validates CNI prerequisites before join (loopback plugin, stale interfaces)
- Verifies node-local DNS after join and auto-recovers kube-proxy when enabled

## Requirements

- Kubernetes packages installed (kubelet, kubeadm, kubectl)
- Control plane already initialized with `kuber_init`
- Network connectivity to control plane
- Vault variables defined in `vault_secrets.yml`

## Role Variables

### Control Plane Configuration

- `kuber_join_control_plane_host` - Control plane host (default: `VIP`)
- `kuber_join_control_plane_ip` - Control plane IP or VIP (from vault)
- `kuber_join_api_port` - Kubernetes API port (from vault)

### Node Configuration

- `kuber_join_token_ttl` - Join token TTL (default: `0` for never expire)
- `kuber_join_kubelet_extra_args` - Kubelet extra arguments (node IP from WireGuard)

### API Version

- `kubeadm_api_version` - kubeadm API version (default: `v1beta4`)

### CNI Validation and Post-Join DNS Probe

- `kuber_join_cni_type` - CNI type used for post-join checks (default: `flannel`)
- `kuber_join_cni_namespace` - CNI namespace selector target
- `kuber_join_cni_label_selector` - CNI daemon pod selector
- `kuber_join_node_dns_probe_enabled` - Enable node-local DNS probe after join (default: `true`)
- `kuber_join_node_dns_probe_domain` - Domain probed via kube-dns (default: `kubernetes.default.svc.cluster.local`)
- `kuber_join_node_dns_auto_repair` - Restart kube-proxy on failed DNS probe and retry (default: `true`)

## Vault Variables

Required in `vault_secrets.yml`:

```yaml
vault_k8s_api_vip: "[vip-address]"
vault_k8s_api_port: "[k8s-api-port]"
vault_interface: "wg99"
```

### VIP Usage (Recommended)

When `kuber_join_control_plane_host: VIP`, the role will:
1. Find control plane hosts from inventory group `planes_all`
2. Generate join token from first control plane
3. Join worker to cluster using VIP as endpoint

### Direct Control Plane

To join to specific control plane:

```yaml
kuber_join_control_plane_host: "[control-plane-hostname]"
```

## Check Mode

This role supports Ansible check mode (`--check`):

- Token generation runs even in check mode (to display what token would be used)
- Actual join and labeling tasks are skipped in check mode

```bash
# Preview what would happen
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit [worker-hostname] --check
```

## Usage

### Playbook

```bash
# Join single worker
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit [worker-hostname]

# Join all workers
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
```

### Rejoin Worker (minimal cleanup)

For rejoining a worker without full reset (preserves packages, containerd, CNI):

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_rejoin.yaml --limit [worker-hostname]
```

### Direct role usage

```yaml
- hosts: workers
  roles:
    - kuber_join
```

## Tasks

1. Check if node is already joined to a cluster
2. Assert control plane inventory group exists (when using VIP)
3. Generate kubeadm join token from control plane
4. Parse join command to extract token and CA cert hash
5. Create kubeadm join configuration
6. Join worker node to cluster
7. Wait for kubelet to be ready
8. Run post-join DNS probe on the joined node
9. Optionally recycle kube-proxy on that node and retry probe
10. Verify node is visible from control plane
11. Display join success message

## Verification

After running this role:

- Worker node should be joined to cluster
- Node should be visible from control plane
- Kubelet service should be active
- Node status should be Ready (after initialization)

Run `kuber_verify.yaml` for full cluster health check.

## Dependencies

- `kuber` role (installs Kubernetes packages)
- `wireguard` role (WireGuard VPN for node IP)
- Control plane initialized with `kuber_init`

## Tags

- `kubernetes` - Kubernetes-related tasks
- `k8s` - Kubernetes tasks (alias)
- `join` - Worker join tasks
- `worker` - Worker node tasks

## Troubleshooting

**Node already joined error:**
```bash
# Option 1: Full reset (removes packages, config, CNI)
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit [worker-hostname]

# Option 2: Soft reset (keeps packages, removes config)
ansible-playbook -i hosts_bay.ini kuber_worker_soft_reset.yaml --limit [worker-hostname]

# Option 3: Rejoin only (minimal - keeps packages, containerd, CNI)
ansible-playbook -i hosts_bay.ini kuber_worker_rejoin.yaml --limit [worker-hostname]

# Then re-join (if using reset options 1 or 2)
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --limit [worker-hostname]
```

**VIP not found error:**
Ensure inventory has `planes_all` group with control plane hosts:

```ini
[planes_all]
plane1 ansible_host=[plane1-ip]
plane2 ansible_host=[plane2-ip]
```

**Join failed error:**
Check network connectivity and firewall rules:
- Ensure worker can reach control plane API port (default: 6443)
- Ensure WireGuard network is configured
- Check control plane is Ready
