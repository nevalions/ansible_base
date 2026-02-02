# Test Script for VIP + HAProxy + Keepalived Architecture
# This script validates the implementation of new VIP-based HA architecture

set -e

echo "=== Kubernetes VIP Architecture Test Suite ==="
echo ""

# Colors for output
GREEN='\033[0;32m\'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "1. Verifying Vault Configuration"
echo "-------------------------------"

# Test 1: Check vault variables exist
ansible-vault view vault_secrets.yml | grep -q "vault_keepalived_vip"
print_result $? "vault_keepalived_vip exists"

ansible-vault view vault_secrets.yml | grep -q "vault_k8s_api_vip"
print_result $? "vault_k8s_api_vip exists"

ansible-vault view vault_secrets.yml | grep -q "vault_k8s_control_planes"
print_result $? "vault_k8s_control_planes exists"

ansible-vault view vault_secrets.yml | grep -q "k8s-api"
print_result $? "k8s-api DNS record exists"

echo ""
echo "2. Verifying Role Structure"
echo "-------------------------------"

# Test 2: Check keepalived role files exist
test -f roles/keepalived/tasks/main.yaml
print_result $? "keepalived/tasks/main.yaml exists"

test -f roles/keepalived/handlers/main.yaml
print_result $? "keepalived/handlers/main.yaml exists"

test -f roles/keepalived/templates/keepalived.conf.j2
print_result $? "keepalived/templates/keepalived.conf.j2 exists"

test -f roles/keepalived/defaults/main.yaml
print_result $? "keepalived/defaults/main.yaml exists"

test -f roles/keepalived/meta/main.yaml
print_result $? "keepalived/meta/main.yaml exists"

echo ""
echo "3. Verifying Playbooks"
echo "-------------------------------"

# Test 3: Check playbooks exist and are valid
test -f keepalived_manage.yaml
print_result $? "keepalived_manage.yaml exists"

ansible-playbook --syntax-check keepalived_manage.yaml > /dev/null 2>&1
print_result $? "keepalived_manage.yaml syntax valid"

test -f haproxy_k8s.yaml
print_result $? "haproxy_k8s.yaml exists"

ansible-playbook --syntax-check haproxy_k8s.yaml > /dev/null 2>&1
print_result $? "haproxy_k8s.yaml syntax valid"

echo ""
echo "4. Verifying Role Configuration"
echo "-------------------------------"

# Test 4: Check role variable configurations
grep -q "vault_k8s_api_vip" roles/kuber_join/defaults/main.yaml
print_result $? "kuber_join uses VIP"

grep -q "vault_k8s_api_vip" roles/kuber_init/defaults/main.yaml
print_result $? "kuber_init uses VIP"

grep -q "vault_k8s_control_planes" roles/haproxy_k8s/tasks/main.yaml
print_result $? "haproxy_k8s supports multi-plane"

echo ""
echo "5. Verifying Inventory"
echo "-------------------------------"

# Test 5: Check inventory groups
grep -q "\[keepalived_hosts\]" hosts_bay.ini
print_result $? "[keepalived_hosts] group exists"

grep -q "\[keepalived_vip_servers\]" hosts_bay.ini
print_result $? "[keepalived_vip_servers] group exists"

grep -q "haproxy_spb" hosts_bay.ini | grep -q "keepalived_hosts"
print_result $? "haproxy_spb in keepalived_hosts group"

echo ""
echo "6. Code Quality Checks"
echo "-------------------------------"

# Test 6: Run ansible-lint
ansible-lint roles/keepalived/ > /dev/null 2>&1
print_result $? "keepalived role passes ansible-lint"

ansible-lint roles/haproxy_k8s/ > /dev/null 2>&1
print_result $? "haproxy_k8s role passes ansible-lint"

ansible-lint roles/kuber_join/ > /dev/null 2>&1
print_result $? "kuber_join role passes ansible-lint"

ansible-lint roles/kuber_init/ > /dev/null 2>&1
print_result $? "kuber_init role passes ansible-lint"

echo ""
echo "7. Documentation Verification"
echo "-------------------------------"

# Test 7: Check documentation updates
grep -q "Virtual IP (VIP)" KUBERNETES_SETUP.md
print_result $? "VIP architecture documented in KUBERNETES_SETUP.md"

grep -q "keepalived" KUBERNETES_SETUP.md
print_result $? "Keepalived mentioned in KUBERNETES_SETUP.md"

grep -q "\[vip-address\]" KUBERNETES_SETUP.md
print_result $? "VIP address documented in KUBERNETES_SETUP.md"

grep -q "\[1.5.0\]" CHANGELOG.md
print_result $? "Version 1.5.0 changelog entry exists"

echo ""
echo "=== Test Summary ==="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Deploy Keepalived: ansible-playbook -i hosts_bay.ini keepalived_manage.yaml"
    echo "2. Deploy HAProxy: ansible-playbook -i hosts_bay.ini haproxy_k8s.yaml"
    echo "3. Initialize control plane: ansible-playbook -i hosts_bay.ini kuber_plane_init.yaml"
    echo "4. Join worker: ansible-playbook -i hosts_bay.ini kuber_worker_join.yaml"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    echo "Please review and fix the issues above."
    exit 1
fi
