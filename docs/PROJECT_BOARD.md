# GitHub Project Board Guide

This document provides information on the IMAP MCP GitHub Project Board setup, configuration, and usage.

## Project Board Overview

The IMAP MCP project uses GitHub Projects to track and visualize the status of tasks. The project board can be accessed at:
[IMAP MCP Project Board](https://github.com/users/non-dirty/projects/X) (replace X with actual project number)

## Board Structure

The project board has the following columns:

1. **Backlog**: All newly created issues that have not been prioritized
2. **Prioritized**: Issues that have been assigned a priority but work has not started
3. **In Progress**: Issues that are currently being worked on
4. **In Review**: Issues with pull requests that are awaiting review
5. **Completed**: Issues that have been successfully completed
6. **Archived**: Issues that are no longer relevant or have been superseded

## Automation Rules

The board has the following automation rules:

- New issues are automatically added to the "Backlog" column
- Issues with "status:prioritized" label move to "Prioritized" column
- Issues with "status:in-progress" label move to "In Progress" column
- Issues with open pull requests move to "In Review" column
- Closed issues with "status:completed" label move to "Completed" column
- Issues with "status:archived" label move to "Archived" column

## Custom Fields

The board includes these custom fields to help with task management:

- **Priority**: Synced with priority labels from issues (priority:1, priority:2, etc.)
- **Estimated Effort**: Low, Medium, High
- **Dependencies**: Links to other issues that this issue depends on

## Working with the Project Board

### Viewing Issues

- Visit the project board URL to see all issues organized by status
- Use filters to show only issues with specific labels, assignees, or other criteria
- Click on an issue to view its details

### Updating Issue Status

The recommended way to update issue status is through commit messages and PR actions:

1. When starting work:
   - Create a branch referencing the issue number
   - Make a commit with "refs #X" in the message
   - This will automatically add the "status:in-progress" label

2. When submitting for review:
   - Create a PR referencing the issue
   - This will automatically move the issue to "In Review"

3. When completing work:
   - Merge the PR with a commit message containing "closes #X" or "fixes #X"
   - This will automatically close the issue and add the "status:completed" label

### Manual Status Updates

If needed, you can manually update an issue's status by:

1. Adding/changing the appropriate status label:
   ```bash
   gh issue edit <ISSUE_NUMBER> --add-label "status:in-progress" --remove-label "status:prioritized"
   ```

2. Dragging the issue card to the appropriate column in the project board view

## Best Practices

1. **Link Related Issues**: Use the "Depends on: #X, #Y" syntax in issue descriptions to establish dependencies
2. **Update Progress**: Add comments to issues to provide status updates
3. **Use Filters**: Utilize filters to focus on specific aspects of the project
4. **Check the Board**: Review the project board regularly to stay up-to-date on project status

## Troubleshooting

If you encounter issues with the project board:

1. Verify the issue has the correct labels
2. Check the automation rules are properly configured
3. Try manually moving the issue to the correct column
4. Contact the repository maintainer if issues persist

---

This document will be updated as the project board evolves.
