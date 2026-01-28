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
ssh-copy-id -p [custom-ssh-port] user@server-ip
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
[internal-ip]
[internal-ip]

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
