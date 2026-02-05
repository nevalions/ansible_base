# kuber_plane_join

Join additional control plane nodes to an existing Kubernetes HA cluster.

## Description

This role handles joining a new node as a Kubernetes control plane, enabling HA (High Availability) cluster configurations. It:

1. Uploads cluster certificates from existing control plane
2. Generates join token with control-plane privileges
3. Configures containerd and kubelet
4. Joins the node as a control plane using kubeadm
5. Verifies the node is Ready and has control-plane components

## Requirements

- Existing Kubernetes cluster with at least one control plane
- Kubernetes prerequisites installed on new node (use `kuber.yaml`)
- Network connectivity to existing control plane (WireGuard VPN)
- VIP configured via Keepalived for HA API access

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `kuber_plane_join_control_plane_host` | `VIP` | Delegate host for control plane operations |
| `kuber_plane_join_control_plane_ip` | `vault_k8s_api_vip` | Control plane endpoint IP |
| `kuber_plane_join_api_port` | `vault_k8s_api_port` | Kubernetes API port |
| `kuber_plane_join_token_ttl` | `0` | Token TTL (0 = no expiry) |
| `kuber_plane_join_kubelet_extra_args` | `{node-ip: wg_ip}` | Extra kubelet arguments |
| `kubeadm_api_version` | `v1beta4` | kubeadm API version |

## Dependencies

- `wireguard` role (for VPN connectivity)
- `keepalived` role (for VIP failover)
- `kuber` role (Kubernetes prerequisites)

## Example Playbook

```yaml
---
- name: Join additional control plane
  hosts: new_plane
  become: true
  gather_facts: true
  vars_files:
    - vault_secrets.yml
  roles:
    - kuber_plane_join
```

## Usage with Full Stack

For complete setup including WireGuard and Keepalived, use the `kuber_plane_join.yaml` playbook:

```bash
# Edit the playbook to set target host
vim kuber_plane_join.yaml
# Change [plane-hostname] to your new control plane host

# Dry run
ansible-playbook kuber_plane_join.yaml --check

# Execute
ansible-playbook kuber_plane_join.yaml
```

## Prerequisites Checklist

Before running, ensure:

1. New host added to inventory groups:
   - `wireguard_servers`
   - `planes_all`

2. WireGuard configuration in `vault_secrets.yml`:
   - Peer entry in `vault_wg_peers`
   - Server IP in `vault_wg_server_ips`
   - Server port in `vault_wg_server_ports`
   - Keys in `vault_wg_peer_private_keys` and `vault_wg_peer_public_keys`

3. Keepalived entry in `vault_secrets.yml`:
   ```yaml
   vault_k8s_control_planes:
     - name: "[new-plane-hostname]"
       wireguard_ip: "[new-plane-wg-ip]"
       api_port: "[k8s-api-port]"
       priority: 100  # Lower than MASTER
   ```

4. Kubernetes packages installed (run `kuber.yaml` first)

## License

MIT

## Author

[your-username]
