# Cluster Redeploy from Scratch

Full ordered runbook for rebuilding the cluster from zero using this repository.
All commands run from `/home/linroot/ansible/` unless noted.

See `docs/cluster_schema.local.txt` for the current network topology and IP assignments.

---

## Prerequisites

- GPG key imported and `vault_password_client.sh` working: `./vault_password_client.sh`
- SSH access to all hosts via `~/.ssh/config` entries
- Ansible vault password decrypts: `ansible-vault view vault_secrets.yml --vault-password-file vault_password_client.sh`
- `hosts_bay.ini` matches current infrastructure

---

## Phase 0 — Verify vault and connectivity

```bash
# Confirm vault readable
ansible-vault view vault_secrets.yml --vault-password-file vault_password_client.sh | head -5

# Confirm SSH reachable to all hosts
ansible all -i hosts_bay.ini --vault-password-file vault_password_client.sh -m ping
```

---

## Phase 1 — WireGuard mesh

WireGuard must be up before Kubernetes is initialized. Everything runs over `wg99`.

### 1.1 Generate keys (only if keys are null in vault)

```bash
bash generate_wg_keys.sh > wg_keys.yaml
# Copy output into vault_secrets.yml:
ansible-vault edit vault_secrets.yml --vault-password-file vault_password_client.sh
```

Keys live at:
- `vault_wg_peer_private_keys.<name>:`
- `vault_wg_peer_public_keys.<name>:`

### 1.2 Deploy WireGuard to all hosts

```bash
ansible-playbook wireguard_manage.yaml --vault-password-file vault_password_client.sh
```

### 1.3 Verify WireGuard

```bash
ansible-playbook wireguard_verify.yaml --vault-password-file vault_password_client.sh
```

Manual spot-check on the HAProxy/ingress node:
```bash
ssh [haproxy-hostname] "sudo wg show wg99"
# Confirm: [k8s-api-vip]/32 is under the primary control-plane peer only
# Confirm: [metallb-pool-cidr] is under the first worker peer only
```

**Critical AllowedIPs rules** (see `cluster_schema.local.txt` section 5):
- `[k8s-api-vip]/32` (k8s API VIP) → only the primary control-plane peer in vault_wg_peers
- `[metallb-pool-cidr]` (MetalLB pool) → only the first worker peer in vault_wg_peers, on HAProxy
- The secondary control-plane must NOT have `[k8s-api-vip]/32` — WG dedup will steal it and break kubelet→API routing

---

## Phase 2 — DNS

DNS servers provide `cluster.local` resolution over wg99. Required before Kubernetes init.

```bash
# Deploy DNS servers (HAProxy node + BGP router node)
ansible-playbook dns_server_manage.yaml --vault-password-file vault_password_client.sh

# Deploy DNS client (node-local dnsmasq with filter-AAAA) on all k8s nodes
ansible-playbook dns_client_manage.yaml --vault-password-file vault_password_client.sh

# Verify
ansible-playbook dns_verify.yaml --vault-password-file vault_password_client.sh
```

Verify `k8s-api.cluster.local` resolves to the k8s API VIP on any node:
```bash
ssh [worker-node] "dig k8s-api.cluster.local +short"
# expected: [k8s-api-vip]
```

---

## Phase 3 — BGP routers (FRR + Keepalived)

BGP routers advertise MetalLB LoadBalancer IPs to HAProxy.

```bash
# Deploy FRR + Keepalived on HAProxy node and BGP router node
ansible-playbook bgp_ha_deploy.yaml --vault-password-file vault_password_client.sh

# Verify BGP HA
ansible-playbook bgp_ha_verify.yaml --vault-password-file vault_password_client.sh
```

Confirm BGP VIP is active on the HAProxy node:
```bash
ssh [haproxy-hostname] "ip addr show wg99 | grep [bgp-vip-address]"
```

---

## Phase 4 — HAProxy ingress (80/443 → MetalLB)

HAProxy forwards public traffic to the MetalLB VIP with PROXY v2 for real client IP preservation.

```bash
ansible-playbook haproxy_k8s.yaml --vault-password-file vault_password_client.sh
```

At this point HAProxy will return errors (no backend yet) — that is expected.

---

## Phase 5 — Kubernetes packages on all nodes

```bash
# Install kubelet, kubeadm, kubectl, containerd on all planes + workers
ansible-playbook kuber.yaml --vault-password-file vault_password_client.sh
```

---

## Phase 6 — Keepalived for k8s API VIP

Keepalived floats `[k8s-api-vip]/32` between control planes over wg99.

```bash
ansible-playbook keepalived_manage.yaml --vault-password-file vault_password_client.sh \
  --limit kuber_small_planes
```

Confirm VIP on primary control plane:
```bash
ssh [primary-plane-host] "ip addr show wg99 | grep [k8s-api-vip]"
```

---

## Phase 7 — Initialize first control plane

```bash
ansible-playbook kuber_plane_init.yaml --vault-password-file vault_password_client.sh \
  --limit [primary-plane-group]
```

Verify:
```bash
ssh [primary-plane-host] "sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get nodes"
# [primary-plane-host]   Ready   control-plane
```

---

## Phase 8 — Flannel CNI

Must run before workers join (otherwise CNI daemon pods fail on join).

```bash
ansible-playbook kuber_flannel_install.yaml --vault-password-file vault_password_client.sh
```

---

## Phase 9 — Join second control plane (vas_plane1)

```bash
ansible-playbook kuber_plane_join.yaml --vault-password-file vault_password_client.sh \
  --limit vas_plane1
```

---

## Phase 10 — Join all workers

```bash
ansible-playbook kuber_worker_join.yaml --vault-password-file vault_password_client.sh
```

Workers: all hosts in `kuber_small_workers` and `vas_workers_all` groups.

Verify all nodes Ready:
```bash
ssh [primary-plane-host] "sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get nodes -o wide"
```

---

## Phase 11 — MetalLB (BGP mode)

```bash
ansible-playbook kuber_metallb_install.yaml --vault-password-file vault_password_client.sh
```

Confirm MetalLB BGP sessions established on FRR routers:
```bash
ssh [bgp-router-host] "sudo vtysh -c 'show bgp summary'"
ssh [haproxy-hostname] "sudo vtysh -c 'show bgp summary'"
# All worker neighbors should show Established
```

---

## Phase 12 — Helm

```bash
ansible-playbook kuber_helm_install.yaml --vault-password-file vault_password_client.sh
```

---

## Phase 13 — cert-manager

```bash
ansible-playbook kuber_cert_manager_install.yaml --vault-password-file vault_password_client.sh
```

---

## Phase 14 — Traefik

```bash
ansible-playbook kuber_traefik_install.yaml --vault-password-file vault_password_client.sh
```

Confirm Traefik DaemonSet is running on all workers and LoadBalancer VIP is `[metallb-vip]`:
```bash
ssh [primary-plane-host] "sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get svc -n traefik"
ssh [primary-plane-host] "sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get pods -n traefik -o wide"
```

Confirm Traefik args include (verify PROXY v2 is configured):
```bash
ssh [primary-plane-host] "sudo KUBECONFIG=/etc/kubernetes/admin.conf \
  kubectl get pod -n traefik -o jsonpath='{.items[0].spec.containers[0].args}' \
  | tr ',' '\n' | grep -E 'proxy|forward|trusted'"
# Must show: proxyProtocol.trustedIPs=[vpn-network-cidr] and forwardedHeaders.trustedIPs=[vpn-network-cidr]
```

---

## Phase 15 — Worker MASQUERADE rules (pod → HAProxy reply path)

Ensures pod reply traffic is SNATed to the worker wg99 IP before leaving the tunnel,
so HAProxy never sees raw pod IPs in responses.

```bash
ansible-playbook wireguard_manage.yaml --vault-password-file vault_password_client.sh \
  --limit kuber_small_workers,vas_workers_all
```

The MASQUERADE rule is embedded in `wg_worker_postup_rules` and applied on wg99 PostUp:
```
iptables -t nat -A POSTROUTING -s [pod-network-cidr] -d [haproxy-wg-ip]/32 -j MASQUERADE
```

---

## Phase 16 — NFS CSI (optional, for PVC storage)

```bash
ansible-playbook kuber_nfs_csi_install.yaml --vault-password-file vault_password_client.sh
```

---

## Phase 17 — Full cluster verification

```bash
ansible-playbook kuber_verify.yaml --vault-password-file vault_password_client.sh
ansible-playbook bgp_ha_verify.yaml --vault-password-file vault_password_client.sh
ansible-playbook wireguard_verify.yaml --vault-password-file vault_password_client.sh
```

End-to-end HTTP check from HAProxy:
```bash
ssh [haproxy-hostname] "curl -sk -o /dev/null -w '%{http_code}' https://[metallb-vip]/"
# expected: 404 (Traefik no-route) — proves full path works
```

---

## Phase 18 — Application deployments

Applications are deployed via `kubectl apply` manifests (not managed by Ansible).

### Real client IP

Traefik extracts the real client IP from the PROXY v2 header and sets `X-Real-IP`
and `X-Forwarded-For` on every request before it reaches the backend. Most modern
frameworks read these headers automatically — no extra configuration needed.

Apps that ignore these headers and use the raw TCP connection IP instead require
proxy trust to be configured. That configuration belongs in the **app's deployment
manifest** (env var, ConfigMap, or config file mounted from a PVC) — not applied
as a live patch. This keeps it in git and ensures it survives cluster rebuilds and
PVC wipes without manual intervention.

---

## Teardown / Reset

### Full cluster reset (keep WireGuard)

```bash
# Reset all workers first
ansible-playbook kuber_worker_reset.yaml --vault-password-file vault_password_client.sh

# Reset control planes
ansible-playbook kuber_plane_reset.yaml --vault-password-file vault_password_client.sh
```

Then re-run from Phase 7.

### WireGuard key rotation

```bash
ansible-playbook wireguard_rotate_keys.yaml --vault-password-file vault_password_client.sh
```

---

## Troubleshooting quick reference

| Symptom | Check | Fix |
|---------|-------|-----|
| Worker/node NotReady | `wg show wg99 allowed-ips \| grep [k8s-api-vip]` — must be under primary plane pubkey only | Remove `[k8s-api-vip]/32` from secondary plane in vault_wg_peers, redeploy WG |
| HAProxy → MetalLB returns `000` | WG route `[metallb-pool-cidr]` on HAProxy — must point to a worker peer | Only the first worker peer should have `[metallb-pool-cidr]` in allowed_ips |
| App sees Traefik pod IP (raw pod IP) | App not trusting proxy | Add `[pod-network-cidr]` to app's KnownProxies/trusted proxy config |
| kubelet `certificate signed by unknown authority` | User kubeconfig stale | Use `sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl ...` |
| wg-quick fails: `wg99 already exists` | Stale interface after failed stop | `sudo ip link delete wg99 && sudo systemctl restart wg-quick@wg99` |
| BGP sessions not Established | WireGuard down or firewall | Check `wg show wg99`, `nc -zv <bgp-peer> 179` |
| ImagePullBackOff: IPv6 unreachable | AAAA records, no IPv6 route | Deploy dns_client_manage.yaml (filter-AAAA dnsmasq) |
