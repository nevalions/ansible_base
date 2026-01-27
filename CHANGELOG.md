# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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