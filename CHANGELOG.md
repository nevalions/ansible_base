# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0//),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-02-14

### Added
- **keepalived Role**:
  - Auto-assign VRRP priority (150, 100, 50...) based on list position if not explicitly set
  - Priority auto-assignment supports both control planes and BGP routers
  - Simplifies multi-node HA configuration with minimal manual priority management

- **bgp_keepalived Role**:
  - Auto-assign VRRP priority for BGP routers based on position in `vault_bgp_routers` list
  - Reduced health check weight from -50 to -30 to ensure MASTER election works even when health checks fail on all routers
  - Priority gap (50) exceeds weight penalty, ensuring proper MASTER/BACKUP election

- **dns_client Role**:
  - systemd override for dnsmasq to start after WireGuard interface is up
  - Use `bind-dynamic` mode to tolerate interfaces/addresses appearing after service start
  - Automatic dnsmasq restart after WireGuard configuration changes with listen IP validation
  - Prevents dnsmasq from binding to non-existent WireGuard IPs during boot

- **wireguard Role**:
  - Interface address drift detection and automatic service restart when IP changes
  - Peer AllowedIPs deduplication logic to avoid duplicate routes in server/client templates
  - Smart routing of CIDRs: API VIP excluded from non-plane peers when marked as server
  - Improved configuration updates with `wg syncconf` for zero-downtime changes

- **wireguard_verify Role**:
  - Simplified connectivity tests using runtime routes from `wg show allowed-ips`
  - Removed complex server/client logic - now uses actual configured peers from WireGuard
  - More accurate testing based on live WireGuard state rather than inventory assumptions

### Changed
- **keepalived/bgp_keepalived**:
  - Priority field is now optional in `vault_k8s_control_planes` and `vault_bgp_routers`
  - Explicit priority values still supported for custom ordering
  - Better documentation of auto-assignment behavior in README files

- **wireguard**:
  - Detect when interface address changes and restart service instead of using syncconf
  - Preserve connections when address hasn't changed using `wg syncconf`
  - Improved peer configuration generation with deduplication across all peers

- **vault_secrets.example.yml**:
  - Updated control plane and BGP router examples to show priority as optional
  - Added comments explaining auto-assignment behavior

### Fixed
- **wireguard**:
  - Duplicate AllowedIPs entries when multiple server peers exist
  - Interface address changes not being applied until manual service restart
  - Peers getting routes for VIPs they shouldn't (API VIP filtering for non-planes)

- **dns_client**:
  - dnsmasq failing to start if WireGuard interface isn't ready during boot
  - Static binding (`bind-interfaces`) causing issues with dynamically appearing interfaces

- **wireguard_verify**:
  - Inaccurate connectivity testing based on inventory rather than actual WireGuard state
  - Complex server/client logic that didn't reflect real peer relationships

## [1.7.0] - 2026-02-09

### Added
- **haproxy_verify Role**:
  - Comprehensive HAProxy verification for Kubernetes API load balancing
  - Service status checks (active state, enabled state, PIDs)
  - Configuration validation (syntax, frontend port, backend servers)
  - Network verification (listening ports, firewall rules)
  - Backend connectivity tests (TCP connections, ping tests)
  - Non-failing design - continues even when checks fail
  - Support for custom timeouts and retry counts
  - Vault Variables:
  - `vault_haproxy_k8s_frontend_port`: HAProxy frontend port
  - `vault_k8s_control_planes`: List of control plane backends
  - `vault_wg_network_cidr`: WireGuard network CIDR for firewall checks
  - **Role Variables**:
  - `verify_timeout_seconds`: Timeout for checks (default: 30)
  - `verify_retry_count`: Retry count for checks (default: 3)
  - `verify_sleep_seconds`: Sleep between retries (default: 2)

- **Playbooks**:
  - `playbooks/haproxy_spb_k8s.yaml`: Configure HAProxy on [haproxy-hostname] for Kubernetes API
  - `playbooks/haproxy_start_and_verify.yaml`: Combined configuration and verification playbook
  - `playbooks/haproxy_verify.yaml`: Standalone HAProxy verification playbook

- **Unit Tests**:
  - `tests/unit/test_haproxy_verify_variables.yaml`: Validate haproxy_verify role variables

### Documentation
- **HAPROXY_K8S_IMPLEMENTATION.md**:
  - Complete HAProxy for Kubernetes API implementation summary
  - Architecture diagrams showing WireGuard network integration
  - Usage examples for start & verify playbooks
  - Verification report template
  - Troubleshooting guides
- **roles/haproxy_verify/README.md**:
  - Role requirements and variables documentation
  - Usage examples with tags
  - Detailed checks performed breakdown
  - Example output and troubleshooting section
- **roles/haproxy_k8s/README.md**:
  - Updated architecture section with multi-control plane VIP support
  - Enhanced usage examples

### Changed
- **vault_secrets.example.yml**:
  - Added HAProxy Kubernetes API variables structure
  - Enhanced vault variable documentation

### Security
- **Verification Script** (`scripts/verify_sensitive_data.py`):
  - Updated to allow standard K8s API port (6443) in hosts: field
  - Improved false positive handling for inventory group names
  - Better detection of real infrastructure identifiers

## [1.6.0] - 2026-02-03

### Added
- **kuber Role**:
  - Comprehensive pre-flight validation before Kubernetes installation
  - Docker detection and conflict prevention
  - Container runtime conflict detection (dockerd, cri-o, crictl)
  - Port availability checks for Kubernetes components
  - Existing CNI plugin detection
  - Running Kubernetes process detection
  - Kernel module availability validation
  - Swap status validation
  - **Vault Variables**:
  - `vault_k8s_preflight_skip_docker_check`: Skip Docker conflict check
  - `vault_k8s_preflight_skip_swap_check`: Skip swap status check
  - `vault_k8s_preflight_skip_port_check`: Skip port availability check
  - `vault_k8s_preflight_skip_cni_check`: Skip CNI plugin check
  - `vault_k8s_preflight_skip_container_runtime_check`: Skip container runtime check
  - `vault_k8s_preflight_skip_process_check`: Skip Kubernetes process check
  - `vault_k8s_preflight_fail_on_warnings`: Fail playbook on warnings (default: false)
  - **Role Variables** (roles/kuber/defaults/main.yaml):
  - `k8s_preflight_check_ports`: List of ports to check for conflicts
  - `k8s_preflight_conflicting_runtimes`: List of conflicting container runtimes
  - `k8s_preflight_cni_paths`: List of CNI directories to check
  - `k8s_preflight_k8s_processes`: List of Kubernetes processes to detect
- **Unit Tests**:
  - `tests/unit/test_kuber_variables.yaml`: Validate pre-flight validation variables

### Documentation
- **KUBERNETES_SETUP.md**:
  - Added pre-flight validation section to kuber.yaml documentation
  - Documented all pre-flight variables and their purposes
  - Added usage examples for skipping individual checks

## [1.3.0] - 2026-01-30

### Fixed
- **upgrade_deb Role**:
  - Added automatic cleanup of stale apt lock files (0-byte locks from crashed processes)
  - Implemented expired GPG key refresh for third-party repositories (e.g., Caddy)
  - Added disk space validation before upgrade (requires 500MB minimum)
  - Implemented retry logic for transient network errors (3 retries, 10s delay)
  - Added comprehensive error diagnostics on upgrade failures
  - Fixes "Failed to update apt cache: unknown reason" errors caused by stale locks or expired keys

### Changed
- **upgrade_deb Role**:
  - Wrapped apt operations in block/rescue for better error handling
  - Added pre-check tasks: lock file detection, disk space, GPG key refresh
  - Improved troubleshooting output with detailed diagnostic information

### Documentation
- **README.md**:
   - Added detailed Upgrade role section with features and usage
   - Documented automatic error recovery capabilities
   - Included specific examples for targeted upgrades

## [1.5.0] - 2026-02-02

### Added
- **keepalived Role**:
  - New role for managing Kubernetes API VIP with health checks
  - Configures iptables DNAT for VIP:[k8s-api-port] → plane:[haproxy-frontend-port]
  - Health checks for both HAProxy and Kubernetes API on control planes
  - Multi-plane support with automatic failover
  - **Vault Variables**:
  - `vault_keepalived_vip`: Virtual IP address ([vip-address])
  - `vault_keepalived_vip_cidr`: VIP CIDR (32)
  - `vault_keepalived_vip_interface`: Network interface (wg99)
  - `vault_keepalived_password`: VRRP authentication password
  - `vault_keepalived_router_id`: VRRP router ID
  - `vault_k8s_api_vip`: Kubernetes API VIP for workers
  - `vault_k8s_api_port`: Kubernetes API port ([k8s-api-port])
  - `vault_k8s_control_planes`: List of control planes with WireGuard IPs
- **Playbook**:
  - `keepalived_manage.yaml`: Deploy and manage keepalived on [haproxy-hostname]

### Changed
- **haproxy_k8s Role**:
  - Updated to support multi-plane configuration from vault
  - Changed backend hosts to use WireGuard IPs from `vault_k8s_control_planes`
  - Added firewall rules to allow WireGuard network access to HAProxy:[haproxy-frontend-port]
- **kuber_join Role**:
  - Changed to use VIP (`vault_k8s_api_vip`) instead of direct plane IP
  - Workers now connect to VIP:[k8s-api-port] for high availability
- **kuber_init Role**:
  - Changed control plane endpoint to use VIP:[k8s-api-port]
  - Workers join through VIP for consistent access
- **Inventory**:
  - Added `[keepalived_hosts]` group for [haproxy-hostname]
  - Added `[keepalived_vip_servers]` group for planes_all
- **haproxy_k8s.yaml Playbook**:
  - Changed hosts from `planes` to `planes_all` for consistency

### Fixed
- Port mismatch between worker join ([k8s-api-port]) and control plane endpoint ([haproxy-frontend-port])
- Resolved with iptables DNAT: VIP:[k8s-api-port] → plane:[haproxy-frontend-port]

### Documentation
- Updated `KUBERNETES_SETUP.md` with VIP architecture
- Updated `roles/haproxy_k8s/README.md` with multi-plane support
- Added detailed testing procedures for VIP failover

## [1.4.0] - 2026-02-02

### Fixed
- **Privilege Escalation**:
  - Disabled SSH pipelining in `ansible.cfg` to prevent timeout errors during concurrent host operations
  - Increased `become_timeout` to 30 seconds for improved stability with privilege escalation
  - Fixes "Timeout (12s) waiting for privilege escalation prompt" errors when running playbooks on multiple hosts
- **upgrade_deb Role**:
  - Fixed DNS connectivity check from placeholder `[dns-server]` to Google public DNS (8.8.8.8)
  - Added conditional check `when: caddy_repo.stat.exists` to Caddy GPG keyring verification task
  - Eliminates misleading "keyring not found" messages on hosts without Caddy repository

### Added
- **upgrade_deb Playbook**:
  - New final summary play that aggregates upgrade results across all hosts
  - Displays total packages upgraded across all hosts
  - Lists hosts requiring reboot with IP addresses masked (e.g., `192.***.***.22`)
  - Shows reboot reminder when hosts require reboot to complete upgrades
  - Includes `vars_files: - vault_secrets.yml` for AGENTS.md compliance

### Changed
- **Kubernetes Configuration**:
  - `roles/kuber_init/defaults/main.yaml`:
    - Replaced placeholder `[internal-ip]/16` with vault variable `{{ vault_k8s_pod_subnet | default('10.244.0.0/16') }}`
    - Replaced placeholder `[internal-ip]/16` with vault variable `{{ vault_k8s_service_subnet | default('10.96.0.0/12') }}`
    - Changed control plane endpoint to use `{{ vault_haproxy_k8s_frontend_port | default('[haproxy-frontend-port]') }}`
    - Uses Kubernetes standard pod and service network defaults when vault variables not defined
  - `roles/kuber/tasks/main.yaml`:
    - Added port `[haproxy-frontend-port]` to firewall rules (standard alternative Kubernetes API port)

- **Vault Configuration**:
  - `vault_secrets.example.yml`:
    - Added new Kubernetes configuration variables: `[pod-network-cidr]`, `[service-network-cidr]`
    - Added HAProxy Kubernetes API variables: `[haproxy-frontend-port]`, `[haproxy-backend-port]`, `[control-plane-ip]`
    - Provides template structure for custom Kubernetes network and HAProxy configuration

### Documentation
- **README.md**:
  - Updated ansible.cfg section to reflect SSH pipelining disabled (line 165)
  - Added privilege escalation timeout information (30s)
  - Enhanced Upgrade role features to include final summary capability
- **CHANGELOG.md**:
  - Added comprehensive entry for version 1.4.0

### Security
- **IP Address Masking**:
  - Final upgrade summary masks middle octets of IP addresses (e.g., `[server-ip]` → `[server-ip]`)
  - Prevents exposure of sensitive network information in logs and output
  - Uses regex pattern: `^(\\d+)\\.(\\d+)\\.(\\d+)\\.(\\d+)$` → `\1.***.***.\4`

## [1.2.0] - 2026-01-29

### Changed
- **Playbook Flexibility**:
  - `kuber_plane_reset.yaml` now loads `vault_secrets.yml` via `vars_files` for vault variable access
  - `longhorn_master_cleanup.yaml` now targets `masters` group instead of `workers_all`
  - This enables flexible `--limit` patterns (planes, workers_all, etc.) without playbook modifications
- **Documentation**:
  - Updated `README.md` to reflect `longhorn_master_cleanup.yaml` targeting `masters` group
  - Maintains consistency with `kuber_plane_reset.yaml` which also targets `masters`

## [1.1.0] - 2026-01-28

### Security
- **Security Hardening**:
  - Moved connection details (ansible_user, ansible_port, ansible_become) from `group_vars/` to inventory files (`hosts_*.ini`)
  - Connection details now stored in gitignored inventory files instead of tracked group_vars
  - Created `group_vars/*.example.yml` template files for local configuration
  - Added `group_vars/*.yml` to `.gitignore` to prevent committing sensitive connection details
- **Documentation**:
  - New `SECURITY.md` with comprehensive security best practices and setup guide
  - Updated `README.md` with Security section and security checklist
  - Added security requirements to code quality checklist

### Changed
- **Inventory Management**:
  - Connection parameters moved back to `:vars` sections in `hosts_bay.ini`, `hosts_haproxy.ini`, `hosts_restream.ini`
  - Actual `group_vars/*.yml` files removed from git tracking (kept locally)
  - Template files `group_vars/*.example.yml` added to git for user reference

### Improved
- Repository no longer exposes connection details in git history
- Infrastructure topology protected by gitignoring inventory files
- Better security posture while maintaining playbook usability

### Security Posture
- ✅ No connection details in git
- ✅ No passwords or API keys in repository
- ✅ Inventory files (*.ini) properly gitignored
- ✅ Group variables gitignored (templates provided)
- ✅ SSH keys and passphrases not in repository
- ✅ Comprehensive security documentation provided

## [1.0.0] - 2026-01-27

### Added
- **Configuration Management**:
  - `ansible.cfg` with project-wide defaults (inventory, roles_path, fact caching, logging)
  - `.ansible-lint` configuration for code quality checks
- **Role Metadata**:
  - `meta/main.yaml` for all 11 roles with galaxy_info, platforms, tags, and dependencies
- **Variable Organization**:
  - `group_vars/` directory structure for inventory variables
  - Group variable files for BGP routers, load balancers, control planes, and workers
- **Playbook Enhancements**:
  - `tags:` parameter to all 12 playbooks for selective execution
  - `gather_facts:` explicit declarations to all playbooks
  - `serial:` parameter for rolling updates in cluster playbooks
- **Role Completeness**:
  - Handlers added to `kuber_reset` role (restart kubelet, restart containerd, reload systemd)
  - Tasks updated to use handlers in `kuber_reset` role
- **Documentation**:
  - New Configuration section in README.md (ansible.cfg, group_vars, .ansible-lint)
  - New Tags usage section in README.md with examples
  - New Rolling Updates section in README.md
  - New Code Quality section in README.md with linting and checklist
  - Updated project structure in README.md to include meta/ and handlers/ directories
  - New Configuration Management section in AGENTS.md
  - New Playbook Best Practices section in AGENTS.md (tags, gather_facts, serial)
  - New Role Metadata section in AGENTS.md

### Changed
- **Inventory Cleanup**:
  - Removed all `:vars` sections from `hosts_bay.ini`
  - Variables now managed in `group_vars/` directory
- **Playbook Updates** (12 playbooks):
  - Added tags for selective execution
  - Added explicit `gather_facts: true/false` declarations
  - Added rolling update support with `serial` parameter where appropriate
  - **workstation.yaml**: tags (workstation, setup, zsh, dotfiles, docker), gather_facts: true
  - **docker.yaml**: tags (docker, containers, install), gather_facts: true
  - **kuber.yaml**: tags (kubernetes, k8s, install, cluster), gather_facts: true, serial: 1
  - **haproxy.yaml**: tags (loadbalancer, haproxy, install), gather_facts: false
  - **common_install.yaml**: tags (common, packages, tools, zsh, dotfiles), gather_facts: true
  - **nfs_server_manage.yaml**: tags (nfs, server, storage, manage), gather_facts: true, serial: 1
  - **nfs_client_manage.yaml**: tags (nfs, client, storage, manage), gather_facts: true, serial: "50%"
  - **upgrade_deb.yaml**: tags (upgrade, maintenance, debian), gather_facts: true, serial: "30%"
  - **longhorn_remove_workers.yaml**: tags (longhorn, storage, cleanup, remove), gather_facts: false, serial: "30%"
  - **kuber_worker_reset.yaml**: tags (kubernetes, k8s, reset, cleanup, worker), gather_facts: false, serial: 1
  - **kuber_plane_reset.yaml**: tags (kubernetes, k8s, reset, cleanup, master), gather_facts: false, serial: 1
  - **playbooks/disk/create_config_mount_new_disk.yaml**: tags (disk, storage, partition, mount), gather_facts: false
- **Role Tasks**:
  - `kuber_reset/tasks/main.yaml`: Updated stop services tasks to notify handlers

### Standardized
- All roles now include complete metadata in `meta/main.yaml`
- All playbooks use consistent tag naming conventions
- All inventory variables organized in `group_vars/` directory
- Consistent use of FQCN throughout codebase
- All cluster operations implement rolling updates with serial parameter

### Improved
- Better organization of inventory variables with `group_vars/`
- Selective playbook execution with tags
- Safer cluster operations with rolling updates
- Enhanced code quality with ansible-lint
- Better configuration management with ansible.cfg
- Comprehensive documentation updates
- All tests pass (54/54)
- All ansible-lint checks pass (0 failures, 0 warnings)

### Refactored
- Inventory variable management from inline `:vars` to `group_vars/` directory
- Playbook structure to include tags, gather_facts, and serial parameters
- kuber_reset role to use handlers for service management

## [Unreleased]

### Added
- **Configuration Management**:
  - `ansible.cfg` with project-wide defaults (inventory, roles_path, fact caching, logging)
  - `.ansible-lint` configuration for code quality checks
- **Role Metadata**:
  - `meta/main.yaml` for all 11 roles with author, description, platforms, tags, and dependencies
- **Variable Organization**:
  - `group_vars/` directory structure for inventory variables
  - Group variable files for BGP routers, load balancers, control planes, and workers
- **Playbook Enhancements**:
  - `tags:` parameter to all 12 playbooks for selective execution
  - `gather_facts:` explicit declarations to all playbooks
  - `serial:` parameter for rolling updates in cluster playbooks
- **Role Completeness**:
  - Handlers added to `kuber_reset` role (restart kubelet, restart containerd, reload systemd)
  - Tasks updated to use handlers in `kuber_reset` role
- **Documentation**:
  - New Configuration section in README.md (ansible.cfg, group_vars, .ansible-lint)
  - New Tags usage section in README.md with examples
  - New Rolling Updates section in README.md
  - New Code Quality section in README.md with linting and checklist
  - Updated project structure in README.md

### Changed
- **Inventory Cleanup**:
  - Removed all `:vars` sections from `hosts_bay.ini`
  - Variables now managed in `group_vars/` directory
- **Playbook Updates** (12 playbooks):
  - Added tags for selective execution
  - Added explicit `gather_facts: true/false` declarations
  - Added rolling update support with `serial` parameter where appropriate
  - **workstation.yaml**: tags (workstation, setup, zsh, dotfiles, docker), gather_facts: true
  - **docker.yaml**: tags (docker, containers, install), gather_facts: true
  - **kuber.yaml**: tags (kubernetes, k8s, install, cluster), gather_facts: true, serial: 1
  - **haproxy.yaml**: tags (loadbalancer, haproxy, install), gather_facts: false
  - **common_install.yaml**: tags (common, packages, tools, zsh, dotfiles), gather_facts: true
  - **nfs_server_manage.yaml**: tags (nfs, server, storage, manage), gather_facts: true, serial: 1
  - **nfs_client_manage.yaml**: tags (nfs, client, storage, manage), gather_facts: true, serial: "50%"
  - **upgrade_deb.yaml**: tags (upgrade, maintenance, debian), gather_facts: true, serial: "30%"
  - **longhorn_remove_workers.yaml**: tags (longhorn, storage, cleanup, remove), gather_facts: false, serial: "30%"
  - **kuber_worker_reset.yaml**: tags (kubernetes, k8s, reset, cleanup, worker), gather_facts: false, serial: 1
  - **kuber_plane_reset.yaml**: tags (kubernetes, k8s, reset, cleanup, master), gather_facts: false, serial: 1
  - **playbooks/disk/create_config_mount_new_disk.yaml**: tags (disk, storage, partition, mount), gather_facts: false
- **Role Tasks**:
  - `kuber_reset/tasks/main.yaml`: Updated stop services tasks to notify handlers

### Standardized
- All roles now include complete metadata in `meta/main.yaml`
- All playbooks use consistent tag naming conventions
- All inventory variables organized in `group_vars/` directory
- Consistent use of FQCN throughout codebase
- All cluster operations implement rolling updates with serial parameter

### Improved
- Better organization of inventory variables with `group_vars/`
- Selective playbook execution with tags
- Safer cluster operations with rolling updates
- Enhanced code quality with ansible-lint
- Better configuration management with ansible.cfg
- Comprehensive documentation updates

### Refactored
- Inventory variable management from inline `:vars` to `group_vars/` directory
- Playbook structure to include tags, gather_facts, and serial parameters
- kuber_reset role to use handlers for service management

## [Unreleased]

### Added
- Complete testing infrastructure with unit and integration tests
- Test automation script (`run_tests.sh`) with comprehensive validation
- Defaults/main.yaml to all roles (common, docker, zsh, dotfiles, kuber, setup, upgrade, upgrade_deb, nfs_client)
- Handlers to all roles (common, docker, zsh, dotfiles, kuber, setup, upgrade, upgrade_deb, nfs_client)
- Template for containerd configuration (kuber/templates/containerd-config.toml.j2)
- Role documentation (README.md for nfs_server, docker, kuber)
- Project documentation (main README.md)
- Testing documentation (tests/README.md)
- Validation tasks in roles (Docker installation verification)
- Improved error handling with `changed_when: false` on check commands

### Changed
- Fixed playbook name/description mismatches:
  - `common_install.yaml`: Updated from "Install HAProxy" to "Setup common tools, zsh and dotfiles"
  - `upgrade_deb.yaml`: Updated from "Install Docker" to "Upgrade Debian packages"
- Converted ALL_CAPS variables to lowercase in NFS playbooks (10 variables):
  - `nfs_server_manage.yaml`: `ADD_NFS_SERVER_EXPORTS_PATH`, `ADD_NFS_SERVER_EXPORTS`, `REMOVE_NFS_SERVER_EXPORTS_PATH`, `REMOVE_NFS_SERVER_EXPORTS`
  - `nfs_client_manage.yaml`: `ADD_NFS_SERVER`, `ADD_NFS_CLIENTS_PATH`, `ADD_NFS_CLIENTS_MOUNT_POINT`, `REMOVE_NFS_SERVER`, `REMOVE_NFS_CLIENTS_PATH`, `REMOVE_NFS_CLIENTS_MOUNT_POINT`
- Replaced shell commands with built-in modules:
  - Docker role: Now uses `apt_repository` instead of shell for repo addition
  - Kuber role: Now uses `apt_repository` and `get_url` instead of shell commands
- Fixed error message in `check_folders_mount_list.yaml`: Now references `.mount_point` instead of `.path`

### Standardized
- All roles now follow complete structure (tasks, defaults, handlers)
- Consistent FQCN usage throughout all modules
- Proper error handling patterns with `changed_when`, `failed_when`, `assert`
- Lowercase_with_underscores variable naming convention enforced
- Template usage for managed configuration files

### Improved
- Added comprehensive documentation with usage examples
- Created automated testing covering syntax, structure, conventions, and validation
- Enhanced role documentation with troubleshooting guides
- Improved test coverage from 0 to 43 tests (100% pass rate)
- Better code maintainability through standardized structure

### Refactored
- NFS server role: Uses template for exports configuration
- Kubernetes role: Template-based containerd configuration
- Common role: Added handlers for package management
- Docker role: Added service handlers and validation
- All roles: Complete defaults and handlers implementation

## [0.0.1] - Initial Release

### Added
- Initial project structure
- Core roles: common, docker, zsh, dotfiles, kuber, setup, upgrade, upgrade_deb, nfs_client, nfs_server
- Playbooks: workstation, docker, kuber, haproxy, common_install, nfs_server_manage, nfs_client_manage, upgrade_deb
- Common validation tasks in `common/tasks/`
- Package definitions in `vars/packages.yaml`
- Multiple inventory files (hosts_bay.ini, hosts_haproxy.ini, hosts_restream.ini)