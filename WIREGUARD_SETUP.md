# WireGuard Setup Instructions

## Step 1: Generate WireGuard Keys

### Prerequisites

1. Ensure `vault_secrets.yml` contains `vault_wg_peers` list with peer names:
   ```yaml
   vault_wg_peers:
     - name: "[PEER_1]"
       host_group: "[ansible-host-group]"
       allowed_ips: "[peer-vpn-ip]/32"
       endpoint: "[peer-public-ip]:[port]"
       client_listen_port: "[unique-port-for-nat-peers]"
     - name: "[PEER_2]"
       host_group: "[ansible-host-group]"
       allowed_ips: "[peer-vpn-ip]/32]"
       endpoint: "[peer-public-ip]:[port]"
       client_listen_port: "[unique-port-for-nat-peers]"
   ```

2. Ensure vault password client exists and GPG is set up:
   - Verify `vault_password_client.sh` exists and is executable
   - Ensure `vault_password.gpg` file exists (GPG-encrypted vault password)
   - Have GPG secret key for `***@gmail.com` imported
   - First use: GPG passphrase prompt will appear

   For GPG setup details, see **[SECURITY.md](SECURITY.md#recommended-gpg-secured-vault-password)**

### Generate Keys

Run the script to generate all necessary keys:

```bash
bash generate_wg_keys.sh > wg_keys.yaml
```

This will automatically:
- Decrypt vault password using GPG via `vault_password_client.sh`
- Read peer names from `vault_wg_peers` in `vault_secrets.yml`
- Generate server private and public keys
- Generate private and public keys for each peer listed in vault
- Output YAML keys in vault-compatible format

## Step 2: Update vault_secrets.yml

Open the vault file:
```bash
ansible-vault edit vault_secrets.yml
```

### Around line 103-108, replace the peer keys sections:
```yaml
vault_wg_peer_private_keys:
  [PEER_1]: null
  [PEER_2]: null
  [PEER_3]: null
  [PEER_4]: null

vault_wg_peer_public_keys:
  [PEER_1]: "null"
  [PEER_2]: "null"
  [PEER_3]: "null"
  [PEER_4]: "null"
```

With the generated keys:
```yaml
vault_wg_peer_private_keys:
  [PEER_1]: "PEER_PRIVATE_KEY_HERE"
  [PEER_2]: "PEER_PRIVATE_KEY_HERE"
  [PEER_3]: "PEER_PRIVATE_KEY_HERE"
  [PEER_4]: "PEER_PRIVATE_KEY_HERE"

vault_wg_peer_public_keys:
  [PEER_1]: "PEER_PUBLIC_KEY_HERE"
  [PEER_2]: "PEER_PUBLIC_KEY_HERE"
  [PEER_3]: "PEER_PUBLIC_KEY_HERE"
  [PEER_4]: "PEER_PUBLIC_KEY_HERE"
```

 ## Step 3: Verify Keys

 Verify keys are properly configured:
 ```bash
 ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard --limit [server-ip] --check
 ```

The playbook should now pass the key validation check.

 ## Step 4: Deploy WireGuard

 Run full deployment:
 ```bash
 ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard
 ```

 ## Step 5: Verify WireGuard is Running

 Check WireGuard status on each host:
 ```bash
 # Server ([server-hostname])
 ansible -i hosts_bay.ini [server-ip] -b -m shell -a "wg show [interface-name]"

 # Client ([client-hostname])
 ansible -i hosts_bay.ini [client-ip] -b -m shell -a "wg show [interface-name]"
 ```

## Step 5: Verify WireGuard is Running

Check WireGuard status on each host:
```bash
# Server ([SERVER_HOSTNAME])
ansible -i hosts_bay.ini [SERVER_IP] -b -m shell -a "wg show [INTERFACE_NAME]"

# Client ([CLIENT_HOSTNAME])
ansible -i hosts_bay.ini [CLIENT_IP] -b -m shell -a "wg show [INTERFACE_NAME]"
```

## Troubleshooting

 ### Service fails to start
 Check journal logs:
 ```bash
 ansible -i hosts_bay.ini [hostname] -b -m shell -a "journalctl -xeu wg-quick@[interface-name].service --no-pager -n 50"
 ```

### Keys are empty in config
Verify vault keys are properly set:
```bash
ansible-vault view vault_secrets.yml | grep -A 5 "vault_wg_peer_private_keys"
ansible-vault view vault_secrets.yml | grep -A 5 "vault_wg_peer_public_keys"
```

### Config has wrong endpoint IP
The client template was fixed to use `server_public_ip` instead of `ansible_default_ipv4.address`.

### Vault password script not found
Error message: `Error: Vault password script not found: ./vault_password_client.sh`

**Solutions:**
```bash
# Ensure script exists and is executable
chmod +x vault_password_client.sh

# Or use custom path if needed
export ANSIBLE_VAULT_PASSWORD_FILE=./custom_vault.sh
```

### GPG passphrase not appearing
If GPG passphrase prompt doesn't appear:

```bash
# Ensure GPG agent is running
gpg-agent --daemon

# Check GPG TTY
export GPG_TTY=$(tty)

# Test decryption manually
gpg --decrypt vault_password.gpg
```

### Cannot decrypt vault password
If vault decryption fails:

```bash
# Verify you have the GPG secret key
gpg --list-secret-keys

# Check file permissions
ls -la vault_password.gpg  # Should be 600

# Test vault password script directly
./vault_password_client.sh

# Test ansible-vault manually
ansible-vault view vault_secrets.yml
```

For detailed GPG setup and troubleshooting, see **[SECURITY.md](SECURITY.md)**
