import datetime
import tiktoken
import threading
from typing import List, Tuple, Dict, Optional
from .mem_db_adapter import DatabaseAdapter

class Mem4AI:
    _instances = {}
    _lock = threading.RLock()
    
    def __init__(self, db_path: str, context_window: int = 4096, 
                 session_timeout: int = 1800, chunk_gap: int = 600,
                 safety_buffer: float = 0.2):
        self.db_path = db_path
        self.context_window = context_window
        self.session_timeout = session_timeout  # Seconds
        self.chunk_gap = chunk_gap  # Seconds between chunks
        self.safety_buffer = safety_buffer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Use our new database adapter
        self.db = DatabaseAdapter(db_path)
        
        # Initialize DB if needed
        self.db.initialize_db()
        
        self.active_session_id = None

    def load_session(self, session_id: str, user_id: str = None) -> str:
        """
        Load or create a session using the session_id
        
        Args:
            session_id: The unique identifier for the session
            user_id: Optional user identifier (required for new sessions)
            
        Returns:
            Session ID that was loaded or created
        """
        # Check if session exists
        session_exists = self.db.session_exists(session_id)
        
        # Check if session is active
        if self.db.session_is_active(session_id, self.session_timeout):
            # Session exists and is active
            self.active_session_id = session_id
            
            # Update last_active timestamp
            self.db.update_session(session_id, user_id if user_id else None)
        else:
            # Create or update session - user_id is required for new sessions
            if not user_id and not session_exists:
                raise ValueError("user_id is required when creating a new session")
            
            self.active_session_id = session_id
            
            if session_exists:
                # Update existing session
                self.db.update_session(session_id, user_id if user_id else None)
            else:
                # Insert new session
                self.db.create_session(session_id, user_id)
            
        return self.active_session_id

    def add_memory(self, message: str, role: str, metadata: Dict = None):
        """Add message to memory with automatic chunk indexing"""
        if not self.active_session_id:
            raise ValueError("No active session - call load_session() first")
        
        # Calculate tokens
        tokens = len(self.tokenizer.encode(message))
        
        # Determine chunk index
        chunk_index = 0
        if role == 'user':
            # Get last assistant message in this session
            last_timestamp, last_chunk_index = self.db.get_last_assistant_message(self.active_session_id)
            
            if last_timestamp:
                last_asst_time = datetime.datetime.fromisoformat(last_timestamp)
                time_diff = (datetime.datetime.now() - last_asst_time).total_seconds()
                chunk_index = last_chunk_index + 1 if time_diff > self.chunk_gap else last_chunk_index
        
        # Insert message
        self.db.add_message(
            self.active_session_id, 
            chunk_index, 
            role, 
            message, 
            tokens, 
            metadata
        )

    def build_context(self, user_query: str, max_tokens: int = None) -> Dict[str, List[Dict]]:
        """
        Build conversation context with smart token allocation.
        Returns short-term and middle-term memory separately for proper sequencing.
        """
        max_tokens = max_tokens or self.context_window
        usable_tokens = int(max_tokens * (1 - self.safety_buffer))
        
        # Get short-term memory (70% allocation)
        short_term_max = int(usable_tokens * 0.7)
        short_term = self.get_session_messages(token_limit=short_term_max)
        
        # Get middle-term memory (30% allocation)
        middle_term_max = usable_tokens - sum(m['tokens'] for m in short_term)
        if middle_term_max > 0:
            middle_term = self.search_memory(
                user_query, 
                limit_tokens=middle_term_max
            )
        else:
            middle_term = []
        
        # Return as separate components
        return {
            "short_term": short_term,
            "middle_term": middle_term
        }

    def search_memory(self, query: str, 
                      metadata_filter: Dict = None,
                      time_range: Tuple[datetime.datetime, datetime.datetime] = None,
                      limit_tokens: int = None) -> List[Dict]:
        """Search memory with BM25 and filters"""
        # Use the secure search from our adapter
        results = self.db.search_messages(
            query=query, 
            session_id=self.active_session_id,
            metadata_filter=metadata_filter,
            time_range=time_range,
            limit=100  # Get enough results to apply token filter
        )
        
        # Apply token limit if specified
        if limit_tokens:
            filtered_results = []
            total_tokens = 0
            for result in results:
                if total_tokens + result['tokens'] <= limit_tokens:
                    filtered_results.append(result)
                    total_tokens += result['tokens']
                else:
                    break
            return filtered_results
        
        return results

    def get_session_messages(self, token_limit: int) -> List[Dict]:
        """Retrieve recent session messages within token limit"""
        # Get messages from database
        all_messages = self.db.get_session_messages(self.active_session_id, limit=100)
        
        # Apply token limit
        messages = []
        total_tokens = 0
        
        for message in all_messages:
            if total_tokens + message['tokens'] <= token_limit:
                messages.append(message)
                total_tokens += message['tokens']
            else:
                break
                
        return messages
    
    def close(self):
        """Close database connection"""
        self.db.close()
        
    def clear_memory(self, session_id: Optional[str] = None, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """
        Clear memory entries based on specified parameters.
        
        Args:
            session_id: Optional ID of the session to clear
            agent_id: Optional ID of the agent to clear (stored in metadata)
            user_id: Optional ID of the user to clear
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.db.clear_memory_by_conditions(session_id, agent_id, user_id)

    def clear_all(self):
        """Clear all memory entries"""
        return self.db.clear_all()


# Usage
if __name__ == "__main__":
    # Clear all memory
    mem4ai = Mem4AI("memory.db")
    success = mem4ai.clear_all()
    if success:
        print("All memory entries cleared successfully.")
    else:
        print("Failed to clear memory entries.")