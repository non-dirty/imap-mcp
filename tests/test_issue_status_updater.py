"""Test module for the issue status updater script."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call

# Add the scripts directory to the path so we can import the module directly
sys.path.append('scripts')
import issue_status_updater as isu


class TestIssueUpdater:
    """Test class for the IssueUpdater class."""
    
    @pytest.fixture
    def issue_updater(self):
        """Create an IssueUpdater instance for testing."""
        return isu.IssueUpdater('test-owner', 'test-repo')
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_get_current_status(self, mock_get_issue, issue_updater):
        """Test getting the current status of an issue."""
        # Mock the API response
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:in-progress'},
                {'name': 'priority:1'},
            ]
        }
        
        # Call the method
        status = issue_updater.get_current_status(123)
        
        # Verify the result
        assert status == 'in-progress'
        mock_get_issue.assert_called_once_with(
            owner='test-owner', repo='test-repo', issue_number=123
        )
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_get_current_status_no_status_label(self, mock_get_issue, issue_updater):
        """Test getting the current status when no status label is present."""
        # Mock the API response with no status label
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'priority:1'},
                {'name': 'type:bug'},
            ]
        }
        
        # Call the method
        status = issue_updater.get_current_status(123)
        
        # Verify the result is the default status
        assert status == 'prioritized'
    
    def test_validate_status_transition(self, issue_updater):
        """Test validation of status transitions."""
        # Valid transitions
        assert issue_updater.validate_status_transition('prioritized', 'in-progress') is True
        assert issue_updater.validate_status_transition('in-progress', 'in-review') is True
        assert issue_updater.validate_status_transition('in-review', 'completed') is True
        
        # Invalid transitions
        assert issue_updater.validate_status_transition('prioritized', 'completed') is False
        assert issue_updater.validate_status_transition('prioritized', 'in-review') is False
        
        # Same status is always valid
        assert issue_updater.validate_status_transition('in-progress', 'in-progress') is True
    
    @patch('issue_status_updater.mcp5_get_issue')
    @patch('issue_status_updater.mcp5_update_issue')
    def test_update_issue_status(self, mock_update_issue, mock_get_issue, issue_updater):
        """Test updating an issue's status."""
        # Mock the API responses
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ]
        }
        mock_update_issue.return_value = {'updated': True}
        
        # Call the method
        result = issue_updater.update_issue_status(123, 'in-progress')
        
        # Verify the result
        assert result == {'updated': True}
        mock_get_issue.assert_called_once_with(
            owner='test-owner', repo='test-repo', issue_number=123
        )
        mock_update_issue.assert_called_once_with(
            owner='test-owner', 
            repo='test-repo', 
            issue_number=123,
            labels=['priority:1', 'status:in-progress']
        )
    
    @patch('issue_status_updater.mcp5_get_issue')
    @patch('issue_status_updater.mcp5_update_issue')
    def test_update_issue_status_invalid_transition(self, mock_update_issue, mock_get_issue, issue_updater):
        """Test that invalid status transitions are blocked."""
        # Mock the API responses
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ]
        }
        
        # Call the method with an invalid transition
        result = issue_updater.update_issue_status(123, 'completed')
        
        # Verify the API was not called and empty result was returned
        assert result == {}
        mock_get_issue.assert_called_once()
        mock_update_issue.assert_not_called()
    
    @patch('issue_status_updater.mcp5_get_issue')
    @patch('issue_status_updater.mcp5_update_issue')
    def test_update_issue_status_force(self, mock_update_issue, mock_get_issue, issue_updater):
        """Test forcing an invalid status transition."""
        # Mock the API responses
        mock_get_issue.return_value = {
            'labels': [
                {'name': 'status:prioritized'},
                {'name': 'priority:1'},
            ]
        }
        mock_update_issue.return_value = {'updated': True}
        
        # Call the method with force=True
        result = issue_updater.update_issue_status(123, 'completed', force=True)
        
        # Verify the API was called despite invalid transition
        assert result == {'updated': True}
        mock_get_issue.assert_called_once()
        mock_update_issue.assert_called_once()
    
    @patch('issue_status_updater.mcp5_add_issue_comment')
    @patch('issue_status_updater.datetime')
    def test_add_status_comment_in_progress(self, mock_datetime, mock_add_comment, issue_updater):
        """Test adding a comment for in-progress status."""
        # Mock the datetime
        mock_datetime.now.return_value.strftime.return_value = '2025-03-16 01:00:00'
        
        # Call the method
        details = {
            'commit': 'abcd123',
            'message': 'Start implementing feature'
        }
        issue_updater.add_status_comment(123, 'in-progress', details)
        
        # Verify the API was called with appropriate message
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        assert args['owner'] == 'test-owner'
        assert args['repo'] == 'test-repo'
        assert args['issue_number'] == 123
        assert 'Status Update: `in-progress`' in args['body']
        assert 'abcd123' in args['body']
        assert 'Start implementing feature' in args['body']
    
    @patch('issue_status_updater.mcp5_add_issue_comment')
    @patch('issue_status_updater.datetime')
    def test_add_status_comment_in_review(self, mock_datetime, mock_add_comment, issue_updater):
        """Test adding a comment for in-review status."""
        # Mock the datetime
        mock_datetime.now.return_value.strftime.return_value = '2025-03-16 01:00:00'
        
        # Call the method
        details = {
            'pr_number': 42,
            'pr_title': 'Implement new feature'
        }
        issue_updater.add_status_comment(123, 'in-review', details)
        
        # Verify the API was called with appropriate message
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        assert 'Status Update: `in-review`' in args['body']
        assert '#42' in args['body']
        assert 'Implement new feature' in args['body']
    
    @patch('issue_status_updater.mcp5_add_issue_comment')
    @patch('issue_status_updater.datetime')
    def test_add_status_comment_completed(self, mock_datetime, mock_add_comment, issue_updater):
        """Test adding a comment for completed status."""
        # Mock the datetime
        mock_datetime.now.return_value.strftime.return_value = '2025-03-16 01:00:00'
        
        # Call the method
        details = {
            'pr_number': 42,
            'test_results': {'success': True, 'coverage': 85.5}
        }
        issue_updater.add_status_comment(123, 'completed', details)
        
        # Verify the API was called with appropriate message
        mock_add_comment.assert_called_once()
        args = mock_add_comment.call_args[1]
        assert 'Status Update: `completed`' in args['body']
        assert '#42' in args['body']
        assert 'Test status: ✅ Passed' in args['body']
        assert 'Test coverage: 85.5%' in args['body']
        assert 'Status Timeline' in args['body']


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
        
        # Set up issue_updater.get_current_status
        issue_updater.get_current_status.return_value = 'prioritized'
        
        return {
            'commit_analyzer': commit_analyzer,
            'pr_analyzer': pr_analyzer,
            'test_analyzer': test_analyzer,
            'issue_updater': issue_updater,
            'priority_manager': priority_manager
        }
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_update_single_issue_prioritized_to_in_progress(self, mock_get_issue, mock_classes):
        """Test transitioning from prioritized to in-progress."""
        # Set up mocks
        mock_get_issue.return_value = {'labels': [{'name': 'status:prioritized'}]}
        
        commit_analyzer = mock_classes['commit_analyzer']
        pr_analyzer = mock_classes['pr_analyzer']
        issue_updater = mock_classes['issue_updater']
        
        # Mock commit analyzer to return a commit
        commit_analyzer.get_commits_for_issue.return_value = [
            {'hash': 'abcd123', 'message': 'refs #123: Start work', 'action': 'refs'}
        ]
        
        # Mock PR analyzer to return no PR
        pr_analyzer.get_pr_for_issue.return_value = None
        pr_analyzer.get_open_pr_for_issue.return_value = None
        
        # Call the function
        isu.update_single_issue(
            123,
            commit_analyzer,
            pr_analyzer,
            mock_classes['test_analyzer'],
            issue_updater,
            mock_classes['priority_manager']
        )
        
        # Verify the issue was updated correctly
        issue_updater.update_issue_status.assert_called_once_with(123, 'in-progress', force=False)
        issue_updater.add_status_comment.assert_called_once()
        
        # Verify the details passed to add_status_comment
        call_args = issue_updater.add_status_comment.call_args[0]
        assert call_args[0] == 123
        assert call_args[1] == 'in-progress'
        assert call_args[2]['commit'] == 'abcd123'
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_update_single_issue_in_progress_to_in_review(self, mock_get_issue, mock_classes):
        """Test transitioning from in-progress to in-review."""
        # Set up mocks
        mock_get_issue.return_value = {'labels': [{'name': 'status:in-progress'}]}
        
        commit_analyzer = mock_classes['commit_analyzer']
        pr_analyzer = mock_classes['pr_analyzer']
        issue_updater = mock_classes['issue_updater']
        
        # Set current status to in-progress
        issue_updater.get_current_status.return_value = 'in-progress'
        
        # Mock commit analyzer to return a commit
        commit_analyzer.get_commits_for_issue.return_value = [
            {'hash': 'abcd123', 'message': 'refs #123: Start work', 'action': 'refs'}
        ]
        
        # Mock PR analyzer to return an open PR
        pr_analyzer.get_pr_for_issue.return_value = None
        pr_analyzer.get_open_pr_for_issue.return_value = {
            'number': 42,
            'title': 'Implement feature',
            'state': 'open'
        }
        
        # Call the function
        isu.update_single_issue(
            123,
            commit_analyzer,
            pr_analyzer,
            mock_classes['test_analyzer'],
            issue_updater,
            mock_classes['priority_manager']
        )
        
        # Verify the issue was updated correctly
        issue_updater.update_issue_status.assert_called_once_with(123, 'in-review', force=False)
        issue_updater.add_status_comment.assert_called_once()
        
        # Verify the details passed to add_status_comment
        call_args = issue_updater.add_status_comment.call_args[0]
        assert call_args[0] == 123
        assert call_args[1] == 'in-review'
        assert call_args[2]['pr_number'] == 42
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_update_single_issue_in_review_to_completed(self, mock_get_issue, mock_classes):
        """Test transitioning from in-review to completed."""
        # Set up mocks
        mock_get_issue.return_value = {'labels': [{'name': 'status:in-review'}]}
        
        commit_analyzer = mock_classes['commit_analyzer']
        pr_analyzer = mock_classes['pr_analyzer']
        test_analyzer = mock_classes['test_analyzer']
        issue_updater = mock_classes['issue_updater']
        priority_manager = mock_classes['priority_manager']
        
        # Set current status to in-review
        issue_updater.get_current_status.return_value = 'in-review'
        
        # Mock commit analyzer to return a commit with 'fixes'
        commit_analyzer.get_commits_for_issue.return_value = [
            {'hash': 'efgh456', 'message': 'fixes #123: Complete feature', 'action': 'fixes', 'issue_refs': [123]}
        ]
        
        # Mock PR analyzer to return a closed PR
        pr_analyzer.get_pr_for_issue.return_value = {
            'number': 42,
            'title': 'Implement feature',
            'state': 'closed'
        }
        pr_analyzer.get_open_pr_for_issue.return_value = None
        
        # Mock test analyzer to return successful tests
        test_analyzer.run_tests_for_issue.return_value = {'success': True}
        test_analyzer.get_coverage_for_issue.return_value = {'coverage': 90.5}
        
        # Call the function
        isu.update_single_issue(
            123,
            commit_analyzer,
            pr_analyzer,
            test_analyzer,
            issue_updater,
            priority_manager
        )
        
        # Verify the issue was updated correctly
        issue_updater.update_issue_status.assert_called_once_with(123, 'completed', force=False)
        issue_updater.add_status_comment.assert_called_once()
        
        # Verify the details passed to add_status_comment
        call_args = issue_updater.add_status_comment.call_args[0]
        assert call_args[0] == 123
        assert call_args[1] == 'completed'
        assert call_args[2]['pr_number'] == 42
        assert call_args[2]['test_results']['success'] is True
        
        # Verify priorities were adjusted
        priority_manager.adjust_priorities_after_completion.assert_called_once_with(123)
    
    @patch('issue_status_updater.mcp5_get_issue')
    def test_update_single_issue_invalid_transition(self, mock_get_issue, mock_classes):
        """Test handling of invalid status transitions."""
        # Set up mocks
        mock_get_issue.return_value = {'labels': [{'name': 'status:prioritized'}]}
        
        commit_analyzer = mock_classes['commit_analyzer']
        pr_analyzer = mock_classes['pr_analyzer']
        issue_updater = mock_classes['issue_updater']
        
        # Mock current status as 'prioritized'
        issue_updater.get_current_status.return_value = 'prioritized'
        
        # Mock validate_status_transition to return False
        issue_updater.validate_status_transition.return_value = False
        
        # Mock PR analyzer to return a closed PR (which would normally trigger 'completed')
        pr_analyzer.get_pr_for_issue.return_value = {
            'number': 42,
            'title': 'Implement feature',
            'state': 'closed'
        }
        
        # Call the function
        isu.update_single_issue(
            123,
            commit_analyzer,
            pr_analyzer,
            mock_classes['test_analyzer'],
            issue_updater,
            mock_classes['priority_manager']
        )
        
        # Verify the issue was not updated
        issue_updater.update_issue_status.assert_not_called()
        issue_updater.add_status_comment.assert_not_called()
