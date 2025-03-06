"""
Utility functions for agentloop.
Provides helpers for tool schema generation, SQLite access, and token estimation.
"""

import os
import json
import sqlite3
import inspect
import re
import tiktoken
from typing import List, Dict, Any, Callable, Union, Optional


def get_function_schema(func: Callable) -> Dict[str, Any]:
    """
    Generate a JSON schema for a function based on its signature and docstring.
    
    Args:
        func: The function to generate a schema for
        
    Returns:
        A dictionary representing the function schema in OpenAI function calling format
    """
    # Get function name and docstring
    name = func.__name__
    docstring = inspect.getdoc(func) or ""
    
    # Get signature information
    signature = inspect.signature(func)
    parameters = {}
    required_params = []
    
    for param_name, param in signature.parameters.items():
        # Skip self, cls, and *args/**kwargs
        if param_name in ('self', 'cls') or param.kind in (
            inspect.Parameter.VAR_POSITIONAL, 
            inspect.Parameter.VAR_KEYWORD
        ):
            continue
        
        # Extract type hints
        param_type = "string"  # Default type
        if param.annotation != inspect.Parameter.empty:
            # Convert Python type annotations to JSON schema types
            type_name = str(param.annotation)
            if "str" in type_name:
                param_type = "string"
            elif "int" in type_name:
                param_type = "integer"
            elif "float" in type_name:
                param_type = "number"
            elif "bool" in type_name:
                param_type = "boolean"
            elif "List" in type_name or "list" in type_name:
                param_type = "array"
            elif "Dict" in type_name or "dict" in type_name:
                param_type = "object"
        
        # Extract description from docstring
        param_description = ""
        if docstring:
            pattern = rf"\s*{param_name}\s*:\s*(.*?)(?:\n\s*\w+\s*:|$)"
            matches = re.search(pattern, docstring, re.DOTALL)
            if matches:
                param_description = matches.group(1).strip()
        
        # Add parameter to schema
        parameters[param_name] = {
            "type": param_type,
            "description": param_description
        }
        
        # Check if parameter is required (has no default value)
        if param.default == inspect.Parameter.empty:
            required_params.append(param_name)
    
    # Extract return type from docstring
    return_description = ""
    if docstring:
        match = re.search(r"Returns:(.*?)(?:\n\s*\w+:|$)", docstring, re.DOTALL)
        if match:
            return_description = match.group(1).strip()
    
    # Create function schema
    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": docstring.split("\n\n")[0] if docstring else "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required_params
            }
        }
    }
    
    return schema


def create_db_tables(db_path: str):
    """
    Create necessary tables in the SQLite database.
    Also handles schema migration from older versions.
    
    Args:
        db_path: Path to the SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if sessions table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # Create new sessions table with current schema
        cursor.execute('''
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            history TEXT,
            metadata TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
    else:
        # Table exists, check if it needs migration
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Check if old schema (with 'assistant' column)
        if 'assistant' in columns and 'metadata' not in columns:
            print("Migrating database schema...")
            # Create a backup of the old table
            cursor.execute("ALTER TABLE sessions RENAME TO sessions_old")
            
            # Create new table with updated schema
            cursor.execute('''
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                history TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            ''')
            
            # Copy data from old table to new table
            cursor.execute('''
            INSERT INTO sessions (session_id, history, metadata, created_at, updated_at)
            SELECT session_id, history, '{}', created_at, updated_at FROM sessions_old
            ''')
            
            # Drop the old table
            cursor.execute("DROP TABLE sessions_old")
    
    conn.commit()
    conn.close()


def save_session(db_path: str, session_id: str, history: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """
    Save a session to the database. Only stores session history and metadata.
    Does not store the assistant configuration with function references.
    
    Args:
        db_path: Path to the SQLite database
        session_id: Unique identifier for the session
        history: Conversation history
        metadata: Additional session metadata (optional)
    """
    import datetime
    now = datetime.datetime.now().isoformat()
    
    # Use empty dict if no metadata provided
    metadata = metadata or {}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if session exists
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    if cursor.fetchone():
        # Update existing session
        cursor.execute(
            "UPDATE sessions SET history = ?, metadata = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(history), json.dumps(metadata), now, session_id)
        )
    else:
        # Insert new session
        cursor.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            (session_id, json.dumps(history), json.dumps(metadata), now, now)
        )
    
    conn.commit()
    conn.close()


def load_session(db_path: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a session from the database.
    
    Args:
        db_path: Path to the SQLite database
        session_id: Unique identifier for the session
        
    Returns:
        Session dictionary or None if not found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return {
            "session_id": result[0],
            "history": json.loads(result[1]),
            "metadata": json.loads(result[2]),
            "created_at": result[3],
            "updated_at": result[4]
        }
    return None


def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate the number of tokens in a text string.
    
    Args:
        text: The text to estimate tokens for
        model: The model to use for estimation
        
    Returns:
        Estimated token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base for newer models not yet in tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def ensure_db_dir_exists():
    """Ensure the ~/.agentloop directory exists."""
    home_dir = os.path.expanduser("~")
    agentloop_dir = os.path.join(home_dir, ".agentloop")
    os.makedirs(agentloop_dir, exist_ok=True)
    return agentloop_dir


def get_db_path() -> str:
    """Get the path to the SQLite database."""
    agentloop_dir = ensure_db_dir_exists()
    return os.path.join(agentloop_dir, "agentloop.db")


def reset_database():
    """
    Reset the database by deleting and recreating it.
    This is useful for testing or when schema changes are problematic.
    """
    db_path = get_db_path()
    try:
        # Remove the database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Database reset: {db_path}")
        
        # Create fresh tables
        create_db_tables(db_path)
        return True
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        return False


def render_template(template_string: str, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2-like template with the given context.
    
    Args:
        template_string: The template string with {{ variable }} placeholders
        context: Dictionary of values to substitute into the template
        
    Returns:
        The rendered template
    """
    if not template_string:
        return ""
    
    # Simple template rendering without jinja2 dependency
    result = template_string
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        placeholder_with_spaces = "{{ " + key + " }}"
        result = result.replace(placeholder, str(value))
        result = result.replace(placeholder_with_spaces, str(value))
    
    return result