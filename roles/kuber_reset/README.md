# Kubernetes Worker Reset Role

This role completely cleans a Kubernetes worker node to prepare it for a fresh `kubeadm join` operation.

## What It Cleans

- Kubernetes cluster configuration (`kubeadm reset`)
- All pods and containers
- CNI plugins and network configurations (Calico, Flannel, etc.)
- Kubernetes data directories
- Network interfaces and iptables rules
- Containerd data
- All Kubernetes-related namespaces

## Usage

### Basic usage (preserves container images)

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml
```

### Remove container images as well

```bash
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml -e "remove_container_images=true"
```

### Target specific worker groups

```bash
# Main workers
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_main

# Office workers  
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_office

# Super worker
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --limit workers_super
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
- Removes all Kubernetes configuration
- Ensure you have proper backups before running
- Run against correct target group only

## Example Workflow

```bash
# 1. Reset workers
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml

# 2. Get fresh join command from control plane
# On control plane:
# kubeadm token create --print-join-command

# 3. Join workers to cluster
# Execute the join command on each worker or via automation
```
