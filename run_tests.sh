#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

echo "=========================================="
echo "Ansible Project Test Suite"
echo "=========================================="
echo ""

echo -e "${YELLOW}[1/5] Running syntax checks...${NC}"
echo "------------------------------------------"

for playbook in *.yaml; do
    if [ -f "$playbook" ]; then
        echo -n "Testing $playbook... "
        if ansible-playbook --syntax-check "$playbook" &>/dev/null; then
            echo -e "${GREEN}PASS${NC}"
            ((PASSED++))
        else
            echo -e "${RED}FAIL${NC}"
            ((FAILED++))
        fi
    fi
done

echo ""
echo -e "${YELLOW}[2/5] Checking role structure...${NC}"
echo "------------------------------------------"

for role in roles/*/; do
    if [ -d "$role" ]; then
        rolename=$(basename "$role")
        echo -n "Testing role $rolename... "
        
        if [ -f "$role/tasks/main.yaml" ]; then
            echo -n "tasks "
            ((PASSED++))
        else
            echo -n "no_tasks "
            ((WARNINGS++))
        fi

        if [ -f "$role/defaults/main.yaml" ]; then
            echo -n "defaults "
            ((PASSED++))
        else
            echo -n "no_defaults "
            ((WARNINGS++))
        fi

        if [ -f "$role/handlers/main.yaml" ]; then
            echo -n "handlers "
            ((PASSED++))
        else
            echo -n "no_handlers "
            ((WARNINGS++))
        fi

        echo -e "${GREEN}OK${NC}"
    fi
done

echo ""
echo -e "${YELLOW}[3/5] Running unit tests...${NC}"
echo "------------------------------------------"

for test_file in tests/unit/*.yaml; do
    if [ -f "$test_file" ]; then
        echo -n "Running $test_file... "
        if ansible-playbook "$test_file" &>/dev/null; then
            echo -e "${GREEN}PASS${NC}"
            ((PASSED++))
        else
            echo -e "${RED}FAIL${NC}"
            ((FAILED++))
        fi
    fi
done

echo ""
echo -e "${YELLOW}[4/5] Checking variable naming conventions...${NC}"
echo "------------------------------------------"

echo -n "Checking for ALL_CAPS variables in playbooks... "
all_caps=$(grep -r "{{ [A-Z]" *.yaml 2>/dev/null | wc -l)
if [ "$all_caps" -eq 0 ]; then
    echo -e "${GREEN}PASS${NC} (no ALL_CAPS found)"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} (found $all_caps instances)"
    ((FAILED++))
fi

echo -n "Checking FQCN usage in tasks... "
fqcn_count=$(grep -E "^\s+[a-z][a-z0-9_]+:\s*$" roles/*/tasks/*.yaml 2>/dev/null | grep -v "ansible.builtin" | grep -v "community.general" | grep -v "ansible.posix" | grep -v "name:" | grep -v "hosts:" | grep -v "vars:" | grep -v "tasks:" | grep -v "roles:" | grep -v "handlers:" | grep -v "when:" | grep -v "loop:" | grep -v "with_items:" | grep -v "become:" | grep -v "ignore_errors:" | grep -v "register:" | grep -v "changed_when:" | grep -v "failed_when:" | grep -v "notify:" | grep -v "tags:" | grep -v "args:" | grep -v "dest:" | grep -v "path:" | grep -v "state:" | grep -v "repo:" | grep -v "src:" | grep -v "mode:" | grep -v "file:" | grep -v "filename:" | grep -v "that:" | grep -v "loop_control:" | grep -v "loop_var:" | grep -v "label:" | grep -v "executable:" | grep -v "creates:" | grep -v "removes:" | grep -v "enabled:" | grep -v "daemon_reload:" | grep -v "selection:" | grep -v "backup:" | grep -v "regexp:" | grep -v "replace:" | grep -v "sysctl_set:" | grep -v "reload:" | grep -v "rule:" | grep -v "proto:" | grep -v "port:" | grep -v "policy:" | grep -v "owner:" | grep -v "group:" | grep -v "recurse:" | grep -v "shell:" | grep -v "user:" | grep -v "appended:" | wc -l)
if [ "$fqcn_count" -eq 0 ]; then
    echo -e "${GREEN}PASS${NC} (all modules use FQCN)"
    ((PASSED++))
else
    echo -e "${YELLOW}WARN${NC} (found $fqcn_count modules without FQCN)"
    ((WARNINGS++))
fi

echo ""
echo -e "${YELLOW}[5/5] Validating YAML structure...${NC}"
echo "------------------------------------------"

yaml_count=$(find . -name "*.yaml" -type f | wc -l)
echo -n "Validating $yaml_count YAML files... "
if [ "$yaml_count" -gt 0 ]; then
    echo -e "${GREEN}PASS${NC} (found $yaml_count YAML files)"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} (no YAML files found)"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo "Total: $((PASSED + FAILED + WARNINGS))"
echo "=========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi