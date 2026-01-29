# NFS Server Role

Configures and manages NFS server exports.

## Role Variables

### Required Variables

None - all variables have defaults.

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `skip_folder_check` | `true` | Skip folder existence checks during setup |

### Export Configuration

Define NFS exports in playbook variables:

```yaml
nfs_exports:
  - path: /export/data
    clients:
      - "[client-network]"
      - "[backup-server-ip]"
    options: "rw,sync,no_subtree_check"

nfs_exports_to_remove:
  - path: /export/old_share
    clients: ["[backup-network]"]
    options: "rw,sync,no_subtree_check"
    remove_dir: false
```

### Export Options

Common export options:
- `rw` - Read-write access
- `ro` - Read-only access
- `sync` - Synchronous writes
- `no_subtree_check` - Disable subtree checking (recommended)
- `root_squash` - Map root to anonymous user (default)
- `no_root_squash` - Don't map root (use with caution)

## Handlers

Available handlers:

| Handler | Description |
|---------|-------------|
| `restart nfs` | Restart NFS server service |
| `reload exports` | Reload NFS exports configuration |

## Tasks Structure

```
roles/nfs_server/
├── tasks/
│   ├── main.yaml      # Main entry point
│   ├── folders.yaml   # Create export directories
│   ├── exports.yaml   # Configure exports
│   └── remove.yaml   # Remove exports
├── handlers/
│   └── main.yaml      # Service handlers
├── defaults/
│   └── main.yaml     # Default variables
└── templates/
    └── exports.j2     # Exports configuration template
```

## Usage

### Basic Usage

```yaml
- name: Configure NFS server
  hosts: nfs_servers
  become: yes
  vars:
    nfs_exports:
      - path: /export/data
        clients: ["[client-network]"]
        options: "rw,sync,no_subtree_check"
  roles:
    - nfs_server
```

### Using the Management Playbook

```bash
# Add new export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=install \
  -e add_nfs_server_exports_path=/export/new_share \
  -e add_nfs_server_exports="[client-network]"

# Remove export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=remove \
  -e remove_nfs_server_exports_path=/export/old_share \
  -e remove_nfs_server_exports="[client-network]"
```

## Dependencies

- `ufw` (Debian/Ubuntu) for firewall rules
- `nfs-kernel-server` package

## OS Compatibility

| OS Family | Status |
|-----------|--------|
| Debian/Ubuntu | ✅ Supported |
| Arch/Manjaro | ⚠️ Untested |

## Examples

### Multiple Exports

```yaml
nfs_exports:
  - path: /export/web
    clients: ["web_server_group"]
    options: "rw,sync,no_subtree_check"
  
  - path: /export/backup
    clients: ["backup_server", "[backup-network]"]
    options: "ro,sync,no_subtree_check"
  
  - path: /export/data
    clients: ["0.0.0.0/0"]
    options: "rw,sync,no_root_squash"
```

### Custom Export Directory Permissions

```yaml
nfs_exports:
  - path: /export/special
    clients: ["[backup-network]"]
    options: "rw,sync,no_subtree_check"
```

## Firewall Configuration

The role automatically configures UFW firewall rules for each client:
```yaml
- name: Allow NFS through firewall for each client
  community.general.ufw:
    rule: allow
    proto: tcp
    port: "2049"
    src: "{{ client }}"
```

## Validation

The role includes validation tasks to ensure:
- NFS server is installed and running
- Export directories exist with proper permissions
- Firewall rules are configured
- Exports are properly registered

## Troubleshooting

### Export not accessible
```bash
# Check exports
showmount -e localhost

# Check NFS status
systemctl status nfs-kernel-server

# View logs
journalctl -u nfs-kernel-server
```

### Firewall blocking access
```bash
# Check UFW status
ufw status

# Test connectivity
telnet <nfs_server_ip> 2049
```

### Permission denied
```bash
# Check directory permissions
ls -ld /export/data

# Check export permissions
cat /etc/exports
```