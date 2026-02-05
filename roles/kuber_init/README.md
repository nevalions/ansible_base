# kuber_init

Initialize Kubernetes control plane with kubeadm and Calico CNI.

## Overview

This role performs the complete initialization of a Kubernetes control plane node:

- Initializes Kubernetes cluster with kubeadm
- Configures containerd cgroup driver
- Installs Calico CNI with Tigera Operator
- Configures kubeadm API version and control plane endpoint
- Verifies cluster readiness and Calico installation
- Sets up kubeconfig for admin user

## Requirements

- Kubernetes packages installed (kubelet, kubeadm, kubectl)
- Containerd configured and running
- Network firewall configured for Kubernetes ports
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
- `calico_encapsulation` - Encapsulation type (default: `VXLANCrossSubnet`)
- `calico_nat_outgoing` - NAT outgoing traffic (default: `true`)
- `calico_node_selector` - Node selector for Calico (default: `all()`)
- `calico_block_size` - IP block size (default: `26`)
- `calico_mtu` - MTU size (default: `1440`)
- `calico_node_address_interface` - Network interface (default: `wg99`)

### Kubeconfig Configuration

- `kubeconfig_user` - Admin user (default: current user)
- `kubeconfig_user_home` - User home directory
- `kubeconfig_path` - Kubeconfig path (default: `~/.kube/config`)

### API Version

- `kubeadm_api_version` - kubeadm API version (default: `v1beta4`)

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
9. Verify cluster node status
10. Verify Tigera Operator is running
11. Display initialization summary

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
