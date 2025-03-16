# GitHub Issue Status Automation

This document describes the automated issue status tracking system implemented for the IMAP-MCP project.

## Overview

The Issue Status Updater automatically monitors repository activity and updates GitHub issue statuses based on:
- Commit messages referencing issues
- Pull request activity
- Test execution results

The system reduces manual maintenance of task tracking and ensures the task board stays up-to-date.

## How It Works

### Status Lifecycle

Issues automatically transition through these statuses:

1. `prioritized` - Initial state when an issue is created and prioritized
2. `in-progress` - Activated when a commit references the issue
3. `completed` - Set when a PR fixing the issue is merged and tests pass
4. `reviewed` - Set when a reviewer approves the changes (currently manual)
5. `archived` - Set when the issue is closed (currently manual)

### Automatic Priority Management

When an issue is completed, the system automatically adjusts the priorities of remaining tasks:

1. The system identifies the priority number of the completed task
2. All tasks with lower priority (higher priority numbers) have their priority numbers decreased by 1
3. Notification comments are added to affected issues, explaining the priority change

This ensures that:
- Priority numbers are always consecutive
- The highest priority task is always priority #1
- There are no gaps in the priority numbering sequence

### Commit Message Format

The system recognizes these commit message formats:

```
<action> #<issue-number>: <description>
```

Where `<action>` can be:
- `fixes` - Indicates this commit fixes the issue
- `closes` - Same as fixes, but with higher precedence
- `resolves` - Same as fixes
- `implements` - Indicates this commit implements functionality for the issue
- `refs` - References the issue but doesn't resolve it

Examples:
```
fixes #42: Fix authentication bug
implements #100: Add OAuth flow
refs #5, #8: Update documentation
```

### GitHub Actions Integration

The system is integrated with GitHub Actions, which automatically runs on:
- New commits to main/master branches
- Pull request activity (opened, closed, synchronized)
- Manual trigger with specified issue number

## Usage

### Automatic Updates

No user action is required for automatic status updates. The system will:
1. Detect when work on an issue begins (first commit related to a task)
2. Monitor test coverage and execution to help determine completion
3. Add status update comments to issues with relevant information

### Manual Triggers

You can manually trigger status updates for specific issues:

1. Go to the Actions tab in GitHub
2. Select "Issue Status Updater" workflow
3. Click "Run workflow"
4. Enter the issue number to update
5. Click "Run workflow"

### Configuration

Environment variables:
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `GITHUB_OWNER`: Repository owner (set automatically in workflow)
- `GITHUB_REPO`: Repository name (set automatically in workflow)

## Extending the System

The status updater is designed to be modular and extensible:

1. `CommitAnalyzer`: Analyzes git commits for issue references
2. `PullRequestAnalyzer`: Analyzes pull requests for issue references
3. `TestResultsAnalyzer`: Analyzes test results for issue-related code
4. `IssueUpdater`: Updates GitHub issue statuses and adds comments

To add new functionality:
1. Add new methods to the appropriate class
2. Write tests for the new functionality
3. Update the documentation

## Testing

Run the tests with:

```bash
uv run -m pytest tests/test_issue_status_updater.py -v
```

## Troubleshooting

If status updates aren't working as expected:

1. Check commit message format - ensure it follows the conventions
2. Verify GitHub Actions is running - check the Actions tab for workflow runs
3. Check for error messages in the workflow logs
4. Ensure tests are passing - failed tests will prevent "completed" status
