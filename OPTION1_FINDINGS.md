# SSH Key Passphrase Implementation - Findings and Solution

## Option 1 (libssh + ansible_private_key_passphrase) - NOT WORKING

### Issues Discovered:

1. **Vault Variable Timing Issue**
   - Inventory variables with `{{ vault_ssh_key_passphrase }}` don't work
   - Vault is loaded during playbook execution, but connection happens before that
   - ansible_private_key_passphrase must be available at connection time

2. **LibSSH TTY/PTY Issues**
   - Error: "Inappropriate ioctl for device" on multiple hosts
   - libssh has compatibility issues with some SSH servers
   - Even with `pty: False` in ansible.cfg, issues persist

3. **ansible-pylibssh Requirements**
   - Must be installed on Ansible controller (not remote hosts)
   - Version 1.3.0 successfully installed on controller
   - Bootstrap playbook successfully installed on hosts, but not needed

### Test Results:
- ❌ LibSSH with passphrase-protected key: Failed
- ❌ LibSSH with passphrase-less key: Partial success (module failures)
- ❌ Inventory variable interpolation with vault: Failed
- ✅ ansible-pylibssh installation: Success

## Working Solution: SSH Agent Automation (Option 3)

### Why This Works:
1. SSH agent manages passphrase in memory only
2. Works with any SSH connection type (ssh, libssh, paramiko)
3. No modifications to inventory variables needed
4. Secure: Passphrase never written to disk
5. Ansible playbooks can load vault for become password

### Implementation Steps:

#### 1. Create SSH Agent Automation Script

File: `/home/[your-username]/ansible/ansible_with_agent.sh`
```bash
#!/bin/bash
# Start SSH agent, add keys, run Ansible playbook with vault

# Start SSH agent
eval "$(ssh-agent -s)"

 # Add SSH key with passphrase
 echo "Adding SSH key..."
 # Note: Passphrase should be retrieved from vault, not hardcoded
 ssh-add ~/.ssh/id_rsa <<< "your-passphrase-here"

# Verify key added
if ssh-add -l > /dev/null 2>&1; then
    echo "✅ SSH key added to agent"
else
    echo "❌ Failed to add SSH key"
    exit 1
fi

# Run Ansible playbook
ansible-playbook "$@" --vault-password-file .vault_pass

# Optional: Kill agent after playbook
ssh-agent -k
```

#### 2. Update Inventory Configuration

File: `/home/[your-username]/ansible/hosts_bay.ini`
```ini
[workers_all:vars]
ansible_connection=ansible.builtin.ssh  # or ansible.netcommon.libssh
ansible_port=[custom-ssh-port]
ansible_user=[your-username]
ansible_become=true
ansible_become_method=sudo
ansible_private_key_file=~/.ssh/id_rsa
ansible_become_pass="{{ vault_become_pass }}"
ansible_python_interpreter=/usr/bin/python3
```

**Key changes:**
- Removed `ansible_private_key_passphrase` (not needed with SSH agent)
- Removed `ansible_connection=ansible.netcommon.libssh` (optional, can use)
- Keep vault vars only for `ansible_become_pass`

#### 3. Update Playbooks

All playbooks that need SSH + sudo should:
```yaml
---
- name: Your playbook
  hosts: workers_all
  gather_facts: true
  vars_files:
    - vault_secrets.yml  # Load vault for become password
  tasks:
    - name: Your task
      ansible.builtin.debug:
        msg: "Running with SSH agent + vault for sudo"
```

#### 4. Usage Examples

**Simple playbook:**
```bash
./ansible_with_agent.sh test_ssh_only.yaml
```

**With extra variables:**
```bash
./ansible_with_agent.sh playbook.yaml -e "var=value"
```

**With tags:**
```bash
./ansible_with_agent.sh playbook.yaml --tags docker
```

## Alternative Solutions Considered

### Option 2: Vault Encrypted SSH Key
- Complexity: Medium
- Security: High
- Pros: Key never stored unencrypted on disk
- Cons: Requires custom task to decrypt, key briefly unencrypted in /tmp

### Option 5: Passphrase-less SSH Key
- Complexity: Low
- Security: Low
- Pros: Simple, no passphrase management
- Cons: **NOT RECOMMENDED** - if private key is stolen, unrestricted access

## Files Created for Testing

1. `bootstrap_libssh.yaml` - Bootstrap playbook (can be kept for future use)
2. `hosts_bay_bootstrap.ini` - Bootstrap inventory (can be deleted)
3. `hosts_test.ini` - Test inventory (can be deleted)
4. `test_libssh_connection.yaml` - Test playbook (can be deleted)
5. `run_bootstrap.sh` - Bootstrap script (can be deleted)
6. `~/.ssh/id_ansible` - Test passphrase-less key (can be deleted)
7. `group_vars/workers_all_test.yml` - Test group_vars (can be deleted)

## Recommended Final Configuration

### Keep These Files:
- ✅ `ansible.cfg` - With libssh_connection settings (for future use)
- ✅ `hosts_bay.ini` - Updated with standard SSH config
- ✅ `vault_secrets.yml` - Encrypted vault with passphrases
- ✅ `ansible_with_agent.sh` - SSH agent automation script (to be created)
- ✅ All existing playbooks (test_ssh_only.yaml, etc.)

### Delete These Files:
- ❌ `bootstrap_libssh.yaml`
- ❌ `hosts_bay_bootstrap.ini`
- ❌ `hosts_test.ini`
- ❌ `test_libssh_connection.yaml`
- ❌ `run_bootstrap.sh`
- ❌ `~/.ssh/id_ansible` and `~/.ssh/id_ansible.pub`
- ❌ `group_vars/workers_all_test.yml`

## Security Considerations

### SSH Agent Approach Security:
1. **Passphrase in memory only** - Never written to disk
2. **Agent lifetime** - Keys removed when agent killed
3. **Source restriction** - Can restrict which hosts can use the key
4. **Audit trail** - All SSH connections logged on target hosts
5. **Single entry** - Enter passphrase once per session

### Vault Security:
1. **Double encryption** - Vault password protects become password
2. **Vault file encryption** - AES256 encryption
3. **Not in git** - vault_secrets.yml is .gitignored
4. **Vault password** - Stored in .vault_pass (600 permissions)

## Next Steps

1. Create `ansible_with_agent.sh` script
2. Update `hosts_bay.ini` to remove libssh-specific vars
3. Test all playbooks with SSH agent
4. Clean up test files
5. Update documentation

## Conclusion

Option 1 (libssh with ansible_private_key_passphrase) is **not viable** due to:
- Vault variable timing issues
- LibSSH compatibility problems
- Complex variable interpolation requirements

**SSH Agent automation (Option 3)** is the recommended solution:
- ✅ Reliable across all hosts
- ✅ Secure (passphrase in memory only)
- ✅ Works with any SSH connection type
- ✅ Simple to implement
- ✅ Production-ready approach
