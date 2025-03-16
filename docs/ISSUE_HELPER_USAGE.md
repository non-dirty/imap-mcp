# Issue Helper Script

This document describes how to use the `issue_helper.py` script for managing GitHub issues efficiently.

## Overview

The Issue Helper script simplifies common GitHub issue management tasks, making it easier for AI agents and human developers to work with issues consistently. It standardizes issue workflows and reduces the number of commands needed for routine operations.

## Installation

The script is located in the `scripts` directory and requires Python 3.6+:

```bash
# Make the script executable
chmod +x scripts/issue_helper.py

# Run with Python
python scripts/issue_helper.py [command] [arguments]
```

## Commands

### Start Work on an Issue

```bash
python scripts/issue_helper.py start [issue_number]
```

This command:
1. Creates a new branch named `feature/issue-[number]-[title]`
2. Makes an initial commit that references the issue
3. Pushes the branch to GitHub
4. Updates the issue status to "in-progress"

Example:
```bash
python scripts/issue_helper.py start 42
```

### Complete an Issue with a PR

```bash
python scripts/issue_helper.py complete [issue_number] [--branch branch_name]
```

This command:
1. Creates a pull request that references the issue
2. Uses "Closes #[number]" in the PR body to trigger automatic status updates
3. Sets the PR title based on the issue title

Example:
```bash
python scripts/issue_helper.py complete 42
```

### Update Issue Status Manually

```bash
python scripts/issue_helper.py update [issue_number] [status]
```

Where `[status]` is one of:
- `prioritized`
- `in-progress`
- `completed`
- `reviewed`
- `archived`

Example:
```bash
python scripts/issue_helper.py update 42 completed
```

### Force Status Update for Testing

```bash
python scripts/issue_helper.py test [issue_number] [status]
```

This command is specifically for testing the status workflow:
1. Updates the issue status
2. Adds a comment explaining the forced update
3. Documents how the status would normally be triggered

Example:
```bash
python scripts/issue_helper.py test 42 in-progress
```

### Check Issue Status

```bash
python scripts/issue_helper.py check [issue_number]
```

This command displays comprehensive information about an issue:
1. Basic details (title, URL)
2. Current status and priority
3. Recent commit activity related to the issue
4. Associated pull requests

Example:
```bash
python scripts/issue_helper.py check 42
```

Output:
```
Issue #42: Implement Feature X
URL: https://github.com/username/repo/issues/42
Status: in-progress
Priority: 2

Recent activity:
Commits:
  a1b2c3d refs #42 Start implementing Feature X
  e4f5g6h implements #42 Add core functionality

Pull Requests:
  #15 Implement Feature X (open)
```

## Integration with Automated Workflow

The Issue Helper script complements the automated GitHub Actions workflow:

1. **Normal operation**: Let the GitHub Actions workflow handle status updates automatically based on commit messages and PRs
2. **Manual intervention**: Use the script when you need to manually update statuses or troubleshoot the workflow
3. **Testing**: Use the `test` command to verify status transitions without waiting for GitHub Actions

## Best Practices

1. **Always use the `start` command** when beginning work on a new issue to ensure consistent branch naming and initial commit messages
2. **Use the standard commit message format** even when using the helper script:
   - `refs #N` - For general work on an issue
   - `implements #N` - For implementing a feature
   - `fixes #N` - For fixing a bug
   - `closes #N` - For completing an issue
3. **Include meaningful commit messages** beyond just the issue reference

## Troubleshooting

If you encounter issues with the script:

1. Check that you have the GitHub CLI (`gh`) installed and authenticated
2. Ensure you're running the script from the root directory of the repository
3. Verify that your repository has the expected label structure (status:prioritized, status:in-progress, etc.)

## Contributing

To extend the Issue Helper:

1. Add new functionality to the script
2. Update this documentation with new commands and examples
3. Add tests for the new functionality
