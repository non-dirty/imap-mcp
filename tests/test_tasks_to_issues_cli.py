"""
Tests for the tasks_to_issues_cli.py script that migrates tasks from TASKS.md to GitHub Issues using GitHub CLI.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add the scripts directory to the path so we can import tasks_to_issues_cli
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
import tasks_to_issues_cli as cli


@patch('subprocess.run')
class TestRunCommand(unittest.TestCase):
    """Test the run_command function."""
    
    def test_successful_command(self, mock_subprocess_run):
        """Test running a command successfully."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_subprocess_run.return_value = mock_result
        
        # Call the function
        result = cli.run_command("gh --version")
        
        # Verify
        self.assertEqual(result, "Command output")
        mock_subprocess_run.assert_called_once_with(
            "gh --version", shell=True, text=True, capture_output=True
        )
    
    def test_failed_command(self, mock_subprocess_run):
        """Test handling a command that fails."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error message"
        mock_subprocess_run.return_value = mock_result
        
        # Call the function
        result = cli.run_command("gh invalid")
        
        # Verify
        self.assertIsNone(result)
        mock_subprocess_run.assert_called_once()


class TestCreateRequiredLabels(unittest.TestCase):
    """Test the create_required_labels function."""
    
    @patch('tasks_to_issues_cli.run_command')
    def test_create_labels(self, mock_run_command):
        """Test creating GitHub labels."""
        # Setup mock
        mock_run_command.return_value = "Label created"
        
        # Call the function
        cli.create_required_labels()
        
        # Verify
        # Should be called for each status label (5) and priority labels (20)
        expected_calls = 25
        self.assertEqual(mock_run_command.call_count, expected_calls)
        
        # Check content of some calls
        calls = mock_run_command.call_args_list
        
        # Check for status:prioritized label
        found_status_prioritized = False
        for call in calls:
            cmd = call[0][0]
            if "status:prioritized" in cmd and "0075ca" in cmd:
                found_status_prioritized = True
                break
        self.assertTrue(found_status_prioritized, "status:prioritized label creation not found")
        
        # Check for a priority label
        found_priority_label = False
        for call in calls:
            cmd = call[0][0]
            if "priority:1" in cmd and "d93f0b" in cmd:
                found_priority_label = True
                break
        self.assertTrue(found_priority_label, "priority:1 label creation not found")


class TestParseTasks(unittest.TestCase):
    """Test the parse_tasks function."""
    
    def test_parse_tasks_valid_content(self):
        """Test parsing tasks from valid TASKS.md content."""
        # Mock content for TASKS.md
        mock_content = """
# IMAP MCP Server Implementation Tasks

## Implementation Tasks

### Task Tracker

| Priority | Task # | Status      | Description                                      |
|----------|--------|-------------|--------------------------------------------------|
| 5        | 21     | prioritized | Implement Gmail OAuth2 Authentication Flow       |
| 3        | 22     | prioritized | Implement Secure Token Storage                   |
| -        | 1      | completed   | Expand Core IMAP Client Tests                    |
| 1        | 24     | prioritized | Transition to Git Issues from tasks.md           |

### Implementation Details

#### 21. Implement Gmail OAuth2 Authentication Flow

**Description**:
Implement the OAuth2 flow for Gmail:
- Create the authentication flow
- Store tokens securely
"""
        
        # Patch open to return our mock content
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Call the function
            tasks = cli.parse_tasks()
            
            # Verify - should find 3 non-completed tasks
            self.assertEqual(len(tasks), 3)
            
            # Check specific task
            task21 = None
            for task in tasks:
                if task.get('task_number') == 21:
                    task21 = task
                    break
            
            self.assertIsNotNone(task21)
            self.assertEqual(task21['priority'], 5)
            self.assertEqual(task21['status'], 'prioritized')
            self.assertEqual(task21['description'], 'Implement Gmail OAuth2 Authentication Flow')
    
    def test_parse_tasks_no_details(self):
        """Test parsing tasks when no detailed sections are found."""
        # Mock content for TASKS.md with task table but no detailed descriptions
        mock_content = """
# IMAP MCP Server Implementation Tasks

## Implementation Tasks

### Task Tracker

| Priority | Task # | Status      | Description                                      |
|----------|--------|-------------|--------------------------------------------------|
| 5        | 21     | prioritized | Implement Gmail OAuth2 Authentication Flow       |
| 3        | 22     | prioritized | Implement Secure Token Storage                   |
"""
        
        # Patch open to return our mock content
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Call the function
            tasks = cli.parse_tasks()
            
            # Verify
            self.assertEqual(len(tasks), 2)
            
            # Verify task structure
            for task in tasks:
                self.assertIn('priority', task)
                self.assertIn('task_number', task)
                self.assertIn('status', task)
                self.assertIn('description', task)


class TestCreateIssueWithGh(unittest.TestCase):
    """Test the create_issue_with_gh function."""
    
    @patch('tasks_to_issues_cli.run_command')
    def test_create_issue(self, mock_run_command):
        """Test creating an issue with GitHub CLI."""
        # Setup mock
        mock_run_command.return_value = "Created issue #42"
        
        # Create a sample task
        task = {
            'task_number': 21,
            'priority': 5,
            'status': 'prioritized',
            'description': 'Implement Gmail OAuth2 Authentication Flow'
        }
        
        # Call the function
        result = cli.create_issue_with_gh(task)
        
        # Verify
        self.assertTrue(result)
        mock_run_command.assert_called_once()
        
        # Check command contains expected elements
        cmd = mock_run_command.call_args[0][0]
        self.assertIn('gh issue create', cmd)
        self.assertIn('--title', cmd)
        self.assertIn('Implement Gmail OAuth2 Authentication Flow', cmd)
        self.assertIn('--body', cmd)
        self.assertIn('--label "priority:5"', cmd)
        self.assertIn('--label "status:prioritized"', cmd)


class TestMainFunction(unittest.TestCase):
    """Test the main function."""
    
    @patch('tasks_to_issues_cli.create_issue_with_gh')
    @patch('tasks_to_issues_cli.parse_tasks')
    @patch('tasks_to_issues_cli.create_required_labels')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_function_dry_run(self, mock_args, mock_create_labels, mock_parse_tasks, mock_create_issue):
        """Test the main function in dry run mode."""
        # Setup mocks
        mock_args.return_value = type('Args', (), {
            'tasks_file': 'TASKS.md',
            'dry_run': True,
            'skip_labels': False
        })
        
        mock_parse_tasks.return_value = [
            {
                'task_number': 21,
                'priority': 5,
                'status': 'prioritized',
                'description': 'Implement Gmail OAuth2 Authentication Flow'
            },
            {
                'task_number': 22,
                'priority': 3,
                'status': 'prioritized',
                'description': 'Implement Secure Token Storage'
            }
        ]
        
        # Call the function
        with patch('sys.stdout'):  # Suppress print output for testing
            cli.main()
        
        # Verify
        mock_create_labels.assert_not_called()  # Should not create labels in dry run mode
        mock_parse_tasks.assert_called_once()
        mock_create_issue.assert_not_called()  # Should not create issues in dry run
    
    @patch('tasks_to_issues_cli.create_issue_with_gh')
    @patch('tasks_to_issues_cli.parse_tasks')
    @patch('tasks_to_issues_cli.create_required_labels')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_function_actual_run(self, mock_args, mock_create_labels, mock_parse_tasks, mock_create_issue):
        """Test the main function in actual run mode."""
        # Setup mocks
        mock_args.return_value = type('Args', (), {
            'tasks_file': 'TASKS.md',
            'dry_run': False,
            'skip_labels': False
        })
        
        mock_parse_tasks.return_value = [
            {
                'task_number': 21,
                'priority': 5,
                'status': 'prioritized',
                'description': 'Implement Gmail OAuth2 Authentication Flow'
            },
            {
                'task_number': 22,
                'priority': 3,
                'status': 'prioritized',
                'description': 'Implement Secure Token Storage'
            }
        ]
        
        mock_create_issue.return_value = True
        
        # Call the function
        with patch('sys.stdout'):  # Suppress print output for testing
            cli.main()
        
        # Verify
        mock_create_labels.assert_called_once()
        mock_parse_tasks.assert_called_once()
        self.assertEqual(mock_create_issue.call_count, 2)  # Should create both issues
    
    @patch('tasks_to_issues_cli.create_issue_with_gh')
    @patch('tasks_to_issues_cli.parse_tasks')
    @patch('tasks_to_issues_cli.create_required_labels')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_function_no_labels(self, mock_args, mock_create_labels, mock_parse_tasks, mock_create_issue):
        """Test the main function with skip_labels option."""
        # Setup mocks
        mock_args.return_value = type('Args', (), {
            'tasks_file': 'TASKS.md',
            'dry_run': False,
            'skip_labels': True
        })
        
        mock_parse_tasks.return_value = [
            {
                'task_number': 21,
                'priority': 5,
                'status': 'prioritized',
                'description': 'Implement Gmail OAuth2 Authentication Flow'
            }
        ]
        
        mock_create_issue.return_value = True
        
        # Call the function
        with patch('sys.stdout'):  # Suppress print output for testing
            cli.main()
        
        # Verify
        mock_create_labels.assert_not_called()  # Should not create labels
        mock_parse_tasks.assert_called_once()
        mock_create_issue.assert_called_once()


if __name__ == "__main__":
    unittest.main()
