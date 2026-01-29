# Ansible Vault + SSH Key Passphrase Setup

## Overview

This setup uses **ansible.netcommon.libssh** connection plugin to connect with SSH key passphrase and sudo password, both stored encrypted in Ansible Vault.

## Architecture

```
┌─────────────────┐
│ Vault Password  │ (Entered once per session)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  vault_secrets.yml (encrypted)   │
│  - vault_ssh_key_passphrase      │ (SSH key passphrase)
│  - vault_become_pass             │ (sudo password)
└────────┬────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  ansible.netcommon.libssh                │
│  - Uses ansible_private_key_passphrase     │
│  - Uses ansible_become_pass                │
└────────┬──────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Inventory Variables (hosts_bay.ini)                │
│  - ansible_connection=ansible.netcommon.libssh      │
│  - ansible_private_key_file=~/.ssh/id_rsa           │
│  - ansible_private_key_passphrase="{{ ... }}"       │
│  - ansible_become_pass="{{ ... }}"                 │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

- ansible.netcommon collection installed (version 5.3.0 or higher)
- SSH key with passphrase
- Vault file setup

## Setup Steps

### 1. Verify Collection Installation

```bash
ansible-galaxy collection list | grep netcommon
```

Should show: `ansible.netcommon 5.3.0`

### 2. Configure Vault Variables

Edit `vault_secrets.yml` to include:

```yaml
---
vault_ssh_key_passphrase: "your_ssh_key_passphrase"
vault_become_pass: "your_sudo_password"
```

Encrypt the vault:

```bash
ansible-vault encrypt vault_secrets.yml
```

### 3. Inventory Configuration

Host groups in `hosts_bay.ini` are configured to use:

```ini
[workers_all:vars]
ansible_connection=ansible.netcommon.libssh
ansible_user=[your-username]
ansible_port=[custom-ssh-port]
ansible_become=true
ansible_become_method=sudo
ansible_private_key_file=~/.ssh/id_rsa
ansible_private_key_passphrase="{{ vault_ssh_key_passphrase }}"
ansible_become_pass="{{ vault_become_pass }}"
ansible_python_interpreter=/usr/bin/python3
```

### 4. Test Connectivity

**Test vault variables:**
```bash
ansible-playbook test_vault_vars.yaml --ask-vault-pass
```

**Test SSH connection without sudo:**
```bash
ansible-playbook test_ssh_only.yaml --ask-vault-pass
```

**Test SSH connection with sudo:**
```bash
ansible-playbook test_vault_connectivity.yaml --ask-vault-pass
```

## Usage in Playbooks

All playbooks that need SSH + sudo access must include:

```yaml
---
- name: Your playbook
  hosts: workers_all
  gather_facts: true
  vars_files:
    - vault_secrets.yml
  tasks:
    - name: Your task
      ansible.builtin.apt:
        name: nginx
        state: present
```

## Connection Variables Explained

| Variable | Purpose | Source |
|----------|---------|--------|
| `ansible_connection` | Use libssh plugin | inventory |
| `ansible_private_key_file` | Path to SSH key | inventory |
| `ansible_private_key_passphrase` | SSH key passphrase | vault via inventory |
| `ansible_become_pass` | Sudo password | vault via inventory |

## Security Benefits

1. **Dual encryption**: Vault password protects both SSH key passphrase and sudo password
2. **No plaintext passwords**: All credentials encrypted in vault
3. **SSH key auth**: More secure than password-based SSH
4. **Audit trail**: Sudo operations are logged on target servers
5. **Single entry point**: One vault password per session

## Troubleshooting

### Vault password prompt fails

Check that `vault_secrets.yml` is properly encrypted:
```bash
ansible-vault view vault_secrets.yml
```

### Connection timeout with libssh

Verify the collection is installed:
```bash
ansible-galaxy collection list | grep netcommon
```

### "Timeout waiting for privilege escalation prompt"

This means sudo password is incorrect. Check:
```bash
ansible-playbook test_vault_vars.yaml --ask-vault-pass
```

### SSH key passphrase error

Verify the key exists and has passphrase:
```bash
ssh-keygen -y -f ~/.ssh/id_rsa
```

## Alternative: Password File for Automation

Create `.vault_pass` file:
```bash
echo 'your_vault_password' > .vault_pass
chmod 600 .vault_pass
```

Use with playbooks:
```bash
ansible-playbook playbook.yaml --vault-password-file .vault_pass
```

## Files Reference

- `vault_secrets.yml` - Encrypted vault (gitignored)
- `vault_secrets.example.yml` - Example vault structure
- `hosts_bay.ini` - Inventory with libssh configuration
- `test_vault_vars.yaml` - Test vault decryption
- `test_ssh_only.yaml` - Test SSH without sudo
- `test_vault_connectivity.yaml` - Test SSH with sudo

## Vault Management Commands

```bash
# View vault
ansible-vault view vault_secrets.yml

# Edit vault
ansible-vault edit vault_secrets.yml

# Change vault password
ansible-vault rekey vault_secrets.yml

# Decrypt vault (temporary)
ansible-vault decrypt vault_secrets.yml

# Encrypt string
ansible-vault encrypt_string 'secret' --name 'my_var'
```

## Important Notes

- SSH keys MUST have passphrase (not empty)
- Use different passwords for vault and SSH key
- Never commit vault_secrets.yml to git
- Keep vault password secure
- This setup works with ansible-core 2.16+
