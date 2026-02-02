#!/bin/bash
# Generate WireGuard keys and output in YAML format
# Reads peer names from vault_secrets.yml

set -e

VAULT_FILE="vault_secrets.yml"
TEMP_DECRYPTED=""

cleanup() {
  [ -n "$TEMP_DECRYPTED" ] && rm -f "$TEMP_DECRYPTED"
}
trap cleanup EXIT

decrypt_vault() {
  local vault_pass_script="${ANSIBLE_VAULT_PASSWORD_FILE:-./vault_password_client.sh}"

  if [ ! -f "$vault_pass_script" ]; then
    echo "Error: Vault password script not found: $vault_pass_script" >&2
    echo "" >&2
    echo "Ensure vault_password_client.sh exists and is executable:" >&2
    echo "  chmod +x vault_password_client.sh" >&2
    echo "" >&2
    echo "For GPG setup details, see SECURITY.md" >&2
    exit 1
  fi

  TEMP_DECRYPTED=$(mktemp)
  ansible-vault view "$VAULT_FILE" --vault-password-file "$vault_pass_script" > "$TEMP_DECRYPTED"
}

extract_peer_names() {
  python3 - "$TEMP_DECRYPTED" << 'PYTHON_SCRIPT'
import sys
import yaml

try:
    with open(sys.argv[1], 'r') as f:
        vault = yaml.safe_load(f)

    if vault and 'vault_wg_peers' in vault:
        peers = vault['vault_wg_peers']
        if peers:
            for peer in peers:
                if 'name' in peer and peer['name']:
                    print(peer['name'])
except Exception as e:
    print(f"Error parsing vault: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
}

generate_server_keys() {
  WG_SERVER_PRIVATE=$(wg genkey)
  WG_SERVER_PUBLIC=$(echo "$WG_SERVER_PRIVATE" | wg pubkey)

  echo "# WireGuard Keys - Add to vault_secrets.yml"
  echo "vault_wg_server_private_key: \"$WG_SERVER_PRIVATE\""
  echo "vault_wg_server_public_key: \"$WG_SERVER_PUBLIC\""
}

generate_peer_keys() {
  local peers
  peers=$(extract_peer_names)

  if [ -z "$peers" ]; then
    echo "" >&2
    echo "Warning: No peers found in vault_wg_peers" >&2
    echo "Skipping peer key generation" >&2
    return
  fi

  declare -A PEER_PRIVATE_KEYS

  echo ""
  echo "vault_wg_peer_private_keys:"
  for peer in $peers; do
    PRIVATE=$(wg genkey)
    echo "  $peer: \"$PRIVATE\""
    PEER_PRIVATE_KEYS[$peer]=$PRIVATE
  done

  echo ""
  echo "vault_wg_peer_public_keys:"
  for peer in $peers; do
    PRIVATE="${PEER_PRIVATE_KEYS[$peer]}"
    PUBLIC=$(echo "$PRIVATE" | wg pubkey)
    echo "  $peer: \"$PUBLIC\""
  done
}

decrypt_vault
generate_server_keys
generate_peer_keys
