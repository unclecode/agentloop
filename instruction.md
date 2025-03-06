## **Technical Documentation: `agentloop`**

### **Overview**
`agentloop` is a lightweight, transparent, and highly customizable Python library designed to simplify the creation of AI assistants using OpenAI’s Chat Completions API. With a core implementation under 200 lines, it balances simplicity with power, enabling developers to build assistants that manage long conversations, execute multiple tasks, and maintain context across sessions—all while offering full control over data and behavior. Whether you’re building a travel planner, a customer support bot, or a creative writing assistant, `agentloop` provides the tools you need with minimal overhead.

#### **Key Features**
- **Assistant Creation**: Define assistants with models, system messages, tools, templates, and guardrails.
- **Session Management**: Persistent, locally stored sessions with SQLite for seamless conversation continuity.
- **Memory System**: Integration with `Mem4ai` for storing and retrieving contextual data.
- **Message Processing**: Handle user inputs, tool execution loops, and structured outputs with ease.
- **Transparency**: Inspect and modify conversation history, memory, and session data directly.
- **Flexibility**: Supports vision, token tracking, and dynamic templates for tailored interactions.

#### **Why Use `agentloop`?**
- **Minimalist Design**: A small footprint that’s easy to understand and extend.
- **Developer Empowerment**: Local data storage and full access to internals.
- **Versatility**: Ideal for both simple chats and complex, multi-step workflows.

---

### **Getting Started**
To use `agentloop`, install it along with its memory dependency, `Mem4ai`:

```bash
pip install agentloop
pip install https://github.com/unclecode/mem4ai.git
```

You’ll also need an OpenAI API key set as an environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

---

### **File Structure**
The library is split into three core files:
- **`agentloop.py`**: Handles assistant creation, session management, and message processing.
- **`mem4ai.py`**: Manages memory storage and retrieval.
- **`utils.py`**: Provides helper functions like tool schema generation, SQLite access, and token estimation.

All session data is stored locally in `~/.agentloop/agentloop.db`, a SQLite database.

---

## **1. Assistant Creation**
The assistant is the foundational configuration that defines how your AI behaves, what it can do, and how it interacts with users. You create it using the `create_assistant` function, which offers a wide range of customization options.

### **Function Signature**
```python
def create_assistant(
    model_id: str,
    system_message: Optional[str] = None,
    tools: List[Callable] = [],
    params: Dict[str, Any] = {},
    template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    guardrail: Optional[str] = None
) -> Dict[str, Any]
```

### **Parameters**
- **`model_id`** (str): The OpenAI model to power the assistant (e.g., `"gpt-4o"`, `"gpt-3.5-turbo"`).
- **`system_message`** (Optional[str]): A static string defining the assistant’s role or instructions (e.g., "You are a helpful travel assistant.").
- **`tools`** (List[Callable]): A list of Python functions the assistant can call (e.g., `[get_weather, book_flight]`).
- **`params`** (Dict[str, Any]): Optional OpenAI API parameters (e.g., `{"temperature": 0.8, "max_tokens": 1000}`).
- **`template`** (Optional[str]): A Jinja2 template string for dynamic system messages (e.g., "Hello, {{name}}! I’m your {{role}} assistant.").
- **`template_params`** (Dict[str, Any]): Variables to render the template (e.g., `{"name": "Alice", "role": "travel"}`).
- **`guardrail`** (Optional[str]): A rule to enforce behavior (e.g., "Don’t discuss sensitive topics like politics.").

### **How It Works**
- **System Message Logic**:
  - If you provide a `template`, it’s rendered with `template_params` to create the system message.
  - If no `template` is provided, the `system_message` is used directly.
  - If a `guardrail` is specified, it’s appended to the final system message for every interaction.
- **Tool Integration**:
  - Each function in `tools` is converted into a JSON schema (using its signature and docstring) for OpenAI’s tool-calling feature. This happens automatically via `utils.py`.

### **Example**
```python
from agentloop import create_assistant

# Define a simple tool
def get_weather(city: str) -> str:
    """Return the weather for a given city."""
    return f"Weather in {city}: Sunny, 20°C"

# Create an assistant
assistant = create_assistant(
    model_id="gpt-4o",
    template="Hello, {{name}}! I’m your {{role}} assistant.",
    template_params={"name": "Alice", "role": "travel"},
    tools=[get_weather],
    guardrail="Don’t discuss politics.",
    params={"temperature": 0.7}
)
```

**Resulting System Message**:  
"Hello, Alice! I’m your travel assistant. Don’t discuss politics."

This assistant is now configured to assist with travel-related tasks, use the `get_weather` tool, and avoid political discussions.

---

## **2. Session Management**
Sessions are how `agentloop` tracks ongoing conversations. Each session is tied to a unique `session_id`, stored locally, and linked to a memory system for context continuity.

### **Function Signature**
```python
def start_session(assistant: Dict[str, Any], session_id: str) -> Dict[str, Any]
```

### **Parameters**
- **`assistant`** (Dict[str, Any]): The assistant configuration from `create_assistant`.
- **`session_id`** (str): A unique identifier for the session (e.g., `"user123"`, `"trip_planner_001"`).

### **How It Works**
- **Session Creation or Loading**:
  - If the `session_id` doesn’t exist, a new session is created.
  - If it exists, the session’s conversation history and memory are loaded from the database.
- **Storage**:
  - All session data is saved in a SQLite database at `~/.agentloop/agentloop.db`.
  - The `~/.agentloop` directory is created automatically if it doesn’t exist.
- **Memory Link**:
  - Each session is paired with a `Mem4ai` instance, which manages user-specific context (e.g., preferences, past interactions).

### **Why Local Storage?**
- **Persistence**: Conversations survive app restarts or crashes.
- **Control**: Developers can inspect or modify the database directly (e.g., using a SQLite client).
- **Privacy**: No reliance on external servers—everything stays on the user’s machine.

### **Example**
```python
session = start_session(assistant, "user123")
# Creates or loads a session for "user123", stored in ~/.agentloop/agentloop.db
```

### **Session Data Structure**
The session object returned by `start_session` is a dictionary containing:
- `"assistant"`: The assistant configuration.
- `"session_id"`: The unique identifier.
- `"history"`: A list of past messages (e.g., `[{"role": "user", "content": "Hi!"}, ...]`).
- `"memory"`: A reference to the `Mem4ai` instance for this session.

---

## **3. Memory System with `Mem4ai`**
The memory system, powered by `Mem4ai`, enables the assistant to remember and use contextual information across interactions. This is critical for long conversations or recurring users.

### **What is `Mem4ai`?**
`Mem4ai` is a memory management library that stores, searches, and updates pieces of information (memories) tied to a user or session. It’s integrated into `agentloop` to provide context-awareness.

### **Key Operations**
Here’s how to interact with `Mem4ai`:

#### **Adding a Memory**
```python
from mem4ai import Memtor
memtor = Memtor()
memory_id = memtor.add_memory(
    content="User prefers dark mode for all apps",
    metadata={"category": "ui", "preference": "dark"},
    user_id="user123"
)
```

#### **Searching Memories**
```python
results = memtor.search_memories("interface preferences", user_id="user123")
print(results[0].content)  # "User prefers dark mode for all apps"
```

#### **Updating a Memory**
```python
memtor.update_memory(
    memory_id,
    content="User prefers dark mode, except for text editors",
    metadata={"category": "ui", "preference": "dark", "exception": "text_editors"}
)
```

#### **Deleting a Memory**
```python
memtor.delete_memory(memory_id)
```

### **Integration with `agentloop`**
- **Before a Message**:
  - `Mem4ai` searches for relevant memories based on the user’s input (e.g., "dark mode" triggers the above memory).
  - These memories are injected into the conversation context sent to OpenAI.
- **After a Message**:
  - New insights from the interaction (e.g., "User likes metric units") are added or updated in `Mem4ai`.

### **Example Scenario**
1. User says: "I prefer metric units for weather."
2. `Mem4ai` stores: "User prefers metric units" with `user_id="user123"`.
3. Later, user asks: "What’s the weather in Paris?"
4. Memory is retrieved, and the assistant responds: "Sunny, 20°C" (metric) instead of Fahrenheit.

---

## **4. Message Processing**
Message processing is where the assistant interacts with the user, handling inputs, calling tools, and generating responses. The `process_message` function manages this entire workflow.

### **Function Signature**
```python
def process_message(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    token_callback: Optional[Callable[[Dict[str, int]], None]] = None
) -> Dict[str, Any]
```

### **Parameters**
- **`session`** (Dict[str, Any]): The session object from `start_session`.
- **`message`** (Union[str, Dict[str, Any]]): The user’s input. Use a string for text (e.g., "What’s the weather?") or a dict for vision (e.g., `{"text": "What’s this?", "image_url": "https://example.com/image.jpg"}`).
- **`user_template`** (Optional[str]): A Jinja2 template for the user message (e.g., "Query from {{name}}: {{message}}").
- **`template_params`** (Dict[str, Any]): Variables for the user template (e.g., `{"name": "Alice"}`).
- **`context`** (Optional[Union[str, List[Dict[str, Any]]]]): Extra context to include (e.g., `"Previous task: Plan a trip"` or a list of messages).
- **`schema`** (Optional[Dict[str, Any]]): A JSON schema for structured outputs (e.g., `{"type": "object", "properties": {"weather": {"type": "string"}}}`).
- **`token_callback`** (Optional[Callable]): A function to process token usage (e.g., `lambda usage: print(usage["total_tokens"])`).

### **How It Works**
1. **Memory Retrieval**:
   - `Mem4ai` finds relevant memories and adds them to the conversation context.
2. **Message Rendering**:
   - If a `user_template` is provided, the message is rendered with `template_params`.
   - Otherwise, the raw `message` is used.
3. **Conversation Assembly**:
   - Combines the system message (from the assistant), conversation history, memory context, and user message.
4. **API Call**:
   - Sends the assembled data to OpenAI’s Chat Completions API.
   - If a `schema` is provided, it enforces structured output.
5. **Tool Execution Loop**:
   - If the API response includes tool calls:
     - Executes each tool (e.g., `get_weather("Paris")`).
     - Appends results to the conversation.
     - Calls the API again with updated context.
   - Loops until no more tools are needed or a limit (e.g., 5 iterations) is hit.
6. **Response**:
   - Returns a dict: `{"response": "...", "usage": {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}}`.
   - Calls `token_callback` with usage data if provided.
7. **Updates**:
   - Adds new memories to `Mem4ai` (e.g., task outcomes).
   - Saves the updated history to the SQLite database.

### **Example**
```python
response = process_message(
    session,
    message="What’s the weather in Paris?",
    user_template="Query from {{name}}: {{message}}",
    template_params={"name": "Alice"},
    schema={"type": "object", "properties": {"weather": {"type": "string"}}},
    token_callback=lambda usage: print(f"Tokens: {usage['total_tokens']}")
)
print(response["response"])  # {"weather": "Sunny, 20°C"}
```

---

## **5. Transparency and Flexibility**
`agentloop` empowers developers with full visibility and control over the assistant’s state. Here are the key functions:

### **Functions**
- **`get_history(session)`**: Returns the conversation history as a list of messages.
  ```python
  history = get_history(session)
  print(history)  # [{"role": "user", "content": "Hi!"}, ...]
  ```
- **`set_history(session, new_history)`**: Overwrites the history with a new list.
  ```python
  set_history(session, [{"role": "user", "content": "Test"}])
  ```
- **`add_messages(session, messages)`**: Adds messages to the history (prepend or append).
  ```python
  add_messages(session, [{"role": "assistant", "content": "Hello!"}])
  ```
- **`get_memory(session)`**: Accesses the `Mem4ai` instance for inspection.
- **`update_memory(session, new_memory)`**: Manually updates memory content.

### **Why It Matters**
- **Debugging**: Inspect what the assistant has said or remembered.
- **Customization**: Adjust history or memory mid-conversation (e.g., inject context).
- **Data Ownership**: All changes are saved locally, not hidden in a black box.

---

## **6. Token Consumption Tracking**
To manage costs and performance, `agentloop` tracks token usage:
- **Estimation**: Use `estimate_tokens(text, model)` from `utils.py` to predict token counts.
- **Actual Usage**: Returned in `process_message` as `"usage"`.
- **Callback**: Pass a `token_callback` to log or process usage dynamically.

### **Example**
```python
def log_tokens(usage):
    print(f"Used {usage['total_tokens']} tokens")
response = process_message(session, "Hi!", token_callback=log_tokens)
```

---

## **7. Complete Example**
Here’s a full example tying everything together:

```python
from agentloop import create_assistant, start_session, process_message, get_history
from mem4ai import Memtor

# Initialize memory
memtor = Memtor()

# Define a tool
def get_weather(city: str) -> str:
    """Fetches weather for a city."""
    return f"Weather in {city}: Sunny, 20°C"

# Create assistant
assistant = create_assistant(
    model_id="gpt-4o",
    template="Hello, {{name}}! I’m your {{role}} assistant.",
    template_params={"name": "Bob", "role": "travel"},
    tools=[get_weather],
    guardrail="No politics."
)

# Start session
session = start_session(assistant, "travel_bob")

# Add a memory
memtor.add_memory(
    content="User prefers metric units",
    metadata={"type": "units", "value": "metric"},
    user_id="travel_bob"
)

# Process a message
response = process_message(
    session,
    message="What’s the weather in Paris?",
    user_template="Query from {{name}}: {{message}}",
    template_params={"name": "Bob"},
    schema={"type": "object", "properties": {"weather": {"type": "string"}}}
)
print(response["response"])  # {"weather": "Sunny, 20°C"}

# Inspect history
history = get_history(session)
print(history)  # Shows full conversation
```

---

## **Pipeline Flow**
For complex tasks (e.g., "Plan a trip"), the pipeline works like this:
1. **Input**: User sends "Plan a trip to Paris."
2. **Memory**: Retrieves "prefers metric units."
3. **API Call**: OpenAI suggests tools (`get_weather`, `search_flights`).
4. **Tool Loop**:
   - Calls `get_weather("Paris")` → "Sunny, 20°C".
   - Calls `search_flights("Paris")` → "Flights tomorrow."
   - Loops back to OpenAI with results.
5. **Output**: "Paris: Sunny, 20°C. Flights tomorrow."
6. **Update**: Stores "planned trip to Paris" in memory.

---

## **Conclusion**
This expanded documentation covers every detail of `agentloop`, from assistant setup to session persistence, memory management, and message handling. It’s now a comprehensive, self-explanatory guide that should equip any developer to build robust AI assistants. If you need more clarification or examples, just let me know—I’m here to make it perfect for you!


>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Connection between Session and Memory
 
### **How Memory Connects to Sessions**
In `agentloop`, the memory system (`Mem4ai`) is tied to each session via the `session_id`. Here’s how it works conceptually:

1. **Session Initialization**:
   - When you call `start_session(assistant, session_id)`, the session object is created or loaded, and it includes a reference to a `Mem4ai` instance initialized with that `session_id` as the `user_id`. This links the memory directly to the session.
   - The `Mem4ai` instance stores and retrieves memories specific to that `session_id`, ensuring that each session has its own memory context.

2. **Memory in the Session Object**:
   - The session dictionary contains a `"memory"` key that holds the `Mem4ai` `Memtor` object. This allows `process_message` to access and update the memory seamlessly.

3. **Processing a Message**:
   - `process_message` uses the session’s memory to:
     - **Retrieve** relevant context before calling the OpenAI API (e.g., user preferences or past task details).
     - **Update** the memory after the response with new insights from the conversation.

4. **Updating the Memory**:
   - After the OpenAI API responds, `process_message` analyzes the response and conversation history to extract key information (e.g., user preferences or task outcomes) and adds or updates these in `Mem4ai`.

---

### **Detailed Connection**
- **Session Creation (`start_session`)**:
  - Initializes a `Memtor` instance with `user_id=session_id`.
  - Stores it in the session as `session["memory"] = memtor`.

- **Message Processing (`process_message`)**:
  - **Before API Call**: Queries `session["memory"]` to fetch relevant memories and injects them into the conversation context (e.g., as part of the system message or user message).
  - **After API Call**: Extracts new information from the response (e.g., "User prefers metric units") and calls `session["memory"].add_memory()` or `session["memory"].update_memory()` to store it.
  - **Persistence**: The session history is saved to `~/.agentloop/agentloop.db`, and memory updates are handled by `Mem4ai`’s internal storage.

---

### **Why This Matters**
- **Long Conversations**: The memory ensures that past interactions (e.g., "I like metric units") influence future responses, even across multiple sessions with the same `session_id`.
- **Multiple Tasks**: As tools are called and tasks evolve, memory tracks progress (e.g., "User is planning a trip to Paris"), making the assistant context-aware.

---

### **Updated Documentation**

Below is the revised documentation with a clear explanation of the memory-session connection and how `process_message` updates it.

---

## **Technical Documentation: `agentloop`**

### **Overview**
`agentloop` is a lightweight, transparent Python library for building AI assistants with OpenAI’s Chat Completions API. Designed to be simple (core under 200 lines) yet powerful, it supports long conversations, multi-task workflows, and full developer control over data and behavior. It’s stored locally in `~/.agentloop`, leveraging SQLite for persistence and `Mem4ai` for memory management.

#### **Key Features**
- **Assistant Creation**: Configurable with models, templates, tools, and guardrails.
- **Session Management**: Persistent sessions with integrated memory.
- **Memory System**: Powered by `Mem4ai` for context-aware interactions.
- **Message Processing**: Handles tools, structured outputs, and vision.
- **Transparency**: Full access to history and memory.

#### **Installation**
```bash
pip install agentloop
pip install https://github.com/unclecode/mem4ai.git
export OPENAI_API_KEY="your-api-key-here"
```

---

### **File Structure**
- **`agentloop.py`**: Core logic (assistant, session, message handling).
- **`mem4ai.py`**: Memory integration with `Mem4ai`.
- **`utils.py`**: Helpers (tool schemas, SQLite, token estimation).

**Storage**: All data is saved in `~/.agentloop/agentloop.db`.

---

## **1. Assistant Creation**
Define the assistant’s behavior and capabilities.

### **Function Signature**
```python
def create_assistant(
    model_id: str,
    system_message: Optional[str] = None,
    tools: List[Callable] = [],
    params: Dict[str, Any] = {},
    template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    guardrail: Optional[str] = None
) -> Dict[str, Any]
```

### **Parameters**
- `model_id` (str): OpenAI model (e.g., `"gpt-4o"`).
- `system_message` (Optional[str]): Static prompt (e.g., "You’re a travel assistant.").
- `tools` (List[Callable]): Python functions (e.g., `[get_weather]`).
- `params` (Dict[str, Any]): API settings (e.g., `{"temperature": 0.7}`).
- `template` (Optional[str]): Jinja2 system message template (e.g., "Hello, {{name}}!").
- `template_params` (Dict[str, Any]): Template variables (e.g., `{"name": "Alice"}`).
- `guardrail` (Optional[str]): Behavioral rule (e.g., "No politics.").

### **How It Works**
- Renders the system message from `template` or uses `system_message`.
- Appends `guardrail` to the system message.
- Converts `tools` to JSON schemas.

### **Example**
```python
def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny, 20°C"

assistant = create_assistant(
    model_id="gpt-4o",
    template="Hello, {{name}}! I’m your {{role}} assistant.",
    template_params={"name": "Bob", "role": "travel"},
    tools=[get_weather],
    guardrail="No sensitive topics."
)
```

---

## **2. Session Management**
Sessions track conversations and tie them to memory for context.

### **Function Signature**
```python
def start_session(assistant: Dict[str, Any], session_id: str) -> Dict[str, Any]
```

### **Parameters**
- `assistant` (Dict[str, Any]): Assistant configuration.
- `session_id` (str): Unique identifier (e.g., `"user123"`).

### **How It Works**
- **Initialization**:
  - Creates a new session or loads an existing one from `~/.agentloop/agentloop.db`.
  - Initializes a `Mem4ai` `Memtor` instance with `user_id=session_id` and stores it as `session["memory"]`.
- **Session Object**:
  - `"assistant"`: The assistant config.
  - `"session_id"`: The identifier.
  - `"history"`: List of past messages.
  - `"memory"`: The `Memtor` instance.

### **Memory Connection**
- The `session_id` doubles as the `user_id` for `Mem4ai`, linking all memories to this session.
- Example: Memories stored with `user_id="user123"` are specific to the session `"user123"`.

### **Example**
```python
session = start_session(assistant, "user123")
# Loads or creates session, links memory via session["memory"]
```

---

## **3. Memory System with `Mem4ai`**
Memory ensures the assistant remembers user preferences and past interactions.

### **Integration**
- **Initialization**: Done in `start_session`:
  ```python
  from mem4ai import Memtor
  memtor = Memtor()
  session["memory"] = memtor
  ```
- **Storage**: `Mem4ai` manages its own internal storage, tied to the `session_id`.

### **Operations**
- **Add Memory**:
  ```python
  session["memory"].add_memory(
      content="User prefers metric units",
      metadata={"type": "units", "value": "metric"},
      user_id=session["session_id"]
  )
  ```
- **Search Memories**:
  ```python
  results = session["memory"].search_memories("units", user_id=session["session_id"])
  ```
- **Update Memory**:
  ```python
  session["memory"].update_memory(memory_id, "Updated content", metadata={...})
  ```

### **Role in Sessions**
- **Context Retrieval**: Before processing a message, `process_message` queries `session["memory"]` for relevant context.
- **Context Update**: After a response, new insights are stored in `session["memory"]`.

---

## **4. Message Processing**
The heart of `agentloop`, handling user inputs and responses.

### **Function Signature**
```python
def process_message(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    token_callback: Optional[Callable[[Dict[str, int]], None]] = None
) -> Dict[str, Any]
```

### **Parameters**
- `session` (Dict[str, Any]): Session object.
- `message` (Union[str, Dict]): Text (e.g., "Hi") or vision input (e.g., `{"text": "What’s this?", "image_url": "..."}`).
- `user_template` (Optional[str]): Jinja2 template for user messages.
- `template_params` (Dict[str, Any]): Template variables.
- `context` (Optional[Union[str, List]]): Extra context.
- `schema` (Optional[Dict]): JSON schema for structured output.
- `token_callback` (Optional[Callable]): Token usage handler.

### **How It Works with Memory**
1. **Memory Retrieval**:
   - Queries `session["memory"].search_memories()` with the message content (e.g., "weather" → "prefers metric units").
   - Injects results into the system message or conversation history.
2. **Message Preparation**:
   - Renders `user_template` with `message` if provided.
   - Assembles: system message, history, memory context, and user message.
3. **API Call**:
   - Sends to OpenAI with tools and schema.
4. **Tool Loop**:
   - Executes tools if called, loops until resolved (max 5 iterations).
5. **Memory Update**:
   - Analyzes response and history for new insights (e.g., "User asked about Paris weather").
   - Calls `session["memory"].add_memory()` or `update_memory()`:
     ```python
     session["memory"].add_memory(
         content="User inquired about Paris weather",
         metadata={"topic": "travel", "location": "Paris"},
         user_id=session["session_id"]
     )
     ```
6. **Response**:
   - Returns `{"response": "...", "usage": {...}}`.

### **Example**
```python
response = process_message(
    session,
    "What’s the weather in Paris?",
    user_template="Query from {{name}}: {{message}}",
    template_params={"name": "Bob"}
)
# Memory retrieves "prefers metric units", response uses °C
```

---

## **5. Transparency and Flexibility**
Full control over data and state.

### **Functions**
- `get_history(session)`: Returns conversation history.
- `set_history(session, new_history)`: Updates history.
- `add_messages(session, messages)`: Adds messages.
- `get_memory(session)`: Returns the `Memtor` instance.
- `update_memory(session, content, metadata)`: Manually adds memory.

---

## **6. Token Tracking**
- `estimate_tokens(text, model)`: Predicts token count.
- `process_message` returns `"usage"`: Actual tokens used.

---

## **7. Example**
```python
from agentloop import create_assistant, start_session, process_message

def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny, 20°C"

assistant = create_assistant(
    model_id="gpt-4o",
    template="Hello, {{name}}! I’m your {{role}} assistant.",
    template_params={"name": "Bob", "role": "travel"},
    tools=[get_weather]
)

session = start_session(assistant, "bob_travel")
session["memory"].add_memory(
    "User prefers metric units",
    {"type": "units", "value": "metric"},
    "bob_travel"
)

response = process_message(
    session,
    "What’s the weather in Paris?",
    user_template="Query from {{name}}: {{message}}",
    template_params={"name": "Bob"}
)
print(response["response"])  # "Weather in Paris: Sunny, 20°C"
```

---

## **Pipeline Flow**
For "Plan a trip to Paris":
1. Memory retrieves "prefers metric units."
2. OpenAI calls `get_weather`, then suggests more tools.
3. Loops until complete, updates memory with "planning trip to Paris."




Focusing on processed message functions, I found one significant issue. The current code only allows for one    │
│   cycle iteration of calling and searching for tools. When the user sends a message, if the AI responds, we call  │
│   the tool functions, but then we assume that's the end after the second call. We receive the response and        │
│   return it. However, what if the AI responds again, indicating the need for additional tool calls? We need a     │
│   loop that waits until the AI's response does not require any further tool calls. That's one very important      │
│   point.  