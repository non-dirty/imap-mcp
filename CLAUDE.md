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