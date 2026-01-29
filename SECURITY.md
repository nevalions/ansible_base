# Security Best Practices

This document outlines security practices for this Ansible repository.

## Overview

This repository follows a minimal hardening approach to balance security and usability. Connection details are kept out of git, while SSH keys with passphrases are used for authentication.

## Security Architecture

### Connection Details
- **Location**: All connection variables (ansible_user, ansible_port, ansible_become) are stored in inventory files (`hosts_*.ini`)
- **Git Status**: Inventory files are excluded from git via `.gitignore`
- **Rationale**: Connection details reveal infrastructure topology and user accounts, which should be private

### SSH Key Management
- **Authentication**: SSH key-based authentication with passphrases
- **Passphrase Storage**: Passphrases are never stored in files; they are entered once per session via SSH agent
- **Key Storage**: Private keys are stored locally in `~/.ssh/` with restricted permissions (600)
- **SSH Agent**: Passphrases are cached in memory only for the duration of the session

### Group Variables
- **Templates**: Example files are provided in `group_vars/*.example.yml`
- **Local Configuration**: Users should create their own `group_vars/*.yml` files locally
- **Git Status**: Actual group_vars files are excluded from git via `.gitignore`

## Required Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ansible
```

### 2. Set Up SSH Keys
If you don't have SSH keys already:
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
```

Add public keys to target servers:
```bash
ssh-copy-id -p [custom-ssh-port] [your-username]@server-ip
```

### 3. Create Local Group Variables
Copy example files and customize for your environment:
```bash
cd group_vars
cp bay_cluster_all.example.yml bay_cluster_all.yml
cp bgp.example.yml bgp.yml
cp lb.example.yml lb.yml
# ... and so on for other groups
```

Customize the copied files with your connection details.

### 4. Configure Inventory Files
The inventory files (`hosts_*.ini`) are gitignored. If this is a fresh clone, you'll need to create them based on your infrastructure.

Example `hosts_bay.ini`:
```ini
[bay_cluster_all]
[control-plane-ip]
[worker-main-ip]

[bay_cluster_all:vars]
ansible_port=[custom-ssh-port]
ansible_user=[your-username]
ansible_become=true
ansible_become_method=sudo
ansible_python_interpreter=/usr/bin/python3
```

### 5. Start SSH Agent Session
```bash
./ssh-agent-setup.sh
```

This will prompt for your SSH key passphrases and cache them in memory.

### 6. Run Playbooks
```bash
ansible-playbook -i hosts_bay.ini upgrade_deb.yaml
ansible-playbook -i hosts_bay.yaml kuber.yaml
```

### 7. Stop SSH Agent Session
When done working:
```bash
./ssh-agent-stop.sh
```

This removes all keys from memory.

## Security Checklist

### Before Committing
- [ ] No passwords or API keys in any YAML files
- [ ] No ansible_ssh_private_key_file references
- [ ] No connection details in group_vars/*.yml
- [ ] Inventory files (*.ini) are not tracked by git
- [ ] SSH private keys are not in repository
- [ ] .vault.pass files are not in repository

### Before Running Playbooks
- [ ] SSH agent is running (`ssh-add -l` shows loaded keys)
- [ ] Group variables are configured locally
- [ ] Inventory files exist and are correct
- [ ] You have the correct SSH key passphrases
- [ ] SSH keys are added to target servers

### After Working Session
- [ ] SSH agent is stopped (`./ssh-agent-stop.sh`)
- [ ] No keys remain in memory

### Logging Security
- **Logging is disabled** in `ansible.cfg` to prevent secret leakage
- Ansible logs contain sensitive data when enabled:
  - Vault secrets in plaintext (passwords, passphrases)
  - IP addresses and network topology
  - SSH connection details and authentication patterns
  - Hostnames and user accounts
- If logging is required for debugging:
  - Enable temporarily with specific log levels
  - Filter sensitive data from logs
  - Delete logs immediately after use
  - Never commit log files to git

## What Should Never Be in Git

❌ **Never commit these:**
- SSH private keys (`id_rsa`, `id_ed25519`)
- Passwords (plaintext or hashed)
- API tokens or keys
- Inventory files with real IPs and connection details
- Group variable files with real connection details
- Vault password files
- SSH key passphrases

✅ **Safe to commit:**
- Playbooks and roles
- Templates
- Example configuration files (*.example.yml)
- Documentation
- ansible.cfg
- .ansible-lint

## Recommended: GPG-Secured Vault Password

This repository uses GPG encryption to secure the Ansible vault password.

### Architecture
- Vault password encrypted with GPG and stored in `vault_password.gpg`
- Client script `vault_password_client.sh` decrypts on demand
- Password only decrypted in memory during Ansible execution
- Never stored in plaintext on disk

### Initial Setup

#### 1. Create GPG Key (first time only)
```bash
gpg --full-generate-key
# RSA 4096-bit, no expiration
# Name: [your-username]
# Email: nevalions@gmail.com
# Comment: Ansible Vault
# Use a strong passphrase for the GPG key
```

#### 2. Encrypt Vault Password
```bash
# If migrating from plaintext .vault_pass:
cat .vault_pass | gpg --encrypt --recipient nevalions@gmail.com --armor --output vault_password.gpg

# For new passwords:
echo "your-new-vault-password" | gpg --encrypt --recipient nevalions@gmail.com --armor --output vault_password.gpg
```

#### 3. Make Script Executable
```bash
chmod 700 vault_password_client.sh
```

### Usage

When running Ansible:
- First use in session: Prompts for GPG key passphrase
- GPG caches passphrase (default 10 minutes)
- Subsequent runs: No prompt if passphrase cached

### Running Playbooks

```bash
# Direct ansible-playbook (uses ansible.cfg)
ansible-playbook upgrade_deb.yaml

# With vault script explicitly specified
ansible-playbook upgrade_deb.yaml --vault-password-file ./vault_password_client.sh

# Using the automated script with SSH agent
./ansible_with_agent.sh playbook.yaml
```

### Security Benefits
- ✅ Password encrypted at rest with strong cryptography (GPG AES256)
- ✅ Only decrypted in memory during use
- ✅ GPG passphrase required for each new session
- ✅ No plaintext password stored on disk
- ✅ Audit trail in GPG trust database
- ✅ Integrates with existing GPG key management

### Vault File Structure

Encrypted file: `vault_password.gpg`
- Contains: Ansible vault password (plaintext of [redacted])
- Encrypted with: GPG key for nevalions@gmail.com
- Format: ASCII-armored PGP message

Client script: `vault_password_client.sh`
- Purpose: Decrypt vault_password.gpg on demand
- Called by: ansible-playbook via ansible.cfg
- Output: Plaintext vault password to stdout

### Rotation

To rotate Ansible vault password:
```bash
# 1. Generate new vault password
NEW_PASS=$(openssl rand -base64 32)

# 2. Encrypt new password with GPG
echo "$NEW_PASS" | gpg --encrypt --recipient nevalions@gmail.com --armor --output vault_password.gpg

# 3. Re-encrypt all vault files with new password
ansible-vault rekey vault_secrets.yml --vault-password-file ./vault_password_client.sh
# Enter old password when prompted, then new password

# 4. Update ansible.cfg to point to new encrypted file (if needed)
```

To rotate GPG key:
```bash
# 1. Generate new GPG key
gpg --full-generate-key

# 2. Re-encrypt vault password with new key
gpg --decrypt --recipient nevalions@gmail.com vault_password.gpg | \
  gpg --encrypt --recipient NEW_EMAIL@gmail.com --armor --output vault_password.gpg.new
mv vault_password.gpg.new vault_password.gpg

# 3. Update vault_password_client.sh with new recipient

# 4. Revoke old GPG key if needed
gpg --edit-key OLD_KEY_ID
# Type "revkey" and follow prompts
```

### Troubleshooting

#### Script permission denied
```bash
chmod 700 vault_password_client.sh
```

#### GPG passphrase prompt not appearing
```bash
# Ensure GPG agent is running
gpg-agent --daemon

# Check GPG TTY
export GPG_TTY=$(tty)
```

#### Cannot decrypt vault password
```bash
# Verify you have the GPG secret key
gpg --list-secret-keys

# Test decryption manually
gpg --decrypt vault_password.gpg

# Check file permissions
ls -la vault_password.gpg  # Should be 600
```

#### Ansible cannot read vault password
```bash
# Test script manually
./vault_password_client.sh

# Check ansible.cfg
grep vault_password_file ansible.cfg

# Check script path
ls -la ./vault_password_client.sh
```

## Optional: Using ansible-vault

If you need to commit connection details to git (not recommended), use ansible-vault:

### Create Vault Password File
```bash
echo "your-vault-password" > .vault.pass
chmod 600 .vault.pass
```

### Add to .gitignore
```
.vault.pass
```

### Encrypt Group Variables
```bash
ansible-vault encrypt group_vars/*.yml
```

### Update ansible.cfg
```ini
vault_password_file = .vault.pass
```

### Run Playbooks with Vault
```bash
ansible-playbook upgrade_deb.yaml --ask-vault-pass
```

## SSH Key Security

### Generate Strong Passphrases
Use a password manager to generate:
- Minimum 16 characters
- Mix of uppercase, lowercase, numbers, and special characters
- Unique for each SSH key

### Key Permissions
Ensure private keys have correct permissions:
```bash
chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/*.pub
```

### Key Rotation
- Rotate SSH keys annually
- Rotate SSH key passphrases annually
- Remove old keys from `~/.ssh/authorized_keys` on servers

### Lost Key Procedures
If SSH keys are lost or compromised:
1. Immediately revoke access from all servers
2. Generate new SSH keys
3. Update `~/.ssh/authorized_keys` on all servers
4. Rotate SSH key passphrases

## Incident Response

### Suspected Compromise
If you suspect this repository or your SSH keys are compromised:

1. **Immediate Actions**
   - Stop SSH agent: `./ssh-agent-stop.sh`
   - Revoke SSH key access from all servers
   - Change server passwords (if used)

2. **Investigation**
   - Review git commit history for suspicious changes
   - Check `~/.ssh/authorized_keys` on all servers
   - Review server logs for unauthorized access

3. **Remediation**
   - Generate new SSH keys with new passphrases
   - Update all server `~/.ssh/authorized_keys` files
   - Rotate any passwords or tokens
   - Audit all infrastructure access

## Resources

- [Ansible Security Best Practices](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
- [SSH Agent Usage](SSH_AGENT_QUICKREF.md)
- [Ansible Galaxy Security](https://galaxy.ansible.com/docs/contributing/content_security.html)

## Contact

For security concerns or questions about this repository's security practices, please contact the repository maintainer.
