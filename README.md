# Ansible Configuration Repository

## ⚠️ SECURITY WARNING - READ BEFORE EDITING

### 🚨 CRITICAL: NEVER COMMIT SENSITIVE DATA

**STRICTLY PROHIBITED in ALL files (docs, playbooks, examples):**

❌ **NEVER** include real usernames
❌ **NEVER** include real IP addresses (e.g., `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`)
❌ **NEVER** include real SSH ports (e.g., `22`, custom SSH ports)
❌ **NEVER** include real hostnames or domain names
❌ **NEVER** include real passwords or API keys
❌ **NEVER** include SSH private keys or certificates
❌ **NEVER** include network CIDRs or network identifiers

**✅ ALWAYS use placeholders instead:**
- Usernames: `[your-username]`
- IP addresses: `[internal-ip]`, `[server-ip]`, `[client-ip]`
- Ports: `[custom-ssh-port]`, `[server-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`
- Passwords: `[your-password-here]`
- API keys: `[your-api-key-here]`

**Example of CORRECT usage:**
```yaml
ansible_user: [your-username]
ansible_port: [custom-ssh-port]
ansible_host: [server-ip]
```

**❌ WRONG - Never use real data even in examples:**
```yaml
ansible_user: some-real-username
ansible_port: 12345
ansible_host: [example-ip]
```

**Violation of this policy will immediately fail code review.**

---

Automated system configuration using Ansible for deploying and managing infrastructure, including Docker, Kubernetes, NFS, and workstation setup.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Security](#security)
- [Quick Start](#quick-start)
- [Roles](#roles)
- [Playbooks](#playbooks)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Contributing](#contributing)
- [Documentation](#documentation)

## Overview

This repository contains Ansible playbooks and roles for:
- Workstation setup (Zsh, dotfiles, common tools)
- Docker installation and configuration
- Kubernetes cluster deployment
- NFS server and client configuration
- WireGuard VPN network management
- System upgrades and maintenance
- HAProxy load balancer setup

## Project Structure

```
ansible/
├── AGENTS.md                    # Coding guidelines and conventions
├── ansible.cfg                  # Project-wide Ansible configuration
├── .ansible-lint                # Linting rules and configuration
├── hosts_bay.ini                # Main inventory (Bay cluster)
├── hosts_haproxy.ini            # HAProxy inventory
├── hosts_restream.ini           # Restream inventory
 ├── KUBERNETES_SETUP.md         # Kubernetes setup guide
 ├── KUBERNETES_QUICKREF.md      # Kubernetes quick reference
 ├── SSH_AGENT_QUICKREF.md       # SSH agent usage guide
 ├── SSH_PASSPHRASE_IMPLEMENTATION.md  # SSH key passphrase implementation
 ├── ansible_with_agent.sh       # Automated SSH agent with preflight/postflight
 ├── ssh-agent-setup.sh          # SSH agent setup script (manual)
 ├── ssh-agent-stop.sh           # SSH agent stop script (manual)
 ├── vars/
│   └── packages.yaml            # Package definitions by OS
├── group_vars/                  # Group-specific variables (templates and local config)
│   ├── *.example.yml           # Example templates (committed to git)
│   ├── *.yml                  # Actual configuration (gitignored, created locally)
├── SECURITY.md                  # Security best practices and setup guide
├── common/
│   └── tasks/                  # Common validation tasks
├── playbooks/
│   └── disk/                   # Disk management playbooks
├── kuber.yaml                  # Kubernetes package installation
├── kuber_plane_init.yaml        # Control plane initialization
├── kuber_worker_join.yaml       # Worker node joining
├── kuber_verify.yaml            # Cluster health verification
├── kuber_plane_reset.yaml       # Control plane cleanup
├── kuber_worker_reset.yaml      # Worker node cleanup
├── wireguard_manage.yaml        # WireGuard VPN management
├── wireguard_rotate_keys.yaml   # WireGuard key rotation
├── roles/
│   ├── common/                 # System package installation
│   │   └── meta/              # Role metadata
│   ├── docker/                 # Docker installation
│   │   └── meta/              # Role metadata
│   ├── dotfiles/               # Dotfiles management
│   │   └── meta/              # Role metadata
│   ├── kuber/                  # Kubernetes package setup
│   │   ├── meta/              # Role metadata
│   │   └── templates/          # Configuration templates
│   ├── kuber_init/            # Control plane initialization
│   │   ├── tasks/             # Init, Calico install, verification
│   │   ├── handlers/          # Service handlers
│   │   ├── defaults/          # Variables (pod CIDR, service CIDR)
│   │   └── templates/         # kubeadm config template
│   ├── kuber_join/            # Worker node joining
│   │   ├── tasks/             # Token generation, join, verification
│   │   ├── defaults/          # Variables (control plane IP)
│   │   └── templates/         # kubeadm join config template
│   ├── kuber_verify/          # Cluster health verification
│   │   ├── tasks/             # Control plane, worker, network checks
│   │   └── defaults/          # Verification configuration
│   ├── kuber_reset/            # Kubernetes node cleanup (worker and control plane)
│   │   ├── handlers/           # Service management handlers
│   │   └── meta/              # Role metadata
│   ├── longhorn_clean/         # Longhorn storage cleanup
│   │   └── meta/              # Role metadata
│   ├── nfs_client/             # NFS client configuration
│   │   └── meta/              # Role metadata
│   ├── nfs_server/             # NFS server configuration
│   │   ├── meta/              # Role metadata
│   │   └── templates/          # Configuration templates
│   ├── setup/                  # Role orchestrator
│   │   └── meta/              # Role metadata
│   ├── upgrade/                # System upgrade wrapper
│   │   └── meta/              # Role metadata
│   ├── upgrade_deb/            # Debian-specific upgrade
│   │   └── meta/              # Role metadata
│   │   ├── wireguard/              # WireGuard VPN configuration
│   │   │   ├── tasks/             # WireGuard setup, key management, UFW
│   │   │   ├── handlers/          # Service restart handlers
│   │   │   ├── defaults/          # Network configuration variables
│   │   │   └── templates/         # WireGuard config templates
│   └── zsh/                    # Zsh shell setup
└── tests/
    ├── integration/             # Integration tests
    ├── unit/                   # Unit tests
    └── README.md               # Testing documentation
```

## Configuration

### ansible.cfg

The `ansible.cfg` file provides project-wide configuration:

- **Inventory**: Defaults to `./hosts_bay.ini`
- **Roles path**: Set to `./roles`
- **Fact caching**: Uses JSON file caching in `/tmp/ansible_facts`
- **Output format**: Uses YAML output for better readability
- **SSH pipelining**: Disabled to prevent connection issues with concurrent operations
- **Privilege escalation timeout**: 30s (increased for stability)
- **Gathering**: Smart gathering to optimize performance
- **Logging**: Logs to `./ansible.log`

### group_vars

**Security Note:** Actual group_vars files with connection details are excluded from git. Example files are provided as templates.

Variables are organized in `group_vars/` directory:
- `*.example.yml` - Example templates (committed to git)
- `*.yml` - Actual configuration files (gitignored, created locally)

Available templates:
- **bgp**: BGP node configuration
- **lb**: Load balancer configuration
- **planes**: Kubernetes control plane configuration
- **workers_super**: Super worker configuration
- **workers_vas**: VAS worker configuration
 - **remote_workers**: Remote worker configuration
 - **remote_planes**: Remote plane configuration
- **bay_cluster_all**: Common cluster variables

To use templates:
```bash
cd group_vars
cp <template-name>.example.yml <template-name>.yml
# Edit the file with your connection details
cd ..
```

Each file contains connection parameters (port, user, become method, Python interpreter).

### .ansible-lint

Code quality rules for Ansible:

- **Enabled rules**: FQCN enforcement, naming conventions, YAML validation
- **Excluded paths**: `.git/`, `tests/`, `.cache/`
- **Profile**: Production-level strictness
- **Warn list**: Experimental rules, ignore-errors usage

Run linting:
```bash
ansible-lint
```

## Quick Start

### Prerequisites
- Ansible 2.16+
- Target systems with SSH access
- Sudo privileges on target systems
- SSH keys configured for target systems (use SSH agent for key-based authentication)

**Security Note:** This repository follows security best practices. Connection details are not stored in git. See [Security](#security) section for details.

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ansible
```

2. Run tests to validate setup:
```bash
./run_tests.sh
```

3. Set up local configuration (required):
```bash
# Copy and customize group_vars templates
cd group_vars
cp bay_cluster_all.example.yml bay_cluster_all.yml
cp bgp.example.yml bgp.yml
cp lb.example.yml lb.yml
# ... copy and customize other example files as needed
cd ..
```

4. Configure inventory files for your environment (these files are gitignored):
```bash
# Create or edit inventory files based on your infrastructure
# Example: Edit hosts_bay.ini with your target hosts and connection details
```

5. Configure SSH agent for key-based authentication (required):

**Option A: Automated (Recommended)**
```bash
./ansible_with_agent.sh playbook.yaml
```
Automatically manages SSH agent lifecycle (start, add key, cleanup).

**Option B: Manual**
```bash
./ssh-agent-setup.sh
./ssh-agent-stop.sh
```
See [SSH_PASSPHRASE_IMPLEMENTATION.md](SSH_PASSPHRASE_IMPLEMENTATION.md) for complete implementation details.
See [SSH_AGENT_QUICKREF.md](SSH_AGENT_QUICKREF.md) for manual SSH agent commands.

6. Run a playbook:
```bash
ansible-playbook -i hosts_bay.ini workstation.yaml
```

## Security

### ⚠️ CRITICAL: NEVER COMMIT SENSITIVE DATA

**STRICTLY PROHIBITED in ALL files (docs, playbooks, examples):**

❌ **Real usernames** (use placeholders instead)
❌ **Real IP addresses** (e.g., `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`)
❌ **Real SSH ports** (e.g., `22`, custom SSH ports)
❌ **Real hostnames or domain names**
❌ **Real passwords** (e.g., `myPassword123`, `secret456`)
❌ **API keys/tokens** (e.g., `sk-1234567890abcdef`, `ghp_xxxxxxxxx`)
❌ **SSH private keys** (e.g., `-----BEGIN RSA PRIVATE KEY-----`)
❌ **Certificates** (e.g., `-----BEGIN CERTIFICATE-----`)
❌ **Network CIDRs** (e.g., `[network-cidr]`)
❌ **Real domain names** (e.g., `mycompany.com`, `internal.domain.org`)

**✅ MANDATORY: Use placeholders ONLY:**
- Usernames: `[your-username]`, `[admin-username]`
- IPs: `[internal-ip]`, `[server-ip]`, `[client-ip]`, `[control-plane-ip]`
- Ports: `[custom-ssh-port]`, `[server-port]`, `[vpn-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`, `[node-hostname]`
- Passwords: `[your-password-here]`, `[sudo-password]`
- API keys: `[your-api-key-here]`
- Networks: `[network-cidr]`, `[vpn-network-cidr]`, `[client-network]`

**Correct usage examples:**
```yaml
# ✅ CORRECT - Uses placeholders
ansible_user: [your-username]
ansible_port: [custom-ssh-port]
ansible_host: [server-ip]
vault_become_pass: [your-password-here]
```

**❌ WRONG - Never use real data even in examples:**
```yaml
ansible_user: some-real-username
ansible_port: 12345
ansible_host: [example-ip]
```

**This repository follows security best practices to protect sensitive infrastructure information.**

### Security Architecture

**Connection Details:**
- Stored in inventory files (`hosts_*.ini`) - **not in git**
- Example templates provided in `group_vars/*.example.yml`
- Actual `group_vars/*.yml` files are gitignored
- Users create local configuration files based on templates

**SSH Key Management:**
- SSH key-based authentication with passphrases
- Passphrases cached in SSH agent (memory only)
- No passwords or API keys in repository
- Automated lifecycle management with preflight/postflight
- See [SSH_PASSPHRASE_IMPLEMENTATION.md](SSH_PASSPHRASE_IMPLEMENTATION.md) for implementation details
- See [SSH_AGENT_QUICKREF.md](SSH_AGENT_QUICKREF.md) for manual SSH agent commands

### Security Checklist

**Repository Security:**
- ✅ No connection details in git
- ✅ No passwords or API keys in repository
- ✅ Inventory files gitignored
- ✅ Group variables gitignored (templates provided)
- ✅ SSH keys not in repository
- ✅ SSH key passphrases not stored in files

**Before Using:**
- Create local `group_vars/*.yml` from templates
- Configure inventory files with your infrastructure
- Set up SSH agent with passphrase-protected keys (automated or manual)
- Add SSH public keys to target servers

**Automated SSH Agent (Recommended):**
```bash
./ansible_with_agent.sh playbook.yaml
```

### Required Setup

For complete security setup instructions, see [SECURITY.md](SECURITY.md).

**Quick Security Setup:**
```bash
# 1. Create local group_vars
cd group_vars
cp *.example.yml *.yml
# Edit each file with your connection details
cd ..

# 2. Configure inventory (not in git)
# Edit hosts_bay.ini, hosts_haproxy.ini, hosts_restream.ini with your servers

# 3. Start SSH agent
./ssh-agent-setup.sh

# 4. Run playbooks
ansible-playbook -i hosts_bay.ini upgrade_deb.yaml
```

## Roles

### Common
Installs common packages and tools across different operating systems.

**Variables:**
- `common_packages`: List of common packages to install
- `arch_packages`: Arch/Manjaro specific packages
- `debian_packages`: Debian/Ubuntu specific packages

**Usage:**
```yaml
- name: Install common packages
  hosts: all
  roles:
    - common
```

### Docker
Installs Docker and Docker Compose on Debian-based systems.

**Variables:**
- `install_docker`: Enable/disable Docker installation (default: true)

**Features:**
- Adds Docker repository and GPG key
- Installs Docker CE, CLI, and plugins
- Adds current user to Docker group
- Validates installation

**Usage:**
```bash
ansible-playbook -i hosts.ini docker.yaml
```

### Kuber
Sets up Kubernetes cluster components (packages only).

**Features:**
- Installs kubelet, kubeadm, kubectl
- Configures containerd with systemd cgroup driver
- Disables swap
- Configures kernel modules and networking
- Sets up UFW firewall rules for K8s
- Holds K8s packages at current version

**Usage:**
```bash
ansible-playbook -i hosts.ini kuber.yaml
```

**Automated Cluster Setup:**
Use these playbooks for full cluster automation:
- `kuber_plane_init.yaml` - Initialize control plane with Calico
- `kuber_worker_join.yaml` - Join workers to cluster
- `kuber_verify.yaml` - Verify cluster health

See [KUBERNETES_SETUP.md](KUBERNETES_SETUP.md) for complete setup guide.

### NFS Server
Configures NFS server with export management.

**Variables:**
- `skip_folder_check`: Skip folder existence checks (default: true)
- `nfs_exports`: List of NFS exports to configure
- `nfs_exports_to_remove`: List of exports to remove

**Structure:**
```yaml
nfs_exports:
  - path: /export/data
    clients: ["[client-network]/24"]
    options: "rw,sync,no_subtree_check"
```

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e add_nfs_server_exports_path=/export/data \
  -e add_nfs_server_exports="[client-network]/24"
```

### DNS Server
Configures Unbound DNS server for Kubernetes cluster with encrypted vault variables.

**Variables (from vault_secrets.yml):**
- `vault_dns_zone`: DNS zone name (e.g., "cluster.local")
- `vault_dns_servers`: List of DNS server IPs
- `vault_dns_records`: List of DNS records (type, name, ip)
- `vault_dns_allowed_networks`: Allowed networks for DNS queries (supports multiple networks)

**Structure:**
```yaml
vault_dns_records:
  - type: "A"
    name: "[node-hostname]"
    ip: "[node-ip]"
  - type: "A"
    name: "[service-hostname]"
    ip: "[service-ip]"
```

**Features:**
- Unbound DNS server installation and configuration
- DNS zone management with encrypted records
- High availability across multiple servers (serial: 1)
- Firewall rules for DNS (UDP/TCP 53) with UFW enablement
- SSH access preservation when enabling UFW (prevents lockout)
- Supports multiple networks for DNS queries (physical, VPN, cloud)
- Check mode support for safe dry-run testing
- Supports both node hostnames and Kubernetes services
- All IPs encrypted in Ansible Vault

**Usage:**
```bash
ansible-playbook -i hosts_dns.ini dns_server_manage.yaml
```

**Security:**
- All IPs, hostnames, and ports encrypted in `vault_secrets.yml`
- No hardcoded values in playbooks
- See `vault_secrets.example.yml` for template structure

### DNS Client
Configures DNS resolvers on client hosts with encrypted vault variables.

**Variables (from vault_secrets.yml):**
- `vault_dns_server_primary`: Primary DNS server IP
- `vault_dns_server_secondary`: Secondary DNS server IP (optional)
- `vault_dns_zone`: DNS search domain
- `vault_dns_client_options`: resolv.conf options (default: timeout:2, attempts:3, rotate)

**Features:**
- Stops and disables systemd-resolved (Debian/Ubuntu)
- Deploys custom `/etc/resolv.conf` with specified DNS servers
- Backs up original configuration before changes
- Tests DNS resolution on deployment
- Supports removal to restore default systemd-resolved configuration
- Check mode support for safe dry-run testing
- All IPs encrypted in Ansible Vault

**Usage:**
```bash
# Install DNS client configuration
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml

# Install on specific hosts
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml --limit dns_clients

# Remove DNS client configuration (restore systemd-resolved)
ansible-playbook -i hosts_bay.ini dns_client_manage.yaml -e dns_operation=remove
```

**Security:**
- All IPs, hostnames, and ports encrypted in `vault_secrets.yml`
- No hardcoded values in playbooks
- Original configuration backed up before changes
- See `vault_secrets.example.yml` for template structure

### DNS Verify
Comprehensive DNS infrastructure health verification for servers, clients, and WireGuard connectivity.

**Variables (from vault_secrets.yml):**
- `vault_dns_server_primary`: Primary DNS server IP
- `vault_dns_server_secondary`: Secondary DNS server IP
- `vault_dns_zone`: DNS search domain
- `vault_wg_interface`: WireGuard interface name
- `vault_wg_peers`: WireGuard peers configuration

**Verification Checks:**

**DNS Servers:**
- Unbound service status (running/stopped)
- Port 53 listening (UDP/TCP)
- Configuration validity with `unbound-checkconf`
- Local DNS resolution test

**DNS Clients:**
- systemd-resolved status (should be disabled)
- `/etc/resolv.conf` existence
- Ansible-managed configuration check
- DNS server configuration validation

**WireGuard:**
- Interface existence and status
- VPN IP assignment
- Connectivity to DNS servers via ping

**DNS Resolution Tests:**
- Internal DNS: Resolve `[dns-server-1].[search-domain]`, `[client-hostname].[search-domain]`
- External DNS: Resolve `google.com`, `example.com` via primary/secondary DNS servers

**Features:**
- Per-host health reporting with pass/fail/warning counts
- Overall cluster health summary
- Fail-fast on critical issues when `verify_fail_immediately: true`
- Serial execution (1 host at a time) for safe testing
- All sensitive IPs masked in output
- Check mode support

**Usage:**
```bash
# Verify DNS infrastructure (check mode)
ansible-playbook -i hosts_bay.ini dns_verify.yaml --check

# Verify DNS infrastructure (run actual tests)
ansible-playbook -i hosts_bay.ini dns_verify.yaml

# Verify specific hosts
ansible-playbook -i hosts_bay.ini dns_verify.yaml --limit dns_clients

# Verify only DNS servers
ansible-playbook -i hosts_bay.ini dns_verify.yaml --limit dns_servers
```

**Exit Codes:**
- `0`: All critical checks passed (cluster HEALTHY or DEGRADED)
- `1`: Critical failures detected when `verify_fail_immediately: true`

**Health Status:**
- **HEALTHY**: All critical checks passed, no warnings
- **DEGRADED**: All critical checks passed, warnings detected
- **CRITICAL**: One or more critical checks failed

**Security:**
- All IPs, hostnames, and ports encrypted in `vault_secrets.yml`
- No secrets logged or displayed
- All sensitive data masked using `sanitize_security` filter
- See `vault_secrets.example.yml` for template structure

### Full DNS Deployment

Wrapper playbook that runs DNS server deployment and verification in sequence.

**Usage:**
```bash
# Deploy DNS servers and verify infrastructure
ansible-playbook -i hosts_bay.ini dns_full_deployment.yaml
```

**Features:**
- Runs `dns_server_manage.yaml` followed by `dns_verify.yaml`
- Single command for complete DNS deployment workflow
- Proper Ansible import semantics ensures sequential execution

### NFS Client
Configures NFS client mounts.

**Variables:**
- `nfs_mounts`: List of NFS mounts to configure
- `nfs_unmounts`: List of mounts to remove

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini nfs_client_manage.yaml \
  -e add_nfs_server="[nfs-server-ip]" \
  -e add_nfs_clients_path="/export/data" \
  -e add_nfs_clients_mount_point="/mnt/data"
```

### Longhorn Clean
Removes Longhorn storage folders and data from workers.

**Variables:**
- `longhorn_data_path`: Longhorn data directory (default: `/var/lib/longhorn`)
- `kubelet_pods_path`: Kubelet pods directory (default: `/var/lib/kubelet/pods`)

**Features:**
- Removes `/var/lib/longhorn/` directory recursively
- Finds and removes Longhorn-related pod data from `/var/lib/kubelet/pods/`
- Verifies removal succeeded with assertions
- Supports check mode for dry-run testing

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini longhorn_remove_workers.yaml
```

### Longhorn Verify
Verifies Longhorn data has been completely removed from worker nodes.

**Variables:**
- `longhorn_data_path`: Longhorn data directory (default: `/var/lib/longhorn`)
- `kubelet_pods_path`: Kubelet pods directory (default: `/var/lib/kubelet/pods`)
- `longhorn_namespace`: Kubernetes namespace to check (default: `longhorn-system`)

**Features:**
- Verifies `/var/lib/longhorn/` directory does not exist
- Checks for Longhorn-related pod directories in `/var/lib/kubelet/pods/`
- Checks Kubernetes resources (namespace, CRDs, pods) on control plane
- Skips Kubernetes checks on worker nodes (kubectl not accessible)
- Generates verification summary report with pass/fail status
- Supports check mode for read-only verification

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini longhorn_verify_cleanup.yaml
```

### Zsh
Installs and configures Zsh shell with Oh My Zsh.

**Features:**
- Installs Oh My Zsh
- Sets up Powerlevel10k theme
- Configures plugins (zsh-autosuggestions, zsh-syntax-highlighting, etc.)

**Usage:**
```yaml
- name: Setup Zsh
  hosts: workstations
  roles:
    - zsh
```

### Dotfiles
Manages user dotfiles using GNU Stow.

**Features:**
- Clones dotfiles repository
- Applies dotfiles using stow
- Sets Zsh as default shell

**Usage:**
```yaml
- name: Install dotfiles
  hosts: workstations
  roles:
    - dotfiles
```

### Setup
Orchestrates multiple roles based on configuration flags.

**Variables:**
- `common`: Enable common packages installation
- `zsh`: Enable Zsh setup
- `dotfiles`: Enable dotfiles management
- `install_docker`: Enable Docker installation
- `kuber`: Enable Kubernetes setup
- `install_haproxy`: Enable HAProxy installation

**Usage:**
```bash
ansible-playbook -i hosts.ini common_install.yaml
```

### Upgrade
System upgrade role with automatic error recovery and diagnostics.

**Variables:**
- `upgrade_all_packages`: Enable all package upgrades (default: true)

**Features:**
- Cleans stale apt lock files automatically (0-byte lock cleanup)
- Validates disk space before upgrade (requires 500MB minimum)
- Refreshes expired GPG keys for third-party repositories (e.g., Caddy)
- Implements retry logic for transient network errors (3 retries, 10s delay)
- Provides detailed diagnostics on upgrade failures
- Reports package count changes and reboot requirements
- Displays final summary with total packages upgraded and hosts requiring reboot (IP addresses masked for security)

**Automatic Error Recovery:**
- Stale lock files from crashed processes
- Insufficient disk space detection
- Expired repository GPG key refresh
- Network connectivity issues with retry

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini upgrade_deb.yaml
```

**Run on specific hosts:**
```bash
ansible-playbook -i hosts_bay.ini upgrade_deb.yaml --limit [host-or-group-name]
```

## Playbooks

### Root Playbooks

| Playbook | Purpose | Hosts |
|----------|---------|-------|
| `workstation.yaml` | Full workstation setup | workers |
| `docker.yaml` | Install Docker only | workers |
| `kuber.yaml` | Setup Kubernetes packages | workers |
| `kuber_plane_init.yaml` | Initialize control plane with Calico | planes |
| `kuber_worker_join.yaml` | Join workers to cluster | workers_all |
| `kuber_verify.yaml` | Verify cluster health | planes |
| `kuber_plane_reset.yaml` | Reset control plane nodes | masters |
| `kuber_worker_reset.yaml` | Reset worker nodes | workers_all |
| `haproxy.yaml` | Install HAProxy | haproxy |
| `common_install.yaml` | Setup common tools, zsh, dotfiles | workers |
| `nfs_server_manage.yaml` | Manage NFS exports | nfs_servers |
| `nfs_client_manage.yaml` | Manage NFS mounts | nfs_clients |
| `dns_server_manage.yaml` | Manage Unbound DNS servers | dns_servers |
| `dns_client_manage.yaml` | Configure DNS clients | dns_clients |
| `dns_verify.yaml` | Verify DNS infrastructure health | wireguard_cluster |
| `dns_full_deployment.yaml` | Deploy and verify DNS servers and infrastructure | localhost |
| `upgrade_deb.yaml` | Upgrade Debian packages | bay_cluster |
| `longhorn_remove_workers.yaml` | Remove Longhorn folders and data | workers_all |
| `longhorn_verify_cleanup.yaml` | Verify Longhorn data cleanup | workers_all |
| `longhorn_master_cleanup.yaml` | Clean and verify Longhorn data (master playbook) | masters |
| `wireguard_manage.yaml` | Manage WireGuard VPN network | wireguard_servers |
| `wireguard_rotate_keys.yaml` | Rotate WireGuard keys | wireguard_servers |

### Subdirectory Playbooks

`playbooks/disk/create_config_mount_new_disk.yaml` - Disk partitioning and mounting

### Using Tags

All playbooks support tags for selective execution:

**Example usage:**
```bash
# Run only Docker-related tasks
ansible-playbook workstation.yaml --tags docker

# Run multiple specific tags
ansible-playbook workstation.yaml --tags "zsh,dotfiles"

# Skip specific tags
ansible-playbook workstation.yaml --skip-tags docker

# List all available tags
ansible-playbook workstation.yaml --list-tags
```

**Available tags by playbook:**
- **workstation.yaml**: `workstation`, `setup`, `zsh`, `dotfiles`, `docker`
- **docker.yaml**: `docker`, `containers`, `install`
- **kuber.yaml**: `kubernetes`, `k8s`, `install`, `cluster`
- **kuber_plane_init.yaml**: `kubernetes`, `k8s`, `init`, `plane`, `cni`
- **kuber_worker_join.yaml**: `kubernetes`, `k8s`, `join`, `worker`
- **kuber_verify.yaml**: `kubernetes`, `k8s`, `verify`, `test`
- **haproxy.yaml**: `loadbalancer`, `haproxy`, `install`
- **common_install.yaml**: `common`, `packages`, `tools`, `zsh`, `dotfiles`
- **nfs_server_manage.yaml**: `nfs`, `server`, `storage`, `manage`
- **nfs_client_manage.yaml**: `nfs`, `client`, `storage`, `manage`
- **upgrade_deb.yaml**: `upgrade`, `maintenance`, `debian`
- **longhorn_remove_workers.yaml**: `longhorn`, `storage`, `cleanup`, `remove`
- **longhorn_verify_cleanup.yaml**: `longhorn`, `verify`, `cleanup`
- **longhorn_master_cleanup.yaml**: `longhorn`, `cleanup`, `verify`
- **kuber_worker_reset.yaml**: `kubernetes`, `k8s`, `reset`, `cleanup`, `worker`
- **kuber_plane_reset.yaml**: `kubernetes`, `k8s`, `reset`, `cleanup`, `master`
- **wireguard_manage.yaml**: `wireguard`, `vpn`
- **wireguard_rotate_keys.yaml**: `wireguard`, `rotate`
- **dns_server_manage.yaml**: `dns`, `server`, `manage`
- **dns_client_manage.yaml**: `dns`, `client`, `manage`
- **dns_verify.yaml**: `dns`, `verify`, `test`
- **dns_full_deployment.yaml**: `dns`, `deploy`, `full`
- **playbooks/disk/create_config_mount_new_disk.yaml**: `disk`, `storage`, `partition`, `mount`

## Code Quality

### Running Linter

Use ansible-lint to check code quality:
```bash
ansible-lint
```

This will:
- Validate YAML syntax
- Check FQCN usage
- Enforce naming conventions
- Validate role structure
- Detect anti-patterns

### Auto-formatting

Install and run yamllint for YAML formatting:
```bash
pip install yamllint
yamllint .
```

### Code Quality Checklist

- [ ] All roles have `meta/main.yaml` with author and platform info
- [ ] All playbooks have descriptive tags
- [ ] All cluster operations use `serial` parameter
- [ ] All modules use Fully Qualified Collection Names (FQCN)
- [ ] All variables follow `lowercase_with_underscores` convention
- [ ] All playbooks pass ansible-lint checks
- [ ] All inventory variables are in `group_vars/`
- [ ] No connection details in group_vars templates (use inventory files instead)
- [ ] No passwords, API keys, or secrets in any YAML files
- [ ] SSH private keys not committed to repository
- [ ] Vault password files not committed to repository

### Rolling Updates

Cluster playbooks use rolling updates with `serial` parameter:

- **kuber.yaml**: `serial: 1` - One node at a time for cluster safety
- **longhorn_remove_workers.yaml**: `serial: "30%"` - 30% of workers at a time
- **longhorn_verify_cleanup.yaml**: `serial: 1` - One worker at a time
- **longhorn_master_cleanup.yaml**: `serial: "30%"` for cleanup, `1` for verify
- **kuber_worker_reset.yaml**: `serial: 1` - One worker at a time
- **kuber_plane_reset.yaml**: `serial: 1` - One control plane at a time
- **nfs_server_manage.yaml**: `serial: 1` - Single NFS server at a time
- **nfs_client_manage.yaml**: `serial: "50%"` - Half of clients at a time
- **upgrade_deb.yaml**: `serial: "30%"` - 30% of cluster at a time

## Testing

### Run All Tests
```bash
./run_tests.sh
```

### Test Categories

1. **Syntax Checks** - Validates all playbooks
2. **Role Structure** - Verifies all roles have tasks/defaults/handlers
3. **Unit Tests** - Validates variable definitions
4. **Convention Checks** - Naming conventions and FQCN usage
5. **YAML Validation** - Validates 61 YAML files

### Running Specific Tests

**Syntax check:**
```bash
ansible-playbook --syntax-check <playbook>.yaml
```

**Unit test:**
```bash
ansible-playbook tests/unit/test_docker_variables.yaml
```

**Integration test (check mode):**
```bash
ansible-playbook tests/integration/test_common.yaml --check
```

For detailed testing documentation, see [tests/README.md](tests/README.md).

## Contributing

### Code Style

All contributions must follow the guidelines in [AGENTS.md](AGENTS.md), including:
- Use `.yaml` extension (not `.yml`)
- Follow standard role structure
- Use FQCN for modules (e.g., `ansible.builtin.apt`)
- Variables must be lowercase_with_underscores
- Add handlers to all roles
- Include defaults in `defaults/main.yaml`

### Workflow

1. Run tests before committing:
   ```bash
   ./run_tests.sh
   ```

2. Ensure all playbooks pass syntax check:
   ```bash
   ansible-playbook --syntax-check *.yaml
   ```

3. Follow naming conventions:
   - Task names: Descriptive, action-oriented
   - Variables: lowercase_with_underscores
   - Playbooks: lowercase_with_underscores

4. Add tests for new features

5. Follow security practices:
   - Never commit connection details, passwords, or API keys
   - Use SSH keys with passphrases
   - Use inventory files for connection details (not group_vars)
   - See [SECURITY.md](SECURITY.md) for complete guidelines

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes following conventions
4. Run test suite
5. Submit pull request with description

## Documentation

### Project Documentation
- [AGENTS.md](AGENTS.md) - Coding guidelines and conventions
- [SECURITY.md](SECURITY.md) - Security best practices and setup guide
- [tests/README.md](tests/README.md) - Testing documentation
- [KUBERNETES_SETUP.md](KUBERNETES_SETUP.md) - Complete Kubernetes setup guide
- [KUBERNETES_QUICKREF.md](KUBERNETES_QUICKREF.md) - Kubernetes quick reference
- [SSH_AGENT_QUICKREF.md](SSH_AGENT_QUICKREF.md) - SSH agent usage guide

### Role Documentation
Each role includes:
- `defaults/main.yaml` - Default variables with comments
- `handlers/main.yaml` - Available handlers
- Task files - Descriptive task names

### Inventory Examples

**Main Inventory (hosts_bay.ini):**
```ini
[bay_cluster_all]
server1 ansible_port=22 ansible_user=[your-username]
server2 ansible_port=[custom-ssh-port] ansible_user=[your-username]

[workers_super]
worker1 ansible_host=[worker1-ip]
worker2 ansible_host=[worker2-ip]

[nfs_servers]
nfs1 ansible_host=[nfs1-ip]

[nfs_clients]
client1 ansible_host=[client1-ip]
```

**NFS Management Example:**
```bash
# Add NFS export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=install \
  -e add_nfs_server_exports_path=/export/share \
  -e add_nfs_server_exports="[client-network]"

# Remove NFS export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=remove \
  -e remove_nfs_server_exports_path=/export/share \
  -e remove_nfs_server_exports="[client-network]"
```

## Troubleshooting

### Common Issues

**SSH connection failed:**
```bash
# Test SSH connection
ssh ansible_user@target_host

# Check inventory
ansible-inventory -i hosts_bay.ini --list

# Start SSH agent if needed
./ssh-agent-setup.sh
```

**Could not open a connection to your authentication agent:**
```bash
# Start SSH agent
eval "$(ssh-agent -s)"

# Add SSH keys
ssh-add ~/.ssh/id_rsa
ssh-add ~/.ssh/id_ed25519
```

**Playbook hangs on package installation:**
```bash
# Run with verbosity
ansible-playbook -i hosts.ini playbook.yaml -vvv

# Check mode (dry-run)
ansible-playbook -i hosts.ini playbook.yaml --check
```

**Handler not triggered:**
```bash
# Force handlers to run
ansible-playbook -i hosts.ini playbook.yaml --force-handlers
```

## License

See LICENSE file for details.

## Support

For issues and questions:
- Check [AGENTS.md](AGENTS.md) for coding guidelines
- Review [tests/README.md](tests/README.md) for testing help
- Open an issue on the repository