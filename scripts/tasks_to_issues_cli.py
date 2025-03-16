#!/usr/bin/env python
"""
Simplified task migration script using GitHub CLI (gh) to transition from TASKS.md to GitHub Issues.

This script:
1. Creates necessary labels in GitHub repo
2. Parses TASKS.md to extract tasks
3. Uses 'gh issue create' to create corresponding GitHub issues
4. Provides a simple one-step migration process

Requirements: 
- GitHub CLI (gh) must be installed and authenticated
- Run from the root of the repository
"""

import re
import os
import sys
import argparse
import subprocess
from typing import Dict, List, Optional, Tuple


def run_command(cmd, capture_output=True):
    """Run a shell command and return the output."""
    result = subprocess.run(cmd, shell=True, text=True, capture_output=capture_output)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip() if capture_output else True


def create_required_labels():
    """Create all required GitHub labels for task tracking."""
    print("Creating required GitHub labels...")
    
    # Define status labels
    status_labels = [
        {"name": "status:prioritized", "color": "0075ca", "description": "Task is prioritized but not started"},
        {"name": "status:in-progress", "color": "fbca04", "description": "Task is in progress"},
        {"name": "status:completed", "color": "0e8a16", "description": "Task is completed"},
        {"name": "status:reviewed", "color": "8250df", "description": "Task has been reviewed"},
        {"name": "status:archived", "color": "6e6e6e", "description": "Task has been archived"}
    ]
    
    # Define priority labels (1-20)
    priority_labels = [
        {"name": f"priority:{i}", "color": "d93f0b", "description": f"Priority level {i}"}
        for i in range(1, 21)
    ]
    
    # Combine all labels
    all_labels = status_labels + priority_labels
    
    # Create each label
    created_count = 0
    for label in all_labels:
        cmd = f'gh label create "{label["name"]}" --color "{label["color"]}" --description "{label["description"]}" || true'
        if run_command(cmd, capture_output=False):
            created_count += 1
    
    print(f"Created or confirmed {created_count} labels")
    return created_count > 0


def parse_tasks(tasks_file='TASKS.md'):
    """
    Parse tasks from TASKS.md file.
    
    Returns:
        List of dictionaries with task information
    """
    try:
        with open(tasks_file, 'r') as f:
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
    
    table_content = table_match.group(1)
    
    # Extract tasks from table
    tasks = []
    for line in table_content.strip().split('\n'):
        if not line.startswith('|'):
            continue
            
        columns = [col.strip() for col in line.split('|')[1:-1]]
        if len(columns) != 4:
            continue
            
        priority, task_number, status, description = columns
        
        # Skip tasks that are already completed
        if status.lower() == 'completed':
            continue
            
        try:
            task = {
                'priority': int(priority),
                'task_number': int(task_number.strip()),
                'status': status,
                'description': description,
            }
            tasks.append(task)
        except ValueError:
            # Skip entries that don't have proper number values
            continue
    
    # Sort tasks by priority
    tasks.sort(key=lambda x: x['priority'])
    return tasks


def create_issue_with_gh(task):
    """Create GitHub issue using gh CLI."""
    title = f"Task #{task['task_number']}: {task['description']}"
    
    # Build the body with task information
    body = f"## Original Task Information\n\n"
    body += f"- Priority: {task['priority']}\n"
    body += f"- Task Number: {task['task_number']}\n"
    body += f"- Original Status: {task['status']}\n\n"
    body += f"## Description\n\n{task['description']}\n\n"
    
    # Create labels - use multiple --label parameters instead of comma-separated
    priority_label = f"priority:{task['priority']}"
    status_label = f"status:{task['status'].lower()}"
    
    # Build the gh command
    cmd = f'gh issue create --title "{title}" --body "{body}" --label "{priority_label}" --label "{status_label}"'
    
    # Run the command
    print(f"Creating issue: {title}")
    result = run_command(cmd)
    
    if result:
        print(f"Created issue: {result}")
        return True
    else:
        print(f"Failed to create issue for task #{task['task_number']}")
        return False


def main():
    """Main function to run the migration."""
    parser = argparse.ArgumentParser(description='Migrate tasks from TASKS.md to GitHub Issues using gh CLI')
    parser.add_argument('--tasks-file', default='TASKS.md', help='Path to TASKS.md file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without creating issues')
    parser.add_argument('--skip-labels', action='store_true', help='Skip creating labels')
    
    args = parser.parse_args()
    
    # Check if gh CLI is available
    if not run_command("gh --version", capture_output=True):
        print("GitHub CLI (gh) is not installed or not in PATH. Please install it and try again.")
        print("See https://cli.github.com/ for installation instructions.")
        return 1
    
    # Check if gh is authenticated
    if not run_command("gh auth status", capture_output=False):
        print("You are not authenticated with GitHub CLI. Please run 'gh auth login' and try again.")
        return 1
    
    # Create required labels
    if not args.skip_labels and not args.dry_run:
        create_required_labels()
    
    # Parse tasks
    tasks = parse_tasks(args.tasks_file)
    
    if not tasks:
        print("No incomplete tasks found in TASKS.md")
        return 0
    
    print(f"Found {len(tasks)} tasks to migrate")
    
    # Create issues or simulate in dry run mode
    if args.dry_run:
        print("Dry run mode: Not creating GitHub issues")
        for task in tasks:
            print(f"Would create issue for Task #{task['task_number']}: {task['description']}")
    else:
        created_count = 0
        for task in tasks:
            if create_issue_with_gh(task):
                created_count += 1
        
        print(f"\nMigration complete! Created {created_count} GitHub issues.")
        print("You can view them by running: gh issue list")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
