"""
Memory integration for agentloop using Mem4ai.
Provides a wrapper around Mem4ai for context management.
"""

from typing import Dict, List, Any, Optional
from mem4ai import Memtor


def get_memory_manager() -> Memtor:
    """
    Get a Memtor instance from Mem4ai.
    
    Returns:
        Memtor instance for memory management
    """
    return Memtor()


def add_memory(memtor: Memtor, content: str, metadata: Dict[str, Any], user_id: str) -> str:
    """
    Add a new memory to the Mem4ai system.
    
    Args:
        memtor: Memtor instance
        content: Content of the memory
        metadata: Additional data associated with the memory
        user_id: Identifier for the user/session
        
    Returns:
        ID of the created memory
    """
    return memtor.add_memory(content, metadata, user_id)


def search_memories(memtor: Memtor, query: str, user_id: str = None, limit: int = 5) -> List[Any]:
    """
    Search for relevant memories.
    
    Args:
        memtor: Memtor instance
        query: Search query
        user_id: Filter by user ID (optional)
        limit: Maximum number of results
        
    Returns:
        List of matching memory objects
    """
    return memtor.search_memories(query, user_id, limit)


def update_memory(memtor: Memtor, memory_id: str, content: str = None, metadata: Dict[str, Any] = None) -> bool:
    """
    Update an existing memory.
    
    Args:
        memtor: Memtor instance
        memory_id: ID of the memory to update
        content: New content (optional)
        metadata: New metadata (optional)
        
    Returns:
        True if update was successful, False otherwise
    """
    return memtor.update_memory(memory_id, content, metadata)


def delete_memory(memtor: Memtor, memory_id: str) -> bool:
    """
    Delete a memory.
    
    Args:
        memtor: Memtor instance
        memory_id: ID of the memory to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    return memtor.delete_memory(memory_id)