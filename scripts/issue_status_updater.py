#!/usr/bin/env python
"""
GitHub Issue Status Updater.

This module automatically updates GitHub issue statuses based on git activity
and test execution results. It works as both a standalone script and as part
of the MCP server infrastructure.

Capabilities:
- Detect when work on an issue begins based on commit messages
- Monitor test execution to determine completion status
- Update issue labels and add explanatory comments
- Create workflow visualizations
"""

import argparse
import os
import re
import subprocess
import sys
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import GitHub MCP functions if available
try:
    from mcp5_get_issue import mcp5_get_issue
    from mcp5_update_issue import mcp5_update_issue
    from mcp5_add_issue_comment import mcp5_add_issue_comment
    from mcp5_list_issues import mcp5_list_issues
    HAS_MCP = True
except ImportError:
    logger.warning("GitHub MCP modules not found, running in standalone mode")
    HAS_MCP = False
    # Define placeholder functions for testing without MCP
    def mcp5_get_issue(**kwargs):
        logger.info(f"Mock get_issue called with {kwargs}")
        return {}
        
    def mcp5_update_issue(**kwargs):
        logger.info(f"Mock update_issue called with {kwargs}")
        return {}
        
    def mcp5_add_issue_comment(**kwargs):
        logger.info(f"Mock add_issue_comment called with {kwargs}")
        return {}
        
    def mcp5_list_issues(**kwargs):
        logger.info(f"Mock list_issues called with {kwargs}")
        return []


class CommitAnalyzer:
    """Analyze git commits for issue references."""
    
    def __init__(self, repo_path: str = '.'):
        """
        Initialize the CommitAnalyzer.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
    
    def get_recent_commits(self, limit: int = 10, branch: str = 'HEAD') -> List[Dict]:
        """
        Get recent commits from the git repository.
        
        Args:
            limit: Maximum number of commits to retrieve
            branch: Git branch to analyze
            
        Returns:
            List of commit dictionaries with hash, message, and issue references
        """
        try:
            # Run git log to get recent commits
            cmd = [
                'git', '-C', self.repo_path, 'log', 
                f'-{limit}', '--pretty=format:%h,%s', branch
            ]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse commit information
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split(',', 1)
                if len(parts) != 2:
                    continue
                    
                commit_hash, message = parts
                parsed = self.parse_commit_message(message)
                
                commits.append({
                    'hash': commit_hash,
                    'message': message,
                    'issue_refs': parsed['issue_refs'],
                    'action': parsed['action']
                })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting git commits: {e}")
            return []
    
    def parse_commit_message(self, message: str) -> Dict:
        """
        Parse a commit message to extract issue references and actions.
        
        Args:
            message: Git commit message
            
        Returns:
            Dictionary with issue references and action type
        """
        # Extract issue numbers using regex
        issue_matches = re.findall(r'#(\d+)', message)
        issue_refs = [int(num) for num in issue_matches]
        
        # Check for action keywords in priority order
        actions = {
            'closes': r'closes\s+#\d+',
            'fixes': r'fixes\s+#\d+',
            'resolves': r'resolves\s+#\d+',
            'implements': r'implements\s+#\d+',
            'refs': r'refs\s+#\d+'
        }
        
        action = None
        for act, pattern in actions.items():
            if re.search(pattern, message.lower()):
                action = act
                break
        
        return {
            'issue_refs': issue_refs,
            'action': action
        }
    
    def get_commits_for_issue(self, issue_number: int, limit: int = 50) -> List[Dict]:
        """
        Get all commits related to a specific issue.
        
        Args:
            issue_number: GitHub issue number
            limit: Maximum number of commits to check
            
        Returns:
            List of commit dictionaries related to the issue
        """
        commits = self.get_recent_commits(limit=limit)
        return [c for c in commits if issue_number in c['issue_refs']]


class PullRequestAnalyzer:
    """Analyze pull requests for issue references."""
    
    def __init__(self, owner: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize the PullRequestAnalyzer.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
        """
        self.owner = owner
        self.repo = repo
    
    def get_pull_requests(self, state: str = 'open') -> List[Dict]:
        """
        Get pull requests from GitHub.
        
        Args:
            state: PR state ('open', 'closed', or 'all')
            
        Returns:
            List of pull request dictionaries with additional metadata
        """
        try:
            # Get issues labeled as PRs
            issues = mcp5_list_issues(
                owner=self.owner,
                repo=self.repo,
                state='all'  # Get all issues, we'll filter by PR type and state later
            )
            
            # Filter for pull requests
            prs = []
            for issue in issues:
                # Check if this is a PR by looking for the PR label
                is_pr = False
                for label in issue.get('labels', []):
                    if label.get('name') == 'type:pr':
                        is_pr = True
                        break
                
                if not is_pr:
                    continue
                
                # Filter by state if not 'all'
                if state != 'all' and issue.get('state') != state:
                    continue
                
                # Extract linked issues from title and body
                title = issue.get('title', '')
                body = issue.get('body', '')
                linked_issues = self.extract_linked_issues(title, body)
                
                prs.append({
                    'number': issue.get('number'),
                    'title': title,
                    'body': body,
                    'state': issue.get('state'),
                    'linked_issues': linked_issues
                })
            
            return prs
            
        except Exception as e:
            logger.error(f"Error getting pull requests: {e}")
            return []
    
    def extract_linked_issues(self, title: str, body: str) -> List[int]:
        """
        Extract issue references from PR title and body.
        
        Args:
            title: PR title
            body: PR body
            
        Returns:
            List of referenced issue numbers
        """
        # Combine title and body for analysis
        text = f"{title}\n{body}"
        
        # Find all issue references
        issue_matches = re.findall(r'#(\d+)', text)
        issue_refs = [int(num) for num in issue_matches]
        
        # Remove duplicates
        return list(set(issue_refs))
    
    def get_pr_for_issue(self, issue_number: int) -> Optional[Dict]:
        """
        Find pull requests related to a specific issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dictionary with PR information or None if not found
        """
        prs = self.get_pull_requests(state='all')
        
        for pr in prs:
            if issue_number in pr['linked_issues']:
                return pr
        
        return None


class TestResultsAnalyzer:
    """Analyze test results for issue-related code."""
    
    def __init__(self):
        """Initialize the TestResultsAnalyzer."""
        pass
    
    def find_files_for_issue(self, issue_number: int, code_dir: str = '.') -> List[str]:
        """
        Find source files related to an issue based on naming conventions.
        
        Args:
            issue_number: GitHub issue number
            code_dir: Directory to search for code files
            
        Returns:
            List of file paths related to the issue
        """
        related_files = []
        
        try:
            # Get issue details to determine keywords
            issue = mcp5_get_issue(
                owner=os.environ.get('GITHUB_OWNER'),
                repo=os.environ.get('GITHUB_REPO'),
                issue_number=issue_number
            )
            
            # Extract keywords from issue title and body
            title = issue.get('title', '')
            body = issue.get('body', '')
            
            # Simple keyword extraction - could be improved with NLP
            text = f"{title} {body}".lower()
            keywords = [w for w in re.split(r'\W+', text) if len(w) > 3]
            
            # Match files that contain these keywords
            for root, _, files in os.walk(code_dir):
                if '.git' in root or '.venv' in root:
                    continue
                    
                for file in files:
                    if not file.endswith('.py'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    file_name = file.lower()
                    
                    # Check if any keywords match
                    if any(kw in file_name for kw in keywords):
                        related_files.append(file_path)
                        continue
                    
                    # If no match by name, check file contents
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read().lower()
                            # Check for issue reference in comments
                            if f'issue #{issue_number}' in content:
                                related_files.append(file_path)
                    except Exception:
                        pass
            
            return related_files
            
        except Exception as e:
            logger.error(f"Error finding files for issue: {e}")
            return []
    
    def run_tests_for_issue(self, issue_number: int, test_dir: str = 'tests') -> Dict:
        """
        Run tests related to a specific issue.
        
        Args:
            issue_number: GitHub issue number
            test_dir: Directory containing test files
            
        Returns:
            Dictionary with test results
        """
        test_files = []
        
        # Find test files related to this issue
        for root, _, files in os.walk(test_dir):
            for file in files:
                if not file.startswith('test_') or not file.endswith('.py'):
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Check if file relates to this issue
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Look for issue reference in comments or docstring
                        if f'Issue #{issue_number}' in content:
                            test_files.append(file_path)
                except Exception:
                    pass
        
        # If no specific test files found, run all tests
        if not test_files:
            logger.info(f"No specific test files found for issue #{issue_number}, running all tests")
            cmd = ['uv', 'run', '-m', 'pytest']
        else:
            logger.info(f"Running tests for issue #{issue_number}: {test_files}")
            cmd = ['uv', 'run', '-m', 'pytest'] + test_files
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'output': result.stdout,
                'error': result.stderr if not success else None,
                'test_files': test_files
            }
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                'success': False,
                'error': str(e),
                'test_files': test_files
            }
    
    def get_coverage_for_issue(self, issue_number: int, coverage_file: str = '.coverage.json') -> Dict:
        """
        Get test coverage for files related to an issue.
        
        Args:
            issue_number: GitHub issue number
            coverage_file: Path to coverage JSON file
            
        Returns:
            Dictionary with coverage information
        """
        # Run pytest with coverage
        try:
            subprocess.run(
                ['uv', 'run', '-m', 'pytest', '--cov=imap_mcp', '--cov-report=json'],
                capture_output=True,
                check=True
            )
        except Exception as e:
            logger.error(f"Error running coverage: {e}")
        
        # Parse coverage data
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading coverage data: {e}")
            return {
                'coverage': 0.0,
                'files': []
            }
        
        # Find files related to this issue
        related_files = self.find_files_for_issue(issue_number)
        
        # Calculate coverage for these files
        total_statements = 0
        covered_statements = 0
        file_coverage = {}
        
        for file_path in related_files:
            rel_path = os.path.relpath(file_path)
            
            if rel_path in coverage_data['files']:
                data = coverage_data['files'][rel_path]['summary']
                statements = data.get('num_statements', 0)
                
                # Handle different coverage data formats
                if 'missing_lines' in data:
                    missing = len(data['missing_lines'])
                    covered = statements - missing
                elif 'covered_lines' in data:
                    covered = data.get('covered_lines', 0)
                else:
                    # Fallback to percent covered
                    percent = data.get('percent_covered', 0.0)
                    covered = int(statements * (percent / 100.0))
                
                total_statements += statements
                covered_statements += covered
                
                if statements > 0:
                    file_coverage[rel_path] = (covered / statements) * 100
        
        # Calculate overall coverage
        overall_coverage = 0.0
        if total_statements > 0:
            overall_coverage = (covered_statements / total_statements) * 100
        
        return {
            'coverage': overall_coverage,
            'files': related_files,
            'file_coverage': file_coverage
        }


class IssueUpdater:
    """Update GitHub issue statuses and add comments."""
    
    def __init__(self, owner: str, repo: str):
        """
        Initialize the IssueUpdater.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
        """
        self.owner = owner
        self.repo = repo
    
    def update_issue_status(self, issue_number: int, status: str) -> Dict:
        """
        Update an issue's status label.
        
        Args:
            issue_number: GitHub issue number
            status: New status ('in-progress', 'completed', etc.)
            
        Returns:
            Response from the GitHub API
        """
        try:
            # Get current issue details
            issue = mcp5_get_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number
            )
            
            # Extract current labels
            current_labels = [label['name'] for label in issue.get('labels', [])]
            
            # Remove existing status labels
            new_labels = [label for label in current_labels if not label.startswith('status:')]
            
            # Add new status label
            new_labels.append(f'status:{status}')
            
            # Update the issue
            result = mcp5_update_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number,
                labels=new_labels
            )
            
            logger.info(f"Updated issue #{issue_number} status to {status}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating issue status: {e}")
            return {}
    
    def add_status_comment(self, issue_number: int, status: str, details: Dict) -> Dict:
        """
        Add a comment to an issue explaining a status change.
        
        Args:
            issue_number: GitHub issue number
            status: New status
            details: Dictionary with relevant details about the change
            
        Returns:
            Response from the GitHub API
        """
        try:
            # Build comment body based on status
            body = f"Status changed to: `{status}`\n\n"
            
            if status == 'in-progress':
                # For started status, include commit info
                commit = details.get('commit', 'unknown')
                message = details.get('message', '')
                body += f"Work started in commit [{commit}](https://github.com/{self.owner}/{self.repo}/commit/{commit}):\n> {message}\n"
            
            elif status == 'completed':
                # For completed status, include test results and PR
                test_results = details.get('test_results', {})
                pr_number = details.get('pr_number')
                
                if test_results:
                    coverage = test_results.get('coverage', 0.0)
                    success = test_results.get('success', False)
                    body += f"Test status: {'✅ Passed' if success else '❌ Failed'}\n"
                    body += f"Test coverage: {coverage:.1f}%\n\n"
                
                if pr_number:
                    body += f"Implemented in PR #{pr_number}: https://github.com/{self.owner}/{self.repo}/pull/{pr_number}\n"
            
            # Add the comment
            result = mcp5_add_issue_comment(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number,
                body=body
            )
            
            logger.info(f"Added status comment to issue #{issue_number}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding status comment: {e}")
            return {}


class PriorityManager:
    """Manage and update issue priorities."""
    
    def __init__(self, owner: str, repo: str):
        """
        Initialize the PriorityManager.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
        """
        self.owner = owner
        self.repo = repo
    
    def get_prioritized_issues(self) -> List[Dict]:
        """
        Get all issues with 'prioritized' status and their priorities.
        
        Returns:
            List of issue dictionaries with extracted priority information
        """
        try:
            # Get all open issues
            issues = mcp5_list_issues(
                owner=self.owner,
                repo=self.repo,
                state='open'
            )
            
            # Filter for prioritized issues and extract priority
            prioritized_issues = []
            for issue in issues:
                # Check status and get priority
                status = None
                priority = None
                
                for label in issue.get('labels', []):
                    name = label.get('name', '')
                    if name.startswith('status:'):
                        status = name.replace('status:', '')
                    elif name.startswith('priority:'):
                        try:
                            priority = int(name.replace('priority:', ''))
                        except ValueError:
                            continue
                
                # Only include issues with prioritized status and valid priority
                if status == 'prioritized' and priority is not None:
                    prioritized_issues.append({
                        'number': issue.get('number'),
                        'title': issue.get('title', ''),
                        'priority': priority,
                        'labels': [label.get('name', '') for label in issue.get('labels', [])]
                    })
            
            # Sort by priority
            prioritized_issues.sort(key=lambda x: x['priority'])
            return prioritized_issues
            
        except Exception as e:
            logger.error(f"Error getting prioritized issues: {e}")
            return []
    
    def adjust_priorities_after_completion(self, completed_issue_number: int, notify: bool = False) -> bool:
        """
        Adjust priorities of remaining issues after a task is completed.
        
        Args:
            completed_issue_number: Issue number of the completed task
            notify: Whether to add comments to issues about priority changes
            
        Returns:
            Boolean indicating success
        """
        try:
            # Get all prioritized issues
            issues = self.get_prioritized_issues()
            
            # Find the completed issue and its priority
            completed_issue = None
            completed_priority = None
            
            for issue in issues:
                if issue['number'] == completed_issue_number:
                    completed_issue = issue
                    completed_priority = issue['priority']
                    break
            
            # If issue not found or not prioritized, do nothing
            if completed_priority is None:
                logger.info(f"Issue #{completed_issue_number} not found or has no priority")
                return False
            
            # Adjust priorities of remaining issues
            for issue in issues:
                # Skip the completed issue
                if issue['number'] == completed_issue_number:
                    continue
                
                # Only adjust issues with higher priority numbers (lower actual priority)
                if issue['priority'] > completed_priority:
                    # Store the old priority for notification
                    old_priority = issue['priority']
                    new_priority = old_priority - 1
                    
                    # Update the issue with new priority
                    self._update_issue_priority(issue['number'], old_priority, new_priority)
                    
                    # Add notification comment if requested
                    if notify:
                        self._add_priority_change_comment(issue['number'], old_priority, new_priority)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adjusting priorities: {e}")
            return False
    
    def _update_issue_priority(self, issue_number: int, old_priority: int, new_priority: int) -> Dict:
        """
        Update an issue's priority label.
        
        Args:
            issue_number: GitHub issue number
            old_priority: Current priority number
            new_priority: New priority number
            
        Returns:
            Response from the GitHub API
        """
        try:
            # Get current issue details
            issue = mcp5_get_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number
            )
            
            # Extract current labels
            current_labels = [label['name'] for label in issue.get('labels', [])]
            
            # Remove old priority label
            new_labels = [label for label in current_labels if not label.startswith('priority:')]
            
            # Add new priority label
            new_labels.append(f'priority:{new_priority}')
            
            # Update the issue
            result = mcp5_update_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number,
                labels=new_labels
            )
            
            logger.info(f"Updated issue #{issue_number} priority from {old_priority} to {new_priority}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating issue priority: {e}")
            return {}
    
    def _add_priority_change_comment(self, issue_number: int, old_priority: int, new_priority: int) -> Dict:
        """
        Add a comment to an issue explaining a priority change.
        
        Args:
            issue_number: GitHub issue number
            old_priority: Previous priority number
            new_priority: New priority number
            
        Returns:
            Response from the GitHub API
        """
        try:
            # Build comment body
            body = f"🔄 **Priority Update**\n\n"
            body += f"Priority updated from {old_priority} to {new_priority} due to the completion of a higher priority task.\n"
            
            # Add the comment
            result = mcp5_add_issue_comment(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number,
                body=body
            )
            
            logger.info(f"Added priority change comment to issue #{issue_number}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding priority comment: {e}")
            return {}


class GitHubActionsWorkflow:
    """Create and manage GitHub Actions workflows for status updates."""
    
    def __init__(self, repo_path: str = '.'):
        """
        Initialize the GitHubActionsWorkflow.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self.workflow_dir = os.path.join(repo_path, '.github', 'workflows')
    
    def create_workflow_file(self) -> bool:
        """
        Create a GitHub Actions workflow file for issue status updates.
        
        Returns:
            Boolean indicating success
        """
        # Ensure workflow directory exists
        os.makedirs(self.workflow_dir, exist_ok=True)
        
        # Workflow file path
        workflow_path = os.path.join(self.workflow_dir, 'issue_status_updater.yml')
        
        # Workflow content
        workflow_content = """name: Issue Status Updater

on:
  push:
    branches: [ main, master ]
  pull_request:
    types: [opened, closed, synchronize]
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'Issue number to update'
        required: true
        type: number

jobs:
  update-issue-status:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 50
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install uv
          uv pip install -r requirements.txt
          uv pip install pytest pytest-cov
      
      - name: Run issue status updater
        run: |
          python scripts/issue_status_updater.py \
            --owner ${{ github.repository_owner }} \
            --repo ${{ github.event.repository.name }} \
            ${{ github.event.inputs.issue_number && format('--issue {0}', github.event.inputs.issue_number) || '' }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
        
        try:
            with open(workflow_path, 'w') as f:
                f.write(workflow_content)
            
            logger.info(f"Created workflow file at {workflow_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating workflow file: {e}")
            return False


def main():
    """Run the issue status updater as a standalone script."""
    parser = argparse.ArgumentParser(description='GitHub Issue Status Updater')
    parser.add_argument('--owner', required=True, help='GitHub repository owner')
    parser.add_argument('--repo', required=True, help='GitHub repository name')
    parser.add_argument('--issue', type=int, help='Specific issue number to update')
    parser.add_argument('--create-workflow', action='store_true', help='Create GitHub Actions workflow file')
    parser.add_argument('--scan-commits', type=int, default=10, help='Number of recent commits to scan')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing them')
    
    args = parser.parse_args()
    
    # Create GitHub Actions workflow if requested
    if args.create_workflow:
        workflow = GitHubActionsWorkflow()
        workflow.create_workflow_file()
        return 0
    
    # Initialize analyzers
    commit_analyzer = CommitAnalyzer()
    pr_analyzer = PullRequestAnalyzer(owner=args.owner, repo=args.repo)
    test_analyzer = TestResultsAnalyzer()
    issue_updater = IssueUpdater(owner=args.owner, repo=args.repo)
    priority_manager = PriorityManager(owner=args.owner, repo=args.repo)
    
    # If a specific issue is provided, only update that one
    if args.issue:
        update_single_issue(
            args.issue, 
            commit_analyzer, 
            pr_analyzer, 
            test_analyzer, 
            issue_updater,
            priority_manager,
            args.dry_run
        )
        return 0
    
    # Otherwise, scan recent commits to find issues to update
    commits = commit_analyzer.get_recent_commits(limit=args.scan_commits)
    issue_numbers = set()
    
    for commit in commits:
        issue_numbers.update(commit['issue_refs'])
    
    # Update each referenced issue
    for issue_number in issue_numbers:
        update_single_issue(
            issue_number, 
            commit_analyzer, 
            pr_analyzer, 
            test_analyzer, 
            issue_updater,
            priority_manager,
            args.dry_run
        )
    
    return 0


def update_single_issue(
    issue_number: int, 
    commit_analyzer: CommitAnalyzer,
    pr_analyzer: PullRequestAnalyzer,
    test_analyzer: TestResultsAnalyzer,
    issue_updater: IssueUpdater,
    priority_manager: PriorityManager,
    dry_run: bool = False
) -> None:
    """
    Update a single issue based on git activity and tests.
    
    Args:
        issue_number: GitHub issue number
        commit_analyzer: CommitAnalyzer instance
        pr_analyzer: PullRequestAnalyzer instance
        test_analyzer: TestResultsAnalyzer instance
        issue_updater: IssueUpdater instance
        priority_manager: PriorityManager instance
        dry_run: If True, print actions without executing them
    """
    # Get issue details
    try:
        issue = mcp5_get_issue(
            owner=issue_updater.owner,
            repo=issue_updater.repo,
            issue_number=issue_number
        )
    except Exception as e:
        logger.error(f"Error getting issue #{issue_number}: {e}")
        return
    
    # Check current status
    current_status = 'prioritized'  # Default
    for label in issue.get('labels', []):
        name = label.get('name', '')
        if name.startswith('status:'):
            current_status = name.replace('status:', '')
            break
    
    # Check for related PR
    pr = pr_analyzer.get_pr_for_issue(issue_number)
    
    # Check for commits
    commits = commit_analyzer.get_commits_for_issue(issue_number)
    
    # Determine new status
    new_status = current_status
    status_details = {}
    
    if current_status == 'prioritized' and commits:
        # Found commits but no PR - mark as in-progress
        new_status = 'in-progress'
        status_details = {
            'commit': commits[0]['hash'],
            'message': commits[0]['message']
        }
    
    elif current_status == 'in-progress' and pr and pr['state'] == 'closed':
        # PR closed, check if it fixed the issue
        for commit in commits:
            if commit['action'] in ('fixes', 'closes', 'resolves') and issue_number in commit['issue_refs']:
                # Run tests to confirm
                test_results = test_analyzer.run_tests_for_issue(issue_number)
                coverage = test_analyzer.get_coverage_for_issue(issue_number)
                
                if test_results['success']:
                    new_status = 'completed'
                    status_details = {
                        'test_results': {
                            'success': True,
                            'coverage': coverage.get('coverage', 0.0)
                        },
                        'pr_number': pr['number']
                    }
    
    # Update issue if status changed
    if new_status != current_status:
        logger.info(f"Updating issue #{issue_number} status from {current_status} to {new_status}")
        
        if not dry_run:
            issue_updater.update_issue_status(issue_number, new_status)
            issue_updater.add_status_comment(issue_number, new_status, status_details)
            if new_status == 'completed':
                priority_manager.adjust_priorities_after_completion(issue_number)
        else:
            logger.info("[DRY RUN] Would update issue status and add comment")


if __name__ == '__main__':
    sys.exit(main())
