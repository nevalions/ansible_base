#!/usr/bin/env python3
"""
Git pre-commit verification script to prevent commits with sensitive data
Checks staged files for hardcoded IPs, ports, usernames, hostnames, and other sensitive patterns
"""

import re
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

# ANSI color codes
COLORS = {
    'RED': '\033[0;31m',
    'GREEN': '\033[0;32m',
    'YELLOW': '\033[1;33m',
    'BLUE': '\033[0;34m',
    'NC': '\033[0m'
}

# File extensions to check
CHECK_EXTENSIONS = {'.yaml', '.yml', '.md', '.j2', '.sh', '.py', '.ini'}

# Sensitive file patterns (based on .gitignore)
SENSITIVE_FILE_PATTERNS = [
    r'vault_secrets\.yml$',
    r'vault_password\.',
    r'wg_keys\.yaml$',
    r'_wg_keys\.yaml$',
    r'\.vault$',
    r'group_vars/[^/]+\.yml$',
    r'hosts_.*\.ini$',
    r'inventory_.*\.yaml$',
    r'\.ssh/.*id_.*$',
    r'ansible_id_.*$',
]

# Sensitive content patterns
SENSITIVE_PATTERNS = {
    'hardcoded_ip': [
        # Real infrastructure IPs
        r'\b9\.11\.0\.\d{1,3}\b',
        r'\b192\.168\.10\.\d{1,3}\b',
        r'\b176\.57\.220\.\d{1,3}\b',
        r'\b194\.39\.101\.\d{1,3}\b',
        r'\b5\.188\.221\.\d{1,3}\b',
        r'\b212\.113\.122\.\d{1,3}\b',
        r'\b87\.249\.54\.\d{1,3}\b',
        # Kubernetes networks
        r'\b10\.244\.\d{1,3}\.\d{1,3}\b',
        r'\b10\.96\.\d{1,3}\.\d{1,3}\b',
        # Private networks (block most)
        r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        r'\b172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}\b',
    ],
    'hardcoded_port': [
        r'"6443"',
        r'"7443"',
        r'"51840"',
        r'"51841"',
        r'"51842"',
        r'"51942"',
        r'ansible_port:\s*\d+',
    ],
    'hardcoded_username': [
        r'ansible_user:\s*["\']?(www|root|linroot)["\']?',
        r'become_user:\s*["\']?(www|root|linroot)["\']?',
        r'"www"\s*:',
        r'"root"\s*:',
    ],
    'hardcoded_hostname': [
        r'haproxy_spb',
        r'bay_bgp',
        r'bay_plane[12]',
        r'bay_worker[12]',
        r'cloud_plane[12]',
        r'cloud_worker[12]',
    ],
    'sensitive_key': [
        r'-----BEGIN\s+(RSA|EC|OPENSSH|PRIVATE)\s+KEY-----',
        r'-----BEGIN\s+CERTIFICATE-----',
        r'vault_become_pass:\s*(?!\[).*(?<!\])',
        r'vault_.*_pass:\s*(?!\[).*(?<!\])',
        r'api[_-]?key:\s*["\']?[a-zA-Z0-9]{20,}',
        r'password:\s*["\']?[a-zA-Z0-9]{8,}',
    ],
}

# Acceptable patterns (allowed in documentation/examples)
ACCEPTABLE_PATTERNS = [
    # Placeholder format
    r'\[vip-address\]',
    r'\[server-ip\]',
    r'\[client-ip\]',
    r'\[control-plane-ip\]',
    r'\[internal-ip\]',
    r'\[custom-ssh-port\]',
    r'\[server-port\]',
    r'\[k8s-api-port\]',
    r'\[haproxy-frontend-port\]',
    r'\[cluster-hostname\]',
    r'\[server-hostname\]',
    r'\[your-username\]',
    r'\[your-password-here\]',
    r'\[your-api-key-here\]',
    r'\[network-cidr\]',
    r'\[vpn-network-cidr\]',
    r'\[pod-network-cidr\]',
    r'\[service-network-cidr\]',
    # Placeholder + standard ports (documentation)
    r'\[vip-address\]:(?:6443|7443)',
    r'\[cluster-hostname\]:(?:6443|7443)',
    r'\[control-plane-ip\]:(?:6443|7443)',
    r'\[haproxy-hostname\]:(?:6443|7443)',
    r':\s*(?:6443|7443|51840|51841|51842|51942)\b',
    # Masked documentation (WireGuard sanitization)
    r'192\.168\.\d+\.\*\*\*',
    r'\d+\.\d+\.\d+\.\*\*\*:\d+\*\*\*',
    # Default YAML keys without values
    r'^ansible_user:',
    r'^ansible_host:',
    r'^ansible_port:',
    # Google DNS in examples (very restrictive)
    r'dns_servers:\s*\["?8\.8\.8\.8"?,\s*"?1\.1\.1\.1"?\]',
    # Documentation examples showing what NOT to do
    r'^\s*❌\s+.*\(e\.g\.',
    r'^\s*\*\*❌ WRONG',
    r'^\s*# ❌ DO NOT',
]

def get_staged_files():
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    except subprocess.CalledProcessError:
        return []

def should_check_file(filepath):
    """Check if file should be verified based on extension."""
    path = Path(filepath)
    return path.suffix.lower() in CHECK_EXTENSIONS

def check_sensitive_file_pattern(filepath):
    """Check if filename matches sensitive patterns."""
    for pattern in SENSITIVE_FILE_PATTERNS:
        if re.search(pattern, filepath):
            return pattern
    return None

def is_line_acceptable(line):
    """Check if line contains acceptable patterns."""
    for pattern in ACCEPTABLE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False

def check_line_for_violations(line, line_num, filepath):
    """Check a single line for security violations."""
    violations = []
    line_content = line.strip()
    
    # Skip empty lines and comments
    if not line_content or line_content.startswith('#'):
        return violations
    
    # Skip pattern definition lines (raw strings in code)
    if "r'" in line_content or 'r"' in line_content:
        return violations
    
    # Skip lines with Python list/dict syntax (pattern definitions)
    if any(marker in line_content for marker in ["SENSITIVE_PATTERNS", "ACCEPTABLE_PATTERNS", "[", "]", "SENSITIVE_FILE_PATTERNS"]):
        return violations
    
    # Check if line has acceptable patterns
    if is_line_acceptable(line):
        return violations
    
    # Check each sensitive pattern category
    for pattern_type, patterns in SENSITIVE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, line):
                # Skip if matched portion has acceptable patterns
                match_text = line[match.start():match.end()]
                
                # Additional check for false positives
                if pattern_type == 'hardcoded_ip':
                    # Skip if this is part of a placeholder
                    if '[' in line and ']' in line:
                        continue
                    # Skip if this is a comment
                    if '#' in line and line.index('#') < match.start():
                        continue
                
                # Skip sensitive_key pattern definitions
                if pattern_type == 'sensitive_key':
                    if 'vault_' in line and 'pass:' in line and ("r'" in line_content or 'r"' in line_content):
                        continue
                    # Skip if key is followed by placeholder pattern
                    if re.search(r'vault_.*_pass:\s*\[', line):
                        continue
                    if re.search(r'password:\s*\[', line):
                        continue
                
                violations.append({
                    'line': line_num,
                    'file': filepath,
                    'type': pattern_type,
                    'pattern': pattern,
                    'message': f"Found {pattern_type}: {match_text}"
                })
    
    return violations

def check_file_for_violations(filepath):
    """Check a single file for security violations."""
    violations = []
    path = Path(filepath)
    
    if not path.exists():
        return violations
    
    # Skip README files (they contain examples)
    if path.name.lower().endswith('readme.md'):
        return violations
    
    # Skip verification script itself (it contains pattern definitions)
    if 'verify_sensitive_data.py' in filepath:
        return violations
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, start=1):
                violations.extend(check_line_for_violations(line, line_num, filepath))
    except (IOError, UnicodeDecodeError):
        # Skip binary files or files that can't be read
        pass
    
    return violations

def print_violations(violations):
    """Print violation results with color-coded output."""
    if not violations:
        print(f"{COLORS['GREEN']}✓ No sensitive data found{COLORS['NC']}")
        return True
    
    print(f"\n{COLORS['RED']}🚨 SECURITY VIOLATIONS FOUND:{COLORS['NC']}\n")
    
    # Group violations by file
    by_file = defaultdict(list)
    for v in violations:
        by_file[v['file']].append(v)
    
    # Print violations grouped by file
    for filepath, file_violations in sorted(by_file.items()):
        print(f"{COLORS['BLUE']}File: {filepath}{COLORS['NC']}")
        
        # Group by type within file
        by_type = defaultdict(list)
        for v in file_violations:
            by_type[v['type']].append(v)
        
        for v_type, v_list in sorted(by_type.items()):
            print(f"{COLORS['YELLOW']}  {v_type.upper()}:{COLORS['NC']}")
            for v in sorted(v_list, key=lambda x: x['line']):
                print(f"    {COLORS['RED']}Line {v['line']}: {v['message']}{COLORS['NC']}")
        print()
    
    total = len(violations)
    print(f"{COLORS['RED']}Total violations: {total}{COLORS['NC']}")
    print(f"{COLORS['YELLOW']}\nCommit blocked! Please fix violations before committing.{COLORS['NC']}")
    print(f"{COLORS['YELLOW']}Use 'git commit --amend' to edit or 'git reset HEAD <file>' to unstage files.{COLORS['NC']}\n")
    
    return False

def main():
    """Main verification entry point."""
    print(f"{COLORS['BLUE']}=== PRE-COMMIT SECURITY VERIFICATION ==={COLORS['NC']}\n")
    
    # Get staged files
    staged_files = get_staged_files()
    
    if not staged_files:
        print(f"{COLORS['YELLOW']}No files staged for commit{COLORS['NC']}\n")
        return 0
    
    # Check file patterns (gitignored files being committed)
    file_pattern_violations = []
    for filepath in staged_files:
        pattern = check_sensitive_file_pattern(filepath)
        if pattern:
            file_pattern_violations.append({
                'file': filepath,
                'pattern': pattern,
                'message': f"Sensitive file pattern detected: {pattern}"
            })
    
    if file_pattern_violations:
        print(f"{COLORS['RED']}🚨 SENSITIVE FILE PATTERNS FOUND:{COLORS['NC']}\n")
        for v in file_pattern_violations:
            print(f"  {COLORS['RED']}File: {v['file']}{COLORS['NC']}")
            print(f"    {v['message']}")
        print(f"\n{COLORS['YELLOW']}These files should be in .gitignore or use placeholder examples.{COLORS['NC']}\n")
        return 1
    
    # Filter files to check
    files_to_check = [f for f in staged_files if should_check_file(f)]
    
    if not files_to_check:
        print(f"{COLORS['GREEN']}✓ No text files to check in commit{COLORS['NC']}\n")
        return 0
    
    print(f"Checking {len(files_to_check)} file(s)...\n")
    
    # Check each file for violations
    all_violations = []
    for filepath in files_to_check:
        violations = check_file_for_violations(filepath)
        all_violations.extend(violations)
    
    # Print results
    success = print_violations(all_violations)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
