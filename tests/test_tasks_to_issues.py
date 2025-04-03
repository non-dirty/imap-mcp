"""
Tests for the tasks_to_issues.py script that migrates tasks from TASKS.md to GitHub Issues.
"""

import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add the scripts directory to the path so we can import tasks_to_issues
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
import tasks_to_issues


class TestTaskParser(unittest.TestCase):
    """Test the TaskParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_tasks_content = """
# IMAP MCP Server Implementation Tasks

## Task Workflow for Claude

## Implementation Tasks

### Task Tracker

| Priority | Task # | Status      | Description                                      |
|----------|--------|-------------|--------------------------------------------------|
| 5        | 21     | prioritized | Implement Gmail OAuth2 Authentication Flow       |
| 3        | 22     | prioritized | Implement Secure Token Storage                   |
| -        | 1      | completed   | Expand Core IMAP Client Tests                    |
| 1        | 24     | prioritized | Transition to Git Issues from tasks.md           |

### Process Improvement Tasks

#### 21. Implement Gmail OAuth2 Authentication Flow

**Task Name**: Integrate Gmail OAuth2 authentication

**Description**:
Implement the OAuth2 flow for Gmail:
- Create the authentication flow
- Store tokens securely
- Refresh tokens when needed
- Test the authentication process

#### 24. Transition to Git Issues from tasks.md

**Task Name**: Integrate Git issues

**Description**:
Leverage Git issues to manage tasks lifecycle:
- Create issues in Git repository
- Update TASKS.md with new workflow
"""
    
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_tasks(self, mock_file):
        """Test parsing tasks from the TASKS.md file."""
        # Set up the mock to return our sample content
        mock_file.return_value.__enter__.return_value.read.return_value = self.sample_tasks_content
        
        parser = tasks_to_issues.TaskParser("fake_path.md")
        tasks = parser.parse_tasks()
        
        # Assert that we got the right number of active tasks
        self.assertEqual(len(tasks), 3, "Should find 3 active tasks (excluding completed ones)")
        
        # Assert that tasks are sorted by priority
        self.assertEqual(tasks[0]['task_number'], 24, "First task should be #24 (priority 1)")
        self.assertEqual(tasks[1]['task_number'], 22, "Second task should be #22 (priority 3)")
        self.assertEqual(tasks[2]['task_number'], 21, "Third task should be #21 (priority 5)")
        
        # Check task details
        self.assertEqual(tasks[0]['description'], "Transition to Git Issues from tasks.md")
        self.assertTrue("Leverage Git issues to manage tasks lifecycle" in tasks[0]['details'])
    
    @patch("builtins.open")
    def test_parse_tasks_file_error(self, mock_file):
        """Test handling of file read errors."""
        mock_file.side_effect = IOError("File not found")
        
        parser = tasks_to_issues.TaskParser("non_existent_file.md")
        tasks = parser.parse_tasks()
        
        self.assertEqual(len(tasks), 0, "Should return empty list on file error")


class TestCoverageReporter(unittest.TestCase):
    """Test the CoverageReporter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_coverage_data = {
            "files": {
                "imap_mcp/server.py": {
                    "summary": {
                        "num_statements": 100,
                        "missing_lines": 15,
                        "excluded_lines": 0
                    }
                },
                "imap_mcp/client.py": {
                    "summary": {
                        "num_statements": 80,
                        "missing_lines": 5,
                        "excluded_lines": 0
                    }
                },
                "imap_mcp/low_coverage.py": {
                    "summary": {
                        "num_statements": 50,
                        "missing_lines": 20,
                        "excluded_lines": 0
                    }
                }
            }
        }
    
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_coverage(self, mock_file, mock_exists, mock_subprocess):
        """Test running coverage reports."""
        # Set up mocks
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(self.sample_coverage_data)
        
        reporter = tasks_to_issues.CoverageReporter(90.0)
        coverage_data = reporter.run_coverage()
        
        # Check that coverage data was parsed correctly
        self.assertEqual(len(coverage_data), 3, "Should find 3 modules")
        self.assertEqual(coverage_data["server.py"], 85.0, "Server coverage should be 85%")
        self.assertEqual(coverage_data["client.py"], 93.75, "Client coverage should be 93.75%")
        self.assertEqual(coverage_data["low_coverage.py"], 60.0, "Low coverage module should be 60%")
    
    def test_get_modules_below_threshold(self):
        """Test identifying modules below coverage threshold."""
        reporter = tasks_to_issues.CoverageReporter(90.0)
        
        # Manually set coverage data
        reporter.coverage_data = {
            "server.py": 85.0,
            "client.py": 93.75,
            "low_coverage.py": 60.0
        }
        
        low_coverage = reporter.get_modules_below_threshold()
        
        # Check that we correctly identified modules below threshold
        self.assertEqual(len(low_coverage), 2, "Should find 2 modules below threshold")
        self.assertTrue("server.py" in low_coverage, "Server should be below threshold")
        self.assertTrue("low_coverage.py" in low_coverage, "Low coverage module should be below threshold")
        self.assertFalse("client.py" in low_coverage, "Client should not be below threshold")


class TestGitHubIssueCreator(unittest.TestCase):
    """Test the GitHubIssueCreator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_task = {
            'task_number': 24,
            'priority': 1,
            'status': 'prioritized',
            'description': 'Transition to Git Issues from tasks.md',
            'details': """#### 24. Transition to Git Issues from tasks.md

**Task Name**: Integrate Git issues

**Description**:
Leverage Git issues to manage tasks lifecycle:
- Create issues in Git repository
- Update TASKS.md with new workflow"""
        }
    
    def test_create_issue(self):
        """Test creating a GitHub issue from a task."""
        # Mock the import statement to avoid actual import
        with patch.dict('sys.modules', {'scripts.mcp5_create_issue': MagicMock()}):
            # Set up the actual mcp5_create_issue function that would be called
            with patch('scripts.tasks_to_issues.mcp5_create_issue', create=True) as mock_create_issue:
                # Set up mock return value
                mock_return = {
                    "number": 42,
                    "title": f"Task #{self.sample_task['task_number']}: {self.sample_task['description']}",
                    "html_url": "https://github.com/owner/repo/issues/42"
                }
                mock_create_issue.return_value = mock_return
                
                # Create issue
                creator = tasks_to_issues.GitHubIssueCreator("owner", "repo")
                
                # Patch the import to return our mock
                with patch.object(creator, 'mcp5_create_issue', mock_create_issue):
                    result = creator.create_issue(self.sample_task)
                
                # Check that the issue was created with the right parameters
                mock_create_issue.assert_called_once()
                args, kwargs = mock_create_issue.call_args
                
                self.assertEqual(kwargs["owner"], "owner")
                self.assertEqual(kwargs["repo"], "repo")
                self.assertEqual(kwargs["title"], f"Task #{self.sample_task['task_number']}: {self.sample_task['description']}")
                self.assertTrue(self.sample_task['details'] in kwargs["body"])
                self.assertEqual(kwargs["labels"], ["priority:1", "status:prioritized"])
                
                # Check the result
                self.assertEqual(result, mock_return)
    
    def test_create_issue_no_mcp(self):
        """Test creating an issue when MCP server is not available."""
        # This test simulates the ImportError path
        creator = tasks_to_issues.GitHubIssueCreator("owner", "repo")
        
        with patch.dict(sys.modules, {"mcp5_create_issue": None}):
            result = creator.create_issue(self.sample_task)
            
            # Check that we got a simulated response
            self.assertEqual(result["number"], self.sample_task["task_number"])
            self.assertTrue(self.sample_task["description"] in result["title"])
            self.assertTrue("owner/repo" in result["html_url"])


class TestWorkflowUpdater(unittest.TestCase):
    """Test the WorkflowUpdater class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_tasks_content = """
# IMAP MCP Server Implementation Tasks

## Task Workflow for Claude

This is the original workflow description.

## Implementation Tasks

Other content...
"""
        self.transition_info = """
### GitHub Issues Transition Workflow

The project is transitioning from using TASKS.md to GitHub Issues for task tracking.
"""
    
    @patch("builtins.open", new_callable=mock_open)
    def test_update_workflow(self, mock_file):
        """Test updating the workflow in TASKS.md."""
        # Set up mock to return our sample content and capture writes
        mock_file.return_value.__enter__.return_value.read.return_value = self.sample_tasks_content
        
        updater = tasks_to_issues.WorkflowUpdater("fake_path.md")
        result = updater.update_workflow(self.transition_info)
        
        # Check result
        self.assertTrue(result, "Should return True on success")
        
        # Check that the file was written with the updated content
        mock_file.return_value.__enter__.return_value.write.assert_called_once()
        write_args = mock_file.return_value.__enter__.return_value.write.call_args[0][0]
        
        # Verify the content was updated correctly
        self.assertTrue("## Task Workflow for Claude" in write_args)
        self.assertTrue("This is the original workflow description." in write_args)
        self.assertTrue("## GitHub Issues Transition" in write_args)
        self.assertTrue("The project is transitioning from using TASKS.md to GitHub Issues" in write_args)


class TestMainFunction(unittest.TestCase):
    """Test the main function."""
    
    @patch("tasks_to_issues.TaskParser")
    @patch("tasks_to_issues.GitHubIssueCreator")
    @patch("tasks_to_issues.CoverageReporter")
    @patch("tasks_to_issues.WorkflowUpdater")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_args, mock_updater, mock_reporter, mock_creator, mock_parser):
        """Test the main function workflow."""
        # Set up mock arguments
        mock_args.return_value = MagicMock(
            tasks_file="TASKS.md",
            repo_owner="owner",
            repo_name="repo",
            dry_run=False,
            coverage_threshold=90.0
        )
        
        # Set up mock task parser
        mock_parser_instance = mock_parser.return_value
        mock_parser_instance.parse_tasks.return_value = [
            {
                'task_number': 24,
                'priority': 1,
                'status': 'prioritized',
                'description': 'Task 24 description',
                'details': 'Task 24 details'
            },
            {
                'task_number': 22,
                'priority': 3,
                'status': 'prioritized',
                'description': 'Task 22 description',
                'details': 'Task 22 details'
            }
        ]
        
        # Set up mock issue creator
        mock_creator_instance = mock_creator.return_value
        mock_creator_instance.create_issue.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42"
        }
        
        # Set up mock coverage reporter
        mock_reporter_instance = mock_reporter.return_value
        mock_reporter_instance.run_coverage.return_value = {
            "server.py": 85.0,
            "client.py": 95.0
        }
        mock_reporter_instance.get_modules_below_threshold.return_value = {
            "server.py": 85.0
        }
        
        # Set up mock workflow updater
        mock_updater_instance = mock_updater.return_value
        mock_updater_instance.update_workflow.return_value = True
        
        # Run the main function
        result = tasks_to_issues.main()
        
        # Verify the result
        self.assertEqual(result, 0, "Should return 0 on success")
        
        # Verify that all the components were called correctly
        mock_parser.assert_called_once_with("TASKS.md")
        mock_parser_instance.parse_tasks.assert_called_once()
        
        mock_creator.assert_called_once_with("owner", "repo")
        # Should create an issue for each task
        self.assertEqual(mock_creator_instance.create_issue.call_count, 3)  # 2 tasks + 1 coverage issue
        
        mock_reporter.assert_called_once_with(90.0)
        mock_reporter_instance.run_coverage.assert_called_once()
        mock_reporter_instance.get_modules_below_threshold.assert_called_once()
        
        mock_updater.assert_called_once_with("TASKS.md")
        mock_updater_instance.update_workflow.assert_called_once()
    
    @patch("tasks_to_issues.TaskParser")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_no_tasks(self, mock_args, mock_parser):
        """Test main function when no tasks are found."""
        # Set up mock arguments
        mock_args.return_value = MagicMock(
            tasks_file="TASKS.md",
            repo_owner="owner",
            repo_name="repo",
            dry_run=False,
            coverage_threshold=90.0
        )
        
        # Set up mock task parser to return empty list
        mock_parser_instance = mock_parser.return_value
        mock_parser_instance.parse_tasks.return_value = []
        
        # Run the main function
        result = tasks_to_issues.main()
        
        # Verify the result
        self.assertEqual(result, 1, "Should return 1 on failure")


if __name__ == "__main__":
    unittest.main()
