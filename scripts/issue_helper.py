#!/usr/bin/env python
"""
GitHub Issue Helper Script.

This script provides simplified commands for common issue management tasks.
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional, Tuple

def run_command(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, and stderr.
    
    Args:
        cmd: Command to run as a list of strings
        check: If True, raise an exception on non-zero exit code
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        proc = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Exit code: {e.returncode}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(e.returncode)
        return e.returncode, e.stdout, e.stderr

def update_issue_status(issue_number: int, status: str) -> None:
    """
    Update an issue's status label.
    
    Args:
        issue_number: GitHub issue number
        status: New status (prioritized, in-progress, completed, reviewed, archived)
    """
    # Get current labels
    cmd = ['gh', 'issue', 'view', str(issue_number), '--json', 'labels']
    _, stdout, _ = run_command(cmd)
    
    import json
    labels_data = json.loads(stdout)
    
    # Find and remove any existing status label
    status_labels = [label for label in labels_data.get('labels', []) 
                    if label.get('name', '').startswith('status:')]
    
    for label in status_labels:
        run_command(['gh', 'issue', 'edit', str(issue_number), 
                    '--remove-label', label.get('name')])
    
    # Add the new status label
    run_command(['gh', 'issue', 'edit', str(issue_number), 
                '--add-label', f'status:{status}'])
    
    print(f"Updated issue #{issue_number} status to '{status}'")

def get_issue_status(issue_number: int) -> str:
    """
    Get the current status of an issue.
    
    Args:
        issue_number: GitHub issue number
        
    Returns:
        Current status without the 'status:' prefix or empty string if not found
    """
    cmd = ['gh', 'issue', 'view', str(issue_number), '--json', 'labels']
    _, stdout, _ = run_command(cmd)
    
    import json
    labels_data = json.loads(stdout)
    
    for label in labels_data.get('labels', []):
        name = label.get('name', '')
        if name.startswith('status:'):
            return name.replace('status:', '')
    
    return ""

def check_issue_status(issue_number: int) -> None:
    """
    Check and display the current status of an issue.
    
    Args:
        issue_number: GitHub issue number
    """
    # Get issue details
    cmd = ['gh', 'issue', 'view', str(issue_number), '--json', 'title,url,labels']
    _, stdout, _ = run_command(cmd)
    
    import json
    issue_data = json.loads(stdout)
    
    # Extract status and priority
    status = ""
    priority = ""
    for label in issue_data.get('labels', []):
        name = label.get('name', '')
        if name.startswith('status:'):
            status = name.replace('status:', '')
        elif name.startswith('priority:'):
            priority = name.replace('priority:', '')
    
    # Display information
    title = issue_data.get('title', 'Unknown')
    url = issue_data.get('url', '')
    
    print(f"Issue #{issue_number}: {title}")
    print(f"URL: {url}")
    print(f"Status: {status or 'Not set'}")
    print(f"Priority: {priority or 'Not set'}")
    
    # Get recent commits for this issue
    print("\nRecent activity:")
    cmd = ['git', 'log', '--grep', f"#{issue_number}", '--oneline', '-n', '5']
    exit_code, stdout, _ = run_command(cmd, check=False)
    
    if exit_code == 0 and stdout.strip():
        print("Commits:")
        for line in stdout.strip().split('\n'):
            print(f"  {line}")
    else:
        print("No commit activity found for this issue")
    
    # Check for PRs
    cmd = ['gh', 'pr', 'list', '--search', f"#{issue_number}", '--json', 'number,title,state']
    _, stdout, _ = run_command(cmd)
    
    import json
    prs = json.loads(stdout)
    
    if prs:
        print("\nPull Requests:")
        for pr in prs:
            print(f"  #{pr.get('number')} {pr.get('title')} ({pr.get('state')})")
    else:
        print("No pull requests found for this issue")

def start_work_on_issue(issue_number: int) -> None:
    """
    Start work on an issue by creating a branch and updating status.
    
    Args:
        issue_number: GitHub issue number
    """
    # Check if issue exists and get its status
    current_status = get_issue_status(issue_number)
    if not current_status:
        print(f"Warning: Issue #{issue_number} not found or has no status label")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    elif current_status != 'prioritized':
        print(f"Warning: Issue #{issue_number} has status '{current_status}', not 'prioritized'")
        print(f"It's recommended to only start work on prioritized issues")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Get issue title for branch name
    cmd = ['gh', 'issue', 'view', str(issue_number), '--json', 'title']
    _, stdout, _ = run_command(cmd)
    
    import json
    title_data = json.loads(stdout)
    title = title_data.get('title', '')
    
    # Create a sanitized branch name
    import re
    branch_title = re.sub(r'[^a-zA-Z0-9_-]', '-', title.lower())
    branch_name = f"feature/issue-{issue_number}-{branch_title}"
    if len(branch_name) > 60:  # Keep branch names reasonably sized
        branch_name = branch_name[:60]
    
    # Check if branch already exists
    _, branches, _ = run_command(['git', 'branch', '--list', branch_name], check=False)
    if branches.strip():
        print(f"Branch '{branch_name}' already exists")
        response = input("Do you want to check out this existing branch? (y/n): ")
        if response.lower() == 'y':
            run_command(['git', 'checkout', branch_name])
            print(f"Checked out existing branch: {branch_name}")
            return
        else:
            sys.exit(1)
    
    # Create and checkout branch
    run_command(['git', 'checkout', '-b', branch_name])
    print(f"Created and checked out branch: {branch_name}")
    
    # Make initial commit to reference the issue
    readme_path = 'README.md'
    if os.path.exists(readme_path):
        # Add a small whitespace change to README to create a commit
        with open(readme_path, 'a') as f:
            f.write('\n')
        
        run_command(['git', 'add', readme_path])
        run_command(['git', 'commit', '-m', f"refs #{issue_number} Start implementing {title}"])
        run_command(['git', 'push', '-u', 'origin', branch_name])
        print(f"Made initial commit and pushed branch")
        
        # Show next steps guidance
        print("\nNext steps:")
        print(f"1. Make your changes to implement the issue requirements")
        print(f"2. Commit with appropriate messages:")
        print(f"   - For work in progress: git commit -m \"implements #{issue_number} ...\"")
        print(f"   - For completed work: git commit -m \"fixes #{issue_number} ...\"")
        print(f"3. When ready to create a PR: python scripts/issue_helper.py complete {issue_number}")
    else:
        print(f"Warning: README.md not found, skipping initial commit")
    
    # Update issue status (may be redundant if automation works, but good fallback)
    update_issue_status(issue_number, 'in-progress')

def complete_issue(issue_number: int, branch_name: Optional[str] = None) -> None:
    """
    Create a PR to complete an issue.
    
    Args:
        issue_number: GitHub issue number
        branch_name: Branch name (if None, will use current branch)
    """
    # Check if issue exists and get its status
    current_status = get_issue_status(issue_number)
    if not current_status:
        print(f"Warning: Issue #{issue_number} not found or has no status label")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    elif current_status != 'in-progress':
        print(f"Warning: Issue #{issue_number} has status '{current_status}', not 'in-progress'")
        print(f"It's recommended to only complete issues that are in progress")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Get current branch if not provided
    if branch_name is None:
        _, branch_name, _ = run_command(['git', 'branch', '--show-current'])
        branch_name = branch_name.strip()
    
    # Verify we're on a feature branch
    if not branch_name.startswith('feature/') and not branch_name.startswith('bugfix/'):
        print(f"Warning: Current branch '{branch_name}' doesn't follow the feature/bugfix naming convention")
        print(f"It's recommended to use the 'start' command to create properly named branches")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Check if branch has uncommitted changes
    _, status, _ = run_command(['git', 'status', '--porcelain'])
    if status.strip():
        print("Warning: You have uncommitted changes:")
        print(status)
        response = input("Do you want to commit these changes before creating the PR? (y/n): ")
        if response.lower() == 'y':
            message = input(f"Enter commit message (will be prefixed with 'fixes #{issue_number}'): ")
            run_command(['git', 'add', '.'])
            run_command(['git', 'commit', '-m', f"fixes #{issue_number} {message}"])
            run_command(['git', 'push'])
            print("Changes committed and pushed")
        else:
            print("Continuing with uncommitted changes. They will not be included in the PR.")
    
    # Get issue title for PR title
    cmd = ['gh', 'issue', 'view', str(issue_number), '--json', 'title']
    _, stdout, _ = run_command(cmd)
    
    import json
    title_data = json.loads(stdout)
    title = title_data.get('title', '')
    
    # Create PR
    pr_title = f"Resolves #{issue_number}: {title}"
    pr_body = f"Closes #{issue_number}"
    
    run_command(['gh', 'pr', 'create', 
                '--title', pr_title,
                '--body', pr_body,
                '--base', 'main'])
    
    print(f"Created PR to complete issue #{issue_number}")
    
    # Show next steps guidance
    print("\nNext steps:")
    print("1. Wait for the CI checks to pass")
    print("2. Request a review if needed")
    print("3. Once approved, the PR can be merged")
    print("4. After merging, the issue should automatically transition to 'completed' status")

def force_update_issue_for_testing(issue_number: int, status: str) -> None:
    """
    Force update an issue's status for testing purposes.
    This is to simulate what the GitHub Actions workflow would do.
    
    Args:
        issue_number: GitHub issue number
        status: New status
    """
    update_issue_status(issue_number, status)
    
    # Add a comment explaining the forced update
    comment = f"""
    This issue status was manually updated to '{status}' for testing purposes.
    
    In normal operation, this status change would be triggered by:
    
    - For 'in-progress': A commit with 'refs #{issue_number}' or 'implements #{issue_number}'
    - For 'completed': A PR being merged with 'closes #{issue_number}' or 'fixes #{issue_number}'
    - For 'reviewed': Currently a manual step after completion
    - For 'archived': Currently a manual step after review
    """
    
    run_command(['gh', 'issue', 'comment', str(issue_number), '--body', comment])
    print(f"Added comment explaining the forced status update")

def main():
    parser = argparse.ArgumentParser(description='GitHub Issue Helper')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Start work on issue
    start_parser = subparsers.add_parser('start', help='Start work on an issue')
    start_parser.add_argument('issue', type=int, help='Issue number')
    
    # Complete issue
    complete_parser = subparsers.add_parser('complete', help='Complete an issue by creating a PR')
    complete_parser.add_argument('issue', type=int, help='Issue number')
    complete_parser.add_argument('--branch', help='Branch name (defaults to current branch)')
    
    # Update issue status
    update_parser = subparsers.add_parser('update', help='Update an issue status')
    update_parser.add_argument('issue', type=int, help='Issue number')
    update_parser.add_argument('status', choices=['prioritized', 'in-progress', 'completed', 'reviewed', 'archived'],
                               help='New status')
    
    # Force update for testing
    test_parser = subparsers.add_parser('test', help='Force update issue status for testing')
    test_parser.add_argument('issue', type=int, help='Issue number')
    test_parser.add_argument('status', choices=['prioritized', 'in-progress', 'completed', 'reviewed', 'archived'],
                               help='New status')
    
    # Check issue status
    check_parser = subparsers.add_parser('check', help='Check current status of an issue')
    check_parser.add_argument('issue', type=int, help='Issue number')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        start_work_on_issue(args.issue)
    elif args.command == 'complete':
        complete_issue(args.issue, args.branch)
    elif args.command == 'update':
        update_issue_status(args.issue, args.status)
    elif args.command == 'test':
        force_update_issue_for_testing(args.issue, args.status)
    elif args.command == 'check':
        check_issue_status(args.issue)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
