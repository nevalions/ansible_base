# Ansible Project Tests

This directory contains test suites for the Ansible project that can run without real servers.

## Test Structure

```
tests/
├── integration/          # Integration tests (run locally)
│   ├── test_common.yaml
│   ├── test_zsh.yaml
│   ├── test_dotfiles.yaml
│   └── test_upgrade_deb.yaml
 └── unit/               # Unit tests (validate variables & structure)
     ├── test_docker_variables.yaml
     ├── test_kuber_reset_variables.yaml
     ├── test_longhorn_clean_variables.yaml
     └── test_nfs_server_variables.yaml
```

## Running Tests

### Run All Tests (Recommended)

**Using Makefile:**
```bash
make test
# or
make all
```

This runs:
1. ansible-lint (entire repository)
2. Syntax checks (all playbooks)
3. Security filter tests (Python)
4. Unit tests (all roles)
5. Integration tests (check mode)

### Run Individual Test Categories

**Lint repository:**
```bash
make lint
```

**Syntax checks:**
```bash
make syntax
```

**Security filter tests:**
```bash
make security-tests
```

**Unit tests:**
```bash
make unit-tests
```

**Integration tests:**
```bash
make integration-tests
# or
make check
```

### Test Specific Playbook

**Lint specific playbook:**
```bash
make lint-playbook PLAYBOOK=wireguard_manage.yaml
```

**Check syntax of specific playbook:**
```bash
make syntax-playbook PLAYBOOK=wireguard_manage.yaml
```

### List Available Targets

```bash
make help
```

### Run Specific Tests (Manual)

**Syntax check only:**
```bash
ansible-playbook --syntax-check <playbook>.yaml
```

**Run specific unit test:**
```bash
ansible-playbook tests/unit/test_docker_variables.yaml
```

**Run integration test (check mode - no changes):**
```bash
ansible-playbook tests/integration/test_common.yaml --check
```

## Test Categories

### 1. Syntax Checks
Validates YAML syntax and Ansible playbook structure for all 8 playbooks.

### 2. Role Structure Validation
Verifies each role has:
- `tasks/main.yaml`
- `defaults/main.yaml`
- `handlers/main.yaml`

### 3. Unit Tests
Tests variable definitions and structures without executing roles:
- **Docker role**: Validates `install_docker` variable and package list
- **Kuber reset role**: Validates `remove_container_images` variable
- **Longhorn clean role**: Validates `longhorn_data_path` and `kubelet_pods_path` variables
- **NFS Server role**: Validates `skip_folder_check` variable and exports structure
- **Variable naming**: Ensures lowercase_with_underscores convention

### 4. Convention Checks
- **ALL_CAPS variables**: Detects violation of naming convention
- **FQCN usage**: Ensures all modules use fully qualified collection names
- **YAML validation**: Checks YAML file structure

### 5. Integration Tests
Tests role execution in check mode (no actual changes):
- Common role
- Dotfiles role
- Upgrade Debian role
- Zsh role

## Test Results

Run `./run_tests.sh` to see:
- Total tests passed/failed
- Warnings
- Detailed breakdown per test category

## Adding New Tests

### Unit Test Example
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
```

### Integration Test Example
```yaml
---
- name: Test <role_name> role
  hosts: localhost
  connection: local
  gather_facts: yes
  become: yes
  tasks:
    - name: Test role import
      ansible.builtin.include_role:
        name: <role_name>
```

## CI Integration

Add to your CI/CD pipeline:

```yaml
test:
  script:
    - ./run_tests.sh
  only:
    - merge_requests
    - main
```

## Benefits

- ✅ No real servers required
- ✅ Fast execution
- ✅ Catch syntax errors early
- ✅ Validate code conventions
- ✅ Ensure role structure consistency
- ✅ Test variable definitions
- ✅ Run locally before deployment