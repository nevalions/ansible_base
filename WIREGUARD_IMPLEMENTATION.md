# WireGuard Implementation Guide

Complete step-by-step configuration for deploying WireGuard VPN network.

## Table of Contents

- [Pre-Requisites](#pre-requisites)
- [Step 1: Configure Vault Variables](#step-1-configure-vault-variables)
- [Step 2: Verify Inventory Configuration](#step-2-verify-inventory-configuration)
- [Step 3: Configure NAT Port Forwarding](#step-3-configure-nat-port-forwarding)
- [Step 4: Run Syntax Check](#step-4-run-syntax-check)
- [Step 5: Deploy WireGuard Network](#step-5-deploy-wireguard-network)
- [Step 6: Verify Deployment](#step-6-verify-deployment)
- [Step 7: Persist Keys to Vault](#step-7-persist-keys-to-vault)
- [Step 8: Deploy DNS Server](#step-8-deploy-dns-server)
- [Step 9: Monitor and Verify](#step-9-monitor-and-verify)
- [Step 10: Troubleshooting](#step-10-troubleshooting)
- [Step 11: Key Rotation](#step-11-key-rotation)
- [Summary Checklist](#summary-checklist)

---

## Pre-Requisites

Before starting, ensure you have:

- Ansible 2.16+ installed
- Access to `vault_secrets.yml` (encrypted vault password file)
- SSH access to all hosts in your inventory
- Root/sudo access on all target hosts
 - Network connectivity to your NAT router for port forwarding configuration

### Verify Prerequisites

```bash
# Check Ansible version
ansible --version

# Check vault access
ansible-vault view vault_secrets.yml | head -5

# Check SSH access to inventory hosts
ansible -i hosts_bay.ini all -m ping
```

---

## Step 1: Configure Vault Variables

### 1.1 Edit Vault Secrets File

```bash
ansible-vault edit vault_secrets.yml
```

### 1.2 Add WireGuard Configuration

Add/update these variables in `vault_secrets.yml`:

 ```yaml
 # WireGuard Network Configuration
 vault_wg_interface: "[interface-name]"                # e.g., wg99
 vault_wg_network_cidr: "[vpn-network-cidr]"          # Your VPN network CIDR
 vault_wg_server_ip: "[vpn-server-ip]"                # Server's VPN IP
 vault_wg_server_port: "[server-port]"                # WireGuard server port
 vault_wg_client_default_port: "[client-default-port]"  # Default client port
 vault_wg_client_port_start: "[port-range-start]"       # NAT port range start
 vault_wg_client_port_end: "[port-range-end]"          # NAT port range end
 vault_wg_dns_primary: "[dns-server-ip]"               # DNS server for VPN
 
 # WireGuard Server Keys (deprecated - use peer keys instead)
  vault_wg_server_private_key: null
  vault_wg_server_public_key: null
 
 # WireGuard Peers Configuration
 vault_wg_peers:
   # Control plane (direct access)
   - name: "[peer-1-name]"
     host_group: "[peer-1-host-group]"
     allowed_ips: "[peer-1-vpn-ip]/32"
     endpoint: "[peer-1-public-ip]:[port]"
   
   # Worker 1 behind NAT
   - name: "[peer-2-name]"
     host_group: "[peer-2-host-group]"
     allowed_ips: "[peer-2-vpn-ip]/32"
     endpoint: "[nat-public-ip]:[unique-port]"
     client_listen_port: "[unique-port]"
   
   # Worker 2 behind NAT
   - name: "[peer-3-name]"
     host_group: "[peer-3-host-group]"
     allowed_ips: "[peer-3-vpn-ip]/32"
     endpoint: "[nat-public-ip]:[unique-port]"
     client_listen_port: "[unique-port]"
   
   # Remote worker (direct access)
   - name: "[peer-4-name]"
     host_group: "[peer-4-host-group]"
     allowed_ips: "[peer-4-vpn-ip]/32"
     endpoint: "[peer-4-public-ip]:[port]"
   
   # Additional worker (direct access)
   - name: "[peer-5-name]"
     host_group: "[peer-5-host-group]"
     allowed_ips: "[peer-5-vpn-ip]/32"
     endpoint: "[peer-5-public-ip]:[port]"
 
 # Auto-generated peer keys (leave empty for first deployment)
 vault_wg_peer_private_keys:
   [peer-1-name]: null
   [peer-2-name]: null
   [peer-3-name]: null
   [peer-4-name]: null
   [peer-5-name]: null
 
 vault_wg_peer_public_keys:
   [peer-1-name]: null
   [peer-2-name]: null
   [peer-3-name]: null
   [peer-4-name]: null
   [peer-5-name]: null
 
 # WireGuard Firewall Configuration
 vault_wg_allowed_networks:
   - "[local-network-cidr]"   # Local network
   - "[vpn-network-cidr]"      # VPN network
   - "[[network-cidr]]" # Remote network 1
   - "[[network-cidr]]" # Remote network 2
   - "[[network-cidr]]" # Remote network 3
   - "127.0.0.0/8"           # Localhost

 # Routed CIDRs for K8s + service access over WG
 # (auto-consumed by wireguard_manage.yaml)
 vault_k8s_api_vip: "[k8s-api-vip]"
 vault_metallb_pool_cidr: "[metallb-subnet-cidr]"
 vault_db_wg_route_cidr: "[db-wg-ip]/32"
  ```

### 1.3 Save and Verify

```bash
# Verify vault variables are set
ansible-vault view vault_secrets.yml | grep vault_wg

# Check specific variables
ansible-vault view vault_secrets.yml | grep -A 5 vault_wg_interface
```

---

## Step 2: Verify Inventory Configuration

### 2.1 Check Inventory Groups

Your `hosts_bay.ini` already includes:

 ```ini
 [wireguard_servers:children]
 [server-group-1]    # [server-1-ip] - WireGuard server
 [server-group-2]    # [server-2-ip] - WireGuard server (backup)
 
 [wireguard_clients:children]
 [clients-group-all]
 [client-group-1]
 [client-group-2]
 ```

### 2.2 Verify Hosts are Reachable

```bash
# Test connectivity to WireGuard servers
ansible -i hosts_bay.ini wireguard_servers -m ping

# Test connectivity to WireGuard clients
ansible -i hosts_bay.ini wireguard_clients -m ping

# Test connectivity to all hosts
ansible -i hosts_bay.ini all -m ping
```

 Expected output:
 ```
 [server-1-ip] | SUCCESS => {
     "changed": false,
     "ping": "pong"
 }
 [server-2-ip] | SUCCESS => {
     "changed": false,
     "ping": "pong"
 }
 ```

---

## Step 3: Configure NAT Port Forwarding

**CRITICAL STEP** - This must be completed before deploying WireGuard for peers behind NAT.

 ### 3.1 Access NAT Router

 SSH or web interface to `[nat-router-ip]`

 ```bash
 ssh user@[nat-router-ip]
 ```

 ### 3.2 Configure Port Forwarding Rules

 Add the following port forwarding rules on your NAT router:

 ```
 NAT Router: [nat-router-ip]

 Rule 1: [peer-2-name]
   External Port: [unique-port-1] (UDP)
   Internal IP: [peer-2-internal-ip]
   Internal Port: [unique-port-1]
   Description: WireGuard for [peer-2-name]

 Rule 2: [peer-3-name]
   External Port: [unique-port-2] (UDP)
   Internal IP: [peer-3-internal-ip]
   Internal Port: [unique-port-2]
   Description: WireGuard for [peer-3-name]

 Rule 3: [peer-1-name] (if behind NAT)
   External Port: [server-port] (UDP)
   Internal IP: [peer-1-internal-ip]
   Internal Port: [server-port]
   Description: WireGuard for [peer-1-name]
 ```

 ### 3.3 Verify Port Forwarding

 ```bash
 # From external host, test port connectivity
 nc -zuv [nat-router-ip] [unique-port-1]
 nc -zuv [nat-router-ip] [unique-port-2]
 nc -zuv [nat-router-ip] [server-port]
 ```

 Expected output (if ports are open):
 ```
 Connection to [nat-router-ip] [unique-port-1] port [udp/*] succeeded!
 ```

 ### 3.4 Test Internal Port Accessibility

 ```bash
 # From internal network, test ports directly
 nc -zuv [peer-2-internal-ip] [unique-port-1]
 nc -zuv [peer-3-internal-ip] [unique-port-2]
 ```

---

## Step 4: Run Syntax Check

### 4.1 Check Playbook Syntax

```bash
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --syntax-check
```

Expected output:
```
playbook: wireguard_manage.yaml
```

### 4.2 Run Check Mode (Dry Run)

```bash
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --check -v
```

This shows what would happen without making changes.

 Expected output summary:
 ```
 TASK [Display WireGuard management start] *************
 ok: [server-1-ip] => {
     "msg": [
         "=== WireGuard [interface-name] Management ===",
         "Interface: [interface-name]",
         "Server port: [server-port]",
         "Network: [vpn-network-cidr]",
         "Server IP: [vpn-server-ip]",
         "Peers: [peer-count]",
         "Operation: install"
     ]
 }
 ```

---

## Step 5: Deploy WireGuard Network

### 5.1 Deploy to WireGuard Servers

```bash
# First deployment - generates keys
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard -v
```

### 5.2 What Happens During Deployment

The playbook will:

1. **Install WireGuard packages** on `wireguard_servers`
2. **Generate server keypair** (auto-generated if null in vault)
3. **Assign ports** to peers (auto-assigned from 51900 range if not specified)
4. **Generate peer keys** (auto-generated for each peer)
5. **Deploy server config** to `/etc/wireguard/wg99.conf`
6. **Deploy client configs** to all peers in `host_group`
7. **Configure firewall** (optional)
8. **Start WireGuard service** on all hosts
9. **Backup existing configs** (if any) to `/etc/wireguard/backups/`

### 5.3 Monitor Key Generation

Watch for key generation output:

 ```
 TASK [Display generated keys summary]
 ok: [server-1-ip] =>
   msg:
   - "Server private key: [truncated-key]..."
   - "Server public key: [truncated-key]..."
   - "Peers configured: [peer-count]"
 ```

**IMPORTANT**: Copy these keys! You'll need them for Step 7.

### 5.4 Wait for Deployment Completion

The playbook runs in `serial: 1` mode (one host at a time). Monitor progress:

 ```
 PLAY RECAP *********************************************************************
 [server-1-ip] : ok=25   changed=15   unreachable=0    failed=0    skipped=2
 [server-2-ip]  : ok=25   changed=15   unreachable=0    failed=0    skipped=2
 ```

### 5.5 Troubleshooting Deployment Issues

If deployment fails:

```bash
# Check Ansible verbose output
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard -vvv

# Check specific task failure
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard --step
```

---

## Step 6: Verify Deployment

### 6.1 Check WireGuard Status on Servers

```bash
ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show wg99"
```

Expected output:
 ```
 interface: [interface-name]
   public key: [public-key]
   private key: (hidden)
   listening port: [server-port]

 peer: [peer-2-public-key]
   endpoint: [nat-router-ip]:[unique-port-1]
   allowed ips: [peer-2-vpn-ip]/32
   latest handshake: 5 seconds ago
   transfer: 2.5 KiB received, 1.2 KiB sent
   persistent keepalive: every 25 seconds

 peer: [peer-5-public-key]
   endpoint: [peer-5-public-ip]:[port]
   allowed ips: [peer-5-vpn-ip]/32
   latest handshake: 10 seconds ago
   transfer: 1.8 KiB received, 2.1 KiB sent
   persistent keepalive: every 25 seconds
 ```

### 6.2 Check WireGuard Status on Clients

```bash
ansible -i hosts_bay.ini wireguard_clients -m shell -a "wg show wg99"
```

Expected output:
 ```
 interface: [interface-name]
   public key: [client-public-key]
   private key: (hidden)
   listening port: [client-port]

 peer: [server-public-key]
   endpoint: [server-ip]:[server-port]
   allowed ips: [vpn-network-cidr]
   latest handshake: 3 seconds ago
   transfer: 1.2 KiB received, 2.5 KiB sent
   persistent keepalive: every 25 seconds
 ```

### 6.3 Check Interface Status

```bash
ansible -i hosts_bay.ini wireguard_servers -m shell -a "ip addr show wg99"
```

Expected output:
 ```
 14: [interface-name]: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420 qdisc noqueue state UNKNOWN group default qlen 1000
     link/none
     inet [vpn-server-ip]/24 scope global [interface-name]
        valid_lft forever preferred_lft forever
 ```

### 6.4 Test Connectivity

 ```bash
 # From server to client
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "ping -c 3 [peer-2-vpn-ip]"

 # From client to server
 ansible -i hosts_bay.ini [peer-2-internal-ip] -m shell -a "ping -c 3 [vpn-server-ip]"

 # From client to client
 ansible -i hosts_bay.ini [peer-2-internal-ip] -m shell -a "ping -c 3 [peer-3-vpn-ip]"
 ```

 Expected output:
 ```
 PING [peer-2-vpn-ip] ([peer-2-vpn-ip]) 56(84) bytes of data.
 64 bytes from [peer-2-vpn-ip]: icmp_seq=1 ttl=64 time=2.45 ms
 64 bytes from [peer-2-vpn-ip]: icmp_seq=2 ttl=64 time=2.38 ms
 64 bytes from [peer-2-vpn-ip]: icmp_seq=3 ttl=64 time=2.41 ms

 --- [peer-2-vpn-ip] ping statistics ---
 3 packets transmitted, 3 received, 0% packet loss
 ```

### 6.5 Check firewall status

 ```bash
 # Check WireGuard server port
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "ufw status | grep [server-port]"  # if UFW is in use

 # Check NAT port
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "ufw status | grep [unique-port]"

 # Check client port on clients
 ansible -i hosts_bay.ini wireguard_clients -m shell -a "ufw status | grep [client-port]"
 ```

 Expected output:
 ```
 [server-port]/udp                   ALLOW       [local-network-cidr]
 [unique-port]/udp                   ALLOW       [nat-router-ip]
 ```

### 6.6 Verify Service Status

```bash
ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl status wg-quick@wg99"
ansible -i hosts_bay.ini wireguard_clients -m shell -a "systemctl status wg-quick@wg99"
```

 Expected output:
 ```
 ● wg-quick@[interface-name].service - WireGuard via wg-quick(8) for [interface-name]
      Loaded: loaded (/etc/systemd/system/wg-quick@[interface-name].service; enabled; preset: enabled)
      Active: active (exited) since Mon [timestamp] UTC; 5min ago
 ```

---

## Step 7: Persist Keys to Vault

### 7.1 Copy Generated Keys

After first deployment, keys are displayed in output. Copy them to `vault_secrets.yml`:

```bash
ansible-vault edit vault_secrets.yml
```

  Update with generated keys:
  ```yaml
  vault_wg_peer_private_keys:
   [peer-1-name]: "[peer-1-private-key]"
   [peer-2-name]: "[peer-2-private-key]"
   [peer-3-name]: "[peer-3-private-key]"
   [peer-4-name]: "[peer-4-private-key]"
   [peer-5-name]: "[peer-5-private-key]"

 vault_wg_peer_public_keys:
   [peer-1-name]: "[peer-1-public-key]"
   [peer-2-name]: "[peer-2-public-key]"
   [peer-3-name]: "[peer-3-public-key]"
   [peer-4-name]: "[peer-4-public-key]"
   [peer-5-name]: "[peer-5-public-key]"
 ```

### 7.2 Verify Vault

```bash
# Verify peer private keys are saved
ansible-vault view vault_secrets.yml | grep -A 5 vault_wg_peer_private_keys

# Verify peer public keys are saved
ansible-vault view vault_secrets.yml | grep -A 5 vault_wg_peer_public_keys
```

### 7.3 Re-run Deployment

After saving keys to vault, re-run to verify:

```bash
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard --check
```

The playbook should now report "no changes" since keys are already present.

---

## Step 8: Deploy DNS Server

### 8.1 Deploy DNS After WireGuard

```bash
# Run DNS server deployment (after WireGuard is up)
ansible-playbook dns_server_manage.yaml -i hosts_dns.ini --tags dns
```

### 8.2 Update WireGuard Clients to Use VPN DNS

```bash
ansible-vault edit vault_secrets.yml
```

Update DNS variable:
 ```yaml
 vault_wg_dns_primary: "[vpn-dns-server-ip]"  # Use VPN DNS server
 ```

### 8.3 Redeploy WireGuard Clients

```bash
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --limit wireguard_clients --tags wireguard
```

### 8.4 Verify DNS Configuration

 ```bash
 # Check DNS setting on client
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "cat /etc/resolv.conf"

 # Test DNS query
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "nslookup [dns-zone] [vpn-dns-server-ip]"

 # Test VPN DNS resolution
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "ping -c 3 [server-hostname].[dns-zone]"
 ```

---

## Step 9: Monitor and Verify

### 9.1 Check Peer Handshakes

```bash
ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show wg99 peers"
```

 Expected output:
 ```
 [peer-2-public-key]  [nat-router-ip]:[unique-port-1]  [peer-2-vpn-ip]/32  (5 seconds ago)
 [peer-5-public-key]  [peer-5-public-ip]:[port]           [peer-5-vpn-ip]/32  (10 seconds ago)
 ```

### 9.2 Monitor Traffic

```bash
# Real-time traffic monitoring
ansible -i hosts_bay.ini wireguard_servers -m shell -a "watch -n 1 'wg show wg99 transfer'"

# Check specific peer transfer stats
ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show wg99 transfer"
```

 Expected output:
 ```
 [peer-2-public-key]  2.5 KiB  1.2 KiB
 [peer-5-public-key]  1.8 KiB  2.1 KiB
 ```

### 9.3 Check Logs

```bash
# Check WireGuard service logs
ansible -i hosts_bay.ini wireguard_servers -m shell -a "journalctl -u wg-quick@wg99 -n 50"

# Follow logs in real-time
ansible -i hosts_bay.ini wireguard_servers -m shell -a "journalctl -u wg-quick@wg99 -f"

# Check UFW logs (only if UFW is enabled)
ansible -i hosts_bay.ini wireguard_servers -m shell -a "grep wg99 /var/log/ufw.log | tail -20"

## Kubernetes Note: Avoid UFW on K8s Nodes

When using Kubernetes (Calico) over WireGuard:
- Prefer disabling UFW on Kubernetes nodes (control planes + workers).
- UFW defaults can drop forwarded pod traffic (`cali*` -> `wg99`) and break pod DNS/egress.
- This repository's Kubernetes role disables UFW on K8s nodes by default.
```

### 9.4 Verify Backup Files

```bash
# List backup files
ansible -i hosts_bay.ini wireguard_servers -m shell -a "ls -lt /etc/wireguard/backups/ | head -5"

# Check backup file content
ansible -i hosts_bay.ini wireguard_servers -m shell -a "cat /etc/wireguard/backups/wg99.conf.backup.YYYY-MM-DDTHH:MM:SS"
```

---

## Step 10: Troubleshooting

### 10.1 Common Issues

#### Issue: Routed CIDRs not added to AllowedIPs for `is_server: true` peers

**Symptoms:** configs deploy successfully, but `AllowedIPs` contains only the peer VPN /32s and is missing the routed CIDRs (VIPs / LoadBalancer pools). This typically shows up as application connectivity failures through the cluster network even though WireGuard handshakes are established.

**Root cause (historical):** the server-side port assignment step previously rebuilt `vault_wg_peers` and unintentionally dropped optional keys like `is_server`. Since routed CIDRs are appended only when `peer.is_server` is true, the template condition evaluated to false and the routed CIDRs were skipped.

**Resolution:** ensure your role version preserves the full peer dict when assigning ports (only adds `client_listen_port`), and that your peer entries in `vault_wg_peers` explicitly include `is_server: true` for nodes expected to route.

**Verification:**
```bash
# Re-render and inspect diff for server config
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --limit wireguard_servers --tags wireguard --diff

# After deploy, inspect AllowedIPs on the server
sudo grep -n "^AllowedIPs" /etc/wireguard/[interface-name].conf
```

#### Issue: Pods cannot reach DB over WireGuard

**Symptoms:** node-to-DB works, but pod-to-DB fails.

**Root cause candidates:**
- Pod egress not SNATed on Calico (`natOutgoing` disabled)
- Worker peers missing DB endpoint route (for example `[db-wg-ip]/32`)

**Fix flow:**
```bash
# 1) Verify Calico natOutgoing
kubectl get ippools.crd.projectcalico.org -o yaml

# 2) Verify worker route path to DB WG endpoint
ip route get [db-wg-ip]

# 3) Re-apply WireGuard after vault updates
ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --tags wireguard
```

#### Issue: Peers not connecting

 ```bash
 # Check if port is open
 nc -zuv [nat-router-ip] [unique-port-1]
 nc -zuv [client-1-ip] [unique-port-1]

 # Check UFW status
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "ufw status verbose"

 # Check WireGuard logs
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "journalctl -u wg-quick@[interface-name] -n 50"

 # Check if WireGuard process is running
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "ps aux | grep wg"
 ```

#### Issue: No handshake

 ```bash
 # Check peer endpoint is correct
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "wg show [interface-name] dump"

 # Verify NAT forwarding
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "netstat -ulnp | grep [unique-port-1]"

 # Check if firewall is blocking
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "iptables -L -n -v | grep [unique-port-1]"

 # Test direct connection
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "tcpdump -i any -n port [unique-port-1]"
 ```

#### Issue: DNS not resolving

 ```bash
 # Check DNS setting
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "cat /etc/resolv.conf"

 # Test DNS query
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "nslookup [dns-zone] [vpn-dns-server-ip]"

 # Check DNS server is reachable
 ansible -i hosts_bay.ini [client-1-ip] -m shell -a "ping -c 3 [vpn-dns-server-ip]"

 # Check DNS server logs
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "journalctl -u unbound -n 50"
 ```

#### Issue: WireGuard service fails to start

 ```bash
 # Check service status
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "systemctl status wg-quick@[interface-name]"

 # Check service logs
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "journalctl -xe"

 # Check config syntax
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "wg-quick up [interface-name]"

 # Check config file
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "cat /etc/wireguard/[interface-name].conf"
 ```

### 10.2 Rollback to Backup

 ```bash
 # Find latest backup
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "ls -lt /etc/wireguard/backups/ | head -1"

 # Restore backup
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "cp /etc/wireguard/backups/[interface-name].conf.backup.[timestamp] /etc/wireguard/[interface-name].conf"

 # Restart WireGuard
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "systemctl restart wg-quick@[interface-name]"

 # Verify status
 ansible -i hosts_bay.ini [server-1-ip] -m shell -a "wg show [interface-name]"
 ```

### 10.3 Re-deploy Specific Host

 ```bash
 # Re-deploy to specific server
 ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --limit [server-1-ip] --tags wireguard

 # Re-deploy to specific client
 ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --limit [client-1-ip] --tags wireguard

 # Re-deploy to specific group
 ansible-playbook -i hosts_bay.ini wireguard_manage.yaml --limit [clients-group-all] --tags wireguard
 ```

### 10.4 Reset WireGuard Configuration

 ```bash
 # Stop WireGuard
 ansible -i hosts_bay.ini all -m shell -a "systemctl stop wg-quick@[interface-name]"

 # Remove config
 ansible -i hosts_bay.ini all -m shell -a "rm /etc/wireguard/[interface-name].conf"

 # Remove interface
 ansible -i hosts_bay.ini all -m shell -a "ip link del [interface-name]"

 # Restart service (if needed)
 ansible -i hosts_bay.ini all -m shell -a "systemctl restart wg-quick@[interface-name]"
 ```

---

## Step 11: Key Rotation

### 11.1 Rotate All Keys

```bash
# Rotate all keys (server + peers)
ansible-playbook -i hosts_bay.ini wireguard_rotate_keys.yaml --tags wireguard,rotate
```

### 11.2 What Happens During Key Rotation

The playbook will:

1. Set all keys to null (forces regeneration)
2. Regenerate server keypair
3. Regenerate all peer keypairs
4. Re-deploy configs to all hosts
5. Restart WireGuard services
6. Display new keys

### 11.3 Update Vault with New Keys

After rotation, copy new keys to `vault_secrets.yml` (see Step 7).

### 11.4 Verify Rotation

 ```bash
 # Check new keys are in use
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name]"

 # Verify all peers reconnected
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name] peers"

 # Test connectivity
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "ping -c 3 [peer-2-vpn-ip]"
 ```

---

## Summary Checklist

### Pre-Deployment

- [ ] Ansible 2.16+ installed
- [ ] SSH access to all inventory hosts
- [ ] Root/sudo access on all target hosts
- [ ] Vault password file configured
- [ ] Vault variables configured (Step 1)
- [ ] Inventory groups verified (Step 2)
- [ ] NAT port forwarding configured (Step 3)
- [ ] Playbook syntax check passed (Step 4)

### Deployment

- [ ] Check mode passed (Step 4)
- [ ] WireGuard deployed successfully (Step 5)
- [ ] All peers connected (handshake within 60s) (Step 6)
- [ ] UFW rules active (Step 6)
- [ ] WireGuard service running on all hosts (Step 6)
- [ ] Keys persisted to vault (Step 7)

### Post-Deployment

- [ ] Connectivity verified (ping tests) (Step 6)
- [ ] DNS server deployed (optional) (Step 8)
- [ ] VPN DNS configured (optional) (Step 8)
- [ ] Monitoring verified (Step 9)
- [ ] Backup files confirmed (Step 9)

### Maintenance

- [ ] Key rotation procedure documented (Step 11)
- [ ] Troubleshooting steps documented (Step 10)
- [ ] Rollback procedure tested (Step 10)

---

## Appendix: Additional Resources

### Useful Commands

 ```bash
 # Show all WireGuard interfaces
 ansible -i hosts_bay.ini all -m shell -a "wg show"

 # Show detailed peer information
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name] dump"

 # Show latest handshakes
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name] latest-handshakes"

 # Show transfer statistics
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name] transfer"

 # Show persistent keepalive
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "wg show [interface-name] persistent-keepalive"

 # Restart WireGuard service
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl restart wg-quick@[interface-name]"

 # Stop WireGuard service
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl stop wg-quick@[interface-name]"

 # Start WireGuard service
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl start wg-quick@[interface-name]"

 # Enable WireGuard service on boot
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl enable wg-quick@[interface-name]"

 # Check WireGuard config file
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "cat /etc/wireguard/[interface-name].conf"

 # Check WireGuard service status
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl is-active wg-quick@[interface-name]"

 # Check WireGuard service enabled status
 ansible -i hosts_bay.ini wireguard_servers -m shell -a "systemctl is-enabled wg-quick@[interface-name]"
 ```

### Network Topology Diagram

 ```
                     Internet
                         |
                         v
                   [nat-router-ip] (NAT Router)
                   /       |       \
                  /        |        \
                 v         v         v
     [server-1-ip]   [client-1-ip]   [client-2-ip]
     (peer-1-name)    (peer-2-name)   (peer-3-name)
          |              |                |
          |              |                |
          v              v                v
     [interface-name] [interface-name] [interface-name]
       (Server)         (Client)          (Client)
        |              |                |
        |              |                |
        v              v                v
     [vpn-server-ip] [peer-2-vpn-ip] [peer-3-vpn-ip]
        |              |                |
        +--------------+----------------+
                       |
                       v
                  [vpn-network-cidr] VPN Network

 Additional Direct-Access Peers:
     [peer-4-public-ip] (peer-4-name) → [peer-4-vpn-ip] (Server)
     [peer-5-public-ip] (peer-5-name) → [peer-5-vpn-ip] (Client)
 ```

### Configuration File Locations

 ```
 Server: [server-1-ip]
   Config: /etc/wireguard/[interface-name].conf
   Backup: /etc/wireguard/backups/
   Service: wg-quick@[interface-name].service
   Log: journalctl -u wg-quick@[interface-name]

 Client: [client-1-ip]
   Config: /etc/wireguard/[interface-name].conf
   Backup: /etc/wireguard/backups/
   Service: wg-quick@[interface-name].service
   Log: journalctl -u wg-quick@[interface-name]

 Ansible Vault:
   File: vault_secrets.yml
   Variables:
     - vault_wg_interface
     - vault_wg_network_cidr
     - vault_wg_server_ip
     - vault_wg_server_port
     - vault_wg_client_default_port
     - vault_wg_client_port_start
     - vault_wg_client_port_end
     - vault_wg_dns_primary
      - vault_wg_peers
      - vault_wg_peer_private_keys
      - vault_wg_peer_public_keys
      - vault_wg_allowed_networks
 ```

### Contact and Support

For issues or questions:
- Check troubleshooting section (Step 10)
- Review role documentation: `roles/wireguard/README.md`
- Check Ansible logs: `ansible.log` (if enabled)
- Review system logs: `journalctl -xe`

---

**Last Updated:** 2025-01-30

**Version:** 1.0

**Compatible with:** Ansible 2.16+, WireGuard 1.0+, Debian/Ubuntu
