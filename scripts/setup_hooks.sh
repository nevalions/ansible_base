#!/bin/bash
# Setup script to install Git hooks from scripts/githooks/ to .git/hooks/
# Run this script to enable pre-commit, commit-msg, and pre-push hooks

set -e

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get repository root directory
REPO_ROOT="$(git rev-parse --show-toplevel)"
GITHOOKS_DIR="$REPO_ROOT/scripts/githooks"
TARGET_DIR="$REPO_ROOT/.git/hooks"

echo -e "${BLUE}=== Git Hooks Setup Script ===${NC}\n"

# Check if githooks directory exists
if [ ! -d "$GITHOOKS_DIR" ]; then
    echo -e "${RED}✗ Error: Githooks directory not found at $GITHOOKS_DIR${NC}"
    exit 1
fi

# Check if .git/hooks directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Creating .git/hooks directory${NC}"
    mkdir -p "$TARGET_DIR"
fi

# List of hooks to install
HOOKS=("pre-commit" "commit-msg" "pre-push" "post-merge" "post-checkout")

# Install each hook
echo -e "${BLUE}Installing Git hooks...${NC}\n"

INSTALLED=0
SKIPPED=0
FAILED=0

for hook in "${HOOKS[@]}"; do
    SOURCE="$GITHOOKS_DIR/$hook"
    TARGET="$TARGET_DIR/$hook"
    
    if [ ! -f "$SOURCE" ]; then
        echo -e "${RED}✗ Hook not found: $SOURCE${NC}"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Check if hook already exists
    if [ -f "$TARGET" ]; then
        # Backup existing hook
        BACKUP="$TARGET.backup"
        echo -e "${YELLOW}Backing up existing hook: $hook${NC}"
        cp "$TARGET" "$BACKUP"
        SKIPPED=$((SKIPPED + 1))
    fi
    
    # Copy hook
    echo -e "${GREEN}✓ Installing: $hook${NC}"
    cp "$SOURCE" "$TARGET"
    chmod +x "$TARGET"
    INSTALLED=$((INSTALLED + 1))
done

# Copy verification script
VERIFY_SOURCE="$GITHOOKS_DIR/verify_sensitive_data.py"
VERIFY_TARGET="$REPO_ROOT/scripts/verify_sensitive_data.py"

if [ -f "$VERIFY_SOURCE" ]; then
    echo -e "${GREEN}✓ Installing verification script${NC}"
    cp "$VERIFY_SOURCE" "$VERIFY_TARGET"
    chmod +x "$VERIFY_TARGET"
else
    echo -e "${RED}✗ Verification script not found${NC}"
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo -e "${BLUE}=== Setup Complete ===${NC}"
echo -e "${GREEN}Hooks installed: $INSTALLED${NC}"
echo -e "${YELLOW}Hooks backed up: $SKIPPED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Hooks failed: $FAILED${NC}"
fi

# Instructions
echo ""
echo -e "${YELLOW}Git hooks are now active!${NC}"
echo -e "${YELLOW}They will automatically run on git operations:${NC}"
echo -e "  ${BLUE}pre-commit${NC}   - Before committing changes"
echo -e "  ${BLUE}commit-msg${NC}  - After writing commit message"
echo -e "  ${BLUE}pre-push${NC}    - Before pushing to remote"
echo -e "  ${BLUE}post-merge${NC}  - After pulling/merging changes (auto-updates hooks)"
echo -e "  ${BLUE}post-checkout${NC} - After switching branches (auto-updates hooks)"
echo ""
echo -e "${YELLOW}To bypass a hook temporarily:${NC}"
echo -e "  ${BLUE}git commit --no-verify${NC}"
echo -e "  ${BLUE}git push --no-verify${NC}"
echo ""
echo -e "${YELLOW}For more information, see:${NC}"
echo -e "  ${BLUE}scripts/githooks/README.md${NC}"
echo ""
