# DNS Client Role

Configure DNS client settings on Debian/Ubuntu systems by managing `/etc/resolv.conf`.

## Requirements

- Debian/Ubuntu system
- Ansible 2.16+
- `become: true` privileges

## Role Variables

### Required Vault Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `vault_dns_server_primary` | Primary DNS server IP | `[primary-dns-server-ip]` |
| `vault_dns_server_secondary` | Secondary DNS server IP | `[secondary-dns-server-ip]` |
| `vault_dns_zone` | DNS search domain | `[search-domain]` |

### Optional Vault Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `vault_dns_client_options` | List of resolv.conf options | `["timeout:2", "attempts:3", "rotate"]` |

## Dependencies

None

## Example Playbook

### Install DNS Client Configuration

```yaml
---
- name: Configure DNS on WireGuard clients
  hosts: wireguard_clients
  become: true
  vars_files:
    - vault_secrets.yml
  vars:
    dns_operation: "install"

  roles:
    - dns_client
```

### Remove DNS Client Configuration

```yaml
---
- name: Restore default DNS configuration
  hosts: wireguard_clients
  become: true
  vars:
    dns_operation: "remove"

  roles:
    - dns_client
```

## Usage

### Using the provided playbook:

```bash
# Install DNS client configuration
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns

# Install on specific hosts
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --limit wireguard_clients

# Remove DNS client configuration (restore systemd-resolved)
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml -e dns_operation=remove --tags dns
```

### Using the role directly:

```bash
ansible-playbook your_playbook.yaml
```

## What This Role Does

### On Install:

1. Stops and disables `systemd-resolved` (Debian/Ubuntu only)
2. Removes the systemd-resolved stub `/etc/resolv.conf`
3. Backs up the original `/etc/resolv.conf` to `/etc/resolv.conf.original`
4. Deploys a new `/etc/resolv.conf` with your custom DNS settings
5. Tests DNS resolution to verify connectivity
6. Asserts that DNS is working correctly

### On Remove:

1. Restores the original `/etc/resolv.conf` from backup (if it exists)
2. Removes the Ansible-managed `/etc/resolv.conf` if no backup exists
3. Re-enables and starts `systemd-resolved`
4. Cleans up backup files

## Inventory Setup

No special inventory groups are required. You can target any hosts:

```ini
# In hosts_bay.ini
[dns_clients:children]
wireguard_clients
# Or add specific hosts as needed
```

## Vault Configuration

The DNS client role reuses existing DNS server variables from `vault_secrets.yml`:

**Required (existing variables):**
```yaml
# DNS Server Configuration
vault_dns_zone: "cluster.local"
vault_dns_server_primary: "[primary-dns-server-ip]"
vault_dns_server_secondary: "[secondary-dns-server-ip]"
```

**Optional:**
```yaml
# DNS Client Options (for resolv.conf settings)
vault_dns_client_options:
  - "timeout:2"
  - "attempts:3"
  - "rotate"
```

## Testing DNS Resolution

The role automatically tests DNS resolution during installation. To manually test:

```bash
# From a client host
nslookup google.com [dns-server-vpn-ip]

# Or use dig
dig @[dns-server-vpn-ip] google.com
```

## Troubleshooting

### DNS resolution fails:

1. Verify WireGuard VPN is running and connected
2. Check that DNS servers are accessible via VPN:
   ```bash
   ping [primary-dns-server-vpn-ip]
   ping [secondary-dns-server-vpn-ip]
   ```
3. Verify DNS server is running:
   ```bash
   systemctl status unbound
   ```
4. Check `/etc/resolv.conf` contains correct nameservers:
   ```bash
   cat /etc/resolv.conf
   ```

### systemd-resolved keeps taking over:

If `systemd-resolved` is interfering:
```bash
# Stop and disable
systemctl stop systemd-resolved
systemctl disable systemd-resolved

# Remove stub file
rm /etc/resolv.conf

# Run this playbook again to deploy custom configuration
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --tags dns
```

## Security Considerations

- This role requires `become: true` (root privileges)
- `/etc/resolv.conf` is a system-critical file - test in non-production first
- Original configuration is backed up before changes

## License

MIT
