# Agentloop

A lightweight, transparent, and highly customizable Python library for building AI assistants using OpenAI's Chat Completions API. With a core implementation under 200 lines, it balances simplicity with power, enabling developers to build assistants that manage long conversations, execute multiple tasks, and maintain context across sessions—all while offering full control over data and behavior.

## Key Features

- **Assistant Creation**: Define assistants with models, system messages, tools, templates, and guardrails.
- **Session Management**: Persistent, locally stored sessions with SQLite for seamless conversation continuity.
- **Memory System**: Integration with `Mem4ai` for storing and retrieving contextual data.
- **Message Processing**: Handle user inputs, tool execution loops, and structured outputs with ease.
- **Transparency**: Inspect and modify conversation history, memory, and session data directly.
- **Flexibility**: Supports vision, token tracking, and dynamic templates for tailored interactions.

## Installation

First, clone the repository:
```bash
git clone https://github.com/MojitoFilms/agentloop.git
cd agentloop
```

Then install the dependencies:
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install directly
pip install openai tiktoken
pip install git+https://github.com/unclecode/mem4ai.git
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Quick Start

Create a simple assistant and start a conversation:

```python
from agentloop import agentloop

# Define a tool
def get_weather(city: str) -> str:
    """Return the weather for a given city."""
    return f"Weather in {city}: Sunny, 20°C"

# Create assistant
assistant = agentloop.create_assistant(
    model_id="gpt-4o",
    template="Hello, {{name}}! I'm your {{role}} assistant.",
    template_params={"name": "Alice", "role": "travel"},
    tools=[get_weather],
    guardrail="Don't discuss politics.",
    synthesizer_model_id="gpt-3.5-turbo"  # Optional: use a different model for tool calls
)

# Start session
session = agentloop.start_session(assistant, "user123")

# Process a message
response = agentloop.process_message(
    session,
    "What's the weather in Paris?"
)

print(response["response"])  # Weather in Paris: Sunny, 20°C
```

## Core Functions

### Creating an Assistant

```python
assistant = agentloop.create_assistant(
    model_id="gpt-4o",
    system_message="You are a helpful assistant.",
    tools=[get_weather, book_flight],
    params={"temperature": 0.7},
    template="Hello {{name}}! I am your {{role}} assistant.",
    template_params={"name": "User", "role": "travel"},
    guardrail="Always be polite and helpful.",
    synthesizer_model_id="gpt-3.5-turbo"  # Optional: different model for tool call processing
)
```

### Managing Sessions

```python
# Start a new session or load existing one
session = agentloop.start_session(assistant, "user123")

# Get or set conversation history
history = agentloop.get_history(session)
agentloop.set_history(session, new_history)
agentloop.add_messages(session, [{"role": "user", "content": "Hello"}])
```

### Processing Messages

```python
# Simple text message
response = agentloop.process_message(
    session,
    "What's the weather in Paris?"
)

# With template
response = agentloop.process_message(
    session,
    "What's the weather?",
    user_template="Query from {{name}}: {{message}}",
    template_params={"name": "Alice"}
)

# With structured output
schema = {
    "name": "weather_response",
    "schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "temperature": {"type": "string"},
            "conditions": {"type": "string"}
        },
        "required": ["city", "temperature", "conditions"],
        "additionalProperties": False
    },
    "strict": True
}

response = agentloop.process_message(
    session,
    "What's the weather in Paris?",
    schema=schema
)
```

### Working with Memory

Agentloop uses [Mem4ai](https://github.com/unclecode/mem4ai) for memory management:

```python
# Add a memory
agentloop.update_memory(
    session,
    "User prefers metric units",
    {"type": "preference", "value": "metric"}
)

# Get memory instance
memtor = agentloop.get_memory(session)
```

## Running the Example

Try the included example:

```bash
# Make sure you're in the agentloop directory
python example.py
```

## Use Cases

- **Travel Planners**: Search flights, recommend destinations, and remember user preferences.
- **Customer Support**: Handle inquiries, search knowledge bases, and maintain conversation context.
- **Research Assistants**: Extract information from documents, organize findings, and generate summaries.
- **Creative Writing Aids**: Brainstorm ideas, suggest improvements, and provide feedback on drafts.

## Data Storage

All session data is stored locally in SQLite at `~/.agentloop/agentloop.db`, giving you full control over your data.

## License

MIT License