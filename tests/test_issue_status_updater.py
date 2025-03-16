#!/usr/bin/env python
"""
Tests for the GitHub issue status updater.

This module tests the automatic update of GitHub issue statuses based on
git activity and test execution.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json
import sys
from pathlib import Path

# Add the scripts directory to the system path to import the module
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

from issue_status_updater import (
    CommitAnalyzer,
    PullRequestAnalyzer,
    TestResultsAnalyzer, 
    IssueUpdater,
    PriorityManager
)


class TestCommitAnalyzer(unittest.TestCase):
    """Test the CommitAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = CommitAnalyzer()
    
    @patch('issue_status_updater.subprocess.run')
    def test_get_recent_commits(self, mock_run):
        """Test getting recent commits."""
        # Mock the subprocess call to git log
        mock_process = MagicMock()
        mock_process.stdout = (
            "abcd1234,refs #5: Start implementing OAuth flow\n"
            "efgh5678,fixes #8: Fix token refresh logic\n"
            "ijkl9012,Update README\n"
        )
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        commits = self.analyzer.get_recent_commits(limit=3)
        
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0]['hash'], 'abcd1234')
        self.assertEqual(commits[0]['issue_refs'], [5])
        self.assertEqual(commits[0]['action'], 'refs')
        
        self.assertEqual(commits[1]['hash'], 'efgh5678')
        self.assertEqual(commits[1]['issue_refs'], [8])
        self.assertEqual(commits[1]['action'], 'fixes')
        
        self.assertEqual(commits[2]['hash'], 'ijkl9012')
        self.assertEqual(commits[2]['issue_refs'], [])
        self.assertEqual(commits[2]['action'], None)
    
    def test_parse_commit_message(self):
        """Test parsing commit messages for issue references."""
        # Test various formats of commit messages
        test_cases = [
            {
                'message': 'fixes #42: Fix authentication bug',
                'expected': {'issue_refs': [42], 'action': 'fixes'}
            },
            {
                'message': 'implements #100: Add OAuth flow',
                'expected': {'issue_refs': [100], 'action': 'implements'}
            },
            {
                'message': 'refs #5, #8: Update documentation',
                'expected': {'issue_refs': [5, 8], 'action': 'refs'}
            },
            {
                'message': 'Regular commit with no reference',
                'expected': {'issue_refs': [], 'action': None}
            },
            {
                'message': 'Multiple refs (closes #10, fixes #15)',
                'expected': {'issue_refs': [10, 15], 'action': 'closes'}
            }
        ]
        
        for case in test_cases:
            result = self.analyzer.parse_commit_message(case['message'])
            self.assertEqual(result['issue_refs'], case['expected']['issue_refs'])
            self.assertEqual(result['action'], case['expected']['action'])


class TestPullRequestAnalyzer(unittest.TestCase):
    """Test the PullRequestAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = PullRequestAnalyzer()
    
    @patch('issue_status_updater.mcp5_list_issues')
    def test_get_pull_requests(self, mock_list_issues):
        """Test getting pull requests."""
        # Mock the GitHub API call
        mock_list_issues.return_value = [
            {
                'number': 10,
                'title': 'Implement OAuth Flow',
                'body': 'This PR implements the OAuth flow. Fixes #5.',
                'labels': [{'name': 'type:pr'}],
                'state': 'open'
            },
            {
                'number': 11,
                'title': 'Update Documentation',
                'body': 'Update the API documentation. Refs #8.',
                'labels': [{'name': 'type:pr'}],
                'state': 'closed'
            }
        ]
        
        # Get open pull requests
        prs = self.analyzer.get_pull_requests(state='open')
        
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0]['number'], 10)
        self.assertEqual(prs[0]['linked_issues'], [5])
        
        # Get all pull requests
        mock_list_issues.return_value = [
            {
                'number': 10,
                'title': 'Implement OAuth Flow',
                'body': 'This PR implements the OAuth flow. Fixes #5.',
                'labels': [{'name': 'type:pr'}],
                'state': 'open'
            },
            {
                'number': 11,
                'title': 'Update Documentation',
                'body': 'Update the API documentation. Refs #8.',
                'labels': [{'name': 'type:pr'}],
                'state': 'closed'
            }
        ]
        
        prs = self.analyzer.get_pull_requests(state='all')
        
        self.assertEqual(len(prs), 2)
        self.assertEqual(prs[0]['number'], 10)
        self.assertEqual(prs[0]['linked_issues'], [5])
        self.assertEqual(prs[1]['number'], 11)
        self.assertEqual(prs[1]['linked_issues'], [8])
    
    def test_extract_linked_issues(self):
        """Test extracting linked issues from PR title and body."""
        test_cases = [
            {
                'title': 'Implement OAuth Flow',
                'body': 'This PR implements the OAuth flow. Fixes #5.',
                'expected': [5]
            },
            {
                'title': 'Fix #10, #15: Authentication bugs',
                'body': 'Addressing multiple auth issues. Closes #10 and fixes #15.',
                'expected': [10, 15]
            },
            {
                'title': 'Documentation update',
                'body': 'General documentation improvements.',
                'expected': []
            },
            {
                'title': 'Fixes #8 - Token refresh',
                'body': 'Also related to #9 but does not fix it.',
                'expected': [8, 9]
            }
        ]
        
        for case in test_cases:
            result = self.analyzer.extract_linked_issues(case['title'], case['body'])
            self.assertEqual(sorted(result), sorted(case['expected']))


class TestTestResultsAnalyzer(unittest.TestCase):
    """Test the TestResultsAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = TestResultsAnalyzer()
    
    @patch('issue_status_updater.subprocess.run')
    def test_run_tests_for_issue(self, mock_run):
        """Test running tests related to an issue."""
        # Create a mock test result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Ran 5 tests, all passed!"
        mock_run.return_value = mock_process
        
        # Mock file paths for test discovery
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock test files
            issue_5_file = os.path.join(tmpdir, "test_oauth_flow.py")
            with open(issue_5_file, "w") as f:
                f.write("# Tests for Issue #5 - OAuth Flow")
            
            # Run tests for issue #5
            result = self.analyzer.run_tests_for_issue(5, test_dir=tmpdir)
            
            self.assertTrue(result['success'])
            self.assertEqual(result['test_files'], [issue_5_file])
    
    @patch('issue_status_updater.subprocess.run')
    def test_get_coverage_for_issue(self, mock_run):
        """Test getting test coverage for an issue."""
        # Mock the coverage report
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "92% coverage"
        mock_run.return_value = mock_process
        
        # Create a temporary coverage data file
        with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
            coverage_data = {
                'files': {
                    'imap_mcp/oauth_flow.py': {
                        'summary': {
                            'covered_lines': 45,
                            'num_statements': 50,
                            'percent_covered': 90.0
                        }
                    }
                }
            }
            tmp.write(json.dumps(coverage_data).encode())
            tmp.flush()
            
            # Mock finding issue-related files
            with patch('issue_status_updater.TestResultsAnalyzer.find_files_for_issue') as mock_find:
                mock_find.return_value = ['imap_mcp/oauth_flow.py']
                
                result = self.analyzer.get_coverage_for_issue(5, coverage_file=tmp.name)
                
                self.assertEqual(result['coverage'], 90.0)
                self.assertEqual(result['files'], ['imap_mcp/oauth_flow.py'])


class TestIssueUpdater(unittest.TestCase):
    """Test the IssueUpdater class."""
    
    def setUp(self):
        """Set up test environment."""
        self.updater = IssueUpdater(
            owner='imap-mcp-owner',
            repo='imap-mcp'
        )
    
    @patch('issue_status_updater.mcp5_get_issue')
    @patch('issue_status_updater.mcp5_update_issue')
    def test_update_issue_status(self, mock_update_issue, mock_get_issue):
        """Test updating issue status."""
        # Mock getting issue details
        mock_get_issue.return_value = {
            'number': 5,
            'title': 'Implement OAuth Flow',
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'}
            ]
        }
        
        # Test updating to "in-progress"
        self.updater.update_issue_status(5, 'in-progress')
        
        # Verify correct API calls
        mock_update_issue.assert_called_once()
        args = mock_update_issue.call_args[1]
        self.assertEqual(args['issue_number'], 5)
        self.assertEqual(args['owner'], 'imap-mcp-owner')
        self.assertEqual(args['repo'], 'imap-mcp')
        self.assertIn('status:in-progress', args['labels'])
        self.assertNotIn('status:prioritized', args['labels'])
        
        # Test updating to "completed"
        mock_update_issue.reset_mock()
        mock_get_issue.return_value = {
            'number': 5,
            'title': 'Implement OAuth Flow',
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'}
            ]
        }
        
        self.updater.update_issue_status(5, 'completed')
        
        # Verify correct API calls
        mock_update_issue.assert_called_once()
        args = mock_update_issue.call_args[1]
        self.assertEqual(args['issue_number'], 5)
        self.assertIn('status:completed', args['labels'])
        self.assertNotIn('status:in-progress', args['labels'])
    
    @patch('issue_status_updater.mcp5_add_issue_comment')
    def test_add_status_comment(self, mock_add_comment):
        """Test adding a status comment to an issue."""
        # Test adding a "started" comment
        self.updater.add_status_comment(
            issue_number=5,
            status='in-progress',
            details={'commit': 'abcd1234', 'message': 'Start implementing OAuth flow'}
        )
        
        # Verify comment was added
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        self.assertEqual(args['issue_number'], 5)
        self.assertEqual(args['owner'], 'imap-mcp-owner')
        self.assertEqual(args['repo'], 'imap-mcp')
        self.assertIn('Status changed to: `in-progress`', args['body'])
        self.assertIn('abcd1234', args['body'])
        
        # Test adding a "completed" comment with test results
        mock_add_comment.reset_mock()
        
        self.updater.add_status_comment(
            issue_number=5,
            status='completed',
            details={
                'test_results': {'success': True, 'coverage': 92.5},
                'pr_number': 10
            }
        )
        
        # Verify comment was added
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        self.assertEqual(args['issue_number'], 5)
        self.assertIn('Status changed to: `completed`', args['body'])
        self.assertIn('Test coverage: 92.5%', args['body'])
        self.assertIn('PR #10', args['body'])


class TestPriorityManager(unittest.TestCase):
    """Test the PriorityManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.priority_manager = PriorityManager(
            owner='imap-mcp-owner',
            repo='imap-mcp'
        )
    
    @patch('issue_status_updater.mcp5_list_issues')
    def test_get_prioritized_issues(self, mock_list_issues):
        """Test getting prioritized issues."""
        # Mock the GitHub API call to return prioritized issues
        mock_list_issues.return_value = [
            {
                'number': 5,
                'title': 'Implement OAuth Flow',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:1'}
                ]
            },
            {
                'number': 8,
                'title': 'Fix Token Refresh',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:2'}
                ]
            },
            {
                'number': 10,
                'title': 'Update Documentation',
                'labels': [
                    {'name': 'status:completed'},
                    {'name': 'priority:3'}
                ]
            }
        ]
        
        # Get prioritized issues
        issues = self.priority_manager.get_prioritized_issues()
        
        # Verify that only prioritized issues are returned
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]['number'], 5)
        self.assertEqual(issues[0]['priority'], 1)
        self.assertEqual(issues[1]['number'], 8)
        self.assertEqual(issues[1]['priority'], 2)
    
    @patch('issue_status_updater.mcp5_update_issue')
    @patch('issue_status_updater.mcp5_list_issues')
    def test_adjust_priorities(self, mock_list_issues, mock_update_issue):
        """Test adjusting priorities when a task is completed."""
        # Mock getting all prioritized issues
        mock_list_issues.return_value = [
            {
                'number': 5,
                'title': 'Implement OAuth Flow',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:1'}
                ]
            },
            {
                'number': 8,
                'title': 'Fix Token Refresh',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:2'}
                ]
            },
            {
                'number': 12,
                'title': 'Add Error Handling',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:3'}
                ]
            }
        ]
        
        # Test completing issue with priority 1
        self.priority_manager.adjust_priorities_after_completion(5)
        
        # Verify that priorities are adjusted correctly
        # Issue #8 should now have priority 1
        # Issue #12 should now have priority 2
        self.assertEqual(mock_update_issue.call_count, 2)
        
        # Since we can't predict the order of calls, check that both expected calls were made
        priority_updates = {}
        for call in mock_update_issue.call_args_list:
            args = call[1]
            issue_number = args['issue_number']
            labels = args['labels']
            
            # Extract priority from labels
            priority = None
            for label in labels:
                if label.startswith('priority:'):
                    priority = int(label.split(':')[1])
                    break
            
            priority_updates[issue_number] = priority
        
        self.assertEqual(priority_updates[8], 1)
        self.assertEqual(priority_updates[12], 2)
    
    @patch('issue_status_updater.mcp5_add_issue_comment')
    @patch('issue_status_updater.mcp5_update_issue')
    @patch('issue_status_updater.mcp5_list_issues')
    def test_notify_priority_changes(self, mock_list_issues, mock_update_issue, mock_add_comment):
        """Test notifications about priority changes."""
        # Mock getting all prioritized issues
        mock_list_issues.return_value = [
            {
                'number': 5,
                'title': 'Implement OAuth Flow',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:1'}
                ]
            },
            {
                'number': 8,
                'title': 'Fix Token Refresh',
                'labels': [
                    {'name': 'status:prioritized'},
                    {'name': 'priority:2'}
                ]
            }
        ]
        
        # Test completing issue with priority 1
        self.priority_manager.adjust_priorities_after_completion(5, notify=True)
        
        # Verify that a comment was added to the issue
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        self.assertEqual(args['issue_number'], 8)
        self.assertIn('Priority updated from 2 to 1', args['body'])


if __name__ == '__main__':
    unittest.main()
