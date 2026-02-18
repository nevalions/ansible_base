# Mosquitto MQTT Broker Role

Manages Mosquitto MQTT broker running in a Docker container.

## Requirements

- Docker installed on target hosts
- `mqtt_servers` inventory group defined
- Vault variables configured in `vault_secrets.yml`

## Role Variables

### Required Vault Variables

```yaml
vault_mosquitto_port: "1883"
```

### Authentication (Optional)

When both user and password are set, authentication is enabled on the external listener:

```yaml
vault_mosquitto_user: "<username>"
vault_mosquitto_password: "<password>"  # minimum 12 characters
```

Note: An internal health-check listener on port 1884 (localhost only, no auth) is always configured.

### Optional Vault Variables

```yaml
vault_mosquitto_container_name: "mosquitto"
vault_mosquitto_image: "eclipse-mosquitto:2"
vault_mosquitto_ws_port: "9001"
vault_mosquitto_volume_name: "mosquitto_data"
vault_mosquitto_network_name: "mosquitto_net"
vault_mosquitto_bind_address: "0.0.0.0"
vault_mosquitto_config_path: "/etc/mosquitto"
vault_mosquitto_pids_limit: 64
vault_mosquitto_memory: "256m"
vault_mosquitto_manage_ufw: true
vault_mosquitto_allowed_networks:
  - 10.0.0.0/8
  - 192.168.0.0/16
vault_mosquitto_enable_websockets: false
vault_mosquitto_persistence_enabled: true
vault_mosquitto_max_connections: -1
vault_mosquitto_max_queued_messages: 1000
```

### Removal Variables

```yaml
vault_mosquitto_remove_config: false   # Remove /etc/mosquitto
vault_mosquitto_remove_volume: false   # Delete persistent data
vault_mosquitto_remove_network: false  # Remove Docker network
```

## Playbooks

| Playbook | Purpose |
|----------|---------|
| `mosquitto_docker_manage.yaml` | Install or manage (set `mosquitto_operation: install/remove`) |
| `mosquitto_docker_verify.yaml` | Verify MQTT connectivity via pub/sub test |
| `mosquitto_docker_remove.yaml` | Remove container and optionally volume/network |

## Usage

### Install

```bash
ansible-playbook -i inventory mosquitto_docker_manage.yaml
```

### Verify

```bash
ansible-playbook -i inventory mosquitto_docker_verify.yaml
```

### Remove

```bash
# Remove container only
ansible-playbook -i inventory mosquitto_docker_remove.yaml

# Remove container, volume, and network
ansible-playbook -i inventory mosquitto_docker_remove.yaml -e "vault_mosquitto_remove_volume=true vault_mosquitto_remove_network=true"
```

## Inventory Example

```ini
[mqtt_servers]
mqtt-host-1 ansible_host=[placeholder-ip]
mqtt-host-2 ansible_host=[placeholder-ip]
```

## License

MIT
