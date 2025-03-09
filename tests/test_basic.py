import datetime
import os
import time
from agentloop.mem4ai import Mem4AI

# Test database path
TEST_DB_PATH = "test_memory.db"

def cleanup():
    """Remove the test database file"""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_mem4ai():
    # Initialize memory module
    memory = Mem4AI(TEST_DB_PATH, context_window=100, session_timeout=30, chunk_gap=10)

    # Test 1: Create a new session and add messages
    print("=== Test 1: New Session ===")
    session_id_1 = memory.load_session(user_id="user123")
    print(f"Session ID: {session_id_1}")
    memory.add_memory("Hello!", "user", {"location": "Paris"})
    memory.add_memory("Hi there! How can I help you?", "assistant")
    memory.add_memory("What's the weather like in Paris?", "user", {"intent": "weather"})
    memory.add_memory("It's sunny and 25°C in Paris today.", "assistant")
    print("Session 1 messages added.")

    # Test 2: Build context (short-term memory)
    print("\n=== Test 2: Short-Term Memory ===")
    context = memory.build_context("What's the weather like?", max_tokens=50)
    print("Context (Short-Term):")
    for msg in context['short_term']:
        print(f"{msg['role']}: {msg['content']} (tokens: {msg['tokens']})")

    # Test 3: Simulate a new session after timeout
    print("\n=== Test 3: New Session After Timeout ===")
    time.sleep(35)  # Wait for session timeout
    session_id_2 = memory.load_session(user_id="user123")
    memory.add_memory("Hello again!", "user", {"location": "Berlin"})
    memory.add_memory("Hi! What can I do for you?", "assistant")
    memory.add_memory("What's the weather like in Berlin?", "user", {"intent": "weather"})
    memory.add_memory("It's cloudy and 18°C in Berlin today.", "assistant")
    print("Session 2 messages added.")

    # Test 4: Build context with middle-term memory (search)
    print("\n=== Test 4: Middle-Term Memory (Search) ===")
    context = memory.build_context("What's the weather like in Paris?", max_tokens=100)
    print("Context (Short-Term + Middle-Term):")
    for msg in context['short_term']:
        print(f"{msg['role']}: {msg['content']} (tokens: {msg['tokens']})")

    for msg in context['middle_term']:
        print(f"{msg['role']}: {msg['content']} (tokens: {msg['tokens']}")

    # Test 5: Search memory with metadata filter
    print("\n=== Test 5: Search Memory with Metadata Filter ===")
    results = memory.search_memory(
        "weather",
        metadata_filter={"location": "Paris"},
        time_range=(datetime.datetime(2023, 1, 1), datetime.datetime.now())
    )
    print("Search Results (Paris Weather):")
    for msg in results:
        print(f"{msg['role']}: {msg['content']} (tokens: {msg['tokens']})")

    # Test 6: Test chunking
    print("\n=== Test 6: Chunking ===")
    memory.add_memory("What about Berlin?", "user", {"intent": "weather"})
    memory.add_memory("It's still cloudy in Berlin.", "assistant")
    time.sleep(15)  # Simulate gap for new chunk
    memory.add_memory("Is it raining in Berlin?", "user", {"intent": "weather"})
    memory.add_memory("No, it's just cloudy.", "assistant")
    print("Chunked messages added.")

    # Verify chunking
    cursor = memory.conn.execute('''
        SELECT chunk_index, role, content FROM messages
        WHERE session_id = ?
        ORDER BY timestamp
    ''', (session_id_2,))
    print("Chunked Messages:")
    for row in cursor:
        print(f"Chunk {row[0]}: {row[1]}: {row[2]}")

    # Test 7: Cleanup and verify
    print("\n=== Test 7: Cleanup ===")
    memory.close()
    cleanup()
    print("Test database cleaned up.")

if __name__ == "__main__":
    test_mem4ai()