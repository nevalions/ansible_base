# Longhorn Clean Role

Removes Longhorn storage folders and data from Kubernetes workers.

## Role Variables

### Default Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `longhorn_data_path` | `/var/lib/longhorn` | Longhorn data directory to remove |
| `kubelet_pods_path` | `/var/lib/kubelet/pods` | Kubelet pods directory for Longhorn pod data |

## Handlers

None - this role performs cleanup operations that don't require service restarts.

## Tasks Structure

```
roles/longhorn_clean/
├── tasks/
│   ├── main.yaml      # Main entry point
│   └── remove.yaml    # Removal tasks with verification
├── handlers/
│   └── main.yaml      # Handlers file (empty)
└── defaults/
    └── main.yaml      # Default variables
```

## Usage

### Basic Usage

```yaml
- name: Remove Longhorn from workers
  hosts: workers_all
  become: yes
  roles:
    - longhorn_clean
```

### Using the Management Playbook

The playbook loads vault secrets from `vault_secrets.yml` for any sensitive credentials.

```bash
# Dry-run to see what will be removed
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml --check

# Execute removal
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml

# With verbosity for debugging
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml -v
```

### Custom Paths

Override default paths if needed:

```bash
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml \
  -e longhorn_data_path=/custom/path/to/longhorn \
  -e kubelet_pods_path=/custom/path/to/kubelet/pods
```

## What Gets Removed

1. **Longhorn Data Directory**: Recursively removes `/var/lib/longhorn/`
2. **Longhorn Pod Data**: Finds and removes directories matching `*longhorn*` pattern in `/var/lib/kubelet/pods/`

## Verification

The role includes verification tasks to ensure:
- Longhorn data directory is successfully removed
- All Longhorn pod directories are removed
- Assertions fail if removal was incomplete

## Safety Features

- **Check Mode**: Supports `--check` flag for dry-run testing
- **Conditional Execution**: Only removes directories that exist
- **Verification**: Confirms successful removal with assertions

## OS Compatibility

| OS Family | Status |
|-----------|--------|
| Debian/Ubuntu | ✅ Supported |
| Arch/Manjaro | ⚠️ Untested |

## Examples

### Target Specific Workers

```yaml
- name: Remove Longhorn from specific workers
  hosts: workers_super
  become: yes
  roles:
    - longhorn_clean
```

### Remove from All Workers

```bash
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml
```

## Troubleshooting

### Check what will be removed

```bash
# Dry-run mode
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml --check -v
```

### Verify directories are gone

```bash
# Check on worker
ssh worker_host "ls -la /var/lib/ | grep longhorn"
ssh worker_host "find /var/lib/kubelet/pods -name '*longhorn*'"
```

### Permission denied errors

Ensure the playbook runs with `become: true` or use sudo:

```bash
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml --ask-become-pass
```

### Files still exist after removal

Check playbook output for verification assertions. If removal failed, ensure:
- Ansible has sufficient privileges
- No processes are holding files open
- Disk/filesystem is not read-only
