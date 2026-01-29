#!/bin/bash
# Ansible automation script with SSH agent
# Usage: ./ansible_with_agent.sh <playbook> [ansible options]

set -e  # Exit on error

echo "=========================================="
echo "Ansible Automation with SSH Agent"
echo "=========================================="
echo ""

# Start SSH agent
echo "Starting SSH agent..."
eval "$(ssh-agent -s)"
echo "✅ SSH agent started (PID: $SSH_AGENT_PID)"
echo ""

# Add SSH key with passphrase
echo "Adding SSH key (~/.ssh/id_rsa)..."
PASSPHRASE=$(ansible-vault view vault_secrets.yml --vault-password-file .vault_pass 2>/dev/null | grep -E '^vault_ssh_key_passphrase:' | cut -d' ' -f2 | tr -d '" ')

ASKPASS_SCRIPT=$(mktemp)
echo "#!/bin/bash" > "$ASKPASS_SCRIPT"
echo "echo '$PASSPHRASE'" >> "$ASKPASS_SCRIPT"
chmod +x "$ASKPASS_SCRIPT"

DISPLAY= SSH_ASKPASS_REQUIRE=force SSH_ASKPASS="$ASKPASS_SCRIPT" ssh-add ~/.ssh/id_rsa

rm -f "$ASKPASS_SCRIPT"

# Verify key added
if ssh-add -l > /dev/null 2>&1; then
    KEY_INFO=$(ssh-add -l)
    echo "✅ SSH key added successfully"
    echo "   $KEY_INFO"
else
    echo "❌ Failed to add SSH key"
    ssh-agent -k
    exit 1
fi

echo ""
echo "Running Ansible playbook..."
echo "------------------------------------------"

# Run Ansible playbook with all passed arguments
ansible-playbook "$@" --vault-password-file .vault_pass

PLAYBOOK_EXIT=$?

 echo ""
 echo "------------------------------------------"
 if [ $PLAYBOOK_EXIT -eq 0 ]; then
     echo "✅ Playbook completed successfully"
 else
     echo "⚠️  Playbook completed with exit code: $PLAYBOOK_EXIT"
 fi
 
 echo ""
 echo "Cleaning up SSH agent..."
 ssh-agent -k
 echo "✅ SSH agent stopped and keys removed from memory"
 
 exit $PLAYBOOK_EXIT
