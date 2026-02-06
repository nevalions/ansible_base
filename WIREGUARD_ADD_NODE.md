---
# Add WireGuard Client or Server

Step-by-step commands and required edits for adding a new WireGuard client or server.
Placeholders only. Do not use real IPs, hostnames, usernames, or ports.

## Prerequisites

- Inventory file is up to date and includes the new host in the correct group.
- `vault_secrets.yml` is accessible via `ansible-vault`.
- You know the new peer name, host group, VPN IP, and endpoint details.

## Add a New Client

### 1) Update inventory

Add the client host to its inventory group.

```bash
# Example (inventory file)
ansible-inventory -i [inventory-file] --list
```

### 2) Update vault peer list

Edit `vault_secrets.yml` and add a peer entry:

```bash
ansible-vault edit vault_secrets.yml
```

```yaml
vault_wg_peers:
  - name: "[client-name]"
    host_group: "[client-inventory-group]"
    allowed_ips: "[client-vpn-ip]/32"
    endpoint: "[client-public-or-internal-ip]:[client-port]"
    client_listen_port: "[client-port]"
```

### 3) Generate client keys

```bash
bash generate_wg_keys.sh > wg_keys.yaml
```

Copy the new client keys from `wg_keys.yaml` into `vault_secrets.yml`:

```yaml
vault_wg_peer_private_keys:
  [client-name]: "[client-private-key]"

vault_wg_peer_public_keys:
  [client-name]: "[client-public-key]"
```

### 4) Apply on servers (required)

Run the playbook on all WireGuard servers so they learn the new client peer:

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [server-group]
```

### 5) Apply on the client

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [client-host]
```

### 6) Verify

```bash
ansible-playbook -i [inventory-file] wireguard_verify.yaml --tags wireguard,verify
```

## Add a New Server

### 1) Update inventory

Add the server host to its inventory group.

### 2) Update server mapping

Edit `vault_secrets.yml` and add the server to the mesh mappings:

```bash
ansible-vault edit vault_secrets.yml
```

```yaml
vault_wg_server_ips:
  [server-group]: "[server-vpn-ip]"

vault_wg_server_ports:
  [server-group]: "[server-port]"
```

### 3) Add server peer entry

```yaml
vault_wg_peers:
  - name: "[server-name]"
    host_group: "[server-group]"
    allowed_ips: "[server-vpn-ip]/32"
    endpoint: "[server-public-or-internal-ip]:[server-port]"
```

### 4) Generate server keys

```bash
bash generate_wg_keys.sh > wg_keys.yaml
```

Copy the new server keys from `wg_keys.yaml` into `vault_secrets.yml`:

```yaml
vault_wg_peer_private_keys:
  [server-name]: "[server-private-key]"

vault_wg_peer_public_keys:
  [server-name]: "[server-public-key]"
```

### 5) Apply on all servers (mesh update)

Run the playbook on the server group so all servers include the new server peer:

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [server-group]
```

### 6) Apply on the new server (if not included above)

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [new-server-host]
```

### 7) Verify

```bash
ansible-playbook -i [inventory-file] wireguard_verify.yaml --tags wireguard,verify
```

## Optional: Dry Run (Check Mode)

```bash
ansible-playbook -i [inventory-file] wireguard_manage.yaml --tags wireguard --limit [host-or-group] --check
```
