# GitHub Issues Workflow

This document outlines the workflow for using GitHub Issues to track and manage tasks in the IMAP MCP project.

## Overview

GitHub Issues provides an integrated task management system that:
- Tracks tasks with priority and status labels
- Links issues to commits and pull requests
- Automates status transitions
- Enables collaboration through comments
- Provides reporting and visualization options

## Issue Structure

Each GitHub Issue contains:
1. **Title**: Brief description prefixed with "Task #X" when migrated from TASKS.md
2. **Description**: Detailed requirements and implementation notes
3. **Labels**: Priority and status indicators
4. **Comments**: Progress updates and discussion
5. **Links**: Related issues, commits, and PRs

## Issue Labels

Issues use two types of labels:
1. **Priority Labels**: `priority:X` where X is a number (lower is higher priority)
2. **Status Labels**: `status:X` where X is one of:
   - `prioritized`: Task is defined and prioritized but not started
   - `in-progress`: Work has begun on the task
   - `completed`: Implementation is finished and passes tests
   - `reviewed`: Task has been reviewed by another contributor
   - `archived`: Task has been completed and archived

## Workflow for AI Assistants (like Claude)

When assigned a task from GitHub Issues, AI assistants should follow this workflow:

1. **Issue Analysis**:
   ```bash
   # View issue details
   gh issue view ISSUE_NUMBER
   ```
   - Understand the requirements
   - Note the priority and status
   - Check for any blockers or dependencies

2. **Starting Work**:
   ```bash
   # Create a branch referencing the issue
   git checkout -b feature/issue-ISSUE_NUMBER-short-description
   
   # Make initial commit
   git commit -m "refs #ISSUE_NUMBER: Begin implementation"
   ```

3. **Test-Driven Development**:
   - Write tests first
   - Implement the feature
   - Refactor while maintaining test coverage
   ```bash
   # Run tests with coverage
   uv run pytest --cov=imap_mcp
   ```

4. **Progress Updates**:
   ```bash
   # Make commits that reference the issue
   git commit -m "implements #ISSUE_NUMBER: Add feature X"
   
   # Push changes
   git push origin feature/issue-ISSUE_NUMBER-short-description
   ```

5. **Completing the Task**:
   ```bash
   # Create a pull request
   gh pr create --title "Implement Feature" --body "Closes #ISSUE_NUMBER"
   ```

6. **Documentation**:
   - Update relevant documentation
   - Add code comments and docstrings

## Issue Helper Script

For simplified issue management, the project includes a helper script that automates common tasks and ensures consistent workflows:

```bash
python scripts/issue_helper.py [command] [arguments]
```

### Key Commands

- **Start Work**: Creates a branch, makes an initial commit, and updates status
  ```bash
  python scripts/issue_helper.py start 42
  ```

- **Complete Issue**: Creates a PR that closes the issue when merged
  ```bash
  python scripts/issue_helper.py complete 42
  ```

- **Check Status**: View current status, activity, and related PRs
  ```bash
  python scripts/issue_helper.py check 42
  ```

- **Update Status**: Manually update issue status (fallback option)
  ```bash
  python scripts/issue_helper.py update 42 completed
  ```

### Integration with Automated Workflow

The helper script complements the automated GitHub Actions workflow by:

1. **Ensuring consistent formats** for branch names, commit messages, and PR titles
2. **Providing guidance** on next steps at each stage of the workflow
3. **Adding safeguards** to prevent workflow errors (branch naming, status transitions)
4. **Serving as fallback** when automated status updates don't trigger correctly

For detailed usage instructions, see [ISSUE_HELPER_USAGE.md](./ISSUE_HELPER_USAGE.md).

## Automated Status Updates

The repository includes a GitHub Actions workflow that automatically updates issue statuses based on git activity and pull request events. This ensures that issue status labels are kept up-to-date throughout the development process.

### CLI-Based Issue Management

The issue management system uses GitHub CLI (`gh`) commands directly, which provides several advantages:

1. **Local Authentication**: Leverages your existing GitHub authentication on the command line
2. **No API Keys Required**: No need to manage separate API credentials 
3. **Consistent Experience**: Same commands work locally and in GitHub Actions
4. **Autonomous Development Support**: AI assistants can use the same CLI tools as human developers

### Using Issue Management Locally

To use the issue management scripts locally:

```bash
# Update status for a specific issue
python scripts/issue_status_updater.py --owner <repo-owner> --repo <repo-name> --issue <issue-number>

# Start work on an issue (creates branch, updates status)
python scripts/issue_helper.py start <issue-number>

# Complete an issue (creates PR, links issue)
python scripts/issue_helper.py complete <issue-number>

# Check current status of an issue
python scripts/issue_helper.py check <issue-number>
```

### Status Transition Rules

The automated system enforces the following status transitions:

1. `prioritized` → `in-progress`
   - Triggered when a commit references an issue with keywords like "refs #X" or "implements #X"
   
2. `in-progress` → `in-review`
   - Triggered when a pull request that references the issue is opened or reopened

3. `in-review` → `completed` 
   - Triggered when a pull request that references the issue with keywords like "fixes #X" or "closes #X" is merged

4. Reversion to previous status
   - If a pull request is closed without merging, the issue status will revert to its previous state (usually `in-progress`)

### Commit Message Conventions

To trigger the automated status updates, use these prefixes in commit messages:

- `refs #X`: References the issue without changing status if already in progress
- `implements #X`: Explicitly indicates implementation progress (changes status to in-progress)
- `fixes #X`: Indicates the issue is fixed (will change to completed when PR is merged)
- `closes #X`: Same as fixes (will close the issue when PR is merged)

Examples:
```
git commit -m "refs #42: Start implementing user authentication"
git commit -m "implements #42: Add login form and validation"
git commit -m "fixes #42: Fix password reset functionality"
```

### Pull Request Conventions

For automatic status tracking, include issue references in your pull request:

1. Include issue numbers in the PR title or description using the `#X` format
2. To auto-close issues when the PR is merged, use one of these phrases in the PR description:
   - `Fixes #X`
   - `Closes #X` 
   - `Resolves #X`

### Manual Status Updates

For special cases where the automated updates don't apply, you can manually update the status:

1. Using GitHub's web interface:
   - Go to the issue page
   - Click on the status label in the right sidebar
   - Select the new status label

2. Using the GitHub CLI:
   ```
   gh issue edit 42 --add-label "status:in-review" --remove-label "status:in-progress"
   ```

### Testing the Workflow

To test the automated status updates:

1. Create a test issue: `gh issue create --title "Test automated status updates" --body "Testing workflow" --label "status:prioritized"`
2. Make a commit referencing the issue: `git commit -m "refs #X: Test commit" --allow-empty`
3. Push the commit: `git push origin main`
4. Create a PR referencing the issue: `gh pr create --title "Test PR for #X" --body "Testing PR workflow"`
5. Merge the PR to test the completed status transition

You can view the workflow runs in the GitHub Actions tab to verify proper execution.

## Issue Status Tracking

The system automatically tracks and updates issue statuses based on repository activity:

1. When commits reference an issue with "refs #X" or "implements #X", the status is updated to "in-progress"
2. When a PR with "fixes #X" or "closes #X" is merged, the status is updated to "completed"
3. When an issue is completed, priorities of remaining issues are automatically adjusted

For more details on the automated status updates, see [Issue Status Automation](ISSUE_STATUS_AUTOMATION.md).

## Best Practices

1. **Always reference issues in commits and PRs** using the # syntax
2. **Create branches that reference issue numbers** for clear association
3. **Use the automated status system** rather than manually changing labels
4. **Keep descriptions updated** with implementation details
5. **Close issues via PRs** using keywords like "Closes #X" in the PR description
6. **Maintain sequential priority numbers** starting from 1 (highest priority)

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
