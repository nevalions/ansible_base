# nfd role

Installs, verifies, or removes Kubernetes Node Feature Discovery (NFD) using upstream kustomize manifests.

## Variables

- `nfd_state` - Role mode: `install`, `verify`, or `remove` (default: `install`)
- `nfd_version` - NFD release tag (default: `v0.18.2`)
- `nfd_manifest_url` - Kustomize URL for NFD manifests
- `nfd_namespace` - Target namespace (default: `node-feature-discovery`)
- `nfd_rollout_timeout` - Rollout wait timeout (default: `180s`)
- `nfd_kubeconfig` - Kubeconfig path, defaults to `$KUBECONFIG` then `~/.kube/config`

## Usage

Use the standalone playbooks in `nfd/`:

```bash
ansible-playbook -i hosts_bay.ini nfd/kuber_nfd_install.yaml
ansible-playbook -i hosts_bay.ini nfd/kuber_nfd_verify.yaml
ansible-playbook -i hosts_bay.ini nfd/kuber_nfd_remove.yaml
```

The playbooks set `become: false` and export `KUBECONFIG` to avoid `kubectl` defaulting to
`http://localhost:8080` when global inventory sudo settings are enabled.
