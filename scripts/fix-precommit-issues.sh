#!/bin/bash
# Script to automatically fix common pre-commit issues

set -e

echo "============================================"
echo "Pre-commit Issue Fixer"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track changes
CHANGES_MADE=0

# Function to display status
status() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Fix 1: Remove unused Dict import from typing
echo "Fixing unused imports in Python files..."
UPDATER_FILE="src/docker_hosts_updater.py"
if grep -q "from typing import.*Dict" "$UPDATER_FILE"; then
    # Use perl for cross-platform compatibility
    perl -i -pe 's/from typing import Dict, /from typing import /g' "$UPDATER_FILE"
    perl -i -pe 's/from typing import Dict,/from typing import/g' "$UPDATER_FILE"
    perl -i -pe 's/, Dict//g' "$UPDATER_FILE"
    status "Removed unused Dict import from $UPDATER_FILE"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    status "Dict import already removed or not found"
fi

# Fix 2: Replace bare except with Exception
echo ""
echo "Fixing bare except clauses..."
if grep -q "^        except:$" "$UPDATER_FILE"; then
    perl -i -pe 's/^(        except):$/\1 Exception:/g' "$UPDATER_FILE"
    status "Fixed bare except clause in $UPDATER_FILE"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    status "No bare except clauses found"
fi

# Fix 3: Replace hardcoded /tmp with tempfile.gettempdir()
echo ""
echo "Fixing hardcoded temp directory..."
if grep -q 'dir="/tmp"' "$UPDATER_FILE"; then
    perl -i -pe 's|dir="/tmp"|dir=tempfile.gettempdir()|g' "$UPDATER_FILE"
    status "Replaced hardcoded /tmp with tempfile.gettempdir()"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    status "Temp directory already fixed"
fi

# Fix 4: Add SHELL directive to Dockerfile for pipefail
echo ""
echo "Fixing Dockerfile SHELL directive..."
if ! grep -q "^SHELL" Dockerfile; then
    # Add SHELL directive after FROM line
    perl -i -pe 's/^(FROM .*)$/\1\nSHELL ["\/bin\/bash", "-o", "pipefail", "-c"]/g' Dockerfile
    status "Added SHELL directive to Dockerfile"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    status "SHELL directive already present in Dockerfile"
fi

# Fix 5: Add language specifiers to markdown code blocks
echo ""
echo "Fixing markdown code blocks..."
for md_file in docs/CLAUDE.md docs/CONTRIBUTING.md docs/IMPROVEMENTS.md; do
    if [ -f "$md_file" ]; then
        # Replace ``` with ```text or ```bash where appropriate
        if grep -q '^```$' "$md_file"; then
            # This is a simple fix - mark as text by default
            # Manual review recommended for proper language tags
            warning "Code blocks without language found in $md_file - manual review recommended"
        else
            status "$md_file: No unfenced code blocks or already fixed"
        fi
    fi
done

# Summary
echo ""
echo "============================================"
echo "Summary"
echo "============================================"
echo "Changes made: $CHANGES_MADE"
echo ""

if [ $CHANGES_MADE -gt 0 ]; then
    status "Auto-fixable issues have been resolved"
    echo ""
    echo "Remaining issues that need manual attention:"
    echo ""
    warning "1. Function complexity (C901): get_docker_container_hosts is too complex"
    echo "   → Consider refactoring into smaller functions"
    echo ""
    warning "2. Markdown line length (MD013): Some lines exceed 120 characters"
    echo "   → Manually break long lines in docs/*.md files"
    echo ""
    warning "3. Markdown code blocks (MD040): Add language specifiers"
    echo "   → Change \`\`\` to \`\`\`bash, \`\`\`python, \`\`\`text, etc."
    echo ""
    warning "4. Various pylint warnings (logging, variable naming, etc.)"
    echo "   → Review pylint output for suggestions"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes: git diff"
    echo "2. Run pre-commit again: pre-commit run --all-files"
    echo "3. Address remaining issues manually if needed"
else
    status "No auto-fixable issues found"
fi

echo ""
echo "Done!"
