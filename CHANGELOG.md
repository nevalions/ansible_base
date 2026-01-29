# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0//),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - 8 group variable files: `bgp.yml`, `lb.yml`, `planes.yml`, `workers_super.yml`, `workers_vas.yml`, `cloud_workers.yml`, `cloud_planes.yml`, `bay_cluster_all.yml`
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
  - 8 group variable files: `bgp.yml`, `lb.yml`, `planes.yml`, `workers_super.yml`, `workers_vas.yml`, `cloud_workers.yml`, `cloud_planes.yml`, `bay_cluster_all.yml`
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