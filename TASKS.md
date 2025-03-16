# IMAP MCP Server Implementation Tasks

This document outlines the detailed tasks required to complete and enhance the IMAP MCP Server implementation using a test-driven development (TDD) approach. Tasks are sequenced for incremental progress with maximum chance of success.

## IMPORTANT: Task Management Has Moved to GitHub Issues

> **Note**: Task management has been moved from this file to GitHub Issues. 
> This file is kept for historical reference only. All new tasks should be created and managed as GitHub Issues.

### Viewing Tasks in GitHub Issues

```bash
# View all open issues
gh issue list

# View specific issue details
gh issue view 1

# Filter issues by label
gh issue list --label "priority:1"
gh issue list --label "status:in-progress"

# Search issues by text
gh issue list --search "OAuth"
```

### Creating New Tasks

```bash
# Create a new task interactively (recommended)
gh issue create

# Create a new task with specific details
gh issue create --title "Task Title" --body "Description" --label "priority:X" --label "status:prioritized"
```

### Working with Tasks

When starting work on a task:
```bash
# Create a branch referencing the issue
git checkout -b feature/issue-X-short-description

# Make commits that reference the issue
git commit -m "refs #X: Description of changes"

# Create a PR that will close the issue when merged
gh pr create --title "Implement Feature" --body "Closes #X"
```

The automated status tracking system will:
- Update issue status based on commits and PRs
- Adjust priorities when tasks are completed
- Add comments about task progress

For detailed guidance, refer to:
- [GitHub Issues Workflow](docs/GITHUB_ISSUES_WORKFLOW.md)
- [Issue Status Automation](docs/ISSUE_STATUS_AUTOMATION.md)
- [Commit Conventions](docs/COMMIT_CONVENTIONS.md)

---

## Task Workflow for Claude

When working on a task from this list, follow these steps:

1. **Task Analysis**:
   - First, carefully read and understand the task requirements
   - Determine if the task needs to be broken down into smaller subtasks
   - If needed, update TASKS.md with the subtask breakdown

2. **Task Status Update**:
   - Update the task's status in the Task Tracker table to "started"

3. **Test-Driven Development**:
   - Write test specifications first before implementation
   - Create failing tests that verify the desired functionality
   - Implement the feature until all tests pass
   - Refactor the code while ensuring tests continue to pass
   - Run the full test suite to check for regressions
   - Run test coverage to check for code coverage of at least 90%
   - Write new tests to increase code coverage to at least 90%
   - Run the full test suite to check for regressions
   - Run test coverage to check for code coverage of at least 90%

4. **Documentation**:
   - Update docstrings and comments in the implementation
   - Add or update README.md as appropriate
   - Add or update INSTALLATION.md as appropriate
   - Add or update CLAUDE.md as appropriate
   
5. **Task Completion**:
   - Change the task's status to "completed" in the Task Tracker
   - Move the task details from TASKS.md to TASKS_COMPLETED.md
   - Add a detailed summary of what was accomplished under the task in TASKS_COMPLETED.md
   - Do NOT renumber the tasks in TASKS.md - maintain their original numbers
   - Clean up the TASKS.md by removing completed tasks


6. **Priority Reassessment**:
   - After completing a task, reassess priorities for remaining tasks
   - Update the priority numbers in the Task Tracker as appropriate to ensure at least one remaining task has priority 1
   - Priorities should be sequential starting from 1, but gaps are allowed to minimize updates to the TASKS.md file

7. **Commit Changes**:
   - Create a git commit with a descriptive message
   - Include the task number and name in the commit message
   - Push the changes to GitHub



## GitHub Issues Transition


### GitHub Issues Transition Workflow

The project is transitioning from using TASKS.md to GitHub Issues for task tracking. During the transition period, both systems will be used in parallel, with the following guidelines:

#### Current Status

* All existing tasks have been migrated to GitHub Issues
* New tasks should be created as GitHub Issues
* TASKS.md will be maintained until the transition is complete
* Code coverage tasks for modules below 90.0% have been created with high priority

#### Using GitHub Issues

1. **Viewing Tasks**: Visit the [Issues page](https://github.com/your-github-username/imap-mcp/issues) to see all open tasks
2. **Task Priority**: Priority is indicated by the `priority:X` label
3. **Task Status**: Status is shown with the `status:X` label
4. **Starting a Task**: Assign the issue to yourself and move it to "In Progress" in the project board
5. **Completing a Task**: Close the issue when the task is done (PR merged)

#### Final Transition

A task has been created to complete the transition by:
1. Updating TASKS.md to keep methodology sections but removing task listings
2. Documenting GitHub Issues workflow in a new WORKFLOW.md file
3. Updating all related documentation to reference GitHub Issues

This transition will improve collaboration, automation, and integration with development activities.



## Task Status Definitions

Tasks in the Task Tracker can have the following statuses:

- **proposed**: Initial idea for a task, not yet fully defined
- **defined**: Task has been specified but not yet prioritized
- **prioritized**: Task has been assigned a priority number
- **started**: Work on the task has begun
- **completed**: Implementation is finished and passes all tests
- **reviewed**: Task has been reviewed by another contributor
- **archived**: Task has been moved to TASKS_COMPLETED.md

## Test-Driven Development Approach

For each task:

1. **Write test specifications first** - Define what successful implementation looks like
2. **Create failing tests** - Implement tests that verify the desired functionality (which often fail initially)
3. **Implement the feature** - Write code until all tests pass
4. **Refactor** - Clean up the implementation without breaking tests
5. **Verify** - Run all existing tests (with coverage report) to ensure no regression, fix broken tests
6. **Test Coverage** - Check for code coverage of at least 90%
7. **Add new tests** - Write new tests to increase code coverage to at least 90%
8. **Run full test suite** - Run all existing tests to ensure no regression
9. **Run test coverage** - Run test coverage to check for code coverage of at least 90%

### Running Tests

```bash
# Run all tests
uv run -m pytest

# Run tests for a specific module (add -v for verbose output)
uv run -m pytest tests/test_module_name.py

# Run tests with coverage report
uv run -m pytest --cov=imap_mcp

# Run tests in verbose mode
uv run -m pytest -v
```

## Historical Tasks (Pre-GitHub Issues Migration)

### Task Tracker

| Priority | Task # | Status      | Description                                      |
|----------|--------|-------------|--------------------------------------------------|
| 5        | 21     | prioritized | Implement Gmail OAuth2 Authentication Flow       |
| 3        | 22     | prioritized | Implement Secure Token Storage                   |
| 4        | 23     | prioritized | Test Basic IMAP Folder Listing with OAuth2       |
| 10       | 11     | prioritized | Implement Email Processing Workflow - States     |
| 11       | 12     | prioritized | Implement Email Processing Workflow - Actions    |
| 12       | 13     | prioritized | Implement Email Processing Workflow - User       |
| 17       | 18     | prioritized | Create Documentation Base                        |
| 18       | 19     | prioritized | Create Integration Tests with Real Account       |
| 19       | 25     | prioritized | Fix Virtual Environment Duplication Issue        |
| 1        | 24     | completed   | Transition to Git Issues from tasks.md           |
| 2        | 26     | completed   | Implement Automated Task Status Updates          |

### Process Improvement Tasks

#### 24. Transition to Git Issues from tasks.md

**Task Name**: Integrate Git issues (needs rewrite and breakdown)

**Description**:
Leverage Git issues to manage tasks lifecycle currently managed by TASKS.md, keep TASKS.md for until the transition is complete:
- create issues in the Git repository from tasks in TASKS.md
- update TASKS.md with the new workflow for using Git issues in addition to TASKS.md and TASKS_COMPLETED.md (parallel usage phase of the transition)
- run the code coverage and make a task in github issues to improve the code coverage for each module that is less than 90% coverage
- write a new task to finish the transition and sunset the tasks.md file (just the task list and priority sections, keeping the methodology and process sections)
- prioritize the new test code coverage tasks as the highest priority and set the priority of the finish transition task to 10

**Test Specifications**:
1. Test task extraction from TASKS.md
   - Test parsing of task table
   - Test extraction of detailed task descriptions
   - Test sorting by priority
2. Test GitHub issue creation
   - Test creation of issues with appropriate metadata
   - Test handling of task details as issue body
   - Test label creation for priority and status
3. Test code coverage reporting
   - Test identification of modules below threshold
   - Test generation of coverage improvement tasks
4. Test workflow documentation updates
   - Test updating TASKS.md with transition information
   - Test parallel workflow documentation

**Implementation Steps**:
1. Create a tasks_to_issues.py script with:
   - TaskParser class to extract tasks from TASKS.md
   - GitHubIssueCreator class to create GitHub issues
   - CoverageReporter class to generate coverage tasks
   - WorkflowUpdater class to update documentation
2. Create test_tasks_to_issues.py for TDD verification
3. Create GitHub workflow to run the migration script
4. Create GITHUB_ISSUES_WORKFLOW.md to document the new process
5. Update TASKS.md with the transition plan
6. Run the migration script to create initial issues
7. Create PR template linking commits to issues
8. Document the new workflow for the team

**Expected Outcome**:
- All existing tasks migrated to GitHub Issues
- TASKS.md updated with transition information
- GitHub Project board set up with automated workflows
- Coverage tasks created for modules below threshold
- Clear documentation of the new workflow
- PR template and commit message conventions established

#### 26. Implement Automated Task Status Updates

**Task Name**: Create automated task status tracking

**Description**:
Develop a Git hook or workflow tool that automatically updates task statuses based on git activity:
- Detect when work on a task begins (first commit related to a task) and update status to "started"
- Monitor test coverage and execution to help determine when a task is "completed"
- Automate the movement of completed tasks to TASKS_COMPLETED.md
- Update priority numbers automatically when tasks are completed

This would reduce manual maintenance of the task tracker and ensure it stays up-to-date.

#### 27. Set Up GitHub Project Board

**Task Name**: Create and configure GitHub Project board

**Description**:
Set up a GitHub Project board to visualize and manage tasks:
- Create a project board with appropriate columns (Backlog, To Do, In Progress, Review, Done)
- Configure automated workflows in the project board
- Link existing issues to the project board
- Set up custom fields for priority, status, and effort estimation
- Document the project board usage in the GitHub Issues workflow

This provides visual task management and leverages GitHub's built-in automation features.

#### 28. Create Issue Templates

**Task Name**: Implement standardized GitHub issue templates

**Description**:
Create templates for different types of issues to ensure consistent information:
- Create a feature task template with sections for test specifications, implementation steps, and expected outcome
- Create a bug template with reproduction steps, expected vs. actual behavior
- Create a documentation task template
- Create a test improvement template for test coverage tasks
- Add appropriate labels to be automatically applied to each template type

This standardizes task creation and ensures all necessary information is captured.

#### 29. Implement GitHub Actions for Task Automation

**Task Name**: Set up GitHub Actions workflows for task automation

**Description**:
Create GitHub Actions workflows to automate task management:
- Set up workflow to automatically label and categorize new issues
- Create workflow to update issue status based on PR activity
- Implement workflow to generate and assign test coverage tasks
- Create workflow to notify on stale issues or PRs
- Document the GitHub Actions workflows and triggers

This provides automation beyond what's available in GitHub Projects natively.

#### 30. Implement Task Dependency Visualization

**Task Name**: Create task dependency visualization and management

**Description**:
Build a tool to visualize and manage dependencies between tasks:
- Create a graph visualization of task dependencies
- Allow tagging issues as blockers or dependencies
- Implement a tool to ensure tasks aren't worked on before their dependencies
- Add an automated check for circular dependencies
- Generate reports on the critical path of dependencies

This helps prioritize work and prevents working on tasks that have unfinished dependencies.

#### 31. Implement AI-Assisted Task Prioritization

**Task Name**: Create AI-driven task priority optimization

**Description**:
Develop a system for AI to analyze and suggest task priorities:
- Create a GitHub Action to periodically analyze open issues
- Implement logic to suggest priority changes based on dependencies and project goals
- Set up notification system for priority change suggestions
- Allow for manual approval of AI-suggested priorities
- Track metrics on how priority adjustments impact project velocity

This leverages AI to optimize the development process and ensure work is done in the most efficient order.

#### 32. Implement Commit-Issue Linking System

**Task Name**: Create system for linking commits to issues

**Description**:
Establish a standardized system for connecting code changes to tasks:
- Document keyword patterns for referencing issues in commits and PRs
- Create GitHub Action to validate commit messages for proper issue references
- Set up automated status updates based on commit references
- Implement PR template with issue reference section
- Create dashboard for tracking issue-to-code traceability

This connects code changes directly to tasks and automates status tracking.

### 20. Set up Google Cloud Project for OAuth2

**Task Name**: Set up Google Cloud Project for Gmail OAuth2

**Status**: Completed - See TASKS_COMPLETED.md for details

### 21. Implement Gmail OAuth2 Authentication Flow

**Task Name**: Implement browser-based Gmail OAuth2 Authentication Flow

**Test Specifications**:
- Test authentication flow initialization
- Test authorization URL generation
- Test token exchange process
- Test refresh token handling
- Test integration with IMAP client authentication

**Implementation Steps**:
1. Create `oauth2_flow.py` with functions for:
   - Generating authorization URLs
   - Starting a local server for the redirect URI
   - Exchanging authorization codes for tokens
   - Handling token refresh
2. Implement a browser-based authentication flow that:
   - Opens the user's browser to the Google authorization URL
   - Captures the authorization code via redirect
   - Exchanges the code for access and refresh tokens
3. Modify the IMAP client to use OAuth2 tokens for Gmail servers
4. Create a command-line tool for initial authentication

**TDD Process**:
1. Create test_oauth2_flow.py with test cases
2. Run to verify tests fail initially
3. Implement OAuth2 flow functions
4. Run tests again to verify implementation

### 22. Implement Secure Token Storage

**Task Name**: Implement secure storage for OAuth2 tokens

**Test Specifications**:
- Test token encryption/decryption
- Test token persistence
- Test token retrieval
- Test automatic token refresh

**Implementation Steps**:
1. Create a secure storage class for OAuth2 tokens
2. Implement encryption for sensitive token data
3. Create functions to store and retrieve tokens
4. Implement automatic token refresh when tokens expire
5. Ensure tokens are stored per user account

**TDD Process**:
1. Create test_token_storage.py with test cases
2. Run tests to verify they fail initially
3. Implement token storage functionality
4. Run tests again to verify implementation

### 23. Test Basic IMAP Folder Listing with OAuth2

**Task Name**: Implement and test basic IMAP folder listing with OAuth2

**Test Specifications**:
- Test IMAP connection with OAuth2 authentication
- Test folder listing functionality
- Test error handling for authentication failures

**Implementation Steps**:
1. Create a test script that:
   - Authenticates with OAuth2
   - Connects to Gmail's IMAP server
   - Lists folders/mailboxes
   - Handles errors appropriately
2. Add documentation for the OAuth2 process
3. Create integration tests for the entire flow

**TDD Process**:
1. Create test_gmail_integration.py
2. Run tests to verify they fail initially
3. Implement the integration functionality
4. Run tests with valid credentials to verify implementation

### 18. Create Documentation Base

**Task Name**: Set up documentation framework

**Test Specifications**:
- Test documentation build
- Test documentation structure
- Test API documentation generation
- Test example code in documentation
- Test documentation completeness

**Implementation Steps**:
```
1. Set up Sphinx documentation framework
2. Create basic documentation structure
3. Configure API documentation generation
4. Add example code that can be tested
5. Create documentation tests to verify functionality
```

**TDD Process**:
1. Create tests/test_documentation.py to verify examples work
2. Set up the documentation framework
3. Run tests to ensure documentation examples function correctly
4. Build documentation and verify completeness

### 19. Create Integration Tests with Real Account

**Task Name**: Implement real-world integration tests

**Test Specifications**:
- Test connection to real IMAP servers
- Test end-to-end email operations
- Test learning with real emails
- Test workflow with real emails
- Test multi-account with real accounts

**Implementation Steps**:
```
1. Create tests/integration/test_real_imap.py with configurable tests
2. Implement skip mechanisms when credentials aren't available
3. Create a safe testing environment that won't affect real emails
4. Implement comprehensive real-world scenarios
```

**TDD Process**:
1. Run `pytest tests/integration/test_real_imap.py -v --skip-real` initially to skip tests
2. Provide test credentials and run without the skip flag
3. Fix issues found during real-world testing
4. Ensure all previous tests still pass

### 25. Fix Virtual Environment Duplication Issue

**Task Name**: Investigate and fix package duplication in virtual environments

**Problem Description**:
The project currently experiences issues with duplicate package installations in the virtual environment, where some dependencies have duplicated folder names with ' 2' suffix (e.g., 'annotated_types-0.7.0 2.dist-info'). This causes errors when running the application with commands like `uv run`.

**Test Specifications**:
- Test virtual environment creation process
- Test dependency installation with both pip and uv
- Test package metadata integrity
- Test for duplicate installations
- Test application startup after environment setup

**Implementation Steps**:
```
1. Create a script to analyze and report on duplicated packages in virtual environments
2. Research causes of package duplication when using uv
3. Implement fixes in package management workflow
4. Create a clean installation script that prevents duplication
5. Add verification steps to CI/CD pipeline
```

**Research Areas**:
1. Investigate uv's package installation mechanics
2. Research potential conflicts between pip and uv
3. Examine any file copy operations during package installation
4. Review naming and versioning handling in the virtual environment
5. Check for race conditions in concurrent installations

**Expected Outcome**:
A reliable virtual environment setup process that doesn't create duplicate packages, allowing the application to run without metadata parsing errors.
