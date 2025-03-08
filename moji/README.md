# Moji Assistant using Agentloop

This directory contains the implementation of the Moji Movie Assistant using the lightweight agentloop library. The Moji assistant helps users discover movies and TV shows, provides information about films, and manages user favorite lists.

## Architecture

The implementation consists of:

1. **MojiAssistant Class** (`moji_assistant.py`): The main class that sets up and manages the assistant.
2. **Tools Directory** (`tools/`): Contains tool functions that the assistant can use.
3. **Example Usage** (`example.py`): Demonstrates how to use the assistant.

## Key Features

- Dynamic tool loading from the `tools/` directory
- Consistent response formatting with type handling
- Memory management using agentloop's Mem4AI integration
- Support for different assistant modes (what2watch, talk2me, etc.)

## Tool Implementation

Each tool is implemented as a separate Python file in the `tools/` directory. Tools must export:

- A `TOOLS` dictionary mapping function names to function implementations
- A `TOOL_SCHEMAS` dictionary mapping function names to JSON schemas

For example, `movie_suggestions.py` exports the `what2watch` tool for recommending movies.

## Response Types

The assistant supports multiple response types:

- `text`: Simple text responses
- `movie_json`: Movie recommendations with metadata
- `list`: Lists of items (like favorite lists)
- `movie_info`: Detailed information about movies
- `trailer`: Movie trailer information

## Usage Example

```python
from moji_assistant import MojiAssistant

# Initialize the assistant
assistant = MojiAssistant(
    user_id="user123",
    model_id="gpt-4o",
    action="what2watch"
)

# Chat with the assistant
response = assistant.chat("Recommend some sci-fi movies from the 80s")
print(response)
```

## Migrating from OpenAI Assistants API

This implementation replaces the original Moji assistant that used the OpenAI Assistants API. Key advantages:

1. **Simplified Architecture**: More direct control over the conversation flow
2. **Lower Latency**: No need for thread/run management with OpenAI
3. **Cost Efficiency**: Better control over token usage
4. **Full Control**: Complete ownership of conversation state

## Next Steps

1. Add more tools to match the original assistant functionality
2. Improve system prompts with more sophisticated templating
3. Add database integration for storing user preferences
4. Implement vision capabilities for movie poster recognition