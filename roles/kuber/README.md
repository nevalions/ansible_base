# Kuber Role

Sets up Kubernetes cluster components including kubelet, kubeadm, kubectl, and containerd.

## Role Variables

### Required Variables

None - all variables have defaults.

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `install_kubernetes` | `true` | Enable/disable Kubernetes installation |

### Installed Components

The role installs and configures:
- `kubelet` - Kubelet agent
- `kubeadm` - Cluster bootstrap tool
- `kubectl` - Command-line tool
- `containerd` - Container runtime

## Handlers

Available handlers:

| Handler | Description |
|---------|-------------|
| `restart kubelet` | Restart kubelet service |
| `restart containerd` | Restart containerd service |
| `reload ufw` | Reload UFW firewall |

## Tasks Structure

```
roles/kuber/
├── tasks/
│   └── main.yaml      # K8s installation and setup
├── handlers/
│   └── main.yaml      # Service and firewall handlers
├── defaults/
│   └── main.yaml     # Default variables
└── templates/
    └── containerd-config.toml.j2  # Containerd configuration
```

## Usage

### Basic Usage

```yaml
- name: Setup Kubernetes cluster
  hosts: k8s_nodes
  become: yes
  roles:
    - kuber
```

### Automated Cluster Setup

After running this role on all nodes, use automated playbooks for full cluster setup:

```bash
# 1. Install packages on all nodes (this role)
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes

# 2. Initialize control plane (automated)
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init

# 3. Install Flannel CNI (default)
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel

# 4. Join workers to cluster (automated)
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join

# 5. Verify cluster health (automated)
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify
```

For complete setup documentation, see [../../KUBERNETES_SETUP.md](../../KUBERNETES_SETUP.md).

### Manual Installation (Alternative)

If you prefer manual setup:

```bash
# On control plane node only
sudo kubeadm init --pod-network-cidr=[internal-ip]/16

# Setup kubectl for current user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Join worker nodes
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

### After Installation

After running this role on all nodes, initialize the cluster on the control plane:

```bash
# On control plane node only
sudo kubeadm init --pod-network-cidr=[internal-ip]/16

# Setup kubectl for current user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Join worker nodes
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

## Installation Process

1. **Update package lists**
   - Updates apt cache for latest packages

2. **Install required packages**
   - `apt-transport-https`
   - `ca-certificates`
   - `curl`

3. **Set up Kubernetes repository**
   - Downloads and installs GPG key
   - Adds Kubernetes repository to apt sources

4. **Install Kubernetes components**
   - kubelet, kubeadm, kubectl, containerd

5. **Hold packages**
   - Prevents automatic updates using `dpkg_selections`

6. **Disable swap**
   - Runs `swapoff -a`
   - Comments out swap entry in `/etc/fstab`

7. **Configure kernel modules**
   - Loads `overlay` and `br_netfilter` modules
   - Enables IP forwarding and bridge networking

8. **Configure containerd**
   - Sets up containerd with systemd cgroup driver

9. **Firewall posture**
- This repository disables UFW on Kubernetes nodes by default.
- Reason: CNI overlay traffic + WireGuard forwarding is easy to break with UFW's default forward policy and chains.
- If you need a host firewall, implement it outside UFW (cloud security groups / upstream firewall) or explicitly
  manage FORWARD allowances for CNI interfaces + `wg*`.

## Firewall Configuration

Kubernetes networking (especially with tunneled/overlay traffic) expects a permissive FORWARD path.
UFW is frequently a source of subtle forwarding drops.

In this repo:
- Kubernetes nodes: UFW is disabled (best-effort)
- WireGuard role: does not enable UFW automatically

## OS Compatibility

| OS Family | Status |
|-----------|--------|
| Debian/Ubuntu | ✅ Supported |
| Arch/Manjaro | ⚠️ Untested |

## Requirements

- Debian or Ubuntu system
- Root/sudo access
- 2GB+ RAM per node
- 2+ CPUs per node
- Network connectivity between nodes
- Swap disabled (role handles this)

## Containerd Configuration

The role configures containerd with systemd cgroup driver:

```toml
version = 2
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
  runtime_type = "io.containerd.runc.v2"
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true
```

## Kernel Configuration

The role sets kernel parameters:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `net.ipv4.ip_forward` | 1 | Enable IP forwarding |
| `net.bridge.bridge-nf-call-iptables` | 1 | Enable bridge networking |

## Network Plugin

After cluster initialization, install a CNI plugin.

```bash
# Default path in this repo: install Flannel via playbook
ansible-playbook -i hosts_bay.ini kuber_flannel_install.yaml --tags flannel

# Legacy Calico Path (optional): Calico-specific playbooks/docs
# ansible-playbook -i hosts_bay.ini calico_bgp_manage.yaml --tags calico,bgp
```

## Post-Installation Validation

```bash
# Check kubelet status
sudo systemctl status kubelet

# Check containerd status
sudo systemctl status containerd

# Check kubectl version
kubectl version --client

# List pods
kubectl get pods -A

# List nodes
kubectl get nodes
```

## Troubleshooting

### kubelet Not Starting

```bash
# Check kubelet status
sudo systemctl status kubelet

# View kubelet logs
sudo journalctl -u kubelet -n 50

# Check swap is disabled
sudo swapon --show

# Check kernel modules
lsmod | grep br_netfilter
```

### Containerd Issues

```bash
# Check containerd status
sudo systemctl status containerd

# View containerd logs
sudo journalctl -u containerd -n 50

# Test containerd
sudo containerd --version

# Reset containerd
sudo systemctl restart containerd
```

### Network Issues

```bash
 # Check UFW is not active (Kubernetes nodes)
 systemctl is-active ufw || true

# Check IP forwarding
sysctl net.ipv4.ip_forward

# Check bridge networking
sysctl net.bridge.bridge-nf-call-iptables

# Check forwarding policy
sudo iptables -S FORWARD

# Test node connectivity
ping <other-node-ip>
telnet <other-node-ip> 6443
```

### Cluster Join Issues

```bash
# Check if kubeadm is installed
kubeadm version

# Check if token is valid
kubeadm token list

# Regenerate token
kubeadm token create --print-join-command

# Reset and reinitialize
sudo kubeadm reset
sudo kubeadm init --pod-network-cidr=[internal-ip]/16
```

## Cluster Management

### Adding Worker Nodes

1. Run the role on the new worker node
2. Get join command from control plane:
   ```bash
   kubeadm token create --print-join-command
   ```
3. Run join command on worker node
4. Verify node joins:
   ```bash
   kubectl get nodes
   ```

### Upgrading Kubernetes

```bash
# Check available versions
apt-cache madison kubeadm

# Hold packages
sudo apt-mark hold kubelet kubeadm kubectl

# Unhold and upgrade
sudo apt-mark unhold kubelet kubeadm kubectl
sudo apt update
sudo apt upgrade

# Drain node (for control plane)
kubectl drain <node-name> --ignore-daemonsets

# Upgrade kubelet/kubeadm
sudo apt upgrade kubelet kubeadm

# Update control plane
sudo kubeadm upgrade apply <version>

# Uncordon node
kubectl uncordon <node-name>
```

### Resetting Cluster

```bash
# On all nodes
sudo kubeadm reset -f

# Clean up
sudo rm -rf /etc/cni/net.d
sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X
```

## Examples

### Multi-Master Cluster (HA)

```yaml
- name: Setup K8s cluster with HA
  hosts: k8s_cluster
  become: yes
  roles:
    - kuber

  vars:
    kubernetes_version: "1.35"
```

Initialize first control plane:
```bash
sudo kubeadm init --control-plane-endpoint "loadbalancer-ip:6443" \
  --upload-certs \
  --pod-network-cidr=[internal-ip]/16
```

Join additional control planes:
```bash
sudo kubeadm join loadbalancer-ip:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <cert-key>
```

## Security Considerations

1. **Firewall Rules**: Review and customize UFW rules based on your requirements
2. **Pod Network CIDR**: Choose appropriate CIDR for your network
3. **RBAC**: Implement Role-Based Access Control after cluster setup
4. **Network Policies**: Use Kubernetes Network Policies for pod-to-pod communication
5. **Secret Management**: Use proper secret management (e.g., Sealed Secrets, HashiCorp Vault)

## Best Practices

1. **Resource Limits**: Set CPU and memory limits on pods
2. **Namespace Isolation**: Use namespaces for different environments
3. **Monitoring**: Install monitoring stack (Prometheus, Grafana)
4. **Logging**: Set up centralized logging (ELK, Loki)
5. **Backup**: Regularly backup etcd and configuration
6. **Updates**: Plan regular cluster maintenance windows for upgrades
