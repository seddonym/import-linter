"""Tests for the output module."""
import io
import sys

from rich.console import Console

from importlinter.application import output, rendering


def test_console_uses_utf8_encoding():
    """Test that the console is configured to use UTF-8 encoding.
    
    This is important for Windows compatibility where the default encoding
    may be cp1252, which cannot handle Unicode characters in the logo.
    """
    # After the fix, stdout should be reconfigured to UTF-8
    assert sys.stdout.encoding.lower() == 'utf-8'
    
    # The console's file should also use UTF-8 encoding
    if hasattr(output.console.file, 'encoding'):
        assert output.console.file.encoding.lower() == 'utf-8'


def test_console_can_print_unicode_characters():
    """Test that the console can print Unicode characters without errors.
    
    This test ensures that Unicode characters (like those in the logo)
    can be printed without raising a UnicodeEncodeError.
    """
    # This should not raise a UnicodeEncodeError
    try:
        # Print to a null device to avoid cluttering test output
        # Create a console that writes to a string buffer
        string_buffer = io.StringIO()
        test_console = Console(file=string_buffer, highlight=False)
        test_console.print(rendering.TEXT_LOGO, style=rendering.BRAND_COLOR)
        
        # If we got here without an exception, the test passes
        result = string_buffer.getvalue()
        assert len(result) > 0
        assert '╔══╗' in result  # Check that Unicode characters are present
    except UnicodeEncodeError:
        # This should not happen after the fix
        raise AssertionError("UnicodeEncodeError raised when printing logo")
