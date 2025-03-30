#!/bin/bash
# Script to run MCP-CLI integration tests against the IMAP MCP server
# Assumes mcp-cli will dynamically launch the server based on its config.

set -e  # Exit immediately if a command exits with a non-zero status.
set -x  # Print commands and their arguments as they are executed.

# Ensure script is run from the project root (imap-mcp)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT="$SCRIPT_DIR"
cd "$PROJECT_ROOT" || exit 1

echo "=== Ensuring Project Virtual Environment (.venv) Exists ==="
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Creating and installing dependencies..."
    uv venv || exit 1
    # Activate venv for subsequent commands in this script context if needed,
    # although uv run should handle it.
    source .venv/bin/activate || exit 1 
    uv pip install -e ".[dev]" || exit 1
else
    echo "Virtual environment .venv found."
fi

# Set up PYTHONPATH just in case uv run needs help finding modules
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"

echo "=== Checking MCP-CLI Subdirectory and Installation ==="
if [ ! -d "mcp-cli" ]; then
    echo "MCP-CLI directory not found. Cloning from GitHub..."
    git clone https://github.com/ModelContextProtocol/mcp-cli.git || exit 1
fi

# Check if mcp-cli is installed in the venv; install/update if necessary
# Using uv pip install ensures it's in the correct environment
echo "=== Installing/Updating MCP-CLI in the virtual environment ==="
# Assuming mcp-cli has a pyproject.toml for installation
(cd mcp-cli && uv pip install -e .) || exit 1

echo "=== Verifying mcp-cli/server_config.json exists ==="
if [ ! -f "mcp-cli/server_config.json" ]; then
    echo "ERROR: mcp-cli/server_config.json not found! Cannot run tests." 
    exit 1
fi
# Optional: Could add a check here to verify the command path in the json is correct
PYTHON_EXEC="${PROJECT_ROOT}/.venv/bin/python"
if ! grep -q "\"command\": \"${PYTHON_EXEC}\"" mcp-cli/server_config.json; then
    echo "WARNING: Python command in mcp-cli/server_config.json might not match expected venv path: ${PYTHON_EXEC}"
    echo "Attempting to run tests anyway..."
fi

echo "=== Running integration tests (using mcp-cli dynamic server launch) ==="
# Run pytest for the specific integration test file
# Add -s to show stdout/stderr from tests, useful for debugging CLI interactions
uv run pytest -s -v tests/integration/test_mcp_cli_integration.py

EXIT_CODE=$?
echo "=== Tests completed with exit code: $EXIT_CODE ==="

exit $EXIT_CODE
