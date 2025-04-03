#!/usr/bin/env python
"""
GitHub Workflow Script

This script provides automation for common GitHub operations including:
- Issue management (creating, updating status)
- Commit management (create commits with appropriate references)
- PR creation and completion

Usage examples:
    # Start working on an issue
    python -m scripts.github_workflow start-issue 123
    
    # Commit changes with issue reference
    python -m scripts.github_workflow commit "Implement feature X" --ref 123 --action implements
    
    # Create PR for an issue
    python -m scripts.github_workflow create-pr "Feature X implementation" "Closes #123" --issue 123
    
    # Complete PR by merging
    python -m scripts.github_workflow complete-pr 45 --merge

This script is designed to minimize API calls by combining common operations.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union


class IssueStatus(str, Enum):
    PRIORITIZED = "prioritized"
    IN_PROGRESS = "in-progress"
    IN_REVIEW = "in-review" 
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class CommitAction(str, Enum):
    REFS = "refs"
    IMPLEMENTS = "implements"
    FIXES = "fixes"
    CLOSES = "closes"
    RESOLVES = "resolves"


@dataclass
class GitHubConfig:
    repo_owner: str
    repo_name: str
    
    @classmethod
    def from_git(cls) -> "GitHubConfig":
        """Extract GitHub repository information from git config."""
        try:
            # Get the remote URL
            remote_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                text=True
            ).strip()
            
            # Extract owner and repo from the URL
            if remote_url.startswith("https://"):
                # https://github.com/owner/repo.git
                parts = remote_url.split("/")
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
            else:
                # git@github.com:owner/repo.git
                parts = remote_url.split(":")
                owner_repo = parts[-1].replace(".git", "")
                owner, repo = owner_repo.split("/")
            
            return cls(repo_owner=owner, repo_name=repo)
        except subprocess.CalledProcessError:
            sys.stderr.write("Error: Not a git repository or remote origin not set\n")
            sys.exit(1)


def run_gh_command(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a GitHub CLI command."""
    try:
        return subprocess.run(
            ["gh"] + args,
            check=check,
            text=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error running GitHub CLI command: {e.stderr}\n")
        if check:
            sys.exit(1)
        return e


def get_issue(issue_number: int) -> dict:
    """Get information about a specific issue."""
    result = run_gh_command([
        "issue", "view", str(issue_number),
        "--json", "number,title,state,labels"
    ])
    return json.loads(result.stdout)


def update_issue_status(issue_number: int, status: IssueStatus, force: bool = False) -> None:
    """Update the status of an issue."""
    # Get current issue information
    issue = get_issue(issue_number)
    
    # Extract current status labels
    status_labels = [
        label["name"] for label in issue["labels"]
        if label["name"].startswith("status:")
    ]
    
    # If status already matches and not forced, skip
    current_status = f"status:{status}"
    if current_status in status_labels and not force:
        print(f"Issue #{issue_number} already has status '{status}'")
        return
    
    # Remove current status labels and add new one
    args = ["issue", "edit", str(issue_number)]
    
    # Add the new status label
    args.extend(["--add-label", current_status])
    
    # Remove old status labels
    for status_label in status_labels:
        if status_label != current_status:
            args.extend(["--remove-label", status_label])
    
    run_gh_command(args)
    print(f"Updated issue #{issue_number} status to '{status}'")


def add_status_comment(issue_number: int, status: IssueStatus, message: str) -> None:
    """Add a comment to explain the status change."""
    comment_body = f"Status changed to **{status}**\n\n{message}"
    run_gh_command([
        "issue", "comment", str(issue_number),
        "--body", comment_body
    ])


def start_issue(issue_number: int) -> None:
    """Start working on an issue by updating its status and creating a branch."""
    # Get issue information
    issue = get_issue(issue_number)
    title = issue["title"]
    
    # Convert title to a branch-friendly name
    branch_name = f"issue-{issue_number}-" + title.lower().replace(" ", "-")
    branch_name = "".join(c for c in branch_name if c.isalnum() or c in "-_")
    
    # Create and checkout a new branch
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            check=True,
            text=True,
            capture_output=True
        )
        print(f"Created and checked out branch '{branch_name}'")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error creating branch: {e.stderr}\n")
        sys.exit(1)
    
    # Update issue status to in-progress
    update_issue_status(issue_number, IssueStatus.IN_PROGRESS)
    add_status_comment(
        issue_number, 
        IssueStatus.IN_PROGRESS,
        "Work has started on this issue."
    )


def create_commit(message: str, issue_number: Optional[int] = None, 
                  action: Optional[CommitAction] = None) -> None:
    """Create a commit with an optional reference to an issue."""
    if issue_number is not None:
        # Format the commit message with issue reference
        if action:
            prefix = f"{action} #{issue_number}: "
        else:
            prefix = f"refs #{issue_number}: "
        
        message = prefix + message
    
    # Commit changes
    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            text=True,
            capture_output=True
        )
        print(f"Created commit: {message}")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error creating commit: {e.stderr}\n")
        sys.exit(1)


def create_pr(title: str, body: str, issue_number: Optional[int] = None, 
              draft: bool = False) -> None:
    """Create a PR with optional reference to an issue."""
    args = ["pr", "create", "--title", title, "--body", body]
    
    if draft:
        args.append("--draft")
    
    result = run_gh_command(args)
    print(f"Created PR: {result.stdout.strip()}")
    
    # If this PR is for an issue, update the issue status
    if issue_number:
        update_issue_status(issue_number, IssueStatus.IN_REVIEW)
        add_status_comment(
            issue_number,
            IssueStatus.IN_REVIEW,
            f"Pull request created: {result.stdout.strip()}"
        )


def complete_pr(pr_number: int, merge: bool = False, 
                squash: bool = False, rebase: bool = False) -> None:
    """Complete a PR by merging, squashing, or rebasing."""
    # Get PR information
    pr_result = run_gh_command([
        "pr", "view", str(pr_number),
        "--json", "number,title,state,body"
    ])
    pr_info = json.loads(pr_result.stdout)
    
    # Check if PR is already merged
    if pr_info["state"] == "MERGED":
        print(f"PR #{pr_number} is already merged")
        return
    
    # Extract issue numbers from PR body
    body = pr_info["body"]
    issue_refs = []
    
    for keyword in ["closes", "fixes", "resolves"]:
        keyword_pos = body.lower().find(keyword)
        if keyword_pos != -1:
            # Find all instances of #NNN after the keyword
            import re
            matches = re.finditer(r'#(\d+)', body[keyword_pos:])
            for match in matches:
                issue_refs.append(int(match.group(1)))
    
    # Merge the PR
    args = ["pr", "merge", str(pr_number)]
    if merge:
        args.append("--merge")
    elif squash:
        args.append("--squash")
    elif rebase:
        args.append("--rebase")
    else:
        args.append("--merge")  # Default to merge
    
    run_gh_command(args)
    print(f"Completed PR #{pr_number}")
    
    # Update status of referenced issues
    for issue_number in issue_refs:
        update_issue_status(issue_number, IssueStatus.COMPLETED)
        add_status_comment(
            issue_number,
            IssueStatus.COMPLETED,
            f"Issue completed with PR #{pr_number}"
        )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="GitHub Workflow Helper")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Start issue command
    start_parser = subparsers.add_parser("start-issue", help="Start working on an issue")
    start_parser.add_argument("issue_number", type=int, help="Issue number to start")
    
    # Commit command
    commit_parser = subparsers.add_parser("commit", help="Create a commit")
    commit_parser.add_argument("message", help="Commit message")
    commit_parser.add_argument("--ref", "--issue", dest="issue_number", type=int, 
                              help="Issue number to reference")
    commit_parser.add_argument("--action", type=CommitAction, choices=list(CommitAction), 
                              default=CommitAction.REFS, help="Action to take in the commit")
    
    # Create PR command
    pr_parser = subparsers.add_parser("create-pr", help="Create a PR")
    pr_parser.add_argument("title", help="PR title")
    pr_parser.add_argument("body", help="PR body")
    pr_parser.add_argument("--issue", type=int, help="Issue number this PR addresses")
    pr_parser.add_argument("--draft", action="store_true", help="Create as draft PR")
    
    # Complete PR command
    complete_parser = subparsers.add_parser("complete-pr", help="Complete a PR")
    complete_parser.add_argument("pr_number", type=int, help="PR number to complete")
    merge_group = complete_parser.add_mutually_exclusive_group()
    merge_group.add_argument("--merge", action="store_true", help="Merge the PR")
    merge_group.add_argument("--squash", action="store_true", help="Squash and merge the PR")
    merge_group.add_argument("--rebase", action="store_true", help="Rebase and merge the PR")
    
    # Update issue status command
    status_parser = subparsers.add_parser("update-status", help="Update issue status")
    status_parser.add_argument("issue_number", type=int, help="Issue number to update")
    status_parser.add_argument("status", type=IssueStatus, choices=list(IssueStatus), 
                              help="New status")
    status_parser.add_argument("--force", action="store_true", 
                              help="Force status update even if already set")
    status_parser.add_argument("--comment", help="Comment to add explaining the status change")
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    if args.command == "start-issue":
        start_issue(args.issue_number)
    
    elif args.command == "commit":
        create_commit(args.message, args.issue_number, args.action)
    
    elif args.command == "create-pr":
        create_pr(args.title, args.body, args.issue, args.draft)
    
    elif args.command == "complete-pr":
        complete_pr(args.pr_number, args.merge, args.squash, args.rebase)
    
    elif args.command == "update-status":
        update_issue_status(args.issue_number, args.status, args.force)
        if args.comment:
            add_status_comment(args.issue_number, args.status, args.comment)
    
    else:
        sys.stderr.write("Error: No command specified\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
