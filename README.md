# Ansible Configuration Repository

Automated system configuration using Ansible for deploying and managing infrastructure, including Docker, Kubernetes, NFS, and workstation setup.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Roles](#roles)
- [Playbooks](#playbooks)
- [Testing](#testing)
- [Contributing](#contributing)
- [Documentation](#documentation)

## Overview

This repository contains Ansible playbooks and roles for:
- Workstation setup (Zsh, dotfiles, common tools)
- Docker installation and configuration
- Kubernetes cluster deployment
- NFS server and client configuration
- System upgrades and maintenance
- HAProxy load balancer setup

## Project Structure

```
ansible/
├── AGENTS.md                    # Coding guidelines and conventions
├── hosts_bay.ini                # Main inventory (Bay cluster)
├── hosts_haproxy.ini            # HAProxy inventory
├── hosts_restream.ini           # Restream inventory
├── vars/
│   └── packages.yaml            # Package definitions by OS
├── common/
│   └── tasks/                  # Common validation tasks
├── playbooks/
│   └── disk/                   # Disk management playbooks
├── roles/
│   ├── common/                 # System package installation
│   ├── docker/                 # Docker installation
│   ├── dotfiles/               # Dotfiles management
│   ├── kuber/                  # Kubernetes setup
│   ├── nfs_client/             # NFS client configuration
│   ├── nfs_server/             # NFS server configuration
│   ├── setup/                  # Role orchestrator
│   ├── upgrade/                # System upgrade wrapper
│   ├── upgrade_deb/            # Debian-specific upgrade
│   └── zsh/                    # Zsh shell setup
└── tests/
    ├── integration/             # Integration tests
    ├── unit/                   # Unit tests
    └── README.md               # Testing documentation
```

## Quick Start

### Prerequisites
- Ansible 2.16+
- Target systems with SSH access
- Sudo privileges on target systems

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

3. Configure inventory for your environment:
```bash
cp hosts_bay.ini hosts.ini
# Edit hosts.ini with your target hosts
```

4. Run a playbook:
```bash
ansible-playbook -i hosts.ini workstation.yaml
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
Sets up Kubernetes cluster components.

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
    clients: ["[internal-ip]/24"]
    options: "rw,sync,no_subtree_check"
```

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e add_nfs_server_exports_path=/export/data \
  -e add_nfs_server_exports="[internal-ip]/24"
```

### NFS Client
Configures NFS client mounts.

**Variables:**
- `nfs_mounts`: List of NFS mounts to configure
- `nfs_unmounts`: List of mounts to remove

**Usage:**
```bash
ansible-playbook -i hosts_bay.ini nfs_client_manage.yaml \
  -e add_nfs_server="[internal-ip]" \
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

## Playbooks

### Root Playbooks

| Playbook | Purpose | Hosts |
|----------|---------|-------|
| `workstation.yaml` | Full workstation setup | workers |
| `docker.yaml` | Install Docker only | workers |
| `kuber.yaml` | Setup Kubernetes cluster | workers |
| `haproxy.yaml` | Install HAProxy | haproxy |
| `common_install.yaml` | Setup common tools, zsh, dotfiles | workers |
| `nfs_server_manage.yaml` | Manage NFS exports | nfs_servers |
| `nfs_client_manage.yaml` | Manage NFS mounts | nfs_clients |
| `upgrade_deb.yaml` | Upgrade Debian packages | bay_cluster |
| `longhorn_remove_workers.yaml` | Remove Longhorn folders and data | workers_all |

### Subdirectory Playbooks

`playbooks/disk/create_config_mount_new_disk.yaml` - Disk partitioning and mounting

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

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes following conventions
4. Run test suite
5. Submit pull request with description

## Documentation

### Project Documentation
- [AGENTS.md](AGENTS.md) - Coding guidelines and conventions
- [tests/README.md](tests/README.md) - Testing documentation

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
worker1 ansible_host=[internal-ip]
worker2 ansible_host=[internal-ip]

[nfs_servers]
nfs1 ansible_host=[internal-ip]

[nfs_clients]
client1 ansible_host=[internal-ip]
```

**NFS Management Example:**
```bash
# Add NFS export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=install \
  -e add_nfs_server_exports_path=/export/share \
  -e add_nfs_server_exports="[internal-ip]/8"

# Remove NFS export
ansible-playbook -i hosts_bay.ini nfs_server_manage.yaml \
  -e nfs_operation=remove \
  -e remove_nfs_server_exports_path=/export/share \
  -e remove_nfs_server_exports="[internal-ip]/8"
```

## Troubleshooting

### Common Issues

**SSH connection failed:**
```bash
# Test SSH connection
ssh ansible_user@target_host

# Check inventory
ansible-inventory -i hosts_bay.ini --list
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