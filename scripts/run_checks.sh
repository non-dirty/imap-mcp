#!/bin/bash
set -e

# run_checks.sh - Automation script for code quality checks
# Runs linting, formatting, type checking, unit tests, and coverage

# Display help message
display_help() {
    echo "Usage: ./scripts/run_checks.sh [OPTIONS]"
    echo ""
    echo "Run code quality checks for the imap-mcp project."
    echo ""
    echo "Options:"
    echo "  --help                      Display this help message"
    echo "  --lint-only                 Run only linting (ruff)"
    echo "  --format-only               Run only formatting (black, isort)"
    echo "  --type-check-only           Run only type checking (mypy)"
    echo "  --test-only                 Run only tests without coverage"
    echo "  --coverage-only             Run only tests with coverage"
    echo "  --skip-integration          Skip integration tests"
    echo "  --ci                        Run in CI mode (stricter checks)"
    echo ""
    echo "If no options are provided, all checks will be run."
    exit 0
}

# Set variables
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/imap_mcp"
TESTS_DIR="${ROOT_DIR}/tests"
PYTHONPATH="${ROOT_DIR}:${PYTHONPATH}"
export PYTHONPATH

RUN_ALL=true
RUN_LINT=false
RUN_FORMAT=false
RUN_TYPE_CHECK=false
RUN_TESTS=false
RUN_COVERAGE=false
SKIP_INTEGRATION=false
CI_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            display_help
            ;;
        --lint-only)
            RUN_ALL=false
            RUN_LINT=true
            ;;
        --format-only)
            RUN_ALL=false
            RUN_FORMAT=true
            ;;
        --type-check-only)
            RUN_ALL=false
            RUN_TYPE_CHECK=true
            ;;
        --test-only)
            RUN_ALL=false
            RUN_TESTS=true
            ;;
        --coverage-only)
            RUN_ALL=false
            RUN_COVERAGE=true
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            ;;
        --ci)
            CI_MODE=true
            ;;
        *)
            echo "Unknown option: $1"
            display_help
            ;;
    esac
    shift
done

if [[ "${RUN_ALL}" = true ]]; then
    RUN_LINT=true
    RUN_FORMAT=true
    RUN_TYPE_CHECK=true
    RUN_TESTS=false
    RUN_COVERAGE=true
fi

echo "=== Running checks for imap-mcp ==="
cd "${ROOT_DIR}"

# Linting
if [[ "${RUN_LINT}" = true ]]; then
    echo -e "\n=== Running linting with ruff ==="
    uv run ruff check "${SRC_DIR}" "${TESTS_DIR}"
    echo "✅ Linting passed"
fi

# Formatting
if [[ "${RUN_FORMAT}" = true ]]; then
    echo -e "\n=== Checking formatting with black ==="
    uv run black --check "${SRC_DIR}" "${TESTS_DIR}"
    
    echo -e "\n=== Checking import sorting with isort ==="
    uv run isort --check-only --profile black "${SRC_DIR}" "${TESTS_DIR}"
    echo "✅ Formatting check passed"
fi

# Type checking
if [[ "${RUN_TYPE_CHECK}" = true ]]; then
    echo -e "\n=== Running type checking with mypy ==="
    uv run mypy "${SRC_DIR}"
    echo "✅ Type checking passed"
fi

# Tests
if [[ "${RUN_TESTS}" = true ]]; then
    echo -e "\n=== Running tests ==="
    if [[ "${SKIP_INTEGRATION}" = true ]]; then
        uv run pytest "${TESTS_DIR}" --skip-integration -v
    else
        uv run pytest "${TESTS_DIR}" -v
    fi
    echo "✅ Tests passed"
fi

# Coverage
if [[ "${RUN_COVERAGE}" = true ]]; then
    echo -e "\n=== Running tests with coverage ==="
    if [[ "${SKIP_INTEGRATION}" = true ]]; then
        uv run pytest "${TESTS_DIR}" --skip-integration --cov="${SRC_DIR}" --cov-report=term --cov-report=json
    else
        uv run pytest "${TESTS_DIR}" --cov="${SRC_DIR}" --cov-report=term --cov-report=json
    fi
    
    # Check coverage threshold in CI mode
    if [[ "${CI_MODE}" = true ]]; then
        MIN_COVERAGE=80
        COVERAGE=$(uv run python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered_display'])")
        
        echo "Coverage: ${COVERAGE}%"
        if (( $(echo "${COVERAGE} < ${MIN_COVERAGE}" | bc -l) )); then
            echo "❌ Coverage is below minimum threshold of ${MIN_COVERAGE}%"
            exit 1
        fi
    fi
    
    echo "✅ Coverage check passed"
fi

echo -e "\n=== All checks completed successfully! ==="
