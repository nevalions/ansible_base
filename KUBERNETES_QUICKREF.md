# Kubernetes Setup Quick Reference

## Playbooks

| Playbook | Purpose | Hosts | Tags |
|----------|---------|-------|------|
| `kuber.yaml` | Install K8s packages | workers_super | kubernetes, k8s, install |
| `kuber_plane_init.yaml` | Initialize control plane | planes | kubernetes, k8s, init, plane, cni |
| `kuber_worker_join.yaml` | Join worker nodes | workers_all | kubernetes, k8s, join, worker |
| `kuber_verify.yaml` | Verify cluster health | planes | kubernetes, k8s, verify, test |
| `kuber_plane_reset.yaml` | Reset control plane | masters | kubernetes, k8s, reset, cleanup |
| `kuber_worker_reset.yaml` | Reset worker nodes | workers_all | kubernetes, k8s, reset, cleanup |

## Quick Setup Commands

```bash
# Full setup (single control plane)
ansible-playbook -i hosts_bay.ini kuber.yaml --tags kubernetes
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join
ansible-playbook -i hosts_bay.ini kuber_verify.yaml --tags verify
```

## Verification Commands

### After Control Plane Init
```bash
kubectl get nodes
kubectl get pods -n kube-system -l k8s-app=calico-node
kubectl get pods -n tigera-operator
kubectl get ippool -o wide
```

### After Worker Join
```bash
kubectl get nodes
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
```

### Network Test
```bash
kubectl run test-pod --image=nginx:alpine --restart=Never
kubectl exec test-pod -- wget -q -O- http://[your-username].google.com --spider
kubectl delete pod test-pod
```

## Roles

| Role | Purpose |
|------|---------|
| `kuber_init` | Control plane init + verification |
| `kuber_join` | Worker join + verification |
| `kuber_verify` | Full cluster health check |
| `kuber_reset` | Reset/cleanup |
| `setup` | System setup (includes kuber role) |

## Inventory Groups

| Group | Hosts |
|-------|-------|
| `[planes]` | [internal-ip] |
| `[workers_all]` | [internal-ip], [internal-ip], [internal-ip] |
| `[workers_main]` | [internal-ip] |
| `[workers_office]` | [internal-ip] |
| `[workers_super]` | [internal-ip] |

## Key Variables

### kuber_init
```yaml
kubeadm_pod_subnet: "[internal-ip]/16"
kubeadm_service_subnet: "[internal-ip]/16"
calico_version: "v3.28.1"
```

### kuber_verify
```yaml
verify_test_namespace: "kuber-verify-test"
verify_test_pod_image: "nginx:alpine"
verify_timeout_seconds: "300"
```

## Verification Summary

**Built-in Verification (automatic):**
- ✓ Control plane Ready status
- ✓ Tigera Operator Running
- ✓ Calico pods Ready
- ✓ Worker nodes Ready
- ✓ Node visibility from control plane

**Full Verification (kuber_verify.yaml):**
- ✓ All above
- ✓ Pod-to-pod connectivity
- ✓ DNS resolution
- ✓ External connectivity

## Troubleshooting

```bash
# Reset everything
ansible-playbook -i hosts_bay.ini kuber_plane_reset.yaml --tags reset
ansible-playbook -i hosts_bay.ini kuber_worker_reset.yaml --tags reset

# Re-setup
ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml --tags init
ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml --tags join
```
