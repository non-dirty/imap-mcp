"""Test module for the issue helper script."""

import sys
import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock

# Add the scripts directory to the path so we can import the module directly
sys.path.append('scripts')
import issue_helper as ih


@pytest.mark.script_test
class TestIssueHelper:
    """Test class for the IssueHelper script."""
    
    @patch('subprocess.run')
    def test_run_command(self, mock_subprocess_run):
        """Test running a command and getting output."""
        # Mock the subprocess response
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Command output"
        mock_process.stderr = ""
        mock_subprocess_run.return_value = mock_process
        
        # Call the function
        exit_code, stdout, stderr = ih.run_command(['gh', 'version'])
        
        # Verify the result
        assert exit_code == 0
        assert stdout == "Command output"
        assert stderr == ""
        mock_subprocess_run.assert_called_once_with(
            ['gh', 'version'],
            check=True,
            capture_output=True,
            text=True
        )
    
    @patch('subprocess.run')
    def test_run_command_error(self, mock_subprocess_run):
        """Test handling of command errors."""
        # Mock a command that fails
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['gh', 'invalid'],
            output=b'',
            stderr=b'Error: unknown command'
        )
        
        # Call the function with check=False to prevent sys.exit
        with patch('sys.exit') as mock_exit:
            exit_code, stdout, stderr = ih.run_command(['gh', 'invalid'], check=False)
            
            # Verify results
            assert exit_code == 1
            mock_exit.assert_not_called()
    
    @patch('json.loads')
    @patch('issue_helper.run_command')
    def test_update_issue_status(self, mock_run_command, mock_json_loads):
        """Test updating an issue's status."""
        # Mock first command (get current labels)
        mock_run_command.return_value = (0, '{"labels": [{"name": "status:prioritized"}, {"name": "priority:1"}]}', '')
        mock_json_loads.return_value = {"labels": [{"name": "status:prioritized"}, {"name": "priority:1"}]}
        
        # Call the function
        ih.update_issue_status(123, 'in-progress')
        
        # Verify that run_command was called correctly
        assert mock_run_command.call_count == 3
        
        # First call should get current labels
        args1, _ = mock_run_command.call_args_list[0]
        assert args1[0][0:3] == ['gh', 'issue', 'view']
        assert args1[0][3] == '123'
        
        # Second call should remove old status
        args2, _ = mock_run_command.call_args_list[1]
        assert args2[0][0:3] == ['gh', 'issue', 'edit']
        assert args2[0][3] == '123'
        assert '--remove-label' in args2[0]
        assert 'status:prioritized' in args2[0]
        
        # Third call should add new status
        args3, _ = mock_run_command.call_args_list[2]
        assert args3[0][0:3] == ['gh', 'issue', 'edit']
        assert args3[0][3] == '123'
        assert '--add-label' in args3[0]
        assert 'status:in-progress' in args3[0]
    
    @patch('json.loads')
    @patch('issue_helper.run_command')
    def test_get_issue_status(self, mock_run_command, mock_json_loads):
        """Test getting an issue's status."""
        # Mock command response
        mock_run_command.return_value = (0, '{"labels": [{"name": "status:in-progress"}, {"name": "priority:1"}]}', '')
        mock_json_loads.return_value = {"labels": [{"name": "status:in-progress"}, {"name": "priority:1"}]}
        
        # Call the function
        status = ih.get_issue_status(123)
        
        # Verify the result
        assert status == 'in-progress'
        mock_run_command.assert_called_once()
        args, _ = mock_run_command.call_args
        assert args[0][0:3] == ['gh', 'issue', 'view']
        assert args[0][3] == '123'
    
    @patch('json.loads')
    @patch('issue_helper.run_command')
    def test_get_issue_status_no_status(self, mock_run_command, mock_json_loads):
        """Test getting an issue's status when no status label is present."""
        # Mock command response
        mock_run_command.return_value = (0, '{"labels": [{"name": "priority:1"}, {"name": "type:bug"}]}', '')
        mock_json_loads.return_value = {"labels": [{"name": "priority:1"}, {"name": "type:bug"}]}
        
        # Call the function
        status = ih.get_issue_status(123)
        
        # Verify the result
        assert status == ""

    @patch('builtins.print')
    @patch('issue_helper.get_issue_status')
    @patch('issue_helper.run_command')
    def test_check_issue_status(self, mock_run_command, mock_get_status, mock_print):
        """Test checking and displaying an issue's status."""
        # Setup mocks
        mock_get_status.return_value = "in-progress"
        
        # Mock the responses for each run_command call
        mock_run_command.side_effect = [
            # First call - issue view with title,url,labels
            (0, json.dumps({
                "title": "Test Issue",
                "url": "https://github.com/user/repo/issues/123",
                "labels": [
                    {"name": "status:in-progress"},
                    {"name": "priority:1"}
                ]
            }), ''),
            # Second call - git log (commits)
            (0, "abcd123 Implement feature\n", ''),
            # Third call - PR list
            (0, json.dumps([
                {
                    "number": 45,
                    "title": "Fix Issue #123",
                    "state": "open"
                }
            ]), '')
        ]
        
        # Call the function
        ih.check_issue_status(123)
        
        # Verify expectations
        assert mock_run_command.call_count == 3
        assert mock_print.call_count > 0
        assert mock_get_status.called is False  # We should use the status from the labels in the response

    @patch('builtins.print')
    @patch('builtins.input', return_value='y')
    @patch('os.path.exists', return_value=True)  # Mock README.md exists
    @patch('builtins.open', new_callable=MagicMock)  # Mock file open
    @patch('issue_helper.update_issue_status')
    @patch('issue_helper.get_issue_status')
    @patch('issue_helper.run_command')
    def test_start_work_on_issue(self, mock_run_command, mock_get_status,
                                mock_update_status, mock_open, mock_path_exists,
                                mock_input, mock_print):
        """Test starting work on an issue."""
        # Mock status check
        mock_get_status.return_value = 'prioritized'
        
        # Mock the issue title lookup and git commands
        mock_run_command.side_effect = [
            # First call - Get issue title
            (0, json.dumps({"title": "Test issue title"}), ''),
            # Second call - Check if branch exists
            (0, '', ''),  # Empty result means branch doesn't exist
            # Third call - Create branch
            (0, '', ''),
            # Fourth call - Add README
            (0, '', ''),
            # Fifth call - Commit
            (0, '', ''),
            # Sixth call - Push
            (0, '', '')
        ]
        
        # Set up file mock
        file_mock = MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock
        
        # Call the function
        ih.start_work_on_issue(123)
        
        # Verify status update was called
        mock_update_status.assert_called_once_with(123, 'in-progress')
        
        # Verify git commands were called
        assert mock_run_command.call_count >= 3
        
        # Verify README was modified
        mock_open.assert_called_once()
        file_mock.write.assert_called_once_with('\n')

    @patch('builtins.print')
    @patch('builtins.input', return_value='y')
    @patch('issue_helper.get_issue_status')
    def test_complete_issue(self, mock_get_status, mock_input, mock_print):
        """Test completing an issue by creating a PR."""
        # Mock status check
        mock_get_status.return_value = 'in-progress'
        
        # We need to mock both run_command and subprocess.run
        with patch('issue_helper.run_command') as mock_run_command:
            # Mock the issue title lookup
            mock_run_command.return_value = (0, json.dumps({"title": "Test Issue"}), '')
            
            # Mock subprocess.run for git commands
            with patch('subprocess.run') as mock_subprocess_run:
                # Setup mock process for git commands
                mock_process = MagicMock()
                mock_process.returncode = 0
                # Return a branch name for git branch command
                mock_process.stdout = "feature/issue-123-test-branch"
                # For git status command
                mock_process.stderr = ""
                mock_subprocess_run.return_value = mock_process
                
                # Call the function
                ih.complete_issue(123)
        
        # Verify that correct commands were called
        mock_get_status.assert_called_once_with(123)
        assert mock_print.call_count > 0
        assert mock_input.call_count > 0

    @patch('issue_helper.update_issue_status')
    @patch('issue_helper.run_command')
    def test_force_update_issue_for_testing(self, mock_run_command, mock_update_status):
        """Test force-updating an issue's status for testing."""
        # Mock so we don't actually call the GitHub CLI
        mock_run_command.return_value = (0, "", "")
        
        # Call the function
        ih.force_update_issue_for_testing(123, 'completed')
        
        # Verify update_issue_status was called with correct args
        mock_update_status.assert_called_once_with(123, 'completed')
        
        # Verify comment was added via run_command
        comment_call_found = False
        for call_args in mock_run_command.call_args_list:
            args = call_args[0][0]
            if 'comment' in args:
                comment_call_found = True
                break
                
        assert comment_call_found, "Expected call to add comment not found"
