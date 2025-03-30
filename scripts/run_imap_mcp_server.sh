#!/bin/bash
# Wrapper script to run the IMAP MCP server within its virtual environment.

set -e # Exit on error

# Get the directory where the script resides
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Assume the project root is one level up from the script directory
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

VENV_PATH="$PROJECT_ROOT/.venv"
SERVER_SCRIPT="$PROJECT_ROOT/imap_mcp/server.py"

echo "Wrapper: Starting IMAP MCP Server..."
echo "Wrapper: Project Root: $PROJECT_ROOT"
echo "Wrapper: Venv Path: $VENV_PATH"
echo "Wrapper: Arguments: $@"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
  echo "Wrapper: Error - Virtual environment not found at $VENV_PATH" >&2
  exit 1
fi

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Set PYTHONPATH just in case (might be redundant after activating venv)
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
echo "Wrapper: PYTHONPATH set to $PYTHONPATH"

# Special case handling for --help and --version flags
if [[ "$*" == *"--help"* ]]; then
    echo "Wrapper: Detected --help flag, showing server help"
    python "$SERVER_SCRIPT" --help
    exit $?
fi

if [[ "$*" == *"--version"* ]]; then
    echo "Wrapper: Detected --version flag, showing server version"
    echo "IMAP MCP Server version 0.1.0"
    echo "Wrapper script version 0.1.0"
    exit 0
fi

# Execute the server script using the venv's python
# Pass all arguments received by the wrapper script to the python script
echo "Wrapper: Executing: python $SERVER_SCRIPT $@"
exec python "$SERVER_SCRIPT" "$@"
