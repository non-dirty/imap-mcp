# IMAP MCP Server Development Guide

> **Important**: Before starting any development task, first consult the [DOCUMENTATION_CATALOG.md](./DOCUMENTATION_CATALOG.md) file to identify the most relevant documentation for your task. This catalog provides a comprehensive overview of all documentation files in the project.

## Environment Setup and Build Commands with `uv`
- Create virtual environment: `uv venv`
- Activate virtual environment: `source .venv/bin/activate` (Unix/macOS) or `.venv\Scripts\activate` (Windows)
- Install dependencies: `uv pip install -e ".[dev]"`
- Install specific packages: `uv add package_name`
- Run commands within the environment: `uv run command [args]`

## Build and Test Commands
- Install dependencies: `uv pip install -e ".[dev]"`
- Run all tests: `uv run pytest`
- Run single test: `uv run pytest tests/test_file.py::TestClass::test_function -v`
- Run with coverage: `uv run pytest --cov`
- Run server: `uv run python -m imap_mcp.server --config /path/to/config.yaml`
- Development mode: `uv run python -m imap_mcp.server --dev`
- One-line execution with dependencies: `uvx run -m imap_mcp.server --config /path/to/config.yaml`

## Code Style Guidelines
- Use Black with 88 character line length
- Imports: Use isort with Black profile
- Types: All functions must have type hints (mypy enforces this)
- Naming: snake_case for variables/functions, PascalCase for classes
- Error handling: Use specific exceptions and provide helpful messages
- Documentation: Write docstrings for all classes and methods
- Testing: Follow TDD pattern (write tests before implementation)
- Project structure follows the standard Python package layout

## Task Workflow
When working on tasks from GitHub Issues, follow this workflow:

1. **Task Analysis**:
   - Read and understand the issue requirements
   - Assess if the issue needs to be broken down into smaller subtasks
   - If needed, create separate issues for subtasks and link them to the parent issue
   - Analyze existing labels and make sure the issue has the correct priority and status labels

2. **Starting Work on an Issue**:
   - Create a branch that references the issue number: `git checkout -b feature/issue-[NUMBER]-[SHORT_DESCRIPTION]`
   - Make an initial commit that references the issue: `git commit -m "refs #[NUMBER]: Start implementing [FEATURE]"`
   - The automated status tracking system will detect this commit and change the issue status to "in-progress"

3. **Test-Driven Development**:
   - Write tests first that verify the desired functionality
   - Implement the feature until all tests pass
   - Refactor code while maintaining test coverage
   - Run full test suite to check for regressions: `uv run pytest --cov=imap_mcp`

4. **Completing an Issue**:
   - Create a pull request that references the issue: `gh pr create --title "[TITLE]" --body "Closes #[NUMBER]"`
   - The body should include "Closes #[NUMBER]" or "Fixes #[NUMBER]" to automatically close the issue when merged
   - The automated status tracking system will update the issue status to "completed" when the PR is merged
   - It will also automatically adjust priorities of remaining tasks

5. **GitHub Issue Management Commands**:
   - View all issues: `gh issue list`
   - View specific issue: `gh issue view [NUMBER]`
   - Filter issues by label: `gh issue list --label "priority:1"`
   - Create new issue: `gh issue create` (interactive) or:
     `gh issue create --title "Title" --body "Description" --label "priority:X" --label "status:prioritized"`
   - Edit issue: `gh issue edit [NUMBER] --add-label "priority:1" --remove-label "priority:2"`

6. **Documentation**:
   - Update docstrings in implementation
   - Update README.md or other docs if needed
   - Add new commands or processes to this CLAUDE.md file if relevant

7. **Commit Conventions**:
   - Use these prefixes in commit messages to trigger automatic status changes:
     - `refs #X`: References the issue without changing status
     - `implements #X`: Indicates implementation progress
     - `fixes #X`: Indicates the issue is fixed (used in final commits)
     - `closes #X`: Same as fixes, will close the issue when merged
   - Always include the issue number with the # prefix
   - Add descriptive message after the issue reference

## Issue Status Definitions

GitHub Issues have the following status labels:

- **status:prioritized**: Task has been assigned a priority, not yet started
- **status:in-progress**: Work on the task has begun (automatic when commits reference issue)
- **status:completed**: Implementation is finished (automatic when PR with "fixes/closes" is merged)
- **status:reviewed**: Task has been reviewed (currently manual update)
- **status:archived**: Task has been archived (currently manual update)

Priority labels follow the format `priority:X` where X is a number starting from 1 (highest priority).

## Integration Testing

Integration tests verify that the IMAP MCP server works correctly with real email services. These tests require valid credentials and network connectivity to external services.

### Environment Setup for Integration Tests

1. **Required Environment Variables**:
   - `TEST_IMAP_HOST`: IMAP server hostname (e.g., `imap.gmail.com`)
   - `TEST_SMTP_HOST`: SMTP server hostname (e.g., `smtp.gmail.com`)
   - `TEST_EMAIL`: Email address for testing
   - `TEST_PASSWORD`: Email password or app password

2. **Set Up Environment Variables**:
   ```bash
   # For temporary use in current session
   export TEST_IMAP_HOST=imap.gmail.com
   export TEST_SMTP_HOST=smtp.gmail.com
   export TEST_EMAIL=your-test-email@gmail.com
   export TEST_PASSWORD=your-app-password
   
   # Or add to your .env file for persistence (make sure it's in .gitignore)
   echo "TEST_IMAP_HOST=imap.gmail.com" >> .env
   echo "TEST_SMTP_HOST=smtp.gmail.com" >> .env
   echo "TEST_EMAIL=your-test-email@gmail.com" >> .env
   echo "TEST_PASSWORD=your-app-password" >> .env
   ```

### Refreshing OAuth2 Credentials

OAuth2 tokens expire periodically. If integration tests fail with authentication errors, refresh your tokens before running tests:

1. **Check if token refresh is needed**:
   ```bash
   uv run python -m imap_mcp.oauth2 check-token --config config.yaml
   ```

2. **Refresh the token if expired**:
   ```bash
   uv run python -m imap_mcp.auth_setup refresh-token --config config.yaml
   ```

3. **Generate a new token if refresh fails**:
   ```bash
   uv run python -m imap_mcp.auth_setup generate-token --config config.yaml
   ```

### Running Integration Tests

1. **Run all tests including integration tests**:
   ```bash
   uv run pytest
   ```

2. **Run only integration tests**:
   ```bash
   uv run pytest tests/integration/
   ```

3. **Skip integration tests when necessary**:
   ```bash
   uv run pytest --skip-integration
   ```

4. **Run specific integration test**:
   ```bash
   uv run pytest tests/integration/test_gmail_integration.py::test_gmail_connect_oauth2
   ```

### Writing New Integration Tests

When writing new integration tests:

1. **Mark tests appropriately**: Use the `@pytest.mark.integration` decorator
2. **Handle authentication errors gracefully**: Tests should fail clearly if credentials are invalid or expired
3. **Clean up after tests**: Restore mailbox state after tests run (delete test messages, reset folders)
4. **Isolate test data**: Use unique identifiers or timestamps for test data to avoid conflicts
5. **Use test fixtures**: Leverage pytest fixtures for setup and teardown
6. **Respect rate limits**: Add delays if necessary to avoid hitting service rate limits

Example integration test structure:
```python
import pytest

@pytest.mark.integration
def test_some_integration_feature(gmail_client):
    # Test implementation
    result = gmail_client.some_operation()
    assert result == expected_value