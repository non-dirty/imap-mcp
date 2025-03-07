# IMAP MCP Server Development Guide

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
- Run with coverage: `uv run pytest --cov=imap_mcp`
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
When working on tasks from TASKS.md, follow this workflow:

1. **Task Analysis**:
   - Read and understand the task requirements
   - Assess if the task needs to be broken down into smaller subtasks
   - If needed, update TASKS.md with the subtask breakdown

2. **Task Status Update**:
   - Update the task's status in the Task Tracker table from "prioritized" to "started"
   - Commit this change before beginning implementation

3. **Test-Driven Development**:
   - Write tests first that verify the desired functionality
   - Implement the feature until all tests pass
   - Refactor code while maintaining test coverage
   - Run full test suite to check for regressions

4. **Task Completion**:
   - Change the task's status to "completed" in the Task Tracker
   - Move task details from TASKS.md to TASKS_COMPLETED.md
   - Add a detailed summary of accomplishments under the task in TASKS_COMPLETED.md
   - Keep task numbers unchanged - do NOT renumber tasks

5. **Priority Reassessment**:
   - After completing a task, reassess priorities for remaining tasks
   - Update the priority numbers in the Task Tracker as appropriate
   - Document the reasoning for any priority changes

6. **Documentation**:
   - Update docstrings in implementation
   - Update README.md or other docs if needed
   - Add new commands or processes to CLAUDE.md if relevant

7. **Commit Changes**:
   - Create a descriptive commit message including the task number
   - Push commits to GitHub repository

## Task Status Definitions

Tasks in the Task Tracker can have the following statuses:

- **proposed**: Initial idea for a task, not yet fully defined
- **defined**: Task has been specified but not yet prioritized
- **prioritized**: Task has been assigned a priority number
- **started**: Work on the task has begun
- **completed**: Implementation is finished and passes all tests
- **reviewed**: Task has been reviewed by another contributor
- **archived**: Task has been moved to TASKS_COMPLETED.md