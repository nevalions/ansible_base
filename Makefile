.PHONY: test all lint syntax check security-tests unit-tests integration-tests
.PHONY: lint-playbook syntax-playbook help

# Main test target - runs everything
test all: lint syntax security-tests unit-tests integration-tests
	@echo ""
	@echo "=========================================="
	@echo "All tests completed successfully!"
	@echo "=========================================="

# Lint entire repository
lint:
	@echo "=========================================="
	@echo "Running ansible-lint..."
	@echo "=========================================="
	@ansible-lint
	@echo "✓ Linting passed"

# Run syntax checks on all playbooks
syntax:
	@echo "=========================================="
	@echo "Running syntax checks..."
	@echo "=========================================="
	@for playbook in *.yaml; do \
		if [ -f "$$playbook" ]; then \
			echo "Checking $$playbook..."; \
			ansible-playbook --syntax-check "$$playbook" || exit 1; \
		fi; \
	done
	@echo "✓ Syntax checks passed"

# Run security filter tests (Python)
security-tests:
	@echo "=========================================="
	@echo "Running security filter tests..."
	@echo "=========================================="
	@python3 tests/test_security_filters.py
	@echo "✓ Security filter tests passed"

# Run all unit tests
unit-tests:
	@echo "=========================================="
	@echo "Running unit tests..."
	@echo "=========================================="
	@for test in tests/unit/*.yaml; do \
		if [ -f "$$test" ]; then \
			echo "Running $$test..."; \
			ansible-playbook -e 'ansible_become_pass=test' "$$test" || exit 1; \
		fi; \
	done
	@echo "✓ Unit tests passed"

# Run integration tests in check mode (no actual changes)
integration-tests check:
	@echo "=========================================="
	@echo "Running integration tests (check mode)..."
	@echo "=========================================="
	@for test in tests/integration/*.yaml; do \
		if [ -f "$$test" ]; then \
			echo "Running $$test..."; \
			ansible-playbook -e 'ansible_become_pass=test' "$$test" --check || exit 1; \
		fi; \
	done
	@echo "✓ Integration tests passed"

# Lint a specific playbook
lint-playbook:
	@echo "Linting $(PLAYBOOK)..."
	@ansible-lint $(PLAYBOOK)

# Check syntax of a specific playbook
syntax-playbook:
	@echo "Checking syntax of $(PLAYBOOK)..."
	@ansible-playbook --syntax-check $(PLAYBOOK)

# Display available targets
help:
	@echo "Ansible Project - Available Make Targets"
	@echo "======================================"
	@echo ""
	@echo "Primary Targets:"
	@echo "  make test / make all    Run complete test suite"
	@echo "  make help              Show this help message"
	@echo ""
	@echo "Individual Test Targets:"
	@echo "  make lint              Run ansible-lint on entire repository"
	@echo "  make syntax            Run syntax checks on all playbooks"
	@echo "  make security-tests    Run Python security filter tests"
	@echo "  make unit-tests        Run all unit tests"
	@echo "  make integration-tests Run integration tests in check mode"
	@echo "  make check             Alias for integration-tests"
	@echo ""
	@echo "Detailed Targets:"
	@echo "  make lint-playbook PLAYBOOK=<name>   Lint specific playbook"
	@echo "  make syntax-playbook PLAYBOOK=<name> Check syntax of specific playbook"
	@echo ""
	@echo "Examples:"
	@echo "  make test"
	@echo "  make lint"
	@echo "  make security-tests"
	@echo "  make lint-playbook PLAYBOOK=wireguard_manage.yaml"
	@echo ""
	@echo "Documentation: See tests/README.md"
