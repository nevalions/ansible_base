#!/bin/bash
# Stop SSH Agent and Remove Keys

echo "Removing all keys from SSH agent..."
ssh-add -D

echo ""
echo "Stopping SSH agent..."
eval "$(ssh-agent -k)"

echo "SSH agent stopped."
