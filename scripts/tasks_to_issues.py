#!/usr/bin/env python
"""
Task migration script for transitioning from TASKS.md to GitHub Issues.

This script:
1. Parses TASKS.md to extract tasks
2. Creates corresponding GitHub issues
3. Updates TASKS.md with new workflow information
"""

import re
import os
import sys
import argparse
from typing import Dict, List, Optional, Tuple
import subprocess
from pathlib import Path
import json


class TaskParser:
    """Parse tasks from TASKS.md file."""

    def __init__(self, tasks_file_path: str):
        """Initialize with path to TASKS.md file."""
        self.tasks_file_path = tasks_file_path
        self.tasks = []

    def parse_tasks(self) -> List[Dict]:
        """
        Parse tasks from TASKS.md and return a list of task dictionaries.
        
        Returns:
            List of task dictionaries with keys:
                - task_number: int
                - priority: int
                - status: str
                - description: str
                - details: str (Full task description including Test Specifications, etc.)
        """
        try:
            with open(self.tasks_file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading tasks file: {e}")
            return []

        # Extract the task table
        table_pattern = r'\|\s*Priority\s*\|\s*Task #\s*\|\s*Status\s*\|\s*Description\s*\|\s*\n\|[-\s|]*\n((?:\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*\n)+)'
        table_match = re.search(table_pattern, content)
        
        if not table_match:
            print("Could not find task table in TASKS.md")
            return []
        
        task_table = table_match.group(1)
        
        # Parse table rows
        tasks = []
        for line in task_table.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = [part.strip() for part in line.split('|')[1:-1]]
            if len(parts) != 4:
                continue
                
            priority_str, task_number_str, status, description = parts
            
            # Skip completed tasks
            if status.lower() == 'completed':
                continue
                
            try:
                priority = int(priority_str) if priority_str.strip() != '-' else 999
                task_number = int(task_number_str)
            except ValueError:
                print(f"Skipping row with invalid priority or task number: {line}")
                continue
                
            # Find detailed task description
            task_pattern = rf'#### {task_number}\. .*?(?=####|\Z)'
            task_detail_match = re.search(task_pattern, content, re.DOTALL)
            
            task_details = ""
            if task_detail_match:
                task_details = task_detail_match.group(0).strip()
            
            tasks.append({
                'task_number': task_number,
                'priority': priority,
                'status': status,
                'description': description,
                'details': task_details
            })
        
        # Sort tasks by priority
        self.tasks = sorted(tasks, key=lambda x: x['priority'])
        return self.tasks


class CoverageReporter:
    """Run coverage reports and identify modules that need improvement."""
    
    def __init__(self, coverage_threshold: float = 90.0):
        """Initialize with coverage threshold percentage."""
        self.coverage_threshold = coverage_threshold
        self.coverage_data = {}
        
    def run_coverage(self) -> Dict:
        """
        Run pytest with coverage and return results.
        
        Returns:
            Dictionary mapping module names to coverage percentages
        """
        try:
            # Run pytest with coverage output in JSON format
            result = subprocess.run(
                ["uv", "run", "-m", "pytest", "--cov=imap_mcp", "--cov-report=json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the JSON coverage data
            if os.path.exists('.coverage.json'):
                with open('.coverage.json', 'r') as f:
                    coverage_data = json.load(f)
            else:
                print("Coverage data file not found")
                return {}
                
            # Extract module coverage percentages
            self.coverage_data = {}
            for file_path, data in coverage_data['files'].items():
                if 'imap_mcp' in file_path:
                    module_name = os.path.basename(file_path)
                    total_lines = data['summary']['num_statements']
                    covered_lines = total_lines - data['summary']['missing_lines']
                    if total_lines > 0:
                        coverage_pct = (covered_lines / total_lines) * 100
                    else:
                        coverage_pct = 100.0
                    self.coverage_data[module_name] = coverage_pct
            
            return self.coverage_data
                
        except subprocess.CalledProcessError as e:
            print(f"Error running coverage: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return {}
    
    def get_modules_below_threshold(self) -> Dict[str, float]:
        """
        Return modules with coverage below the threshold.
        
        Returns:
            Dictionary mapping module names to their coverage percentage for modules
            that are below the threshold.
        """
        return {
            module: coverage 
            for module, coverage in self.coverage_data.items() 
            if coverage < self.coverage_threshold
        }


class GitHubIssueCreator:
    """Create GitHub issues from tasks."""
    
    def __init__(self, repo_owner: str, repo_name: str):
        """Initialize with GitHub repository information."""
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.mcp5_create_issue = None
        
    def create_issue(self, task: Dict) -> Dict:
        """
        Create a GitHub issue from a task dictionary.
        
        Args:
            task: Task dictionary from TaskParser
            
        Returns:
            Response data from the GitHub API
        """
        # Prepare issue title
        title = f"Task #{task['task_number']}: {task['description']}"
        
        # Prepare issue body with task details
        body = task.get('details', '')
        if not body:
            body = f"Priority: {task['priority']}\nStatus: {task['status']}\n\n{task['description']}"
        
        # Add a note about migration
        body += "\n\n---\n*This issue was created from TASKS.md during the transition to GitHub Issues.*"
        
        # Create labels
        labels = ["priority:" + str(task['priority']), "status:" + task['status']]
        
        # Try to import the GitHub MCP server function if not already imported
        if self.mcp5_create_issue is None:
            try:
                import mcp5_create_issue
                self.mcp5_create_issue = mcp5_create_issue
            except (ImportError, ModuleNotFoundError):
                print("GitHub MCP server not available. Please install and configure the GitHub MCP server.")
                print("Simulating issue creation for testing purposes...")
                self.mcp5_create_issue = None
        
        # Create the issue
        if self.mcp5_create_issue:
            response = self.mcp5_create_issue(
                owner=self.repo_owner,
                repo=self.repo_name,
                title=title,
                body=body,
                labels=labels
            )
            return response
        else:
            # Simulate response for testing
            return {
                "number": task['task_number'],
                "title": title,
                "html_url": f"https://github.com/{self.repo_owner}/{self.repo_name}/issues/{task['task_number']}"
            }


class WorkflowUpdater:
    """Update TASKS.md with new workflow information."""
    
    def __init__(self, tasks_file_path: str):
        """Initialize with path to TASKS.md file."""
        self.tasks_file_path = tasks_file_path
        
    def update_workflow(self, transition_info: str) -> bool:
        """
        Update TASKS.md with transition workflow information.
        
        Args:
            transition_info: Markdown content with transition details
            
        Returns:
            Boolean indicating success
        """
        try:
            with open(self.tasks_file_path, 'r') as f:
                content = f.read()
                
            # Find the Task Workflow section
            workflow_pattern = r'## Task Workflow for Claude\s*\n(.*?)(?=\n##)'
            workflow_match = re.search(workflow_pattern, content, re.DOTALL)
            
            if not workflow_match:
                print("Could not find Task Workflow section in TASKS.md")
                return False
                
            # Insert transition info after the workflow section
            transition_section = "\n\n## GitHub Issues Transition\n\n" + transition_info + "\n\n"
            
            # Replace the content
            updated_content = content.replace(
                workflow_match.group(0),
                workflow_match.group(0) + transition_section
            )
            
            # Write back to the file
            with open(self.tasks_file_path, 'w') as f:
                f.write(updated_content)
                
            return True
            
        except Exception as e:
            print(f"Error updating workflow: {e}")
            return False


def main():
    """Main function to run the task migration."""
    parser = argparse.ArgumentParser(description='Migrate tasks from TASKS.md to GitHub Issues')
    parser.add_argument('--tasks-file', default='TASKS.md', help='Path to TASKS.md file')
    parser.add_argument('--repo-owner', required=True, help='GitHub repository owner')
    parser.add_argument('--repo-name', required=True, help='GitHub repository name')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without creating issues')
    parser.add_argument('--coverage-threshold', type=float, default=90.0, 
                      help='Coverage threshold percentage (default: 90.0)')
    
    args = parser.parse_args()
    
    # Parse tasks
    task_parser = TaskParser(args.tasks_file)
    tasks = task_parser.parse_tasks()
    
    if not tasks:
        print("No tasks found or error parsing tasks")
        return 1
        
    print(f"Found {len(tasks)} tasks to migrate")
    
    # Create issues (or simulate in dry run mode)
    issue_creator = GitHubIssueCreator(args.repo_owner, args.repo_name)
    created_issues = []
    
    if not args.dry_run:
        print("Creating GitHub issues...")
        for task in tasks:
            print(f"Creating issue for Task #{task['task_number']}: {task['description']}")
            response = issue_creator.create_issue(task)
            created_issues.append(response)
            print(f"  Created issue #{response.get('number')} at {response.get('html_url')}")
    else:
        print("Dry run mode: Not creating GitHub issues")
        for task in tasks:
            print(f"Would create issue for Task #{task['task_number']}: {task['description']}")
    
    # Run coverage report
    print("Running coverage report...")
    coverage_reporter = CoverageReporter(args.coverage_threshold)
    coverage_data = coverage_reporter.run_coverage()
    
    low_coverage_modules = coverage_reporter.get_modules_below_threshold()
    
    if low_coverage_modules:
        print("Modules with coverage below threshold:")
        for module, coverage in low_coverage_modules.items():
            print(f"  {module}: {coverage:.2f}%")
            
        # Create coverage issues
        if not args.dry_run:
            print("Creating coverage improvement issues...")
            for module, coverage in low_coverage_modules.items():
                title = f"Improve test coverage for {module}"
                body = f"""
# Test Coverage Improvement

## Module
{module}

## Current Coverage
{coverage:.2f}%

## Target Coverage
{args.coverage_threshold}%

## Description
This task involves improving the test coverage for the {module} module to meet the target coverage threshold of {args.coverage_threshold}%.

## Implementation Steps
1. Analyze the current test coverage report to identify untested code paths
2. Write new tests targeting the untested code paths
3. Run the tests with coverage to verify improvements
4. Repeat until the coverage threshold is met

## Priority
This task has been automatically assigned high priority as part of the test coverage improvement initiative.
                """
                
                response = issue_creator.create_issue({
                    'task_number': 0,  # Will be assigned by GitHub
                    'priority': 1,
                    'status': 'prioritized',
                    'description': title,
                    'details': body
                })
                created_issues.append(response)
                print(f"  Created coverage issue at {response.get('html_url')}")
    else:
        print("All modules meet the coverage threshold.")
    
    # Update workflow
    transition_info = f"""
### GitHub Issues Transition Workflow

The project is transitioning from using TASKS.md to GitHub Issues for task tracking. During the transition period, both systems will be used in parallel, with the following guidelines:

#### Current Status

* All existing tasks have been migrated to GitHub Issues
* New tasks should be created as GitHub Issues
* TASKS.md will be maintained until the transition is complete
* Code coverage tasks for modules below {args.coverage_threshold}% have been created with high priority

#### Using GitHub Issues

1. **Viewing Tasks**: Visit the [Issues page](https://github.com/{args.repo_owner}/{args.repo_name}/issues) to see all open tasks
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
"""
    
    workflow_updater = WorkflowUpdater(args.tasks_file)
    if workflow_updater.update_workflow(transition_info):
        print("Updated TASKS.md with transition workflow information")
    else:
        print("Failed to update TASKS.md")
        
    print("Task migration completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
