#!/bin/bash
# Run integration tests for the mcp-cli chat mode

set -e

# Change to the project root directory
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Running MCP CLI Chat Mode Integration Tests${NC}"
echo -e "${BLUE}=============================================${NC}"

# Ensure mcp-cli dependencies are installed
echo -e "${YELLOW}Ensuring mcp-cli dependencies are installed...${NC}"
cd "$PROJECT_ROOT/mcp-cli"
uv sync --reinstall
cd "$PROJECT_ROOT"

# Make sure the integration test has the right permissions
chmod +x "$PROJECT_ROOT/tests/integration/test_mcp_cli_chat.py"

# Set environment variables for integration tests (if needed)
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Function to run a specific test
run_test() {
    local test_name=$1
    local test_class="TestMcpCliChatMode"
    local test_file="tests/integration/test_mcp_cli_chat.py"
    
    echo -e "${YELLOW}Running test: ${test_name}${NC}"
    uv run pytest -xvs "$test_file::$test_class::$test_name"
}

# Parse command line arguments
ALL_TESTS=true
SPECIFIC_TEST=""

if [ $# -gt 0 ]; then
    if [ "$1" == "--test" ] && [ $# -gt 1 ]; then
        ALL_TESTS=false
        SPECIFIC_TEST=$2
    elif [ "$1" == "--help" ]; then
        echo "Usage: $0 [OPTIONS]"
        echo "Run MCP CLI chat mode integration tests."
        echo ""
        echo "Options:"
        echo "  --test TEST_NAME    Run a specific test (e.g., test_server_and_tool_commands)"
        echo "  --help              Show this help message"
        exit 0
    fi
fi

# Run the tests
if [ "$ALL_TESTS" = true ]; then
    echo -e "${GREEN}Running all MCP CLI chat mode tests${NC}"
    # Skip the skip marker for these specific tests
    uv run pytest -xvs tests/integration/test_mcp_cli_chat.py::TestMcpCliChatMode -k "not skip"
else
    run_test "$SPECIFIC_TEST"
fi

echo -e "${GREEN}Tests completed successfully!${NC}"
