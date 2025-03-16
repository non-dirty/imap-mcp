# GitHub Issues Workflow

This document describes the workflow for using GitHub Issues for task tracking in the IMAP MCP project.

## Overview

The IMAP MCP project is transitioning from using TASKS.md to GitHub Issues for task management. This transition will enhance our development process by:

1. Improving collaboration and visibility
2. Enabling automation through GitHub Actions
3. Integrating task tracking with code reviews and pull requests
4. Providing better organization with labels, milestones, and project boards

## Task Lifecycle

### Creating Tasks

New tasks should be created as GitHub Issues:

1. Navigate to the [Issues tab](https://github.com/non-dirty/imap-mcp/issues)
2. Click "New issue"
3. Use a descriptive title prefixed with "Task: " (e.g., "Task: Implement OAuth2 Flow")
4. Include detailed information in the description:
   - Test Specifications
   - Implementation Steps
   - Expected Outcome
5. Add appropriate labels:
   - `priority:X` to indicate priority (e.g., `priority:1` for highest priority)
   - `status:prioritized` for tasks that are ready to be worked on
   - Other relevant labels (e.g., `type:feature`, `type:bug`, `type:test`)

### Tracking Progress

Tasks progress through the following stages:

1. **Backlog**: Tasks that are defined but not yet prioritized
2. **Prioritized**: Tasks that are ready to be worked on
3. **In Progress**: Tasks that are actively being worked on
4. **Review**: Tasks that are completed and awaiting review
5. **Done**: Tasks that are completed and merged

The project board will automatically move tasks between columns based on labels and issue state.

### Working on Tasks

When you start working on a task:

1. Assign the issue to yourself
2. Change the status label to `status:in-progress`
3. Create a branch named after the issue (e.g., `task-24-github-issues`)
4. Reference the issue number in your commits (e.g., "refs #24: Implement GitHub Issues integration")
5. Create a pull request that references the issue (e.g., "Closes #24")

### Completing Tasks

When a task is completed:

1. Ensure all tests pass and code coverage meets the threshold
2. Submit a pull request that references the issue
3. Update the issue with any relevant information
4. The issue will be automatically closed when the PR is merged

## Automated Workflows

The following automated workflows are in place:

1. **Issue Templates**: Standard templates for different types of tasks
2. **Project Board Automation**: Automatic movement of issues between columns
3. **Issue Linking**: Automatic linking of issues and pull requests
4. **Status Updates**: Automatic status updates based on actions

## Issue Status Tracking

Issues follow this lifecycle:

1. **prioritized**: Task has been assigned a priority number
2. **in-progress**: Work on the task has begun
3. **completed**: Implementation is finished and passes all tests
4. **reviewed**: Task has been reviewed by another contributor
5. **archived**: Task has been closed and archived

### Automated Status Updates

The project includes an automated status tracking system that monitors repository activity and updates issue statuses accordingly. This system:

- Automatically transitions issues from `prioritized` to `in-progress` when work begins
- Updates to `completed` when tests pass and a PR is merged
- Adds informative comments about status changes with relevant details

For detailed information on this automation, see [ISSUE_STATUS_AUTOMATION.md](../docs/ISSUE_STATUS_AUTOMATION.md).

## Issue Labels

1. **Keep issues atomic**: Each issue should represent a single, cohesive task
2. **Write clear specifications**: Include detailed test specifications in each issue
3. **Link related issues**: Use GitHub's reference syntax to link related issues
4. **Update status promptly**: Keep the status labels current to reflect actual progress
5. **Provide context**: Include enough information for anyone to understand the task

## Code Coverage Tasks

As part of our test-driven development approach, maintaining high code coverage is essential. The transition script automatically creates high-priority tasks for modules with coverage below the threshold (90%).

These tasks should be addressed before other feature work to ensure a solid foundation for future development.

## Legacy Tasks

During the transition period:

1. TASKS.md will be maintained with a reference to the new workflow
2. Existing tasks will be migrated to GitHub Issues
3. New tasks should be created as GitHub Issues, not in TASKS.md
4. The Task Workflow sections in TASKS.md will be preserved for reference

## GitHub Issues Best Practices

1. **Keep issues atomic**: Each issue should represent a single, cohesive task
2. **Write clear specifications**: Include detailed test specifications in each issue
3. **Link related issues**: Use GitHub's reference syntax to link related issues
4. **Update status promptly**: Keep the status labels current to reflect actual progress
5. **Provide context**: Include enough information for anyone to understand the task

---

This workflow is designed to support our test-driven development approach while leveraging GitHub's collaboration features. The goal is to maintain our disciplined development process while reducing overhead and improving visibility.
