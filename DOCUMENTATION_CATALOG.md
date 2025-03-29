# IMAP MCP Documentation Catalog

This document provides a comprehensive overview of all documentation files in the IMAP MCP project. Use this catalog as your first reference point to find specific information about the project's setup, configuration, development practices, and workflows.

## Documentation Files

| Filename | Description | Purpose | Audience | When to Read |
|----------|-------------|---------|----------|--------------|
| README.md | Project overview, features, setup instructions | Provide a high-level introduction to the project and quick setup instructions | User | When first encountering the project or needing a general overview |
| CLAUDE.md | Development guide for AI assistance | Provide development patterns, conventions, and workflows for implementing features | AI Coder | Before starting any development task to ensure compliance with project standards |
| INSTALLATION.md | Detailed installation instructions | Guide users through the complete installation process | User | When setting up the project for the first time |
| GMAIL_SETUP.md | Gmail authentication setup guide | Help users configure Gmail-specific authentication | User | When configuring the project to work with Gmail accounts |
| TASKS.md | Historical task reference (deprecated) | Reference for development tasks (note: actual tasks now in GitHub Issues) | User & AI Coder | Only for historical reference - active tasks are in GitHub Issues |
| TASKS_COMPLETED.md | List of completed tasks | Track development progress | User & AI Coder | When reviewing project history or checking if a feature was implemented |
| TASKS_ICEBOX.md | Backlog of potential future tasks | Track ideas for future development | User & AI Coder | When planning future development or considering new features |
| DOCUMENTATION_CATALOG.md | This file - catalog of all documentation | Provide a single reference point for all documentation | User & AI Coder | When looking for specific documentation but unsure which file contains it |
| docs/AI_DEV_WORKFLOW.md | AI-assisted development workflow | Explain how AI assistants participate in development | User & AI Coder | When integrating AI assistance into the development process |
| docs/COMMIT_CONVENTIONS.md | Git commit formatting standards | Standardize commit messages and link them to issues | AI Coder | Before making any commits to follow project conventions |
| docs/GITHUB_ISSUES_WORKFLOW.md | GitHub Issues management | Explain how to use GitHub Issues for task management | User & AI Coder | When creating, updating, or managing project tasks |
| docs/GIT_INTEGRATION_CHECKLIST.md | Checklist for Git integration | Ensure proper Git workflow | AI Coder | Before starting work on a new branch or preparing for merge |
| docs/ISSUE_HELPER_USAGE.md | Instructions for using issue helper scripts | Facilitate GitHub Issues automation | User & AI Coder | When working with GitHub Issues and helper scripts |
| docs/ISSUE_STATUS_AUTOMATION.md | Details about issue status automation | Explain how issue status is automatically updated | AI Coder | When monitoring issue status changes or troubleshooting automation |
| tests/issue_test_log.md | Test log for issues | Track issue testing | AI Coder | When reviewing test coverage for specific issues |
| tests/issue_test_log.txt | Text version of test log | Track issue testing | AI Coder | When reviewing test coverage for specific issues (alternative format) |

## Recent Features

The following features have been recently implemented and are documented in the codebase:

1. **Email Reply Functionality**
   - Draft replies to emails with proper headers and formatting
   - Support for both plain text and HTML replies
   - Reply-all functionality with CC support
   - Proper saving of drafts to the appropriate folders

2. **Integration Tests**
   - Tests for email reply drafting functionality
   - Tests for IMAP and SMTP client interactions

## Documentation Update History

| Date | Description |
|------|-------------|
| 2025-03-28 | Added DOCUMENTATION_CATALOG.md and updated references to HTML email reply functionality |

## Usage Instructions

When looking for information:

1. Start with this catalog to identify the most relevant document
2. Review the specific document for detailed information
3. If information spans multiple documents, check cross-references
4. For code-specific documentation, refer to docstrings in the source code

For developers (both human and AI), ensure that documentation is kept up-to-date when implementing new features.
