# Git Hooks Documentation

## Overview

This repository includes comprehensive Git hooks to prevent commits with sensitive data and enforce code quality standards. The hooks automatically verify changes before they are committed or pushed to remote repositories.

## Installation

Hooks are automatically installed in `.git/hooks/` when you clone the repository. They are executable and will run automatically on Git operations.

To reinstall hooks:

```bash
bash scripts/setup_hooks.sh
```

Or manually:

```bash
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg
chmod +x .git/hooks/pre-push
chmod +x .git/hooks/post-merge
chmod +x .git/hooks/post-checkout
chmod +x scripts/verify_sensitive_data.py
```

### Automatic Hook Updates

The repository includes automatic hook synchronization:
- **post-merge**: Automatically updates hooks after pulling/merging changes
- **post-checkout**: Automatically updates hooks after switching branches

This ensures all team members always have the latest version of hooks.

## Available Hooks

### Summary

| Hook | Purpose | Blocking |
|------|---------|----------|
| `pre-commit` | Blocks commits with sensitive data | Yes |
| `commit-msg` | Validates commit message format and content | Yes |
| `pre-push` | Final security check before push | Yes |
| `post-merge` | Auto-updates hooks after pulling/merging | No |
| `post-checkout` | Auto-updates hooks after branch switch | No |

### Pre-Commit Hook (`.git/hooks/pre-commit`)

**Purpose:** Block commits containing sensitive data before they are created.

**When it runs:** Before a commit is created (`git commit`).

**What it checks:**
- Staged files for hardcoded infrastructure data
- Sensitive file patterns (vault_secrets.yml, SSH keys, WireGuard keys)
- Hardcoded IPs, ports, usernames, hostnames
- Sensitive keys and passwords

**How it works:**
1. Gets list of staged files from Git
2. Filters files by extension (.yaml, .yml, .md, .j2, .sh, .py, .ini)
3. Runs verification script on each file
4. Groups violations by file and type
5. Prints color-coded output
6. Blocks commit if violations found

**Example output (blocked):**
```
=== PRE-COMMIT SECURITY VERIFICATION ===

Checking 3 file(s)...

🚨 SECURITY VIOLATIONS FOUND:

File: roles/kuber_init/defaults/main.yaml
  HARDCODED_IP:
    Line 23: Found hardcoded_ip: 198.51.100.250

File: CHANGELOG.md
  HARDCODED_PORT:
    Line 45: Found hardcoded_port: "6443"

Total violations: 2

Commit blocked! Please fix violations before committing.
Use 'git commit --amend' to edit or 'git reset HEAD <file>' to unstage files.
```

**Example output (success):**
```
=== PRE-COMMIT SECURITY VERIFICATION ===

Checking 3 file(s)...

✓ No sensitive data found
```

**Bypass:** Use `git commit --no-verify` (not recommended for production code).

---

### Commit-Message Hook (`.git/hooks/commit-msg`)

**Purpose:** Validate commit messages and ensure they don't contain sensitive data.

**When it runs:** After commit message is written, before commit is finalized.

**What it checks:**
- Empty commit messages (blocks)
- Minimum message length (10 characters)
- Conventional Commits format (warning only)
- Sensitive data in commit message (blocks)
- Placeholder pattern usage (encouraged)

**Conventional Commits format:**
```
type(scope): description

Types:
  - feat:     New feature
  - fix:      Bug fix
  - docs:     Documentation changes
  - refactor: Code refactoring
  - test:     Adding or updating tests
  - chore:     Maintenance tasks
  - style:    Code style changes (formatting)
  - perf:     Performance improvements
  - ci:       CI/CD changes
  - build:    Build system changes
  - revert:   Revert previous commit
```

**Examples:**
```
feat(auth): add login functionality
fix(api): resolve timeout issue
docs(readme): update installation instructions
refactor(core): simplify error handling
test(auth): add unit tests for login
chore(deps): update ansible-lint
```

**Example output (blocked):**
```
✗ Error: Commit message is empty
Please provide a descriptive commit message
```

```
✗ Error: Commit message contains sensitive data
Found pattern: 9\.11\.0\.
Please remove sensitive data from commit message
Use placeholder patterns like [server-ip] instead
```

**Example output (warning):**
```
⚠ Warning: Commit message doesn't follow Conventional Commits format
Recommended format: type(scope): description
Examples:
  feat(auth): add login functionality
  fix(api): resolve timeout issue
  docs(readme): update installation instructions
```

**Example output (success):**
```
✓ Commit message validation passed
```

**Bypass:** Use `git commit --no-verify` (not recommended for production code).

---

### Pre-Push Hook (`.git/hooks/pre-push`)

**Purpose:** Final security verification before pushing to remote repository.

**When it runs:** Before push to remote (`git push`).

**What it checks:**
- All commits being pushed
- Sensitive files in commits
- Hardcoded IPs, ports, hostnames in commit contents (excluding comments and documentation)
- Commit author and date

**Exclusions:**
- YAML comments (lines starting with `#`)
- Inventory group names in `hosts:` fields (e.g., `hosts: bay_bgp`)
- Markdown table entries documenting inventory references

**How it works:**
1. Gets commits being pushed (from remote to local)
2. Checks each commit for violations
3. Verifies file contents for sensitive patterns
4. Groups violations by commit
5. Prints detailed report
6. Blocks push if violations found

**Example output (blocked):**
```
=== PRE-PUSH SECURITY VERIFICATION ===

Checking commits in abc1234..def5678

Commit: def5678
  Author: John Doe
  Date: 2026-02-02
  Message: fix(api): update endpoint
  ✗ Sensitive files detected:
    vault_secrets.yml
  ✗ Found hardcoded IP in: roles/haproxy/defaults/main.yaml

🚨 SECURITY VIOLATIONS FOUND IN 1 COMMIT(S)
Push blocked! Please fix violations before pushing.
You can bypass this check with: git push --no-verify
```

**Example output (success):**
```
=== PRE-PUSH SECURITY VERIFICATION ===

Checking commits in abc1234..def5678

Commit: def5678
  Author: John Doe
  Date: 2026-02-02
  Message: docs(readme): update installation guide

✓ All 1 commit(s) verified successfully

✅ PRE-PUSH VERIFICATION PASSED
```

**Bypass:** Use `git push --no-verify` (not recommended for production code).

---

## Verification Script

**Location:** `scripts/.git/hooks/verify_sensitive_data.py`

**Purpose:** Main verification logic for detecting sensitive data.

**Supported file types:**
- YAML: `.yaml`, `.yml`
- Markdown: `.md`
- Jinja2 templates: `.j2`
- Shell scripts: `.sh`
- Python: `.py`
- INI files: `.ini`

**Sensitive patterns detected:**

### Hardcoded IPs
- Real infrastructure IPs: `192.168.10.x`, `176.57.220.x`, etc.
- Kubernetes networks: `10.244.0.0/16`, `10.96.0.0/12`
- Private networks: `10.x.x.x`, `172.16-31.x.x`

### Hardcoded Ports
- Kubernetes API: `6443`, `7443`
- WireGuard: `51840-51842`, `51942`
- Custom SSH ports: `ansible_port:` with value

### Hardcoded Usernames
- Real usernames: `www`, `root`, `linroot`
- Format: `ansible_user: www`, `become_user: root`

### Hardcoded Hostnames
- Real hostnames: `haproxy_spb`, `bay_bgp`, `bay_plane1-2`, `bay_worker1-2`
- Cloud hostnames: `cloud_plane1-2`, `cloud_worker1-2`

### Sensitive Keys
- SSH private keys: `-----BEGIN RSA PRIVATE KEY-----`
- Certificates: `-----BEGIN CERTIFICATE-----`
- Vault passwords: `vault_become_pass:`, `vault_*_pass:`
- API keys: `api_key:` with long random strings
- Passwords: `password:` with long values

### Sensitive Files
- Vault encrypted files: `vault_secrets.yml`, `*.vault`
- WireGuard keys: `wg_keys.yaml`, `*_wg_keys.yaml`
- Group variables: `group_vars/*.yml` (non-example)
- Inventory files: `hosts_*.ini`, `inventory_*.yaml`
- SSH keys: `id_rsa`, `id_ed25519`, `*.pem`
- All INI files: `*.ini` (may contain connection details)

**Acceptable patterns (allowed):**

### Placeholder Format
- `[vip-address]`, `[server-ip]`, `[client-ip]`, `[control-plane-ip]`, `[internal-ip]`
- `[custom-ssh-port]`, `[server-port]`, `[k8s-api-port]`, `[haproxy-frontend-port]`
- `[cluster-hostname]`, `[server-hostname]`
- `[your-username]`, `[your-password-here]`, `[your-api-key-here]`
- `[network-cidr]`, `[vpn-network-cidr]`, `[pod-network-cidr]`, `[service-network-cidr]`

### Masked Documentation
- `192.168.1.***:518***` (WireGuard sanitization)
- Partially masked IPs/ports for documentation

### Google DNS in Examples
- `dns_servers: ["8.8.8.8", "1.1.1.1"]` (very restrictive)

### Default YAML Keys
- `ansible_host:`, `ansible_user:`, `ansible_port:` (without values)

---

### Post-Merge Hook (`.git/hooks/post-merge`)

**Purpose:** Automatically update hooks after pulling/merging changes from remote.

**When it runs:** After `git pull` or `git merge` operations complete.

**What it does:**
- Automatically runs `scripts/setup_hooks.sh` to update all hooks
- Ensures team members have the latest hook versions
- Non-blocking (fails silently if setup script is missing)

**Example output:**
```
=== Auto-updating Git hooks ===

✓ Git hooks updated successfully
```

---

### Post-Checkout Hook (`.git/hooks/post-checkout`)

**Purpose:** Automatically update hooks after switching branches.

**When it runs:** After `git checkout` operations when switching branches.

**What it does:**
- Automatically runs `scripts/setup_hooks.sh` to update all hooks
- Ensures hooks are consistent across branches
- Non-blocking (fails silently if setup script is missing)

**Example output:**
```
=== Auto-updating Git hooks (branch switch) ===

✓ Git hooks updated successfully
```

---

## Testing Hooks

### Test Pre-Commit Hook

1. Create a test file with sensitive data:
```bash
echo "server_ip: 198.51.100.250" > test_sensitive.yaml
```

2. Stage and try to commit:
```bash
git add test_sensitive.yaml
git commit -m "test: sensitive data"
```

3. Hook should block with error message.

4. Clean up:
```bash
git reset HEAD test_sensitive.yaml
rm test_sensitive.yaml
```

### Test Commit-Message Hook

1. Try to commit with empty message:
```bash
echo "test" > test.txt
git add test.txt
git commit -m ""
```

2. Hook should block with "commit message is empty" error.

3. Try with proper message:
```bash
git commit -m "test: verify commit message validation"
```

4. Should succeed.

### Test Pre-Push Hook

1. Make a commit with sensitive data:
```bash
echo "server_ip: 198.51.100.250" > test_push.yaml
git add test_push.yaml
git commit --no-verify -m "test: bypass pre-commit"
```

2. Try to push:
```bash
git push origin main
```

3. Pre-push hook should detect and block.

4. Fix and push:
```bash
git reset --soft HEAD~1
echo "server_ip: [vip-address]" > test_push.yaml
git add test_push.yaml
git commit -m "test: verify pre-push hook"
git push origin main
```

---

## Troubleshooting

### Hook Not Running

**Problem:** Hook not executing when committing.

**Solution:** Make sure hook is executable:
```bash
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg
chmod +x .git/hooks/pre-push
```

### Verification Script Not Found

**Problem:** Pre-commit hook reports verification script not found.

**Solution:** Ensure script exists:
```bash
ls -la scripts/.git/hooks/verify_sensitive_data.py
chmod +x scripts/.git/hooks/verify_sensitive_data.py
```

### False Positives

**Problem:** Hook blocks valid code.

**Solution:**
1. Check if data uses proper placeholder format: `[vip-address]`, `[server-ip]`
2. For documentation, use masked format: `192.168.1.***:518***`
3. Add to `ACCEPTABLE_PATTERNS` in verification script if needed
4. For emergency, use `git commit --no-verify` (document why)

### Python Version Issues

**Problem:** Hook fails with Python syntax error.

**Solution:** Check Python version:
```bash
python3 --version
```

Requires Python 3.7+. Update verification script shebang if needed:
```python
#!/usr/bin/env python3
```

---

## Best Practices

1. **Always use placeholders:**
   - ✅ `ansible_host: [server-ip]`
   - ❌ `ansible_host: 192.168.1.10`

2. **Follow Conventional Commits:**
   - ✅ `feat(auth): add login functionality`
   - ❌ `added login`

3. **Write descriptive messages:**
   - ✅ `fix(api): resolve timeout issue with retry logic`
   - ❌ `fix timeout`

4. **Test hooks locally:**
   - Test pre-commit with real changes
   - Verify commit messages before pushing
   - Check pre-push output before force pushing

5. **Document bypasses:**
   - If using `--no-verify`, document why in commit message
   - Create follow-up commit to fix violations

6. **Keep hooks updated:**
   - Review patterns quarterly
   - Add new sensitive patterns as infrastructure changes
   - Update documentation

---

## Security Policy

All commits must comply with the [AGENTS.md](../../AGENTS.md) security policy:

### NEVER Commit:
- Real usernames, IP addresses, SSH ports
- Real hostnames or domain names
- Real passwords, API keys, tokens
- SSH private keys or certificates
- Network CIDRs or identifiers

### ALWAYS Use Placeholders:
- Usernames: `[your-username]`
- IPs: `[internal-ip]`, `[server-ip]`, `[client-ip]`
- Ports: `[custom-ssh-port]`, `[server-port]`
- Hostnames: `[cluster-hostname]`, `[server-hostname]`
- Passwords: `[your-password-here]`
- API keys: `[your-api-key-here]`

**Violation of this policy will immediately fail code review.**

---

## Maintenance

### Adding New Sensitive Patterns

Edit `scripts/.git/hooks/verify_sensitive_data.py`:

```python
SENSITIVE_PATTERNS = {
    'hardcoded_ip': [
        r'\bNEW_IP_PATTERN\b',  # Add new pattern
        # ... existing patterns
    ],
    # ... other categories
}
```

### Adding New Acceptable Patterns

Edit `scripts/.git/hooks/verify_sensitive_data.py`:

```python
ACCEPTABLE_PATTERNS = [
    # ... existing patterns
    r'\[new-placeholder\]',  # Add new placeholder
]
```

### Updating Documentation

Keep this README synchronized with:
- Hook code changes
- New sensitive patterns
- Policy updates in AGENTS.md

---

## Support

For issues or questions about Git hooks:

1. Check this documentation first
2. Review hook output for specific errors
3. Test with simple cases to isolate issues
4. Check AGENTS.md for security policies

---

**Last Updated:** 2026-02-03
**Version:** 2.0.0
