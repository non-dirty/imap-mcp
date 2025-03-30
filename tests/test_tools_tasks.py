"""Tests for task-related tools."""

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

import pytest
from mcp.server.fastmcp import FastMCP, Context

from imap_mcp.imap_client import ImapClient
from imap_mcp.tools import register_tools


class TestTaskTools:
    """Test task-related tools."""

    @pytest.fixture
    def tools(self):
        """Set up tools for testing."""
        # Create a mock MCP server
        mcp = MagicMock(spec=FastMCP)
        imap_client = MagicMock(spec=ImapClient)
        
        # Make tool decorator store and return the decorated function
        stored_tools = {}
        
        def mock_tool_decorator():
            def decorator(func):
                stored_tools[func.__name__] = func
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        
        # Register tools with our mock
        register_tools(mcp, imap_client)
        
        # Return the tools dictionary
        return stored_tools

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = MagicMock(spec=Context)
        return context

    @pytest.mark.asyncio
    async def test_create_task_with_description(self, tools, mock_context, tmp_path):
        """Test creating a task with only a description."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Test the create_task tool
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)):
            result = await create_task(
                description="Test task",
                ctx=mock_context
            )
            
            # Verify the result
            assert "success" in result.lower()
            assert "Test task" in result
            
            # Verify the task was written to the file
            assert tasks_file.exists()
            
            # Read the file and check contents
            tasks = json.loads(tasks_file.read_text())
            assert len(tasks) == 1
            assert tasks[0]["description"] == "Test task"
            assert "created_at" in tasks[0]
            assert "due_date" not in tasks[0]
            assert "priority" not in tasks[0]

    @pytest.mark.asyncio
    async def test_create_task_with_optional_params(self, tools, mock_context, tmp_path):
        """Test creating a task with optional parameters."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Test the create_task tool
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)):
            result = await create_task(
                description="Test task with params",
                due_date="2025-04-15",
                priority=1,
                ctx=mock_context
            )
            
            # Verify the result
            assert "success" in result.lower()
            assert "Test task with params" in result
            
            # Verify the task was written to the file
            assert tasks_file.exists()
            
            # Read the file and check contents
            tasks = json.loads(tasks_file.read_text())
            assert len(tasks) == 1
            assert tasks[0]["description"] == "Test task with params"
            assert tasks[0]["due_date"] == "2025-04-15"
            assert tasks[0]["priority"] == 1

    @pytest.mark.asyncio
    async def test_create_task_appends_to_existing_file(self, tools, mock_context, tmp_path):
        """Test creating a task appends to existing tasks file."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Create an initial tasks file
        initial_tasks = [{"description": "Existing task", "created_at": "2025-03-28T12:00:00"}]
        tasks_file.write_text(json.dumps(initial_tasks))
        
        # Test the create_task tool
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)):
            result = await create_task(
                description="New task",
                ctx=mock_context
            )
            
            # Verify the result
            assert "success" in result.lower()
            
            # Read the file and check contents
            tasks = json.loads(tasks_file.read_text())
            assert len(tasks) == 2
            assert tasks[0]["description"] == "Existing task"
            assert tasks[1]["description"] == "New task"

    @pytest.mark.asyncio
    async def test_create_task_missing_description(self, tools, mock_context):
        """Test creating a task without a description."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Test the create_task tool with missing description
        result = await create_task(
            description="",  # Empty description
            ctx=mock_context
        )
        
        # Verify the result contains an error message
        assert "error" in result.lower()
        assert "description is required" in result.lower()

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, tools, mock_context, tmp_path):
        """Test creating a task with invalid priority."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Test the create_task tool with invalid priority (as string)
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)):
            # Mock that the priority is received as a string (which could happen in real use)
            result = await create_task(
                description="Task with invalid priority",
                priority="high",  # Should be an integer
                ctx=mock_context
            )
            
            # Verify the result contains an error message
            assert "error" in result.lower()
            assert "priority" in result.lower()

    @pytest.mark.asyncio
    async def test_create_task_invalid_due_date(self, tools, mock_context, tmp_path):
        """Test creating a task with invalid due date."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Test the create_task tool with invalid due date
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)):
            result = await create_task(
                description="Task with invalid due date",
                due_date="not a date",
                ctx=mock_context
            )
            
            # Verify the result contains an error message
            assert "error" in result.lower()
            assert "due date" in result.lower()

    @pytest.mark.asyncio
    async def test_create_task_logs_details(self, tools, mock_context, tmp_path):
        """Test that task creation is properly logged."""
        # Get the create_task function
        create_task = tools["create_task"]
        
        # Prepare a temporary file path
        tasks_file = tmp_path / "tasks.json"
        
        # Test the create_task tool with logging mock
        with patch("imap_mcp.tools.TASKS_FILE", str(tasks_file)), \
             patch("imap_mcp.tools.logger") as mock_logger:
            
            result = await create_task(
                description="Test task for logging",
                ctx=mock_context
            )
            
            # Verify logging was called
            mock_logger.info.assert_called()
            log_message = mock_logger.info.call_args[0][0]
            assert "Test task for logging" in log_message
