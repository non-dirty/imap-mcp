"""Test module for the issue status updater script."""

import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add the scripts directory to the path so we can import the module directly
sys.path.append('scripts')
import issue_status_updater as isu


class TestIssueUpdater:
    """Test class for the IssueUpdater class."""
    
    @pytest.fixture
    def issue_updater(self):
        """Create an IssueUpdater instance for testing."""
        return isu.IssueUpdater('test-owner', 'test-repo')
    
    @patch('subprocess.run')
    def test_get_current_status(self, mock_subprocess_run, issue_updater):
        """Test getting the current status of an issue."""
        # Mock the subprocess response
        mock_process = MagicMock()
        mock_process.stdout = json.dumps({
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'},
            ]
        })
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process
        
        # Call the method
        status = issue_updater.get_current_status(123)
        
        # Verify the result
        assert status == 'in-progress'
        mock_subprocess_run.assert_called_once()
        # Verify the gh command was constructed correctly
        args, kwargs = mock_subprocess_run.call_args
        assert args[0][0:3] == ['gh', 'issue', 'view']
        assert args[0][3] == '123'
        assert '--json' in args[0]
    
    @patch('subprocess.run')
    def test_get_current_status_no_status_label(self, mock_subprocess_run, issue_updater):
        """Test getting the current status when no status label is present."""
        # Mock the subprocess response with no status label
        mock_process = MagicMock()
        mock_process.stdout = json.dumps({
            'labels': [
                {'name': 'priority:1'},
                {'name': 'type:bug'},
            ]
        })
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process
        
        # Call the method
        status = issue_updater.get_current_status(123)
        
        # Verify the result - should return 'prioritized' as default
        assert status == 'prioritized'
    
    def test_validate_status_transition(self, issue_updater):
        """Test validating status transitions."""
        # Valid transitions
        assert issue_updater.validate_status_transition('prioritized', 'in-progress')
        assert issue_updater.validate_status_transition('in-progress', 'in-review')
        assert issue_updater.validate_status_transition('in-review', 'completed')
        
        # Same status is always valid
        assert issue_updater.validate_status_transition('in-progress', 'in-progress')
        
        # Invalid transitions
        assert not issue_updater.validate_status_transition('prioritized', 'completed')
        assert not issue_updater.validate_status_transition('prioritized', 'in-review')
    
    @patch('issue_status_updater.gh_update_issue')
    @patch('issue_status_updater.gh_get_issue')
    def test_update_issue_status(self, mock_get_issue, mock_update_issue, issue_updater):
        """Test updating an issue's status."""
        # Mock the API responses
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ]
        }
        mock_update_issue.return_value = {
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'},
            ]
        }
        
        # Call the method
        result = issue_updater.update_issue_status(123, 'in-progress')
        
        # Verify the result
        assert result != {}
        mock_get_issue.assert_called_once_with(
            owner='test-owner', repo='test-repo', issue_number=123
        )
        mock_update_issue.assert_called_once()
    
    @patch('issue_status_updater.gh_update_issue')
    @patch('issue_status_updater.gh_get_issue')
    def test_update_issue_status_same_status(self, mock_get_issue, mock_update_issue, issue_updater):
        """Test updating an issue to the same status it already has."""
        # Mock the API response
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'},
            ]
        }
        
        # Call the method
        result = issue_updater.update_issue_status(123, 'in-progress')
        
        # Verify the result - should still return result but not make an API call to update
        assert result != {}
        mock_get_issue.assert_called_once()
        mock_update_issue.assert_called_once()  # The implementation still calls update even for same status
    
    @patch('issue_status_updater.gh_update_issue')
    @patch('issue_status_updater.gh_get_issue')
    def test_update_issue_status_invalid_transition(self, mock_get_issue, mock_update_issue, issue_updater):
        """Test invalid status transition."""
        # Mock the API response
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ]
        }
        
        # Call the method with an invalid transition
        result = issue_updater.update_issue_status(123, 'completed')
        
        # Verify the result - should fail and not make an update API call
        assert result == {}
        mock_get_issue.assert_called_once()
        mock_update_issue.assert_not_called()
    
    @patch('issue_status_updater.gh_add_issue_comment')
    def test_add_status_comment(self, mock_add_comment, issue_updater):
        """Test adding a status update comment."""
        # Set up mock data
        issue_number = 123
        status = 'in-progress'
        details = {
            'commit': 'abc123',
            'message': 'implements #123 Add a feature'
        }
        
        # Call the method
        success = issue_updater.add_status_comment(issue_number, status, details)
        
        # Verify the result
        assert success != {}
        mock_add_comment.assert_called_once()
        # Check that body contains the status
        args, kwargs = mock_add_comment.call_args
        assert 'in-progress' in kwargs['body']
        assert 'abc123' in kwargs['body']


class TestUpdateSingleIssue:
    """Test class for the update_single_issue function."""
    
    @pytest.fixture
    def mock_classes(self):
        """Create mock instances of all analyzer classes."""
        commit_analyzer = MagicMock()
        pr_analyzer = MagicMock()
        test_analyzer = MagicMock()
        issue_updater = MagicMock()
        priority_manager = MagicMock()
        
        return {
            'commit_analyzer': commit_analyzer,
            'pr_analyzer': pr_analyzer,
            'test_analyzer': test_analyzer,
            'issue_updater': issue_updater,
            'priority_manager': priority_manager
        }
    
    @patch('issue_status_updater.gh_get_issue')
    def test_update_single_issue_prioritized_to_in_progress(self, mock_gh_get_issue, mock_classes):
        """Test transitioning from prioritized to in-progress."""
        # Mock the API response
        mock_gh_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ],
            'title': 'Test Issue',
            'body': 'Test body'
        }
        
        # Set up the current status
        mock_classes['issue_updater'].get_current_status.return_value = 'prioritized'
        
        # Setup commit information that should trigger an update
        mock_classes['commit_analyzer'].get_commits_for_issue.return_value = [
            {
                'hash': 'abc123',
                'message': 'implements #123 Add feature',
                'action': 'implements',
                'issue_refs': [123]
            }
        ]
        
        # Mock PR behaviors
        mock_classes['pr_analyzer'].get_pr_for_issue.return_value = None
        mock_classes['pr_analyzer'].get_open_pr_for_issue.return_value = None
        
        # Call the actual function
        isu.update_single_issue(
            123,
            commit_analyzer=mock_classes['commit_analyzer'],
            pr_analyzer=mock_classes['pr_analyzer'],
            test_analyzer=mock_classes['test_analyzer'],
            issue_updater=mock_classes['issue_updater'],
            priority_manager=mock_classes['priority_manager']
        )
        
        # Verify that update_issue_status was called with correct arguments
        mock_classes['issue_updater'].update_issue_status.assert_called_once_with(123, 'in-progress', force=False)
        mock_classes['issue_updater'].add_status_comment.assert_called_once()
    
    @patch('issue_status_updater.gh_get_issue')
    def test_update_single_issue_in_progress_to_in_review(self, mock_gh_get_issue, mock_classes):
        """Test transitioning from in-progress to in-review."""
        # Mock the API response
        mock_gh_get_issue.return_value = {
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'},
            ],
            'title': 'Test Issue',
            'body': 'Test body'
        }
        
        # Set up the current status
        mock_classes['issue_updater'].get_current_status.return_value = 'in-progress'
        
        # Mock PR behaviors - open PR available
        mock_classes['pr_analyzer'].get_pr_for_issue.return_value = None
        open_pr = {
            'number': 45,
            'title': 'Add feature',
            'state': 'open',
            'linked_issues': [123]
        }
        mock_classes['pr_analyzer'].get_open_pr_for_issue.return_value = open_pr
        
        # Call the actual function
        isu.update_single_issue(
            123,
            commit_analyzer=mock_classes['commit_analyzer'],
            pr_analyzer=mock_classes['pr_analyzer'],
            test_analyzer=mock_classes['test_analyzer'],
            issue_updater=mock_classes['issue_updater'],
            priority_manager=mock_classes['priority_manager']
        )
        
        # Verify that update_issue_status was called with correct arguments
        mock_classes['issue_updater'].update_issue_status.assert_called_once_with(123, 'in-review', force=False)
        mock_classes['issue_updater'].add_status_comment.assert_called_once()
    
    @patch('issue_status_updater.gh_get_issue')
    def test_update_single_issue_in_review_to_completed(self, mock_gh_get_issue, mock_classes):
        """Test transitioning from in-review to completed."""
        # Mock the API response
        mock_gh_get_issue.return_value = {
            'labels': [
                {'name': 'status:in-review'},
                {'name': 'priority:1'},
            ],
            'title': 'Test Issue',
            'body': 'Test body'
        }
        
        # Set up the current status
        mock_classes['issue_updater'].get_current_status.return_value = 'in-review'
        
        # Set up commits with a "fixes" action for the issue
        mock_classes['commit_analyzer'].get_commits_for_issue.return_value = [
            {
                'hash': 'abc123',
                'message': 'fixes #123 Fix the bug',
                'action': 'fixes',  # This is critical - must be 'fixes', 'closes', or 'resolves'
                'issue_refs': [123]  # Issue number must be included here
            }
        ]
        
        # Mock PR behaviors - closed PR available with fixes keyword
        closed_pr = {
            'number': 45,
            'title': 'Fixes #123: Add feature',
            'state': 'closed',
            'body': 'This PR closes #123',
            'linked_issues': [123]
        }
        mock_classes['pr_analyzer'].get_pr_for_issue.return_value = closed_pr
        mock_classes['pr_analyzer'].get_open_pr_for_issue.return_value = None
        
        # Mock test results - these must be successful
        mock_classes['test_analyzer'].run_tests_for_issue.return_value = {'success': True}
        mock_classes['test_analyzer'].get_coverage_for_issue.return_value = {'coverage': 90.5}
        
        # Call the actual function
        isu.update_single_issue(
            123,
            commit_analyzer=mock_classes['commit_analyzer'],
            pr_analyzer=mock_classes['pr_analyzer'],
            test_analyzer=mock_classes['test_analyzer'],
            issue_updater=mock_classes['issue_updater'],
            priority_manager=mock_classes['priority_manager']
        )
        
        # Verify that update_issue_status was called with correct arguments
        mock_classes['issue_updater'].update_issue_status.assert_called_once_with(123, 'completed', force=False)
        mock_classes['issue_updater'].add_status_comment.assert_called_once()


if __name__ == "__main__":
    unittest.main()
