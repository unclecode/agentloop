"""
agentloop - A lightweight, transparent Python library for building AI assistants with OpenAI's API.

Designed for simplicity and flexibility, agentloop provides tools for creating assistants, 
managing sessions, and processing conversations with memory and tool support.
"""

from .agentloop import (
    create_assistant,
    start_session,
    process_message,
    reset_all_memory,
    reset_memory,
)

__version__ = "0.1.0"