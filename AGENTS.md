# Ansible Repository Guidelines for Agentic Coding

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
- **Task names**: Use descriptive, action-oriented names in lowercase with underscores
  - Good: `"Install Docker packages"`
  - Good: `"Check if folder exists"`
- **Variables**: Use lowercase with underscores
  - Good: `nfs_exports`, `skip_folder_check`, `docker_check`
- **Handlers**: Use lowercase describing the action
  - Good: `restart nfs`, `reload exports`
- **Playbooks**: Use lowercase with underscores, descriptive of purpose
  - Good: `nfs_server_manage.yaml`, `workstation.yaml`

### Module Usage
- Use FQCN (fully qualified collection name) for clarity:
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
- Use `ansible_facts['os_family']` for OS detection (Debian, Archlinux, etc.)
- Use `ansible_os_family` for broader checks
- Support `skip_folder_check` pattern with defaults: `skip_folder_check | default(false)`

### Loops
- Use `loop` instead of `with_items` (Ansible 2.5+)
- Use `with_subelements` for nested iteration
- Use `| select()`, `| list()`, `| difference()` filters for data manipulation

### Task Organization
- Group related tasks with comments
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
- Preserve custom sections that shouldn't be overwritten
- Use `{% if custom_exports | length > 0 %}` for conditional sections

### Variable Management
- Define default variables in `roles/<role_name>/defaults/main.yaml`
- Load external vars with `vars_files:` in playbooks
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

#### 1. Unit Tests
Test variable definitions and structures without executing roles:
- Validate variable existence and types
- Test naming conventions (lowercase_with_underscores)
- Verify data structures (lists, dicts)

#### 2. Integration Tests
Run role execution in check mode (no actual changes):
- Test role imports and task execution
- Validate task flow and logic
- Ensure handlers are properly defined

#### 3. Validation Tests
- Syntax validation: `ansible-playbook --syntax-check`
- Role structure: Verify tasks/defaults/handlers exist
- Naming conventions: Detect ALL_CAPS violations
- FQCN usage: Ensure modules use fully qualified names

### Adding Tests

**Unit Test Example:**
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

**Integration Test Example:**
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
- Usage examples in comments

### Changelog
Track changes in `CHANGELOG.md`:
- Version number
- Date
- Changes (Added, Changed, Fixed, Removed)