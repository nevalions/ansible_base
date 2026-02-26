# coredns Role

Manage the CoreDNS ConfigMap in a kubeadm cluster. Applies an Ansible-rendered
Corefile that uses **explicit upstream resolvers** and a tuned cache TTL, making
CoreDNS behaviour identical on every node regardless of network segment.

## Why this role exists

kubeadm's default Corefile contains:

```
forward . /etc/resolv.conf
```

This means CoreDNS delegates external DNS to whatever resolver is listed in the
**node's** `/etc/resolv.conf`. On clusters where nodes sit on different network
segments (e.g. `bay-*` nodes vs `vas-worker1` on `9.11.0.x`), the resolver path
differs per node. If one path is degraded, CoreDNS on that node returns SERVFAIL —
even for domains that resolve fine on other nodes.

Additionally, the default external cache TTL is 30 s. A brief WireGuard path
hiccup longer than 30 s will stall every running pod that needs an external DNS
lookup.

This role fixes both issues:

1. Replaces `forward . /etc/resolv.conf` with explicit upstream IPs.
2. Raises the external cache TTL from 30 s to 300 s (configurable).

## Requirements

- A working kubeadm cluster.
- `kubectl` available on the target host with `cluster-admin` access.
- The target host is typically a control plane node (`bay_plane1`).
- `become: true` privileges.

## Role Variables

### Upstream resolvers

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_coredns_upstream_resolvers` | List of upstream forwarder IPs | Falls back to `vault_dns_server_primary` + `vault_dns_server_secondary` |
| `vault_coredns_upstream_protocol` | Protocol prefix (`""` for UDP/TCP, `"tls://"` for DoT) | `""` |

### Cache tuning

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_coredns_cache_ttl` | Positive answer cache TTL (seconds) | `300` |
| `vault_coredns_cache_ttl_negative` | Negative answer cache TTL (seconds) | `30` |

### kubectl connectivity

On kubeadm clusters the kubeconfig server entry is a DNS name
(`k8s-api.cluster.local`). If CoreDNS is broken, kubectl cannot resolve that
name — creating a chicken-and-egg problem. Override the server to use
`127.0.0.1` to bypass DNS resolution entirely.

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_coredns_kubectl_server` | Override API server address | `"https://127.0.0.1:6443"` |
| `vault_coredns_kubectl_kubeconfig` | Explicit kubeconfig path | `"/etc/kubernetes/admin.conf"` |
| `vault_coredns_kubectl_insecure` | Skip TLS verification (needed when server is 127.0.0.1) | `true` when `kubectl_server` is set |
| `vault_coredns_kubectl_validate` | Enable kubectl server-side schema validation | `false` |

### Cluster configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_coredns_cluster_domain` | Kubernetes cluster domain | `cluster.local` |
| `vault_coredns_stub_zones` | List of private zones for split-horizon DNS | `[]` |
| `vault_coredns_log_enabled` | Enable CoreDNS query logging | `false` |
| `vault_coredns_health_port` | Port for the `/health` liveness endpoint | `8080` |

### Rollout control

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_coredns_wait_for_rollout` | Wait for CoreDNS rollout after ConfigMap patch | `true` |
| `vault_coredns_rollout_timeout` | Rollout wait timeout | `120s` |

## vault_secrets.yml configuration

Minimum required:

```yaml
# CoreDNS kubectl connectivity (bypass DNS chicken-and-egg)
vault_coredns_kubectl_server: "https://127.0.0.1:6443"
vault_coredns_kubectl_kubeconfig: "/etc/kubernetes/admin.conf"
vault_coredns_kubectl_insecure: true
vault_coredns_kubectl_validate: false
```

Optional (falls back to `vault_dns_server_primary` / `vault_dns_server_secondary`):

```yaml
vault_coredns_upstream_resolvers:
  - "[primary-dns-server-ip]"
  - "[secondary-dns-server-ip]"
vault_coredns_cache_ttl: 300
```

Optional stub zones for split-horizon DNS:

```yaml
vault_coredns_stub_zones:
  - zone: "internal.example.com"
    resolvers:
      - "[internal-resolver-ip]"
```

## Usage

### Apply (or update) the CoreDNS ConfigMap

```bash
# Apply ConfigMap patch and wait for rollout
ansible-playbook -i hosts_bay.ini kuber_coredns_install.yaml

# Dry-run preview (shows what would change, no cluster writes)
ansible-playbook -i hosts_bay.ini kuber_coredns_install.yaml --check

# Enable query logging for debugging
ansible-playbook -i hosts_bay.ini kuber_coredns_install.yaml \
  -e vault_coredns_log_enabled=true

# Override cache TTL only
ansible-playbook -i hosts_bay.ini kuber_coredns_install.yaml \
  -e vault_coredns_cache_ttl=600
```

### Verify CoreDNS health and resolution

```bash
# Full verification (deployment status + ConfigMap + resolution probes)
ansible-playbook -i hosts_bay.ini kuber_coredns_verify.yaml

# Resolution probes only
ansible-playbook -i hosts_bay.ini kuber_coredns_verify.yaml \
  --tags coredns_resolution
```

### Skip during full cluster deploy

```bash
# Skip the CoreDNS step in kuber_cluster_deploy.yaml
ansible-playbook -i hosts_bay.ini kuber_cluster_deploy.yaml \
  -e skip_coredns=true
```

## Generated Corefile structure

```
.:53 {
    errors
    health { lameduck 5s }
    ready

    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }

    # Optional per-zone stub forwarders (split-horizon)
    # forward <zone> <resolvers> { prefer_udp }

    forward . <upstream1> <upstream2> {
        max_concurrent 1000
        prefer_udp
    }

    cache {
        success 9984 300 300   # positive TTL
        denial  9984 30  30    # negative TTL
        prefetch 10
    }

    loop
    reload
    loadbalance
}
```

## Idempotency

The role reads the current Corefile from the ConfigMap and compares it to the
desired rendered content. `kubectl apply` is only called when they differ, and
`rollout restart` is only triggered when the apply results in a change.
Re-running the playbook on an already-patched cluster completes in seconds with
no pod restarts.

## Troubleshooting

### `Unauthorized` when running kubectl

The kubeconfig on the control plane may not have credentials loaded when
`--server` overrides the endpoint. Ensure `vault_coredns_kubectl_kubeconfig`
points to `/etc/kubernetes/admin.conf` (the kubeadm cluster-admin kubeconfig).

### CoreDNS rollout stuck

If the rollout times out, check for pending pods:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl describe pod -n kube-system <coredns-pod>
```

Common causes: node not ready, image pull failure, resource limits.

### Resolution probe fails after apply

The post-deploy probe runs a `busybox` pod inside the cluster. If it fails:

```bash
# Manual probe
kubectl run dns-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nslookup github.com
```

Verify the upstream resolvers are reachable from inside the cluster:

```bash
kubectl run dns-test --image=busybox:1.36 --restart=Never --rm -it \
  -- nc -zv <upstream-ip> 53
```

## License

MIT
