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
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define status transition constraints
# This defines the valid status transitions
VALID_STATUS_TRANSITIONS = {
    'prioritized': {'in-progress', 'canceled'},
    'in-progress': {'in-review', 'completed', 'canceled', 'prioritized'},
    'in-review': {'in-progress', 'completed', 'canceled'},
    'completed': {'reopened', 'canceled'},
    'reopened': {'in-progress', 'canceled'},
    'canceled': {'prioritized', 'in-progress'}
}

# Define the display order of statuses for visual representation
STATUS_ORDER = ['prioritized', 'in-progress', 'in-review', 'completed', 'reopened', 'canceled']

# GitHub CLI wrapper functions
def gh_get_issue(owner: str, repo: str, issue_number: int) -> Dict:
    """
    Get issue details using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        issue_number: Issue number
        
    Returns:
        Dictionary with issue details
    """
    cmd = ["gh", "issue", "view", str(issue_number), "--json", "title,body,labels,state"]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting issue #{issue_number}: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing GitHub CLI output: {e}")
        return {}

def gh_update_issue(owner: str, repo: str, issue_number: int, labels: List[str] = None, 
                  state: str = None, title: str = None, body: str = None) -> Dict:
    """
    Update an issue using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        issue_number: Issue number
        labels: List of labels to set
        state: State to set (open, closed)
        title: New title
        body: New body
        
    Returns:
        Dictionary with issue details after update
    """
    cmd = ["gh", "issue", "edit", str(issue_number)]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    if labels:
        cmd.extend(["--add-label", ",".join(labels)])
    if state:
        cmd.extend(["--state", state])
    if title:
        cmd.extend(["--title", title])
    if body:
        cmd.extend(["--body", body])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Updated issue #{issue_number}")
        return gh_get_issue(owner, repo, issue_number)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error updating issue #{issue_number}: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}

def gh_add_issue_comment(owner: str, repo: str, issue_number: int, body: str) -> Dict:
    """
    Add a comment to an issue using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        issue_number: Issue number
        body: Comment body
        
    Returns:
        Dictionary with comment details
    """
    cmd = ["gh", "issue", "comment", str(issue_number), "--body", body]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Added comment to issue #{issue_number}")
        return {"body": body}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error adding comment to issue #{issue_number}: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}

def gh_list_issues(owner: str, repo: str, state: str = "open", labels: List[str] = None) -> List[Dict]:
    """
    List issues using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        state: Issue state (open, closed, all)
        labels: Filter by labels
        
    Returns:
        List of issue dictionaries
    """
    cmd = ["gh", "issue", "list", "--json", "number,title,body,labels,state"]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    cmd.extend(["--state", state])
    if labels:
        cmd.extend(["--label", ",".join(labels)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error listing issues: {e}")
        logger.error(f"Command output: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing GitHub CLI output: {e}")
        return []

def gh_list_prs(owner: str, repo: str, state: str = "open") -> List[Dict]:
    """
    List pull requests using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        state: PR state (open, closed, all)
        
    Returns:
        List of PR dictionaries
    """
    cmd = ["gh", "pr", "list", "--json", "number,title,body,state,closedAt,mergedAt"]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    cmd.extend(["--state", state])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error listing PRs: {e}")
        logger.error(f"Command output: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing GitHub CLI output: {e}")
        return []

def gh_get_pr(owner: str, repo: str, pr_number: int) -> Dict:
    """
    Get PR details using GitHub CLI.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        pr_number: PR number
        
    Returns:
        Dictionary with PR details
    """
    cmd = ["gh", "pr", "view", str(pr_number), "--json", "number,title,body,state,closedAt,mergedAt"]
    if owner and repo:
        repo_string = f"{owner}/{repo}"
        cmd.extend(["-R", repo_string])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting PR #{pr_number}: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing GitHub CLI output: {e}")
        return {}

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
        
        # Check for action keywords in priority order with more flexible patterns
        # that allow optional colons and spacing variations
        actions = {
            'closes': r'closes\s*:?\s*#\d+',
            'fixes': r'fixes\s*:?\s*#\d+',
            'resolves': r'resolves\s*:?\s*#\d+',
            'implements': r'implements\s*:?\s*#\d+',
            'refs': r'refs\s*:?\s*#\d+'
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
            # Get PRs using GitHub CLI
            prs = gh_list_prs(self.owner, self.repo, state)
            
            # Add linked issues information to each PR
            for pr in prs:
                title = pr.get('title', '')
                body = pr.get('body', '')
                linked_issues = self.extract_linked_issues(title, body)
                pr['linked_issues'] = linked_issues
            
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
            if issue_number in pr.get('linked_issues', []):
                return pr
        
        return None
    
    def get_open_pr_for_issue(self, issue_number: int) -> Optional[Dict]:
        """
        Find open pull requests related to a specific issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dictionary with PR information or None if not found
        """
        prs = self.get_pull_requests(state='open')
        
        for pr in prs:
            if issue_number in pr.get('linked_issues', []):
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
            issue = gh_get_issue(
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
    
    def get_current_status(self, issue_number: int) -> str:
        """
        Get the current status of an issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Current status string (without 'status:' prefix)
        """
        try:
            # Get current issue details
            issue = gh_get_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number
            )
            
            # Extract current status
            for label in issue.get('labels', []):
                name = label.get('name', '')
                if name.startswith('status:'):
                    return name.replace('status:', '')
            
            # Default if no status found
            return 'prioritized'
            
        except Exception as e:
            logger.error(f"Error getting issue status: {e}")
            return 'prioritized'
    
    def validate_status_transition(self, current_status: str, new_status: str) -> bool:
        """
        Validate if a status transition is allowed.
        
        Args:
            current_status: Current issue status
            new_status: Proposed new status
            
        Returns:
            Boolean indicating if the transition is valid
        """
        # Same status is always valid
        if current_status == new_status:
            return True
        
        # Check transition validity
        return new_status in VALID_STATUS_TRANSITIONS.get(current_status, set())
    
    def update_issue_status(self, issue_number: int, status: str, force: bool = False) -> Dict:
        """
        Update an issue's status label.
        
        Args:
            issue_number: GitHub issue number
            status: New status ('in-progress', 'completed', etc.)
            force: If True, bypass transition validation
            
        Returns:
            Response from the GitHub API or empty dict if update not performed
        """
        try:
            # Get current issue details
            issue = gh_get_issue(
                owner=self.owner,
                repo=self.repo,
                issue_number=issue_number
            )
            
            # Extract current labels
            current_labels = [label['name'] for label in issue.get('labels', [])]
            
            # Extract current status
            current_status = 'prioritized'  # Default
            for label in current_labels:
                if label.startswith('status:'):
                    current_status = label.replace('status:', '')
                    break
            
            # Validate status transition
            if not force and not self.validate_status_transition(current_status, status):
                logger.warning(
                    f"Invalid status transition for issue #{issue_number}: "
                    f"{current_status} -> {status}"
                )
                return {}
            
            # Remove existing status labels
            new_labels = [label for label in current_labels if not label.startswith('status:')]
            
            # Add new status label
            new_labels.append(f'status:{status}')
            
            # Update the issue
            result = gh_update_issue(
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
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Build comment body based on status
            body = f"## Status Update: `{status}`\n\n"
            body += f"*Updated at: {timestamp}*\n\n"
            
            if status == 'in-progress':
                # For started status, include commit info
                commit = details.get('commit', 'unknown')
                message = details.get('message', '')
                body += f"📝 Work started in commit [{commit}](https://github.com/{self.owner}/{self.repo}/commit/{commit}):\n> {message}\n"
            
            elif status == 'in-review':
                # For in-review status, include PR info
                pr_number = details.get('pr_number')
                pr_title = details.get('pr_title', 'Review requested')
                
                if pr_number:
                    body += f"👀 Under review in PR [#{pr_number}](https://github.com/{self.owner}/{self.repo}/pull/{pr_number}):\n> {pr_title}\n"
                else:
                    body += f"👀 Issue is now under review.\n"
            
            elif status == 'completed':
                # For completed status, include test results and PR
                test_results = details.get('test_results', {})
                pr_number = details.get('pr_number')
                
                if test_results:
                    coverage = test_results.get('coverage', 0.0)
                    success = test_results.get('success', False)
                    body += f"🧪 Test status: {'✅ Passed' if success else '❌ Failed'}\n"
                    body += f"📊 Test coverage: {coverage:.1f}%\n\n"
                
                if pr_number:
                    body += f"✅ Implemented in PR [#{pr_number}](https://github.com/{self.owner}/{self.repo}/pull/{pr_number})\n"
            
            elif status == 'reopened':
                # For reopened status
                reason = details.get('reason', 'Issue requires additional work')
                body += f"🔄 Issue reopened: {reason}\n"
            
            elif status == 'canceled':
                # For canceled status
                reason = details.get('reason', 'Issue has been canceled')
                body += f"❌ Issue canceled: {reason}\n"
            
            # Add visualization of status progression
            body += "\n### Status Timeline\n\n"
            body += self._generate_status_timeline(status)
            
            # Add the comment
            result = gh_add_issue_comment(
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
    
    def _generate_status_timeline(self, current_status: str) -> str:
        """
        Generate a visual representation of the status timeline.
        
        Args:
            current_status: The current status to highlight
            
        Returns:
            Markdown string with status timeline visualization
        """
        timeline = ""
        
        for i, status in enumerate(STATUS_ORDER):
            if status == current_status:
                # Highlight current status
                timeline += f"**[{status}]** "
            else:
                timeline += f"{status} "
            
            # Add arrow except for last item
            if i < len(STATUS_ORDER) - 1:
                timeline += "→ "
        
        return timeline


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
            issues = gh_list_issues(
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
            issue = gh_get_issue(
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
            result = gh_update_issue(
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
            result = gh_add_issue_comment(
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
          python scripts/issue_status_updater.py \\
            --owner ${{ github.repository_owner }} \\
            --repo ${{ github.event.repository.name }} \\
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
    parser = argparse.ArgumentParser(description='Update GitHub issue statuses based on git activity')
    parser.add_argument('--owner', help='GitHub repository owner')
    parser.add_argument('--repo', help='GitHub repository name')
    parser.add_argument('--issue', type=int, help='Specific issue number to update')
    parser.add_argument('--update-from-commit', help='Update status based on a specific commit message')
    parser.add_argument('--update-from-pr', type=int, help='Update status based on a specific PR number')
    parser.add_argument('--pr-action', choices=['opened', 'closed', 'merged'], help='PR action for status determination')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing them')
    parser.add_argument('--force', action='store_true', help='Force status updates, bypassing validation')
    args = parser.parse_args()
    
    # Determine owner and repo from environment if not provided
    owner = args.owner
    repo = args.repo
    
    if not owner or not repo:
        if 'GITHUB_REPOSITORY' in os.environ:
            parts = os.environ['GITHUB_REPOSITORY'].split('/')
            if len(parts) == 2:
                if not owner:
                    owner = parts[0]
                if not repo:
                    repo = parts[1]
    
    if not owner or not repo:
        logger.error("GitHub repository owner and name are required")
        return 1
    
    # Create analyzers and updaters
    commit_analyzer = CommitAnalyzer()
    pr_analyzer = PullRequestAnalyzer(owner=owner, repo=repo)
    test_analyzer = TestResultsAnalyzer()
    issue_updater = IssueUpdater(owner=owner, repo=repo)
    priority_manager = PriorityManager(owner=owner, repo=repo)
    
    # If a specific commit message is provided, use it for updating
    if args.update_from_commit:
        if not args.issue:
            logger.error("Issue number is required when updating from commit")
            return 1
        
        parsed = commit_analyzer.parse_commit_message(args.update_from_commit)
        if args.issue in parsed['issue_refs']:
            # Determine status based on commit message keywords
            action = parsed['action']
            status = None
            
            if action == 'closes' or action == 'fixes' or action == 'resolves':
                status = 'completed'
            elif action == 'implements':
                status = 'in-progress'
            elif action == 'refs':
                status = 'in-progress'
            
            if status:
                details = {
                    'commit': 'manual-update',
                    'message': args.update_from_commit,
                    'action': action
                }
                logger.info(f"Setting issue #{args.issue} to {status} based on commit message")
                issue_updater.update_issue_status(args.issue, status, force=args.force)
                issue_updater.add_status_comment(args.issue, status, details)
            else:
                logger.info(f"No status change needed for issue #{args.issue}")
    
    # If a specific PR is provided, use it for updating
    elif args.update_from_pr:
        if not args.issue:
            logger.error("Issue number is required when updating from PR")
            return 1
        
        if not args.pr_action:
            logger.error("PR action is required when updating from PR")
            return 1
        
        status = None
        details = {
            'pr_number': args.update_from_pr,
            'pr_action': args.pr_action
        }
        
        if args.pr_action == 'opened':
            status = 'in-review'
        elif args.pr_action == 'merged':
            status = 'completed'
        elif args.pr_action == 'closed':
            # Revert to previous status (likely in-progress)
            current = issue_updater.get_current_status(args.issue)
            if current == 'in-review':
                status = 'in-progress'
        
        if status:
            logger.info(f"Setting issue #{args.issue} to {status} based on PR {args.update_from_pr} {args.pr_action}")
            issue_updater.update_issue_status(args.issue, status, force=args.force)
            issue_updater.add_status_comment(args.issue, status, details)
    
    # If a specific issue is provided without other options, update it based on general analysis
    elif args.issue:
        update_single_issue(
            args.issue, 
            commit_analyzer, 
            pr_analyzer, 
            test_analyzer, 
            issue_updater, 
            priority_manager,
            args.dry_run, 
            args.force
        )
    
    # Otherwise, update all recent issues
    else:
        # Get all open issues from GitHub
        try:
            issues = gh_list_issues(owner=owner, repo=repo, state='open')
            logger.info(f"Found {len(issues)} open issues")
            
            # Update each issue
            for issue in issues:
                issue_number = issue.get('number')
                if not issue_number:
                    continue
                
                update_single_issue(
                    issue_number, 
                    commit_analyzer, 
                    pr_analyzer, 
                    test_analyzer, 
                    issue_updater, 
                    priority_manager,
                    args.dry_run, 
                    args.force
                )
                
        except Exception as e:
            logger.error(f"Error updating issues: {e}")
            return 1
    
    return 0


def update_single_issue(
    issue_number: int, 
    commit_analyzer: CommitAnalyzer,
    pr_analyzer: PullRequestAnalyzer,
    test_analyzer: TestResultsAnalyzer,
    issue_updater: IssueUpdater,
    priority_manager: PriorityManager,
    dry_run: bool = False,
    force: bool = False
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
        force: If True, bypass transition validation
    """
    # Get issue details
    try:
        issue = gh_get_issue(
            owner=issue_updater.owner,
            repo=issue_updater.repo,
            issue_number=issue_number
        )
    except Exception as e:
        logger.error(f"Error getting issue #{issue_number}: {e}")
        return
    
    # Check current status
    current_status = issue_updater.get_current_status(issue_number)
    logger.info(f"Issue #{issue_number} current status: {current_status}")
    
    # Check for related PRs
    pr = pr_analyzer.get_pr_for_issue(issue_number)
    open_pr = pr_analyzer.get_open_pr_for_issue(issue_number)
    
    logger.info(f"Issue #{issue_number} PR status:")
    logger.info(f"  - Any PR found: {pr is not None}")
    if pr:
        logger.info(f"  - PR state: {pr.get('state')}")
        logger.info(f"  - PR number: {pr.get('number')}")
        logger.info(f"  - PR title: {pr.get('title')}")
    logger.info(f"  - Open PR found: {open_pr is not None}")
    
    # Check for commits
    commits = commit_analyzer.get_commits_for_issue(issue_number)
    logger.info(f"Issue #{issue_number} commits found: {len(commits)}")
    for i, commit in enumerate(commits):
        logger.info(f"  - Commit {i+1}:")
        logger.info(f"    Hash: {commit.get('hash')}")
        logger.info(f"    Message: {commit.get('message')}")
        logger.info(f"    Action: {commit.get('action')}")
        logger.info(f"    Issue refs: {commit.get('issue_refs')}")
    
    # Determine new status
    new_status = current_status
    status_details = {}
    
    # Status transition logic
    if current_status == 'prioritized' and commits:
        logger.info(f"Transition condition met: 'prioritized' -> 'in-progress' (commits found)")
        new_status = 'in-progress'
        status_details = {
            'commit': commits[0]['hash'],
            'message': commits[0]['message']
        }
    
    elif current_status == 'in-progress' and open_pr:
        logger.info(f"Transition condition met: 'in-progress' -> 'in-review' (open PR found)")
        new_status = 'in-review'
        status_details = {
            'pr_number': open_pr['number'],
            'pr_title': open_pr['title']
        }
    
    elif (current_status == 'in-progress' or current_status == 'in-review') and pr and pr['state'] == 'closed':
        logger.info(f"Checking transition conditions for 'in-progress/in-review' -> 'completed'")
        logger.info(f"  - Current status: {current_status}")
        logger.info(f"  - PR found and closed: {pr is not None and pr.get('state') == 'closed'}")
        
        # PR closed, check if it fixed the issue
        found_completing_commit = False
        for commit in commits:
            action = commit.get('action')
            issue_refs = commit.get('issue_refs', [])
            logger.info(f"  - Analyzing commit: {commit.get('hash')}")
            logger.info(f"    Action: {action}")
            logger.info(f"    Issue refs: {issue_refs}")
            logger.info(f"    Is completing commit: {action in ('fixes', 'closes', 'resolves') and issue_number in issue_refs}")
            
            if action in ('fixes', 'closes', 'resolves') and issue_number in issue_refs:
                found_completing_commit = True
                # Run tests to confirm
                test_results = test_analyzer.run_tests_for_issue(issue_number)
                coverage = test_analyzer.get_coverage_for_issue(issue_number)
                
                logger.info(f"  - Test results: {test_results}")
                if test_results['success']:
                    logger.info(f"Transition condition met: '{current_status}' -> 'completed' (PR closed with completing commit and tests pass)")
                    new_status = 'completed'
                    status_details = {
                        'test_results': {
                            'success': True,
                            'coverage': coverage.get('coverage', 0.0)
                        },
                        'pr_number': pr['number']
                    }
        
        if not found_completing_commit:
            logger.info(f"No completing commit found (with fixes/closes/resolves action). Checking PR title/body...")
            # Also check PR title/body for closing keywords
            pr_title = pr.get('title', '').lower()
            pr_body = pr.get('body', '').lower()
            
            closing_keywords = ['fixes #', 'closes #', 'resolves #']
            for keyword in closing_keywords:
                for text in [pr_title, pr_body]:
                    if f"{keyword}{issue_number}" in text.lower().replace(' ', ''):
                        logger.info(f"Found completing keyword in PR: '{keyword}{issue_number}'")
                        # Run tests to confirm
                        test_results = test_analyzer.run_tests_for_issue(issue_number)
                        coverage = test_analyzer.get_coverage_for_issue(issue_number)
                        
                        if test_results['success']:
                            logger.info(f"Transition condition met: '{current_status}' -> 'completed' (PR contains completing keyword and tests pass)")
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
        
        # Validate transition
        if not force and not issue_updater.validate_status_transition(current_status, new_status):
            logger.warning(
                f"Invalid status transition for issue #{issue_number}: "
                f"{current_status} -> {new_status}. Use --force to override."
            )
            return
        
        if not dry_run:
            issue_updater.update_issue_status(issue_number, new_status, force=force)
            issue_updater.add_status_comment(issue_number, new_status, status_details)
            if new_status == 'completed':
                priority_manager.adjust_priorities_after_completion(issue_number)
        else:
            logger.info(f"[DRY RUN] Would update issue #{issue_number} status to {new_status}")
            logger.info(f"[DRY RUN] Status details: {status_details}")
    else:
        logger.info(f"No status change needed for issue #{issue_number}: remains '{current_status}'")


if __name__ == '__main__':
    sys.exit(main())
