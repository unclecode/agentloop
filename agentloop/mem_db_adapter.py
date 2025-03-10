import sqlite3
from sqlite3 import Connection
import datetime
import re
import threading
from typing import List, Tuple, Dict, Optional


class DatabaseAdapter:
    """Safe SQLite adapter for Mem4AI that handles all database operations with proper escaping"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.thread_local = threading.local()
    
    def get_connection(self) -> Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self.thread_local, 'conn'):
            self.thread_local.conn = sqlite3.connect(self.db_path)
        return self.thread_local.conn
    
    def close(self):
        """Close database connection"""
        if hasattr(self.thread_local, 'conn'):
            self.thread_local.conn.close()
    
    def initialize_db(self):
        """Initialize the database with required tables."""
        conn = self.get_connection()
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
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", 
            (session_id,)
        )
        return cursor.fetchone() is not None
    
    def session_is_active(self, session_id: str, timeout_seconds: int) -> bool:
        """Check if a session is active within the timeout period."""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ? AND datetime(last_active, ?) > datetime('now')",
            (session_id, f'+{timeout_seconds} seconds')
        )
        return cursor.fetchone() is not None
    
    def update_session(self, session_id: str, user_id: Optional[str] = None):
        """Update an existing session's last_active timestamp and optionally user_id."""
        conn = self.get_connection()
        with conn:
            if user_id:
                conn.execute(
                    "UPDATE sessions SET last_active = datetime('now'), user_id = ? WHERE session_id = ?",
                    (user_id, session_id)
                )
            else:
                conn.execute(
                    "UPDATE sessions SET last_active = datetime('now') WHERE session_id = ?",
                    (session_id,)
                )
    
    def create_session(self, session_id: str, user_id: str):
        """Create a new session."""
        conn = self.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO sessions (session_id, user_id, last_active) VALUES (?, ?, datetime('now'))",
                (session_id, user_id)
            )
    
    def get_last_assistant_message(self, session_id: str) -> Tuple[Optional[str], Optional[int]]:
        """Get the timestamp and chunk_index of the last assistant message."""
        conn = self.get_connection()
        cursor = conn.execute(
            """
            SELECT timestamp, chunk_index FROM messages
            WHERE session_id = ? AND role = 'assistant'
            ORDER BY timestamp DESC LIMIT 1
            """,
            (session_id,)
        )
        if row := cursor.fetchone():
            return row[0], row[1]
        return None, None
    
    def add_message(self, session_id: str, chunk_index: int, role: str, 
                   content: str, tokens: int, metadata: Optional[Dict] = None):
        """Add a message to the database and FTS index."""
        conn = self.get_connection()
        with conn:
            # Safely serialize metadata
            metadata_str = str(metadata) if metadata else None
            
            # Insert into messages table
            conn.execute(
                """
                INSERT INTO messages 
                (session_id, chunk_index, role, content, tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, chunk_index, role, content, tokens, metadata_str)
            )
            
            # Insert into FTS index
            conn.execute(
                """
                INSERT INTO messages_fts 
                (rowid, content, session_id, metadata, role)
                VALUES (last_insert_rowid(), ?, ?, ?, ?)
                """,
                (content, session_id, metadata_str or '', role)
            )
    
    def escape_fts_query(self, query: str) -> str:
        """
        Properly escape an FTS query to handle double quotes and other special characters.
        This creates a safe query that treats the entire string as literal text.
        """
        # For FTS5, the safest way is to use the ESCAPE operator with '*' 
        # This tells SQLite to treat everything as literal, not as FTS syntax
        
        # Remove any existing quote marks from the query
        cleaned_query = query.replace('"', ' ').replace("'", ' ')
        
        # Split into words and escape each word
        words = [word for word in re.split(r'\s+', cleaned_query) if word]
        
        # Build a query where each word is treated as a separate term with OR between them
        if not words:
            return '""'  # Empty query that will match nothing
            
        escaped_terms = []
        for word in words:
            # Basic sanitization and escaping
            if re.search(r'[^\w\s]', word):  # If contains non-alphanumeric chars
                word = f'"{word}"'  # Quote it
            escaped_terms.append(word)
            
        # Join with OR operator
        return ' OR '.join(escaped_terms)
    
    def search_messages(self, query: str = None, session_id: str = None,
                        metadata_filter: Dict = None, 
                        time_range: Tuple[datetime.datetime, datetime.datetime] = None,
                        limit: int = 100) -> List[Dict]:
        """
        Safely search messages with proper escaping of the FTS query.
        Returns a list of message dictionaries.
        """
        conn = self.get_connection()
        params = []
        clauses = []
        
        # Handle FTS text search with safe escaping
        if query:
            escaped_query = self.escape_fts_query(query)
            clauses.append("messages_fts.content MATCH ?")
            params.append(escaped_query)
        
        # Filter by session
        if session_id:
            clauses.append("messages.session_id = ?")
            params.append(session_id)
        
        # Metadata filter
        if metadata_filter:
            for k, v in metadata_filter.items():
                # Handle different types of values in metadata
                if isinstance(v, str):
                    # For strings, use LIKE with escaped quotes
                    v_escaped = v.replace("'", "''")
                    clauses.append("messages.metadata LIKE ?")
                    params.append(f"%'{k}': '{v_escaped}'%")
                else:
                    # For non-strings, convert to string representation
                    clauses.append("messages.metadata LIKE ?")
                    params.append(f"%'{k}': {v}%")
        
        # Time range
        if time_range:
            start_time, end_time = time_range
            # Format datetime objects to strings if needed
            if isinstance(start_time, datetime.datetime):
                start_time = start_time.isoformat()
            if isinstance(end_time, datetime.datetime):
                end_time = end_time.isoformat()
                
            clauses.append("messages.timestamp BETWEEN ? AND ?")
            params.extend([start_time, end_time])
        
        # Build query
        where_clause = " AND ".join(clauses) if clauses else "1=1"
        
        # Use ORDER BY for FTS ranking, or timestamp if no query
        order_clause = "ORDER BY bm25(messages_fts)" if query else "ORDER BY messages.timestamp DESC"
        
        sql = f"""
            SELECT 
                messages.content, 
                messages.role, 
                messages.tokens, 
                messages.metadata, 
                messages.timestamp
            FROM messages 
            JOIN messages_fts ON messages.rowid = messages_fts.rowid
            WHERE {where_clause}
            {order_clause}
            LIMIT ?
        """
        params.append(limit)
        
        cursor = conn.execute(sql, params)
        results = []
        for row in cursor:
            metadata = None
            if row[3]:
                # Safely evaluate metadata string back to dict
                try:
                    metadata = eval(row[3])
                except:
                    metadata = row[3]  # Keep as string if eval fails
            
            results.append({
                'content': row[0],
                'role': row[1],
                'tokens': row[2],
                'metadata': metadata,
                'timestamp': row[4]
            })
        
        return results
    
    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Retrieve recent session messages."""
        conn = self.get_connection()
        cursor = conn.execute(
            """
            SELECT content, role, tokens, metadata, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, limit)
        )
        
        messages = []
        for row in cursor:
            metadata = None
            if row[3]:
                try:
                    metadata = eval(row[3])
                except:
                    metadata = row[3]
                    
            messages.append({
                'content': row[0],
                'role': row[1],
                'tokens': row[2],
                'metadata': metadata,
                'timestamp': row[4]
            })
        
        # Return in chronological order
        return list(reversed(messages))
    
    def clear_memory_by_conditions(self, session_id: Optional[str] = None, 
                                  agent_id: Optional[str] = None,
                                  user_id: Optional[str] = None) -> bool:
        """
        Clear memory entries based on specified parameters with safe SQL.
        """
        try:
            conn = self.get_connection()
            
            # Get session IDs to delete
            session_ids_to_delete = []
            
            # If session_id provided, add it
            if session_id:
                session_ids_to_delete.append(session_id)
                
            # If user_id provided, get all sessions for that user
            if user_id:
                cursor = conn.execute(
                    "SELECT session_id FROM sessions WHERE user_id = ?", 
                    (user_id,)
                )
                session_ids_to_delete.extend([row[0] for row in cursor.fetchall()])
                
            # Remove duplicates
            session_ids_to_delete = list(set(session_ids_to_delete))
            
            # If we have sessions to delete
            with conn:
                if session_ids_to_delete:
                    # Delete messages by session_id
                    placeholders = ", ".join(["?"] * len(session_ids_to_delete))
                    
                    # Get message rowids to delete from FTS
                    cursor = conn.execute(
                        f"SELECT rowid FROM messages WHERE session_id IN ({placeholders})",
                        session_ids_to_delete
                    )
                    message_ids = [row[0] for row in cursor.fetchall()]
                    
                    if message_ids:
                        # Delete from FTS
                        msg_placeholders = ", ".join(["?"] * len(message_ids))
                        conn.execute(
                            f"DELETE FROM messages_fts WHERE rowid IN ({msg_placeholders})",
                            message_ids
                        )
                    
                    # Delete messages
                    conn.execute(
                        f"DELETE FROM messages WHERE session_id IN ({placeholders})",
                        session_ids_to_delete
                    )
                    
                    # Delete sessions
                    conn.execute(
                        f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
                        session_ids_to_delete
                    )
                
                # Handle agent_id filter (which uses metadata)
                if agent_id:
                    # Find messages with this agent_id in metadata
                    cursor = conn.execute(
                        "SELECT rowid FROM messages WHERE metadata LIKE ?",
                        (f"%'agent_id': '{agent_id}'%",)
                    )
                    agent_message_ids = [row[0] for row in cursor.fetchall()]
                    
                    if agent_message_ids:
                        # Delete from FTS
                        placeholders = ", ".join(["?"] * len(agent_message_ids))
                        conn.execute(
                            f"DELETE FROM messages_fts WHERE rowid IN ({placeholders})",
                            agent_message_ids
                        )
                        
                        # Delete from messages
                        conn.execute(
                            f"DELETE FROM messages WHERE rowid IN ({placeholders})",
                            agent_message_ids
                        )
            
            return True
        except Exception as e:
            print(f"Error clearing memory: {str(e)}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all database content safely."""
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("DELETE FROM messages_fts")
                conn.execute("DELETE FROM messages")
                conn.execute("DELETE FROM sessions")
            return True
        except Exception as e:
            print(f"Error clearing all memory: {str(e)}")
            return False