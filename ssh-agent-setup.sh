#!/bin/bash
# SSH Agent Setup Script for Ansible

echo "Starting SSH agent..."
eval "$(ssh-agent -s)"
echo "SSH agent started with PID: $SSH_AGENT_PID"

echo ""
echo "Adding SSH keys to agent..."
echo "You'll be prompted for passphrases (one per key)"

# Add id_rsa (prompts for passphrase)
echo ""
echo "--- Adding id_rsa key ---"
ssh-add ~/.ssh/id_rsa

# Add id_ed25519 (prompts for passphrase)
echo ""
echo "--- Adding id_ed25519 key ---"
ssh-add ~/.ssh/id_ed25519

echo ""
echo "Loaded keys:"
ssh-add -l

echo ""
echo "SSH agent ready! You can now run Ansible commands."
echo "To stop agent when done, run: ssh-add -D"
