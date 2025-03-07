# IMAP MCP Server Development Guide

## Build and Test Commands
- Install dependencies: `pip install -e ".[dev]"`
- Run all tests: `pytest`
- Run single test: `pytest tests/test_file.py::TestClass::test_function -v`
- Run with coverage: `pytest --cov=imap_mcp`
- Run server: `python -m imap_mcp.server --config /path/to/config.yaml`
- Development mode: `python -m imap_mcp.server --dev`

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
When working on tasks from TASKS.md, follow this workflow:

1. **Task Analysis**:
   - Read and understand the task requirements
   - Assess if the task needs to be broken down into smaller subtasks
   - If needed, update TASKS.md with the subtask breakdown

2. **Test-Driven Development**:
   - Write tests first that verify the desired functionality
   - Implement the feature until all tests pass
   - Refactor code while maintaining test coverage
   - Run full test suite to check for regressions

3. **Task Completion**:
   - Move completed task from TASKS.md to TASKS_COMPLETED.md
   - Add a detailed summary of accomplishments under the task in TASKS_COMPLETED.md
   - Update task numbering in TASKS.md to be sequential
   - Commit changes with a descriptive message (including task number)
   - Push commits to GitHub repository

4. **Documentation**:
   - Update docstrings in implementation
   - Update README.md or other docs if needed
   - Add new commands or processes to CLAUDE.md if relevant