# LibSSH Implementation - Next Steps

## What Was Configured

✅ **Inventory Updated** (`hosts_bay.ini`)
- All host groups now use `ansible_connection=ansible.netcommon.libssh`
- SSH key authentication with `ansible_private_key_file=~/.ssh/id_rsa`
- SSH key passphrase from vault: `ansible_private_key_passphrase="{{ vault_ssh_key_passphrase }}"`
- Sudo password from vault: `ansible_become_pass="{{ vault_become_pass }}"`

✅ **Test Playbooks Updated**
- `test_vault_vars.yaml` - Tests vault variable access
- `test_ssh_only.yaml` - Tests SSH without sudo
- `test_vault_connectivity.yaml` - Tests SSH with sudo
- All playbooks load `vault_secrets.yml`

✅ **Documentation Updated**
- `VAULT_SETUP.md` - Complete guide for libssh + vault setup
- `vault_secrets.example.yml` - Example structure updated

## You Need To Do

### Step 1: Update Vault File

Your `vault_secrets.yml` needs TWO variables:

```yaml
---
vault_ssh_key_passphrase: "your_ssh_key_passphrase"  # Passphrase for ~/.ssh/id_rsa
vault_become_pass: "your_sudo_password"              # Password for sudo
```

Update and re-encrypt:

```bash
ansible-vault edit vault_secrets.yml
# Enter vault password, then edit the file with the above variables
```

### Step 2: Test Vault Variables

Verify vault can decrypt:

```bash
ansible-playbook test_vault_vars.yaml --ask-vault-pass
```

Expected output should show your SSH key passphrase and sudo password.

### Step 3: Test SSH Connection

Test without sudo:

```bash
ansible-playbook test_ssh_only.yaml --ask-vault-pass
```

Expected: All hosts return "[your-username]" as the user.

### Step 4: Test SSH + Sudo

Test with sudo:

```bash
ansible-playbook test_vault_connectivity.yaml --ask-vault-pass
```

Expected: All hosts return "root" as the user.

## Troubleshooting

### "Attempting to decrypt but no vault secrets found"
- This happens with `--syntax-check` because it tries to decrypt vault
- Ignore this error, it's normal

### SSH connection fails
- Check your SSH key has passphrase: `ssh-keygen -y -f ~/.ssh/id_rsa`
- Verify passphrase is correct in vault: `ansible-vault view vault_secrets.yml`

### Sudo fails
- Verify sudo password is correct
- Check user can run sudo manually: `ssh -p [custom-ssh-port] [your-username]@<host> -t sudo whoami`

## How It Works

1. You enter vault password once (per session)
2. Ansible decrypts `vault_secrets.yml`
3. Inventory variables reference vault values
4. libssh plugin uses:
   - `vault_ssh_key_passphrase` → SSH key authentication
   - `vault_become_pass` → Sudo password
5. Connections established securely with encrypted credentials

## For Other Playbooks

All playbooks that need SSH + sudo must include:

```yaml
vars_files:
  - vault_secrets.yml
```

This ensures vault variables are available to the connection plugin.
