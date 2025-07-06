"""
Tests for the CLI functionality.
"""

import json
import pytest
from unittest.mock import patch, mock_open
from pgdn_ws.cli import main, read_json_from_file, read_json_from_stdin


class TestCLI:
    """Test CLI functionality."""
    
    @patch('pgdn_ws.cli.notify')
    @patch('pgdn_ws.cli.read_json_from_file')
    @patch('sys.argv', ['pgdn-notify', 'test.json'])
    def test_cli_with_file(self, mock_read_file, mock_notify):
        """Test CLI with file input."""
        mock_read_file.return_value = {
            "type": "slack",
            "body": "test",
            "meta": {"channel": "#test"}
        }
        mock_notify.return_value = {
            "success": True,
            "type": "slack",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        with patch('builtins.print') as mock_print:
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
        
        mock_read_file.assert_called_once_with('test.json')
        mock_notify.assert_called_once()
        mock_print.assert_called()
    
    @patch('pgdn_ws.cli.notify')
    @patch('pgdn_ws.cli.read_json_from_stdin')
    @patch('sys.argv', ['pgdn-notify', '-'])
    @patch('sys.stdin.isatty', return_value=False)
    def test_cli_with_stdin(self, mock_isatty, mock_read_stdin, mock_notify):
        """Test CLI with stdin input."""
        mock_read_stdin.return_value = {
            "type": "webhook",
            "body": {"event": "test"},
            "meta": {"url": "http://test.com"}
        }
        mock_notify.return_value = {
            "success": True,
            "type": "webhook",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        with patch('builtins.print') as mock_print:
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
        
        mock_read_stdin.assert_called_once()
        mock_notify.assert_called_once()
        mock_print.assert_called()
    
    @patch('pgdn_ws.cli.notify')
    @patch('pgdn_ws.cli.read_json_from_file')
    @patch('sys.argv', ['pgdn-notify', '--pretty', 'test.json'])
    def test_cli_pretty_output(self, mock_read_file, mock_notify):
        """Test CLI with pretty-printed output."""
        mock_read_file.return_value = {"type": "slack", "body": "test", "meta": {"channel": "#test"}}
        mock_notify.return_value = {"success": True, "type": "slack"}
        
        with patch('builtins.print') as mock_print, patch('json.dumps') as mock_json_dumps:
            mock_json_dumps.return_value = "pretty json"
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
            
            mock_json_dumps.assert_called_with({"success": True, "type": "slack"}, indent=2)
    
    @patch('pgdn_ws.cli.notify')
    @patch('pgdn_ws.cli.read_json_from_file')
    @patch('sys.argv', ['pgdn-notify', 'test.json'])
    def test_cli_failure_exit_code(self, mock_read_file, mock_notify):
        """Test CLI exits with error code on notification failure."""
        mock_read_file.return_value = {"type": "slack", "body": "test", "meta": {"channel": "#test"}}
        mock_notify.return_value = {"success": False, "error": "test error"}
        
        with patch('builtins.print'):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestFileReading:
    """Test file reading functionality."""
    
    def test_read_json_from_file_success(self):
        """Test successful JSON file reading."""
        json_content = '{"type": "slack", "body": "test"}'
        
        with patch('builtins.open', mock_open(read_data=json_content)):
            result = read_json_from_file('test.json')
            
        assert result == {"type": "slack", "body": "test"}
    
    def test_read_json_from_file_not_found(self):
        """Test handling of missing file."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            with pytest.raises(ValueError, match="File not found"):
                read_json_from_file('missing.json')
    
    def test_read_json_from_file_invalid_json(self):
        """Test handling of invalid JSON in file."""
        with patch('builtins.open', mock_open(read_data='invalid json')):
            with pytest.raises(ValueError, match="Invalid JSON"):
                read_json_from_file('test.json')


class TestStdinReading:
    """Test stdin reading functionality."""
    
    @patch('sys.stdin.read')
    def test_read_json_from_stdin_success(self, mock_stdin_read):
        """Test successful JSON reading from stdin."""
        mock_stdin_read.return_value = '{"type": "webhook", "body": "test"}'
        
        result = read_json_from_stdin()
        
        assert result == {"type": "webhook", "body": "test"}
    
    @patch('sys.stdin.read')
    def test_read_json_from_stdin_empty(self, mock_stdin_read):
        """Test handling of empty stdin."""
        mock_stdin_read.return_value = ''
        
        with pytest.raises(ValueError, match="No input provided"):
            read_json_from_stdin()
    
    @patch('sys.stdin.read')
    def test_read_json_from_stdin_invalid_json(self, mock_stdin_read):
        """Test handling of invalid JSON from stdin."""
        mock_stdin_read.return_value = 'invalid json'
        
        with pytest.raises(ValueError, match="Invalid JSON from stdin"):
            read_json_from_stdin() 