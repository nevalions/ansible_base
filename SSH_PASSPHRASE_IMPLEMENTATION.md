# ✅ SSH Key Passphrase Implementation - Complete

## Implementation Summary

**Option 1 (libssh + ansible_private_key_passphrase) was attempted but failed** due to:
- Vault variable timing issues (vault loaded after connection established)
- LibSSH compatibility issues ("Inappropriate ioctl for device")
- Complex variable interpolation requirements

**Recommended solution: SSH Agent automation** - ✅ WORKING

## What Was Implemented

### 1. SSH Agent Automation Script
**File:** `ansible_with_agent.sh`

Features:
- Starts SSH agent automatically (preflight)
- Adds SSH key with passphrase
- Runs any Ansible playbook with vault support
- Handles errors gracefully
- Provides clear status messages
- **Automatic cleanup** - Kills SSH agent after playbook completes (postflight)

### 2. Inventory Configuration
**File:** `hosts_bay.ini`

Updated configuration:
- Standard SSH connection (ansible.builtin.ssh)
- SSH key authentication
- Vault-based sudo password
- Removed libssh-specific variables

### 3. Testing
All tests passed:
- ✅ SSH connection without sudo
- ✅ SSH connection with sudo (via vault)
- ✅ All 3 hosts ([worker-main-ip], [worker-office-ip], [worker-super-ip])
- ✅ Vault decryption working

## How to Use

### Running Playbooks

**Basic usage:**
```bash
./ansible_with_agent.sh playbook.yaml
```

**With options:**
```bash
./ansible_with_agent.sh playbook.yaml --tags docker
./ansible_with_agent.sh playbook.yaml -e "var=value"
```

**With limit:**
```bash
./ansible_with_agent.sh playbook.yaml --limit [worker-main-ip]
```

### What Happens

1. SSH agent starts automatically (preflight)
2. SSH key added with passphrase (entered once)
3. Vault password loaded from `.vault_pass`
4. Ansible playbook executes
5. SSH agent killed automatically (postflight)
6. All keys removed from memory

### Security Features

1. **Passphrase in memory only** - Never written to disk
2. **Vault-protected sudo password** - Double encryption
3. **SSH key authentication** - More secure than password auth
4. **Automatic agent cleanup** - Keys removed after playbook completes
5. **Audit trail** - All connections logged on target hosts

### Automatic Cleanup Behavior

The script includes automatic SSH agent cleanup that ensures:
- ✅ SSH agent starts before playbook execution (preflight)
- ✅ SSH key added with passphrase for the session
- ✅ SSH agent killed immediately after playbook finishes (postflight)
- ✅ All keys removed from memory automatically
- ✅ Clean state - No lingering SSH agents

**Example output:**
```bash
Starting SSH agent...
✅ SSH agent started (PID: 211552)
Adding SSH key (~/.ssh/id_rsa)...
✅ SSH key added successfully

Running Ansible playbook...
------------------------------------------
[PLAYBOOK OUTPUT]

Cleaning up SSH agent...
✅ SSH agent stopped and keys removed from memory
```

## Files Modified/Created

### ✅ Created
- `ansible_with_agent.sh` - SSH agent automation script
- `OPTION1_FINDINGS.md` - Detailed research findings

### ✅ Modified
- `hosts_bay.ini` - Removed libssh configuration
- `ansible.cfg` - Added libssh_connection section (for future use)

### ❌ Deleted (test files)
- `bootstrap_libssh.yaml`
- `hosts_bay_bootstrap.ini`
- `hosts_test.ini`
- `test_libssh_connection.yaml`
- `run_bootstrap.sh`
- `~/.ssh/id_ansible` and `~/.ssh/id_ansible.pub`
- `group_vars/workers_all_test.yml`

## Configuration Details

### SSH Key
- Path: `~/.ssh/id_rsa`
- Passphrase: [redacted] (managed via GPG-encrypted vault)
- Type: RSA 4096-bit

### Vault
- File: `vault_secrets.yml` (encrypted)
- Password file: `vault_password.gpg` (GPG-encrypted)
- Variables:
  - `vault_ssh_key_passphrase`: [redacted] (not used with SSH agent)
  - `vault_become_pass`: [redacted] (for sudo)

### Inventory Settings
```ini
[workers_all:vars]
ansible_connection=ansible.builtin.ssh
ansible_port=[custom-ssh-port]
ansible_user=[your-username]
ansible_become=true
ansible_become_method=sudo
ansible_private_key_file=~/.ssh/id_rsa
ansible_become_pass="{{ vault_become_pass }}"
ansible_python_interpreter=/usr/bin/python3
```

## Playbook Requirements

All playbooks must include:
```yaml
vars_files:
  - vault_secrets.yml
```

This ensures `ansible_become_pass` is available from vault.

## Advantages of This Approach

1. **Reliability** - Works consistently across all hosts
2. **Security** - Passphrase only in memory, auto-cleanup
3. **Simplicity** - Easy to use and understand
4. **Flexibility** - Works with any SSH connection type
5. **Production-ready** - Common practice in enterprise environments
6. **Automatic lifecycle** - Preflight/postflight management built-in

## Troubleshooting

### SSH agent issues
```bash
# Check if agent is running
ps aux | grep ssh-agent

# Kill agent
ssh-agent -k

# Check loaded keys
ssh-add -l
```

### Vault issues
```bash
# View vault contents
ansible-vault view vault_secrets.yml

# Edit vault
ansible-vault edit vault_secrets.yml

# Re-encrypt if needed
ansible-vault encrypt vault_secrets.yml
```

### Connection issues
```bash
# Test SSH connection manually
ssh -p [custom-ssh-port] [your-username]@<host>

# Check if key is in agent
ssh-add -l

# Add key to agent manually
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```

## Next Steps

### Optional Enhancements

1. **Systemd SSH Agent Service**
   - Auto-start agent on boot
   - Auto-load keys (requires password manager integration)

2. **Password Manager Integration**
   - Use `pass` or `keepass` for automated passphrase loading
   - Example:
     ```bash
     ssh-add ~/.ssh/id_rsa <<< "$(pass ansible/ssh-passphrase)"
     ```

3. **Timeout Configuration**
   - Add key lifetime limit
   - Auto-expire keys after N hours

4. **Agent Cleanup Script**
   - Scheduled cleanup of stale agents
   - Automatic key removal after playbook completion

## Documentation References

- Vault setup: `VAULT_SETUP.md`
- SSH agent quickref: `SSH_AGENT_QUICKREF.md`
- Security guidelines: `SECURITY.md`

## Support

If you encounter issues:
1. Check `ansible.log` for detailed errors
2. Review `OPTION1_FINDINGS.md` for known issues
3. Verify SSH agent is running with `ssh-add -l`
4. Test vault with `ansible-playbook test_vault_vars.yaml --vault-password-file .vault_pass`

## Automatic Cleanup - Default Behavior

**As of latest update**, `ansible_with_agent.sh` now includes automatic SSH agent cleanup:

### Lifecycle:
```
┌─────────────────────────────────────────────┐
│ 1. Start SSH agent (preflight)      │
│ 2. Add SSH key with passphrase      │
│ 3. Run Ansible playbook              │
│ 4. Kill SSH agent (postflight)       │
└─────────────────────────────────────────────┘
```

### Benefits:
- ✅ Keys only in memory during playbook execution
- ✅ Automatic cleanup prevents stale agents
- ✅ Clean state on playbook completion
- ✅ Enhanced security posture

### Tradeoff:
- Agent restarts for each playbook (negligible overhead)
- Not ideal for rapid consecutive testing (use manual agent in that case)

## Conclusion

The SSH agent automation approach provides a **secure, reliable, and production-ready** solution for using SSH keys with passphrase in Ansible automation.

✅ All requirements met
✅ All tests passing
✅ Automatic preflight/postflight implemented
✅ Ready for production use
