import datetime
import tiktoken
import threading
import numpy as np
import argparse
import sys
from queue import Queue, Empty
from typing import List, Tuple, Dict, Optional, Any, Union
from .mem_db_adapter import DatabaseAdapter

class Mem4AI:
    _instances = {}
    _lock = threading.RLock()
    
    # Embedding configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 512  # Reduced from 1536 for efficiency
    EMBEDDING_BATCH_SIZE = 32  # For batch processing
    EMBEDDING_QUEUE = Queue()
    
    # Class variable for embedding thread
    EMBEDDING_THREAD = None
    
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
        
        # Initialize embedding processor
        self._init_embedding_processor()

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

    def _init_embedding_processor(self):
        """Initialize the background thread for processing embeddings"""
        with self._lock:
            if not self.EMBEDDING_THREAD or not self.EMBEDDING_THREAD.is_alive():
                self.EMBEDDING_THREAD = threading.Thread(
                    target=self._process_embedding_queue,
                    daemon=True
                )
                self.EMBEDDING_THREAD.start()
    
    def _process_embedding_queue(self):
        """Background thread for processing embeddings in batches"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            batch = []
            while True:
                try:
                    # Get message with timeout (5 seconds)
                    message_id, content = self.EMBEDDING_QUEUE.get(timeout=3)
                    batch.append((message_id, content))
                    
                    # Process batch if it reaches the batch size
                    if len(batch) >= self.EMBEDDING_BATCH_SIZE:
                        self._process_embedding_batch(client, batch)
                        batch = []
                        
                except Empty:
                    # Process remaining messages in batch if queue is empty
                    if batch:
                        self._process_embedding_batch(client, batch)
                        batch = []
        except Exception as e:
            print(f"Error in embedding processor thread: {str(e)}")
            # Restart the thread if it fails
            self._init_embedding_processor()
    
    def _process_embedding_batch(self, client, batch):
        """Process a batch of messages for embedding generation"""
        try:
            # Extract content for embedding generation
            texts = [content for _, content in batch]
            
            # Generate embeddings using OpenAI API
            response = client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=texts,
                dimensions=self.EMBEDDING_DIMENSIONS,
                encoding_format="float"
            )
            
            # Convert embeddings to binary format
            embeddings = [np.array(e.embedding, dtype=np.float32).tobytes() 
                         for e in response.data]
            
            # Update database with embeddings
            conn = self.db.get_connection()
            with conn:
                for (message_id, _), embedding in zip(batch, embeddings):
                    conn.execute('''
                        UPDATE messages 
                        SET embedding = ?, embedding_model = ?
                        WHERE message_id = ?
                    ''', (embedding, self.EMBEDDING_MODEL, message_id))
                    
        except Exception as e:
            print(f"Embedding processing failed: {str(e)}")
    
    def add_memory(self, message: str, role: str, metadata: Dict = None):
        """Add message to memory with automatic chunk indexing and async embedding generation"""
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
        
        # Insert message and get ID
        message_id = self.db.add_message(
            self.active_session_id, 
            chunk_index, 
            role, 
            message, 
            tokens, 
            metadata
        )
        
        # Queue for async embedding processing
        if role in ['user', 'assistant']:
            self.EMBEDDING_QUEUE.put((message_id, message))

    def build_context(self, user_query: str, max_tokens: int = None) -> Dict[str, List[Dict]]:
        """
        Build conversation context with smart token allocation.
        Returns short-term and long-term memory separately for proper sequencing,
        with long-term memory using hybrid vector and BM25 search.
        """
        max_tokens = max_tokens or self.context_window
        usable_tokens = int(max_tokens * (1 - self.safety_buffer))
        
        # Get short-term memory (70% allocation)
        short_term_max = int(usable_tokens * 0.7)
        short_term = self.get_session_messages(token_limit=short_term_max)
        
        # Get long-term memory (30% allocation) with hybrid search
        long_term_max = usable_tokens - sum(m['tokens'] for m in short_term)
        if long_term_max > 0:
            long_term = self.search_memory(
                user_query, 
                limit_tokens=long_term_max
            )
        else:
            long_term = []
        
        # Return as separate components
        return {
            "short_term": short_term,
            "long_term": long_term  # Renamed from middle_term to long_term
        }

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a query string"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            response = client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=query,
                dimensions=self.EMBEDDING_DIMENSIONS,
                encoding_format="float"
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error generating query embedding: {str(e)}")
            # Return zero vector as fallback
            return np.zeros(self.EMBEDDING_DIMENSIONS, dtype=np.float32)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        # Handle zero vectors
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return np.dot(a, b) / (norm_a * norm_b)
            
    def vector_search(self, query: str, limit: int = 100) -> List[Dict]:
        """Vector similarity search using cosine distance"""
        # Get query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Search database with current session ID
        results = self.db.search_vectors(
            query_embedding.tobytes(),
            self.EMBEDDING_DIMENSIONS,
            session_id=self.active_session_id,
            limit=limit
        )
        
        return results
    
    def _apply_token_limit(self, messages: List[Dict], limit_tokens: int = None) -> List[Dict]:
        """Apply token limit to a list of messages"""
        if not limit_tokens:
            return messages
            
        filtered_results = []
        total_tokens = 0
        for result in messages:
            if total_tokens + result['tokens'] <= limit_tokens:
                filtered_results.append(result)
                total_tokens += result['tokens']
            else:
                break
        return filtered_results
    
    def search_memory(self, query: str, 
                      metadata_filter: Dict = None,
                      time_range: Tuple[datetime.datetime, datetime.datetime] = None,
                      limit_tokens: int = None) -> List[Dict]:
        """Hybrid search combining vector and BM25 relevance"""
        # Get vector results first (if possible)
        try:
            vector_results = self.vector_search(query, limit=100)
            message_ids = [msg.get('message_id') for msg in vector_results if 'message_id' in msg]
            
            # Get BM25 scores for all candidate messages
            bm25_scores = {}
            if message_ids:
                bm25_scores = self.db.get_bm25_scores(query, message_ids)
            
            # Combine scores (50/50 weight)
            combined = []
            for msg in vector_results:
                msg_id = msg.get('message_id')
                if msg_id:
                    # Combine vector similarity and BM25 score (weighted 50/50)
                    similarity = msg.get('similarity', 0)
                    bm25_score = bm25_scores.get(msg_id, 0)
                    combined_score = 0.5 * similarity + 0.5 * bm25_score
                    combined.append((combined_score, msg))
            
            # Sort by combined score
            combined.sort(reverse=True, key=lambda x: x[0])
            
            # Extract messages
            hybrid_results = [item[1] for item in combined]
            
        except Exception as e:
            print(f"Hybrid search error: {str(e)}, falling back to BM25 only")
            # Fallback to BM25 search
            hybrid_results = self.db.search_messages(
                query=query, 
                session_id=self.active_session_id,
                metadata_filter=metadata_filter,
                time_range=time_range,
                limit=100  # Get enough results to apply token filter
            )
        
        # Apply token limit if specified
        return self._apply_token_limit(hybrid_results, limit_tokens)

    def get_session_messages(self, token_limit: int) -> List[Dict]:
        """Retrieve recent session messages within token limit"""
        # Get messages from database
        all_messages = self.db.get_session_messages(self.active_session_id, limit=100)
        
        # Apply token limit using the helper method
        return self._apply_token_limit(all_messages, token_limit)
    
    def close(self):
        """Close database connection and clean up resources"""
        # Close database connection
        self.db.close()
        
        # Clean up embedding queue
        try:
            while not self.EMBEDDING_QUEUE.empty():
                self.EMBEDDING_QUEUE.get_nowait()
        except:
            pass
        
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


# Migration and CLI functions
def migrate_embeddings(db_path: str = None, batch_size: int = 100, resume_from: int = 0):
    """
    Migrate existing messages to add embeddings for improved search.
    This function processes all messages without embeddings, generating
    embeddings for them in batches.
    
    Args:
        db_path: Path to the database file (default: memory.db)
        batch_size: Number of messages to process in each batch
        resume_from: Message ID to resume from (in case of interrupted migration)
    """
    try:
        from openai import OpenAI
        client = OpenAI()
    except ImportError:
        print("Error: OpenAI package is required for migration.")
        print("Please install it with: pip install openai")
        return
    
    db_path = db_path or "memory.db"
    print(f"Starting embedding migration for database: {db_path}")
    
    # Initialize the database adapter directly
    db = DatabaseAdapter(db_path)
    db.initialize_db()
    
    # Get count of messages without embeddings
    conn = db.get_connection()
    if resume_from > 0:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE embedding IS NULL AND message_id >= ? AND role IN ('user', 'assistant')",
            (resume_from,)
        )
    else:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE embedding IS NULL AND role IN ('user', 'assistant')"
        )
    
    total_messages = cursor.fetchone()[0]
    
    if total_messages == 0:
        print("No messages found that need embeddings. Migration complete!")
        return
    
    print(f"Found {total_messages} messages that need embeddings")
    
    # Function to get messages in batches
    def get_messages_batch(offset, limit, min_id=0):
        if min_id > 0:
            cursor = conn.execute(
                """
                SELECT message_id, content
                FROM messages
                WHERE embedding IS NULL AND message_id >= ? AND role IN ('user', 'assistant')
                ORDER BY message_id
                LIMIT ? OFFSET ?
                """,
                (min_id, limit, offset)
            )
        else:
            cursor = conn.execute(
                """
                SELECT message_id, content
                FROM messages
                WHERE embedding IS NULL AND role IN ('user', 'assistant') 
                ORDER BY message_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
        return cursor.fetchall()
    
    # Process in batches
    offset = 0
    processed = 0
    embedding_model = "text-embedding-3-small"
    embedding_dimensions = 512
    
    while processed < total_messages:
        # Get batch of messages
        batch = get_messages_batch(offset, batch_size, resume_from)
        if not batch:
            break
            
        message_ids = [row[0] for row in batch]
        contents = [row[1] for row in batch]
        
        print(f"Processing batch of {len(batch)} messages...")
        
        try:
            # Generate embeddings
            response = client.embeddings.create(
                model=embedding_model,
                input=contents,
                dimensions=embedding_dimensions,
                encoding_format="float"
            )
            
            # Update database with embeddings
            with conn:
                for i, embedding_data in enumerate(response.data):
                    message_id = message_ids[i]
                    embedding = np.array(embedding_data.embedding, dtype=np.float32).tobytes()
                    
                    conn.execute(
                        """
                        UPDATE messages
                        SET embedding = ?, embedding_model = ?
                        WHERE message_id = ?
                        """,
                        (embedding, embedding_model, message_id)
                    )
            
            processed += len(batch)
            print(f"Progress: {processed}/{total_messages} ({processed/total_messages*100:.1f}%)")
            
        except Exception as e:
            print(f"Error processing batch: {e}")
            print(f"Last message ID processed: {message_ids[0] if message_ids else 'unknown'}")
            print("You can resume migration from this ID")
            break
            
        offset += batch_size
    
    print(f"Migration complete! Added embeddings to {processed} messages.")
    db.close()

def main():
    """Command line interface for Mem4AI utilities"""
    parser = argparse.ArgumentParser(description="Mem4AI CLI Tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Clear memory command
    clear_parser = subparsers.add_parser("clear", help="Clear all memory entries")
    clear_parser.add_argument("--db", default="memory.db", help="Database path")
    
    # Migrate embeddings command
    migrate_parser = subparsers.add_parser("migrate-embeddings", help="Migrate existing messages to add embeddings")
    migrate_parser.add_argument("--db", default="memory.db", help="Database path")
    migrate_parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    migrate_parser.add_argument("--resume-from", type=int, default=0, help="Message ID to resume from")
    
    args = parser.parse_args()
    
    if args.command == "clear":
        mem4ai = Mem4AI(args.db)
        success = mem4ai.clear_all()
        if success:
            print("All memory entries cleared successfully.")
        else:
            print("Failed to clear memory entries.")
        mem4ai.close()
            
    elif args.command == "migrate-embeddings":
        migrate_embeddings(args.db, args.batch_size, args.resume_from)
        
    else:
        parser.print_help()
        
# Usage
if __name__ == "__main__":
    main()