import sqlite3
from sqlite3 import Connection
import datetime
import tiktoken
from typing import List, Tuple, Dict, Optional

class Mem4AI:
    def __init__(self, db_path: str, context_window: int = 4096, 
                 session_timeout: int = 1800, chunk_gap: int = 600,
                 safety_buffer: float = 0.2):
        self.db_path = db_path
        # If file does not exist, it will be created
        self.conn = sqlite3.connect(db_path)
        self.context_window = context_window
        self.session_timeout = session_timeout  # Seconds
        self.chunk_gap = chunk_gap  # Seconds between chunks
        self.safety_buffer = safety_buffer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self._init_db()
        self.active_session_id = None

    def _init_db(self):
        with self.conn:
            # Sessions table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME,
                    is_active BOOLEAN
                )''')
            
            # Messages with chunk indexing
            self.conn.execute('''
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
            self.conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
                USING fts5(content, session_id, metadata, role)''')
            
            # Indexes
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_chunk 
                ON messages(session_id, chunk_index)''')
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON messages(timestamp)''')

    def load(self, user_id: str) -> str:
        """Load or create a new session"""
        # Check for existing active session
        cursor = self.conn.execute('''
            SELECT session_id FROM sessions 
            WHERE user_id = ? AND is_active = 1 
            AND datetime(last_active, ?) > datetime('now')
            ORDER BY last_active DESC LIMIT 1
        ''', (user_id, f'+{self.session_timeout} seconds'))
        
        if row := cursor.fetchone():
            self.active_session_id = row[0]
        else:
            # Create new session
            self.active_session_id = f"sess_{datetime.datetime.now().timestamp()}"
            self.conn.execute('''
                INSERT INTO sessions 
                (session_id, user_id, last_active, is_active)
                VALUES (?, ?, datetime('now'), 1)
            ''', (self.active_session_id, user_id))
            self.conn.commit()
            
        return self.active_session_id

    def add_memory(self, message: str, role: str, metadata: Dict = None):
        """Add message to memory with automatic chunk indexing"""
        if not self.active_session_id:
            raise ValueError("No active session - call load() first")
        
        # Calculate tokens
        tokens = len(self.tokenizer.encode(message))
        
        # Determine chunk index
        chunk_index = 0
        if role == 'user':
            # Get last assistant message in this session
            cursor = self.conn.execute('''
                SELECT timestamp, chunk_index FROM messages
                WHERE session_id = ? AND role = 'assistant'
                ORDER BY timestamp DESC LIMIT 1
            ''', (self.active_session_id,))
            
            if row := cursor.fetchone():
                last_asst_time = datetime.datetime.fromisoformat(row[0])
                time_diff = (datetime.datetime.now() - last_asst_time).total_seconds()
                chunk_index = row[1] + 1 if time_diff > self.chunk_gap else row[1]
        
        # Insert message
        self.conn.execute('''
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
        self.conn.execute('''
            INSERT INTO messages_fts 
            (rowid, content, session_id, metadata, role)
            VALUES (last_insert_rowid(), ?, ?, ?, ?)
        ''', (message, self.active_session_id, 
              str(metadata) if metadata else '', role))
        
        self.conn.commit()

    def build_context(self, user_query: str, max_tokens: int = None) -> Dict[str, List[Dict]]:
        """
        Build conversation context with smart token allocation.
        Returns short-term and middle-term memory separately for proper sequencing.
        """
        max_tokens = max_tokens or self.context_window
        usable_tokens = int(max_tokens * (1 - self.safety_buffer))
        
        # Get short-term memory (70% allocation)
        short_term_max = int(usable_tokens * 0.7)
        short_term = self._get_session_messages(token_limit=short_term_max)
        
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
        
        results = []
        total_tokens = 0
        for row in self.conn.execute(sql, params):
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
        
        return results

    def _get_session_messages(self, token_limit: int) -> List[Dict]:
        """Retrieve recent session messages within token limit"""
        messages = []
        total_tokens = 0
        
        cursor = self.conn.execute('''
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
        
        return messages

    def close(self):
        """Close database connection"""
        self.conn.close()

# Example usage
if __name__ == "__main__":
    memory = Mem4AI("/Users/unclecode/.agentloop/memory.db")
    
    # Start a session
    session_id = memory.load(user_id="user123")
    
    # Add conversation
    memory.add_memory("Hello!", "user", {"location": "Paris"})
    memory.add_memory("Hi there!", "assistant")
    
    # Build context
    context = memory.build_context("What's the weather like?", max_tokens=2000)
    print(f"Context length: {sum(m['tokens'] for m in context)} tokens")
    
    # Search memory
    results = memory.search_memory(
        "Paris",
        metadata_filter={"location": "Paris"},
        time_range=(datetime.datetime(2023, 1, 1), datetime.datetime.now())
    )
    print(f"Found {len(results)} relevant memories")