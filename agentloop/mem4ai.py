import sqlite3
from sqlite3 import Connection
import datetime
import tiktoken
import threading
from typing import List, Tuple, Dict, Optional, Any

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
        
        # Use thread-local connections
        self.thread_local = threading.local()
        
        # Initialize DB if needed
        with self._get_connection() as conn:
            self._init_db(conn)
        
        self.active_session_id = None

    def _get_connection(self) -> Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self.thread_local, 'conn'):
            self.thread_local.conn = sqlite3.connect(self.db_path)
        return self.thread_local.conn
        
    def _init_db(self, conn: Connection):
        """Initialize the database with required tables."""
        with conn:
            # Sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME
                )''')
            
            # Messages with chunk indexing
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    chunk_index INTEGER,
                    role TEXT,
                    content TEXT,
                    tokens INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )''')
            
            # Full-text search virtual table
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
                USING fts5(content, session_id, metadata, role)''')
            
            # Indexes
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_chunk 
                ON messages(session_id, chunk_index)''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON messages(timestamp)''')

    def load_session(self, session_id: str, user_id: str = None) -> str:
        """
        Load or create a session using the session_id
        
        Args:
            session_id: The unique identifier for the session
            user_id: Optional user identifier (required for new sessions)
            
        Returns:
            Session ID that was loaded or created
        """
        conn = self._get_connection()
        
        # First check if the session exists at all, regardless of timeout
        cursor = conn.execute('''
            SELECT session_id FROM sessions 
            WHERE session_id = ?
        ''', (session_id,))
        
        session_exists = cursor.fetchone() is not None
        
        # Now check if it's an active session within the timeout window
        cursor = conn.execute('''
            SELECT session_id FROM sessions 
            WHERE session_id = ? 
            AND datetime(last_active, ?) > datetime('now')
        ''', (session_id, f'+{self.session_timeout} seconds'))
        
        if row := cursor.fetchone():
            # Session exists and is active
            self.active_session_id = row[0]
            
            # Update last_active timestamp
            with conn:
                conn.execute('''
                    UPDATE sessions SET last_active = datetime('now')
                    WHERE session_id = ?
                ''', (self.active_session_id,))
        else:
            # Create or update session - user_id is required for new sessions
            if not user_id and not session_exists:
                raise ValueError("user_id is required when creating a new session")
            
            self.active_session_id = session_id
            with conn:
                if session_exists:
                    # Update existing session
                    update_params = [datetime.datetime.now().isoformat(), session_id]
                    if user_id:  # Only update user_id if provided
                        conn.execute('''
                            UPDATE sessions 
                            SET last_active = ?, user_id = ?
                            WHERE session_id = ?
                        ''', (update_params[0], user_id, session_id))
                    else:
                        conn.execute('''
                            UPDATE sessions 
                            SET last_active = ?
                            WHERE session_id = ?
                        ''', update_params)
                else:
                    # Insert new session
                    conn.execute('''
                        INSERT INTO sessions 
                        (session_id, user_id, last_active)
                        VALUES (?, ?, datetime('now'))
                    ''', (self.active_session_id, user_id))
            
        return self.active_session_id

    def add_memory(self, message: str, role: str, metadata: Dict = None):
        """Add message to memory with automatic chunk indexing"""
        if not self.active_session_id:
            raise ValueError("No active session - call load() first")
        
        conn = self._get_connection()
        
        # Calculate tokens
        tokens = len(self.tokenizer.encode(message))
        
        # Determine chunk index
        chunk_index = 0
        if role == 'user':
            # Get last assistant message in this session
            cursor = conn.execute('''
                SELECT timestamp, chunk_index FROM messages
                WHERE session_id = ? AND role = 'assistant'
                ORDER BY timestamp DESC LIMIT 1
            ''', (self.active_session_id,))
            
            if row := cursor.fetchone():
                last_asst_time = datetime.datetime.fromisoformat(row[0])
                time_diff = (datetime.datetime.now() - last_asst_time).total_seconds()
                chunk_index = row[1] + 1 if time_diff > self.chunk_gap else row[1]
        
        # Insert message
        with conn:
            conn.execute('''
                INSERT INTO messages 
                (session_id, chunk_index, role, content, tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.active_session_id,
                chunk_index,
                role,
                message,
                tokens,
                str(metadata) if metadata else None
            ))
            
            # Update FTS
            conn.execute('''
                INSERT INTO messages_fts 
                (rowid, content, session_id, metadata, role)
                VALUES (last_insert_rowid(), ?, ?, ?, ?)
            ''', (message, self.active_session_id, 
                  str(metadata) if metadata else '', role))

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
        params = []
        clauses = []
        
        # Text search
        if query:
            # Escape single quotes and wrap in double quotes for FTS5
            escaped_query = query.replace("'", "''")  # Escape single quotes
            escaped_query = f'"{escaped_query}"'      # Wrap in double quotes
            clauses.append("messages_fts.content MATCH ?")
            params.append(escaped_query)
        
        # Metadata filter
        if metadata_filter:
            for k, v in metadata_filter.items():
                clauses.append(f"messages_fts.metadata LIKE ?")
                params.append(f'%"{k}": {v}%')
        
        # Time range
        if time_range:
            clauses.append("messages.timestamp BETWEEN ? AND ?")
            params.extend(time_range)
        
        # Build query
        where_clause = " AND ".join(clauses) if clauses else "1=1"
        limit_clause = ""
        if limit_tokens:
            limit_clause = "ORDER BY bm25(messages_fts) LIMIT 100"
        
        sql = f'''
            SELECT messages.content, messages.role, messages.tokens, 
                messages.metadata, messages.timestamp
            FROM messages 
            JOIN messages_fts ON messages.rowid = messages_fts.rowid
            WHERE {where_clause}
            {limit_clause}
        '''
        
        conn = self._get_connection()
        results = []
        total_tokens = 0
        for row in conn.execute(sql, params):
            if limit_tokens and (total_tokens + row[2]) > limit_tokens:
                break
            
            results.append({
                'content': row[0],
                'role': row[1],
                'tokens': row[2],
                'metadata': row[3],
                'timestamp': row[4]
            })
            total_tokens += row[2]
        
        # Convert back metadata string to dict
        for r in results:
            if r['metadata']:
                r['metadata'] = eval(r['metadata'])
        
        return results

    def get_session_messages(self, token_limit: int) -> List[Dict]:
        """Retrieve recent session messages within token limit"""
        conn = self._get_connection()
        messages = []
        total_tokens = 0
        
        cursor = conn.execute('''
            SELECT content, role, tokens, metadata, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
        ''', (self.active_session_id,))
        
        for row in cursor:
            if total_tokens + row[2] > token_limit:
                break
            messages.insert(0, {  # Insert at beginning to maintain order
                'content': row[0],
                'role': row[1],
                'tokens': row[2],
                'metadata': row[3],
                'timestamp': row[4]
            })
            total_tokens += row[2]
        
        # Convert back metadata string to dict
        for m in messages:
            if m['metadata']:        
                m['metadata'] = eval(m['metadata'])

        return messages
    
    def close(self):
        """Close database connection"""
        if hasattr(self.thread_local, 'conn'):
            self.thread_local.conn.close()
        
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
        try:
            # Build where clauses
            conditions = []
            params = []
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
                
            conn = self._get_connection()
            if user_id:
                cursor = conn.execute(
                    "SELECT session_id FROM sessions WHERE user_id = ?", 
                    (user_id,)
                )
                session_ids = [row[0] for row in cursor.fetchall()]
                if session_ids:
                    placeholders = ", ".join(["?"] * len(session_ids))
                    conditions.append(f"session_id IN ({placeholders})")
                    params.extend(session_ids)
            
            if agent_id:
                conditions.append("metadata LIKE ?")
                params.append(f"%'agent_id': '{agent_id}'%")
            
            # If no condition is specified, do nothing (safety measure)
            if not conditions:
                return False
                
            # Remove from messages and FTS
            with conn:
                # Delete from messages table
                where_clause = " AND ".join(conditions)
                
                # First delete from FTS (which links to rowid)
                cursor = conn.execute(
                    f"SELECT rowid FROM messages WHERE {where_clause}", 
                    params
                )
                message_ids = [row[0] for row in cursor.fetchall()]
                
                if message_ids:
                    # Delete from FTS using rowids
                    placeholders = ", ".join(["?"] * len(message_ids))
                    conn.execute(
                        f"DELETE FROM messages_fts WHERE rowid IN ({placeholders})",
                        message_ids
                    )
                
                # Delete from messages
                conn.execute(
                    f"DELETE FROM messages WHERE {where_clause}",
                    params
                )
                
                # If session_id is specified, also clean up the sessions table
                if session_id:
                    conn.execute(
                        "DELETE FROM sessions WHERE session_id = ?",
                        (session_id,)
                    )
                elif user_id:
                    conn.execute(
                        "DELETE FROM sessions WHERE user_id = ?",
                        (user_id,)
                    )
                    
            return True
        except Exception as e:
            print(f"Error clearing memory: {str(e)}")
            return False

    def clear_all(self):
        """Clear all memory entries"""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM messages_fts")
            conn.execute("DELETE FROM sessions")
        return True 


# Usage
if __name__ == "__main__":
    # Clear all memory
    mem4ai = Mem4AI("memory.db")
    success = mem4ai.clear_all()
    if success:
        print("All memory entries cleared successfully.")
    else:
        print("Failed to clear memory entries.")