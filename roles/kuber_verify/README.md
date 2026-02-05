# kuber_verify

Comprehensive verification of Kubernetes cluster health and functionality.

## Overview

This role performs comprehensive verification of a Kubernetes cluster:

- Verifies control plane node status and readiness
- Checks Calico CNI installation and pod status
- Validates worker node joining and readiness
- Tests pod-to-pod networking connectivity
- Tests DNS resolution within cluster
- Generates detailed verification report

## Requirements

- Kubernetes cluster initialized with `kuber_init`
- Worker nodes joined with `kuber_join`
- Kubeconfig accessible at `/etc/kubernetes/admin.conf`
- `kubectl` installed and accessible

## Role Variables

### Verification Settings

- `verify_test_namespace` - Test namespace (default: `kuber-verify-test`)
- `verify_test_pod_image` - Test pod image (default: `nginx:alpine`)
- `verify_test_pod_port` - Test pod port (default: `80`)
- `verify_timeout_seconds` - Verification timeout (default: `300`)
- `verify_sleep_seconds` - Retry delay (default: `5`)
- `verify_retry_count` - Retry count (default: `20`)
- `verify_dns_service` - DNS service to test (from vault)
- `verify_external_hostname` - External hostname for DNS test (from vault)

## Vault Variables

Required in `vault_secrets.yml`:

```yaml
verify_dns_service: "[k8s-service]"
verify_external_hostname: "[external-hostname]"
```

## Usage

### Playbook

```bash
ansible-playbook -i hosts_bay.ini kuber_verify.yaml
```

### Direct role usage

```yaml
- hosts: control_planes
  roles:
    - kuber_verify
```

## Tasks

### Control Plane Verification

1. Get and display all cluster nodes
2. Verify control plane node is Ready
3. Get Calico node pod status
4. Get Tigera Operator pod status
5. Verify Tigera Operator is Running
6. Wait for all Calico node pods to be Ready
7. Display cluster information
8. Display Calico installation status

### Worker Verification

1. Get all worker node names
2. Count joined worker nodes
3. Assert workers are joined to cluster
4. Check if all worker nodes are Ready
5. Display worker readiness status
6. Assert all worker nodes are Ready
7. Get Calico pods on all nodes
8. Display Calico pods distribution
9. Verify Calico pods match cluster nodes
10. Get node details for each worker

### Networking Verification

1. Create test namespace
2. Create test pod manifests (nginx pods)
3. Apply test pods to cluster
4. Wait for test pods to be Ready
5. Display test pods status
6. Get pod IP addresses
7. Test pod-to-pod connectivity (same namespace)
8. Test DNS resolution within cluster
9. Clean up test namespace and pods

### Report Generation

- Displays comprehensive verification report with:
  - Control plane readiness status
  - Calico CNI operational status
  - Worker node count
  - Networking functionality
  - DNS resolution status

## Verification Checks

### Control Plane
- ✅ Control plane node is Ready
- ✅ Calico node pods are Running
- ✅ Tigera Operator is Running
- ✅ Cluster info accessible

### Workers
- ✅ Worker nodes are joined to cluster
- ✅ All worker nodes are Ready
- ✅ Calico pods distributed across nodes
- ✅ Calico pod count matches node count

### Networking
- ✅ Test pods created successfully
- ✅ Pods are Ready and reachable
- ✅ Pod-to-pod connectivity working
- ✅ DNS resolution functional within cluster

## Exit Codes

- `0` - All verifications passed
- `1` - One or more verifications failed

## Dependencies

- `kuber_init` role (cluster initialization)
- `kuber_join` role (worker nodes joined)
- Access to `/etc/kubernetes/admin.conf` kubeconfig

## Tags

- `kubernetes` - Kubernetes-related tasks
- `k8s` - Kubernetes tasks (alias)
- `verify` - Verification tasks
- `test` - Testing tasks

## Troubleshooting

**Control plane not Ready:**
```bash
# Check control plane status
kubectl get nodes

# Check control plane logs
journalctl -u kubelet -f

# Restart kubelet if needed
ansible-playbook -i hosts_bay.ini kuber.yaml --limit [control-plane-host]
```

**Calico pods not Ready:**
```bash
# Check Calico pods
kubectl get pods -n calico-system

# Check Calico logs
kubectl logs -n calico-system -l k8s-app=calico-node

# Restart Calico
kubectl delete pods -n calico-system -l k8s-app=calico-node
```

**Workers not joined:**
```bash
# Check worker nodes
kubectl get nodes

# Re-join workers
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml
```

**Pod networking issues:**
```bash
# Check pod status
kubectl get pods -n kuber-verify-test

# Check pod logs
kubectl logs -n kuber-verify-test test-pod-1

# Check network policies
kubectl get networkpolicies -A

# Check Calico status
kubectl calico status
```

**DNS resolution failures:**
```bash
# Check DNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Test DNS manually
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup [k8s-service]

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

## Cleanup

The role automatically cleans up test resources:

- Deletes test namespace (`kuber-verify-test`)
- Removes test pods
- Cleans up test manifests

To manually clean up if verification fails:

```bash
kubectl delete namespace kuber-verify-test
rm -f /tmp/test-pod.yaml
```
