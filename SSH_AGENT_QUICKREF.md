# SSH Agent Usage for Ansible

## Quick Start

### Start Working Session
```bash
cd /home/[your-username]/ansible
./ssh-agent-setup.sh
```
This will:
1. Start SSH agent
2. Prompt for passphrase for `~/.ssh/id_rsa`
3. Prompt for passphrase for `~/.ssh/id_ed25519`
4. List loaded keys

### Run Ansible Playbooks
```bash
# No password prompts - keys are in memory
ansible-playbook -i hosts_bay.ini kuber.yaml
ansible-playbook -i hosts_haproxy.ini haproxy.yaml
ansible-playbook -i hosts_restream.ini restream.yaml
```

### Stop Working Session
```bash
./ssh-agent-stop.sh
```

## Manual Commands

### Start Agent
```bash
eval "$(ssh-agent -s)"
```

### Add Keys
```bash
ssh-add ~/.ssh/id_rsa       # Prompts for passphrase
ssh-add ~/.ssh/id_ed25519   # Prompts for passphrase
```

### Verify Loaded Keys
```bash
ssh-add -l
```

### Remove Keys
```bash
ssh-add -D    # Remove all keys
ssh-add -d ~/.ssh/id_rsa  # Remove specific key
```

### Stop Agent
```bash
eval "$(ssh-agent -k)"
```

## Testing Connectivity

### Test Bay Cluster ([your-username] user)
```bash
ansible -i hosts_bay.ini planes -m ping
ansible -i hosts_bay.ini workers_all -m ping
```

### Test HAProxy Servers ([your-username] user)
```bash
ansible -i hosts_haproxy.ini haproxy_all -m ping
```

### Test Restream Servers (main/[your-username] users)
```bash
ansible -i hosts_restream.ini restream_all -m ping
```

## Security Notes

- ✅ Passphrases only entered once per session
- ✅ Decrypted keys stored in memory only
- ✅ No passwords in inventory files
- ✅ Works with your existing SSH key infrastructure

- ⚠️ Keys remain in memory until agent stopped or system reboot
- ⚠️ Remember to run `ssh-agent-stop.sh` when done
- ⚠️ Keep your SSH key passphrases secure

## Session Workflow Example

```bash
# 1. Start work
cd ~/ansible
./ssh-agent-setup.sh

# 2. Run playbooks (multiple times, no passwords)
ansible-playbook -i hosts_bay.ini kuber.yaml
ansible-playbook -i hosts_bay.yaml kuber_worker_join.yaml
ansible-playbook -i hosts_haproxy.ini haproxy.yaml

# 3. Stop when done
./ssh-agent-stop.sh
```

## Troubleshooting

### "Could not open a connection to your authentication agent"
- Agent not running: Run `eval "$(ssh-agent -s)"` first
- Agent stopped: Run the setup script again

### "Permission denied (publickey)"
- Keys not added to agent: Run `ssh-add ~/.ssh/id_rsa`
- Wrong key for server: Check `~/.ssh/config` for correct IdentityFile

### Host key verification prompt
- First time connecting to server: Type `yes` to accept
- Host key changed: Contact server admin immediately

### Keys not loading
- Wrong passphrase: Try again
- Key corrupted: Regenerate with `ssh-keygen -t ed25519`
