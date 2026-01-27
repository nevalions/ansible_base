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

## Usage

### Reset worker nodes (preserves container images)

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml
```

### Reset control plane nodes (preserves container images)

```bash
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml
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

- `remove_container_images` (default: `false`) - Set to `true` to remove all container images. Note: This will increase join time as images need to be re-downloaded.

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
