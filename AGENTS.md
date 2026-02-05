# OpenCode Worker Guide for Ansible Repository

This document explains what the OpenCode worker does in this repo and the Ansible best practices we follow. It is the authoritative workflow for edits, reviews, and automation.

## What is the OpenCode worker?

The OpenCode worker is an automated coding agent that:
- Reads and edits files in this repo using the same rules as human contributors.
- Applies Ansible best practices, security policies, and repository conventions.
- Avoids destructive operations and never commits secrets or sensitive data.
- Prefers small, safe changes with clear reasoning and documentation updates.

The OpenCode worker is not allowed to add real infrastructure data. It must use placeholders in all examples and docs.

---

## SECURITY WARNING - READ BEFORE EDITING

### CRITICAL: NEVER COMMIT SENSITIVE DATA

STRICTLY PROHIBITED in ALL files (docs, playbooks, examples):
- Real usernames
- Real IP addresses
- Real SSH ports
- Real hostnames or domain names (except inventory group names in `hosts:` field)
- Real passwords or API keys
- SSH private keys or certificates
- Network CIDRs or network identifiers

ALWAYS use placeholders instead:
- Usernames: `[your-username]`, `[admin-username]`
- IPs: `[internal-ip]`, `[server-ip]`, `[client-ip]`, `[control-plane-ip]`
- Ports: `[custom-ssh-port]`, `[server-port]`, `[vpn-port]`, `[k8s-api-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`, `[node-hostname]`
- Passwords: `[your-password-here]`, `[sudo-password]`
- API keys: `[your-api-key-here]`
- Networks: `[network-cidr]`, `[vpn-network-cidr]`, `[client-network]`

Violation of this policy will immediately fail code review.

---

## Build, Lint, and Test Commands

### Syntax Validation
```bash
# Validate a specific playbook
ansible-playbook --syntax-check <playbook>.yaml

# Validate a specific role
ansible-playbook --syntax-check <playbook>.yaml --tags <role_name>
```

### Linting
```bash
# Lint entire repository
ansible-lint

# Lint specific playbook
ansible-lint <playbook>.yaml

# Lint specific role directory
ansible-lint roles/<role_name>/
```

### YAML Formatting
```bash
# Check YAML syntax
yamllint .

# Format YAML files (if using yamlfmt)
yamlfmt .
```

### Running Playbooks
```bash
# Run playbook with dry-run (check mode)
ansible-playbook -i inventory <playbook>.yaml --check

# Run specific tags
ansible-playbook -i inventory <playbook>.yaml --tags <tag_name>

# Run with verbosity
ansible-playbook -i inventory <playbook>.yaml -v
```

---

## Code Style Guidelines

### File Extensions and Structure
- Use `.yaml` extension for all Ansible files (never `.yml`)
- Follow standard role structure:
  ```
  roles/<role_name>/
    tasks/main.yaml
    handlers/main.yaml
    defaults/main.yaml
    templates/<template>.j2
  ```
- Playbooks go in root directory or `playbooks/` subdirectory
- Common tasks in `common/tasks/`
- Variable definitions in `vars/` directory

### YAML Formatting
- Use 2-space indentation (never tabs)
- Separate task blocks with blank lines for readability
- Use `---` document start marker at beginning of files
- Wrap long lines at ~100 characters for readability

### Naming Conventions
- Task names: descriptive, action-oriented names in lowercase with underscores
  - Good: "install docker packages"
  - Good: "check if folder exists"
- Variables: lowercase with underscores
  - Good: `nfs_exports`, `skip_folder_check`, `docker_check`
- Handlers: lowercase describing the action
  - Good: `restart nfs`, `reload exports`
- Playbooks: lowercase with underscores, descriptive of purpose
  - Good: `nfs_server_manage.yaml`, `workstation.yaml`

### Module Usage
- Use FQCN (fully qualified collection name):
  ```yaml
  ansible.builtin.get_url:
  ansible.builtin.stat:
  ```
- Prefer built-in modules over `command`/`shell` when possible
- Use `package` module for cross-platform package installation
- Use `apt`/`pacman` for Debian/Arch-specific operations

### Error Handling
- Use `ignore_errors: yes` for pre-check or validation tasks
- Use `register` to capture command output
- Set `changed_when: false` for idempotent check commands
- Provide descriptive error messages in `fail` module
- Use `assert` for validation with `success_msg` and `fail_msg`

### Conditionals
- Use `when` clauses for conditional execution
- Use `ansible_facts['os_family']` for OS detection
- Use `ansible_os_family` for broader checks
- Support `skip_folder_check` pattern with defaults: `skip_folder_check | default(false)`

### Loops
- Use `loop` instead of `with_items` (Ansible 2.5+)
- Use `with_subelements` for nested iteration
- Use `| select()`, `| list()`, `| difference()` filters for data manipulation

### Task Organization
- Group related tasks with comments where it improves clarity
- Use `import_tasks` for static file inclusion
- Use `include_role` or `include_tasks` for dynamic inclusion
- Define handlers in `handlers/main.yaml` and notify with same name

### Templates
- Use `.j2` extension for Jinja2 templates
- Include delimiter comments for managed sections:
  ```jinja2
  # BEGIN ANSIBLE MANAGED SECTION
  # END ANSIBLE MANAGED SECTION
  ```
- Preserve custom sections that should not be overwritten
- Use `{% if custom_exports | length > 0 %}` for conditional sections

### Variable Management
- Define default variables in `roles/<role_name>/defaults/main.yaml`
- Load external vars with `vars_files:` in playbooks
- Load vault secrets with `vars_files: - vault_secrets.yml` in all playbooks that use become/sudo
- For playbooks in subdirectories, use relative path: `vars_files: - ../../vault_secrets.yml`
- Use variable interpolation: `{{ variable_name }}`
- Provide defaults with filters: `{{ item.mode | default('0777') }}`

### File Operations
- Use `stat` module for existence checks
- Use `file` module for creating directories with mode/owner/group
- Use `template` with `backup: yes` for managed configuration files
- Use `slurp` with `| b64decode` for reading file contents

### Service Management
- Use conditional service names based on OS:
  ```yaml
  name: "{{ 'nfs-kernel-server' if ansible_os_family == 'Debian' else 'nfs-server' }}"
  ```
- Use handlers for service restarts/reloads
- Use `when: exports_changed.changed` for conditional handler notification

### Validation and Assertions
- Use `assert` module for post-deployment validation
- Check command output with `grep` and register results
- Use `failed_when` and `changed_when` for custom status determination

### OS-Specific Logic
- Debian/Ubuntu: Use `apt`, `ufw`, `systemd`
- Arch/Manjaro: Use `pacman`
- Always condition OS-specific tasks with `when: ansible_facts['os_family'] == "<family>"`

---

## Configuration Management

### ansible.cfg
Always create an `ansible.cfg` file in project root with:
- `inventory` - Default inventory file path
- `roles_path` - Explicit roles directory
- `fact_caching` - Enable fact caching (jsonfile recommended)
- `fact_caching_connection` - Cache location (e.g., `/tmp/ansible_facts`)
- `stdout_callback` - Output format (yaml recommended)
- `gathering` - Fact gathering mode (smart recommended)
- `log_path` - Log file location
- SSH pipelining enabled for faster execution

### group_vars and host_vars
- Use `group_vars/` for group-level inventory variables (non-sensitive only)
- Use `host_vars/` for host-specific variables
- Security: store connection details (`ansible_user`, `ansible_port`, `ansible_become`) in inventory files `:vars` sections, not in `group_vars`
- Security: create `group_vars/*.example.yml` templates and keep actual `group_vars/*.yml` files gitignored
- Organize variables by function and purpose
- Use `.yml` extension for variable files
- Keep sensitive data separate (consider ansible-vault for passwords, API keys)
- See `SECURITY.md` for comprehensive security guidelines

### ansible-lint
Always configure `.ansible-lint` with:
- `profile: production` for production-level strictness
- `exclude_paths` to ignore cache, git, tests
- `enable_list` for specific rules (FQCN, naming conventions)
- `skip_list` for rules to ignore (line-length, jinja spacing)
- `warn_list` for rules to warn about (experimental, ignore-errors)

### SSH Configuration
- Use `~/.ssh/config` hosts for inventory entries
- Set `IdentityFile` to `ansible/ansible_id_ed25519` for SSH connections
- Ensure `ansible_id_ed25519` has correct permissions: `chmod 600 ansible/ansible_id_ed25519`
- Example SSH config entry:
  ```
  Host [server-hostname]
      HostName [server-ip]
      User [your-username]
      IdentityFile ~/.ssh/ansible/ansible_id_ed25519
  ```

---

## Playbook Best Practices

### Tags
- Always add `tags:` to playbooks for selective execution
- Use descriptive tag names (lowercase with underscores)
- Multiple tags allowed per playbook
- Tags enable partial execution and testing
- Example tags: `kubernetes`, `docker`, `nfs`, `upgrade`
- Usage: `ansible-playbook playbook.yaml --tags docker`

### gather_facts
- Always declare `gather_facts: true` or `false` explicitly
- Use `true` when playbooks need OS/system information
- Use `false` for simple operations to save time
- Default is `true` if not specified
- Consider fact caching for large inventories

### Rolling Updates (serial)
- Use `serial:` for cluster operations
- `serial: 1` for critical operations (one host at a time)
- `serial: "30%"` for rolling updates across 30% of hosts
- `serial: "50%"` for updates across half of hosts
- Ensures service availability during updates
- Important for Kubernetes, NFS, and multi-node deployments

---

## Security Guidelines

### CRITICAL: NEVER COMMIT SENSITIVE DATA

STRICTLY PROHIBITED in ALL commits (code, docs, examples):
- Real usernames
- Real IP addresses
- Real SSH ports
- Real hostnames or domain names (except inventory group names in `hosts:` field)
- Real passwords
- API keys/tokens
- SSH private keys
- Certificates
- Network CIDRs

MANDATORY: Use placeholders ONLY:
- Usernames: `[your-username]`, `[admin-username]`
- IPs: `[internal-ip]`, `[server-ip]`, `[client-ip]`, `[control-plane-ip]`
- Ports: `[custom-ssh-port]`, `[server-port]`, `[vpn-port]`, `[k8s-api-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`, `[node-hostname]`
- Exception: inventory group names in `hosts:` field are allowed
- Passwords: `[your-password-here]`, `[sudo-password]`
- API keys: `[your-api-key-here]`
- Networks: `[network-cidr]`, `[vpn-network-cidr]`, `[client-network]`

Examples of correct placeholder usage:
```yaml
ansible_user: [your-username]
ansible_port: [custom-ssh-port]
ansible_host: [server-ip]
vault_become_pass: [your-password-here]
dns_server: [dns-server-ip]
```

Never use real values in examples, even in "wrong" examples.

### Never Commit Secrets
- Never commit plaintext passwords, API keys, tokens, or sensitive data
- Never put logins or passwords in documentation files
- Never include SSH private keys, certificates, or encrypted secrets in git
- Use `[redacted]`, `[REDACTED]`, or placeholder text in documentation examples
- Reference `SECURITY.md` for comprehensive security practices

### Secret Management
- Use `ansible-vault` for encrypting sensitive variables in playbooks
- Use GPG or password managers for vault password storage (see `SECURITY.md`)
- Vault password file: use `.vault_pass` in project root for automation
  - Ensure `.vault_pass` has correct permissions: `chmod 600 .vault_pass`
  - Add `.vault_pass` to `.gitignore` to prevent committing passwords
  - Configure in `ansible.cfg`: `vault_password_file = .vault_pass`
  - Example: `ansible-vault encrypt secrets.yaml` (reads password from `.vault_pass`)
- Store secrets in environment variables only when absolutely necessary
- Consider external secret managers (HashiCorp Vault, AWS Secrets Manager)

### Documentation Security
Documentation must use placeholders only. Never include real data in README files, guides, or examples.

### Pre-Commit Security Checklist
Before any commit, verify:
- [ ] No plaintext passwords in any files (use `git diff` to review)
- [ ] No API keys, tokens, or credentials in code or documentation
- [ ] All secrets properly encrypted with ansible-vault or GPG
- [ ] Sensitive files added to `.gitignore`
- [ ] Inventory group names in `hosts:` field are acceptable

### Git Hooks for Security Validation
The repository includes Git hooks to prevent commits with sensitive data.

Available hooks:
- `pre-commit`: blocks commits containing hardcoded IPs, ports, usernames, hostnames, or other sensitive patterns
- `commit-msg`: validates commit messages and prevents sensitive data in commit messages
- `pre-push`: final security verification before pushing to remote repository
- `post-merge`: automatically updates hooks after pulling/merging changes
- `post-checkout`: automatically updates hooks after switching branches

Hook installation:
```bash
bash scripts/setup_hooks.sh
```

Security patterns detected:
- Hardcoded IPs
- Hardcoded ports
- Hardcoded usernames
- Hardcoded hostnames in variables or config
- Sensitive keys, certificates, vault passwords, API keys, passwords

Acceptable patterns (placeholders only):
- IPs: `[server-ip]`, `[client-ip]`, `[internal-ip]`, `[vip-address]`
- Ports: `[custom-ssh-port]`, `[server-port]`, `[k8s-api-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`
- Usernames: `[your-username]`
- Passwords: `[your-password-here]`
- API keys: `[your-api-key-here]`

Testing hooks:
- Create a temporary file with placeholders and confirm the hook allows it
- To test detection locally, replace placeholders with a real value and confirm the hook blocks the commit
- Never commit or push real values

Documentation for hooks: `scripts/githooks/README.md`

---

## Role Metadata

### meta/main.yaml
All roles MUST include `meta/main.yaml` with:
- `author` - Role author name
- `description` - Clear role purpose
- `company` - Organization (null if personal)
- `license` - License type (MIT recommended)
- `min_ansible_version` - Minimum Ansible version required
- `platforms` - Supported OS distributions and versions
- `galaxy_tags` - Relevant tags for Ansible Galaxy
- `dependencies` - List of role dependencies (empty list if none)

Example `meta/main.yaml`:
```yaml
---
author: yourname
description: Brief description of role purpose
company: null
license: MIT
min_ansible_version: 2.16
platforms:
  - name: Debian
    versions:
      - bullseye
      - bookworm
  - name: Ubuntu
    versions:
      - focal
      - jammy
galaxy_tags:
  - category1
  - category2
dependencies: []
```

---

## Testing

### Test Suite
```bash
# Run all tests (syntax, structure, conventions, unit tests)
./run_tests.sh

# Run specific test category
ansible-playbook tests/unit/test_docker_variables.yaml
ansible-playbook tests/integration/test_common.yaml --check
```

### Test Types

1) Unit Tests
- Validate variable existence and types
- Test naming conventions (lowercase_with_underscores)
- Verify data structures (lists, dicts)

2) Integration Tests
- Run role execution in check mode (no actual changes)
- Test role imports and task execution
- Validate task flow and logic
- Ensure handlers are properly defined

3) Validation Tests
- Syntax validation: `ansible-playbook --syntax-check`
- Role structure: verify tasks/defaults/handlers exist
- Naming conventions: detect ALL_CAPS violations
- FQCN usage: ensure modules use fully qualified names

### Adding Tests
Unit test example:
```yaml
---
- name: Test <role_name> variables
  hosts: localhost
  connection: local
  gather_facts: no
  tasks:
    - name: Verify variable exists
      ansible.builtin.assert:
        that:
          - variable_name is defined
          - variable_name is expected_type
        success_msg: "Variable defined correctly"
        fail_msg: "Variable is missing or wrong type"
```

Integration test example:
```yaml
---
- name: Test <role_name> role
  hosts: localhost
  connection: local
  gather_facts: yes
  become: yes
  vars:
    test_mode: true
  tasks:
    - name: Test role import
      ansible.builtin.include_role:
        name: <role_name>

    - name: Assert role completed
      ansible.builtin.assert:
        that: true
        success_msg: "Role executed successfully"
```

### Test Requirements
- Tests run locally without real servers
- Use `connection: local` for localhost tests
- Use `--check` mode for non-destructive testing
- Tests should be idempotent and repeatable

### CI/CD Integration
Add to your pipeline:
```yaml
test:
  script:
    - ./run_tests.sh
  only:
    - merge_requests
    - main
```

---

## Documentation

### Role Documentation
Each role should include:
- `README.md` in role directory describing purpose and usage
- Default variables in `defaults/main.yaml` with comments
- Handler documentation in `handlers/main.yaml`

### Playbook Documentation
Each playbook should include:
- Descriptive name and purpose
- Host pattern description
- Required variables (if any)
- Usage examples in comments (placeholders only)

### Changelog
Track changes in `CHANGELOG.md`:
- Version number
- Date
- Changes (Added, Changed, Fixed, Removed)
