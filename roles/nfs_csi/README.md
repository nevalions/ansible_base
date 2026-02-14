# NFS CSI Driver Role

Install NFS CSI driver for Kubernetes with dynamic PV provisioning using an existing NFS server.

## Requirements

- Kubernetes cluster with Helm installed
- Existing and configured NFSv3 or NFSv4 server
- Ansible 2.16+
- `become: true` privileges on control-plane nodes
- Debian/Ubuntu system (Ubuntu 24.04, 22.04, 20.04; Debian 12, 11)

## Role Variables

### Required Vault Variables (MUST be defined)

| Variable | Description | Example |
|----------|-------------|---------|
| `vault_nfs_csi_server` | NFS server IP address | `[nfs-server-ip]` |
| `vault_nfs_csi_share` | NFS export path on server | `[nfs-share-path]` |

**Note**: These variables must be defined in `vault_secrets.yml`. The playbook will fail if they are missing or contain placeholder values.

### Optional Vault Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_nfs_csi_enabled` | Enable/disable role | `true` |
| `vault_nfs_csi_operation` | Operation mode (install/verify/remove) | `install` |
| `vault_nfs_csi_version` | CSI driver version | `v4.11.0` |
| `vault_nfs_csi_namespace` | Kubernetes namespace | `kube-system` |
| `vault_nfs_csi_release_name` | Helm release name | `csi-driver-nfs` |
| `vault_nfs_csi_storageclass_name` | StorageClass name | `nfs-csi` |
| `vault_nfs_csi_storageclass_is_default` | Set as default StorageClass | `false` |
| `vault_nfs_csi_controller_run_on_control_plane` | Run controller on control-plane nodes | `true` |
| `vault_nfs_csi_controller_replicas` | Number of controller replicas | `2` |
| `vault_nfs_csi_reclaim_policy` | PVC reclaim policy | `Retain` |
| `vault_nfs_csi_volume_binding_mode` | Volume binding mode | `Immediate` |
| `vault_nfs_csi_allow_volume_expansion` | Allow volume expansion | `true` |
| `vault_nfs_csi_mount_options` | NFS mount options | `["nfsvers=4.1", "hard", "noatime", "rw"]` |
| `vault_nfs_csi_remove_namespace` | Delete namespace on remove | `false` |
| `vault_nfs_csi_helm_binary_path` | Path to Helm binary | `/usr/local/bin/helm` |

## Dependencies

- Helm must be installed on the cluster (run `kuber_helm_install.yaml` first)

## Example Playbook

### Install NFS CSI Driver

```yaml
---
- name: Install NFS CSI driver
  hosts: kuber_small_planes
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    nfs_csi_operation: "install"
  roles:
    - nfs_csi
```

### Verify NFS CSI Driver

```yaml
---
- name: Verify NFS CSI driver
  hosts: kuber_small_planes
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    nfs_csi_operation: "verify"
  roles:
    - nfs_csi
```

### Remove NFS CSI Driver

```yaml
---
- name: Remove NFS CSI driver
  hosts: kuber_small_planes
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    nfs_csi_operation: "remove"
  roles:
    - nfs_csi
```

## Usage

### Using provided playbooks:

```bash
# Install NFS CSI driver and StorageClass
ansible-playbook -i hosts_bay.ini kuber_nfs_csi_install.yaml

# Verify installation
ansible-playbook -i hosts_bay.ini kuber_nfs_csi_verify.yaml

# Remove NFS CSI driver
ansible-playbook -i hosts_bay.ini kuber_nfs_csi_remove.yaml

# Use tags
ansible-playbook -i hosts_bay.ini kuber_nfs_csi_install.yaml --tags nfs,csi
```

### Using the role directly:

```bash
ansible-playbook your_playbook.yaml
```

## What This Role Does

### On Install:

1. Adds NFS CSI driver Helm repository
2. Installs or upgrades NFS CSI driver via Helm
3. Creates StorageClass with dynamic provisioning
4. Configures subdirectory pattern (`${pvc.metadata.namespace}/${pvc.metadata.name}`)
5. Waits for CSI pods to be ready

### On Verify:

1. Checks Helm release status
2. Displays controller and node pods
3. Shows StorageClass details

### On Remove:

1. Deletes StorageClass
2. Uninstalls Helm release
3. Optionally deletes namespace

## Vault Configuration

Add the following to your `vault_secrets.yml`:

**Required:**
```yaml
# NFS CSI Driver Configuration
vault_nfs_csi_server: "[nfs-server-ip]"
vault_nfs_csi_share: "[nfs-share-path]"
```

**Optional:**
```yaml
# NFS CSI Driver Settings
vault_nfs_csi_enabled: true
vault_nfs_csi_version: "v4.11.0"
vault_nfs_csi_namespace: "kube-system"
vault_nfs_csi_storageclass_name: "nfs-csi"
vault_nfs_csi_storageclass_is_default: "false"
vault_nfs_csi_controller_run_on_control_plane: true
vault_nfs_csi_controller_replicas: 2
vault_nfs_csi_reclaim_policy: "Retain"
vault_nfs_csi_volume_binding_mode: "Immediate"
vault_nfs_csi_allow_volume_expansion: true
vault_nfs_csi_mount_options:
  - "nfsvers=4.1"
  - "hard"
  - "noatime"
  - "rw"
```

## Testing NFS CSI

After installation, test dynamic provisioning:

```bash
# Create a test PVC
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-nfs-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-csi
  resources:
    requests:
      storage: 1Gi
EOF

# Check PVC status
kubectl get pvc test-nfs-pvc

# Create a test pod using the PVC
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: test-nfs-pod
spec:
  containers:
  - name: test-container
    image: nginx:alpine
    volumeMounts:
    - mountPath: /data
      name: nfs-storage
  volumes:
  - name: nfs-storage
    persistentVolumeClaim:
      claimName: test-nfs-pvc
EOF

# Check pod status
kubectl get pod test-nfs-pod

# Clean up
kubectl delete pod test-nfs-pod
kubectl delete pvc test-nfs-pvc
```

## StorageClass Details

The created StorageClass uses the following configuration:

- **Provisioner**: `nfs.csi.k8s.io`
- **Server**: From `vault_nfs_csi_server`
- **Share**: From `vault_nfs_csi_share`
- **Subdirectory**: Dynamic (`${pvc.metadata.namespace}/${pvc.metadata.name}`)
- **Reclaim Policy**: Retain (configurable)
- **Volume Binding Mode**: Immediate (configurable)
- **Volume Expansion**: Enabled (configurable)
- **Mount Options**: NFSv4.1, hard, noatime, rw (configurable)

## Troubleshooting

### Helm release fails to install:

1. Verify Helm is installed:
   ```bash
   ansible-playbook kuber_helm_verify.yaml
   ```

2. Check Helm can access the repo:
   ```bash
   helm repo list
   helm search repo csi-driver-nfs
   ```

3. Review Helm install logs:
   ```bash
   helm -n kube-system status csi-driver-nfs
   ```

### CSI pods not starting:

1. Check pod status and logs:
   ```bash
   kubectl -n kube-system get pods -l app.kubernetes.io/instance=csi-driver-nfs
   kubectl -n kube-system describe pod <pod-name>
   kubectl -n kube-system logs <pod-name>
   ```

2. Verify NFS server is accessible:
   ```bash
   showmount -e <nfs-server-ip>
   ```

3. Check kubelet can access NFS:
   ```bash
   ssh <node-ip> showmount -e <nfs-server-ip>
   ```

### PVC stuck in pending:

1. Check StorageClass:
   ```bash
   kubectl get storageclass nfs-csi -o yaml
   ```

2. Check PVC events:
   ```bash
   kubectl describe pvc <pvc-name>
   ```

3. Verify CSI driver is registered:
   ```bash
   kubectl get csidriver
   kubectl get csidriver nfs.csi.k8s.io -o yaml
   ```

### Volume expansion not working:

1. Verify StorageClass has `allowVolumeExpansion: true`:
   ```bash
   kubectl get storageclass nfs-csi -o yaml | grep allowVolumeExpansion
   ```

2. Update PVC size:
   ```bash
   kubectl patch pvc <pvc-name> -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
   ```

## Security Considerations

- This role requires `become: true` (root privileges) on control-plane nodes
- NFS server IP and share path must be configured in `vault_secrets.yml`
- The StorageClass uses `Retain` reclaim policy by default to prevent accidental data loss
- Ensure proper NFS server security (export restrictions, authentication, etc.)

## License

MIT
