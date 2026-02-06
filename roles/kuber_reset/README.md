# Kubernetes Node Reset Role

This role completely cleans a Kubernetes node (worker or control plane) to prepare it for a fresh `kubeadm join` or `kubeadm init` operation.

## What It Cleans

- Kubernetes cluster configuration (`kubeadm reset`)
- All pods and containers
- CNI plugins and network configurations (Calico, Flannel, etc.)
- Kubernetes data directories
- Network interfaces and iptables rules
- Containerd data
- All Kubernetes-related namespaces
- **Best-effort** cleanup of CNI network namespace mounts (see "Orphaned Network Namespaces" below)

## Usage

### Reset worker nodes (preserves container images)

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml
```

### Reset control plane nodes (preserves container images)

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml
```

### Soft reset control plane (preserve packages)

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_soft_reset.yaml
```

### Remove container images as well

```bash
# Worker nodes
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml -e "remove_container_images=true"

# Control plane nodes
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml -e "remove_container_images=true"
```

### Target specific worker groups

```bash
# Main workers
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_main

# Office workers  
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_office

# Super worker
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_super

# Specific masters
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml --limit master1
```

## Variables

- `remove_container_images` (default: `true`) - Set to `true` to remove all container images. Note: This will increase join time as images need to be re-downloaded.
- `remove_kubernetes_packages` (default: `true`) - Set to `false` to keep kubelet/kubeadm/kubectl installed.

## What Happens After Reset

1. Containerd service is restarted
2. Node is ready for a fresh `kubeadm join`
3. If container images were preserved, they remain available

## Safety Notes
 
- This operation is destructive
- Stops all running pods on the target nodes
- Removes all Kubernetes configuration (including etcd data on control plane)
- Ensure you have proper backups before running
- Run against correct target group only (workers or masters)
- Control plane reset will remove etcd data and cluster state

## Orphaned Network Namespaces

### What They Are

After running `kubeadm reset`, you may see warnings about **orphaned CNI network namespace mounts**:

```
WARNING: Orphaned CNI Network Namespaces Detected
Found 5 orphaned network namespace mount(s)
```

These are **systemd mount units** (`run-netns-cni-*.mount`) that reference `nsfs` (network namespace filesystem) mounts under `/run/netns/cni-*`.

### Why They Persist

According to Kubernetes documentation:
- `kubeadm reset` is a **"best-effort"** cleanup tool
- It does NOT clean up:
  - Network namespace mounts (nsfs)
  - Systemd mount unit references
  - IPVS, iptables, nftables rules
  - CNI configuration directories

These orphaned mounts occur when CNI plugin teardown fails or when network namespaces are created by pods that were terminated abnormally.

### Are They Harmful?

**No, they are harmless**:
- They DO NOT interfere with Kubernetes initialization
- They DO NOT interfere with cluster join operations
- They are stale systemd references only
- No actual network resources are held
- Kubernetes ignores them on cluster startup

### How to Remove Them Completely

If you want a completely clean system without orphaned references, reboot the node:

```bash
sudo reboot
```

After reboot, all orphaned `nsfs` mounts will be gone.

### Manual Cleanup (Without Reboot)

The role attempts programmatic cleanup, but some `nsfs` mounts may still require manual intervention:

```bash
# 1. List orphaned mounts
systemctl list-units --all --type=mount | grep 'run-netns-cni'

# 2. Stop each mount unit
sudo systemctl stop run-netns-cni-<hash>.mount

# 3. Force lazy unmount
sudo umount -l /run/netns/cni-<hash>

# 4. Delete namespace references
sudo ip netns delete cni-<hash>

# 5. Remove namespace directories
sudo rm -rf /run/netns/cni-*
```

### Production Recommendation

**Accept the orphaned mounts and proceed** unless:
- You have a maintenance window for reboot
- You need a completely clean system for debugging
- You're redeploying the node from scratch

In production environments, orphaned mounts are safe to ignore and do not require immediate remediation.

## Example Workflow

```bash
# 1. Reset control plane
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml

# 2. Initialize new control plane (on master node)
# kubeadm init --config=kubeadm-config.yaml

# 3. Reset workers
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml

# 4. Get fresh join command from control plane
# On control plane:
# kubeadm token create --print-join-command

# 5. Join workers to cluster
# Execute the join command on each worker or via automation
```
