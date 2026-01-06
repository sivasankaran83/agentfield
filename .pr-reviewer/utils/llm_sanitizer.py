"""
LLM Output Sanitizer
Provides utilities to sanitize and validate LLM outputs across all agents
"""

import re
import html
from typing import Any, Dict, List, Union
from pydantic import BaseModel


def sanitize_llm_output(output: Any, max_length: int = 10000) -> Any:
    """
    Sanitize LLM output to prevent code injection, XSS, and other security issues.

    This function:
    1. Handles Pydantic models by converting to dict
    2. Recursively sanitizes strings in nested structures
    3. Escapes HTML/XML special characters
    4. Removes potentially dangerous patterns
    5. Truncates excessively long strings

    Args:
        output: The LLM output to sanitize (can be str, dict, list, Pydantic model, etc.)
        max_length: Maximum allowed length for string values

    Returns:
        Sanitized output in the same structure as input
    """
    # Handle Pydantic models
    if isinstance(output, BaseModel):
        return sanitize_llm_output(output.model_dump(), max_length)

    # Handle dictionaries
    if isinstance(output, dict):
        return {
            key: sanitize_llm_output(value, max_length)
            for key, value in output.items()
        }

    # Handle lists
    if isinstance(output, list):
        return [sanitize_llm_output(item, max_length) for item in output]

    # Handle strings
    if isinstance(output, str):
        return _sanitize_string(output, max_length)

    # Return other types as-is (int, float, bool, None, etc.)
    return output


def _sanitize_string(text: str, max_length: int) -> str:
    """
    Sanitize a string value.

    Args:
        text: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not text:
        return text

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "... (truncated)"

    # Escape HTML special characters to prevent XSS
    text = html.escape(text, quote=True)

    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove or escape potentially dangerous patterns
    # Note: We're being conservative here - adjust based on your security requirements

    # Remove script tags (case insensitive)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove event handlers (onclick, onerror, etc.)
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

    # Remove javascript: protocol
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)

    # Remove data: URLs (can be used for XSS)
    text = re.sub(r'data:text/html[^,]*,', '', text, flags=re.IGNORECASE)

    return text


def sanitize_for_display(text: str) -> str:
    """
    Sanitize text specifically for display in web UI or markdown.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for display
    """
    if not text:
        return text

    # Apply basic sanitization
    text = _sanitize_string(text, max_length=50000)

    # Unescape common markdown-safe characters that were escaped by html.escape
    # This allows legitimate markdown to work while blocking XSS
    # Note: Only unescape if you're rendering in a markdown context

    return text


def sanitize_for_storage(data: Any) -> Any:
    """
    Sanitize data before storing in database or files.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data
    """
    return sanitize_llm_output(data, max_length=100000)


def validate_llm_response(response: Any, expected_type: type = None) -> bool:
    """
    Validate that LLM response is of expected type and structure.

    Args:
        response: LLM response to validate
        expected_type: Expected type (e.g., dict, list, str)

    Returns:
        True if valid, False otherwise
    """
    if expected_type is None:
        return response is not None

    # Handle Pydantic models
    if isinstance(response, BaseModel):
        return True

    return isinstance(response, expected_type)


def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown code blocks if LLM wrapped it.

    Args:
        text: Text that might contain JSON in markdown

    Returns:
        Extracted JSON string or original text
    """
    # Try to extract from ```json ... ``` blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    # Try to extract from ``` ... ``` blocks
    code_match = re.search(r'```\s*\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    return text
