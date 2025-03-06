"""
Core implementation of agentloop.
Provides assistant creation, session management, and message processing.
"""

import os
import json
import inspect
import datetime
from typing import List, Dict, Any, Optional, Callable, Union


from . import utils
from .mem4ai import Mem4AI  # Import the memory implementation directly

# Define memory reset function
def reset_memory():
    """
    Reset the memory database by deleting and recreating it.
    This is useful for testing or clearing all conversations.
    """
    home_dir = os.path.expanduser("~")
    memory_db_path = os.path.join(home_dir, ".agentloop", "memory.db")
    try:
        # Remove the database file if it exists
        if os.path.exists(memory_db_path):
            os.remove(memory_db_path)
            print(f"Memory database reset: {memory_db_path}")
        return True
    except Exception as e:
        print(f"Error resetting memory database: {str(e)}")
        return False


def create_assistant(
    model_id: str,
    system_message: Optional[str] = None,
    tools: List[Callable] = [],
    params: Dict[str, Any] = {},
    template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    guardrail: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an assistant with the specified configuration.
    
    Args:
        model_id: The OpenAI model to use (e.g., "gpt-4o", "gpt-3.5-turbo")
        system_message: Static system message for the assistant
        tools: Python functions that the assistant can call
        params: Additional parameters for the OpenAI API
        template: Jinja2 template for dynamic system messages
        template_params: Variables to render the template
        guardrail: Rule to enforce behavior
        
    Returns:
        Assistant configuration dictionary
    """
    # Process system message - either from template or direct
    final_system_message = ""
    if template:
        final_system_message = utils.render_template(template, template_params)
    elif system_message:
        final_system_message = system_message
    
    # Add guardrail if specified
    if guardrail:
        if final_system_message:
            final_system_message = f"{final_system_message}\n\n{guardrail}"
        else:
            final_system_message = guardrail
    
    # Process tools if provided
    tool_schemas = []
    if tools:
        for tool in tools:
            schema = utils.get_function_schema(tool)
            tool_schemas.append(schema)
    
    # Create assistant configuration
    assistant = {
        "model": model_id,
        "system_message": final_system_message,
        "tools": tool_schemas,
        "tool_map": {tool.__name__: tool for tool in tools},
        "params": params
    }
    
    return assistant


def start_session(assistant: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Start or resume a session with the given assistant.
    
    Args:
        assistant: Assistant configuration from create_assistant
        session_id: Unique identifier for the session
        
    Returns:
        Session dictionary with assistant and memory
    """
    # Create new session with just essential information
    session = {
        "session_id": session_id,
        "assistant": assistant,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "metadata": {}
    }
    
    # Initialize memory for this session with the session ID
    # Create path to memory database
    home_dir = os.path.expanduser("~")
    memory_db_path = os.path.join(home_dir, ".agentloop", "memory.db")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(memory_db_path), exist_ok=True)
    
    # Initialize Mem4AI directly
    mem = Mem4AI(memory_db_path)
    mem.load(user_id=session_id)
    session["memory"] = mem
    
    return session


def process_message(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    token_callback: Optional[Callable[[Dict[str, int]], None]] = None
) -> Dict[str, Any]:
    """
    Process a user message in the given session.
    
    Args:
        session: Session dictionary from start_session
        message: Text message or dict with text and image_url for vision
        user_template: Jinja2 template for the user message
        template_params: Variables to render the template
        context: Additional context to include
        schema: JSON schema for structured output
        token_callback: Function to call with token usage statistics
        
    Returns:
        Dictionary with response and usage statistics
    """
    import openai
    
    assistant = session["assistant"]
    memtor = session.get("memory")
    
    # Format user message
    formatted_message = message
    if isinstance(message, str) and user_template:
        # Apply template to text message
        template_params["message"] = message
        formatted_message = utils.render_template(user_template, template_params)
    
    # Prepare message content
    if isinstance(message, str):
        message_content = {"role": "user", "content": formatted_message}
    else:
        # Handle vision or complex message format
        message_content = {"role": "user", "content": formatted_message}
    
    # Get memory context (both short-term and middle-term)
    short_term_context = []
    middle_term_context = []
    
    if memtor and isinstance(message, str):
        # Get context directly from Mem4AI with updated structure
        query = message
        max_tokens = 2000  # Default limit
        memory_contexts = memtor.build_context(query, max_tokens)
        
        # Process short-term memory
        for mem in memory_contexts.get("short_term", []):
            if mem['role'] in ['user', 'assistant']:
                # Keep only role and content for API compatibility
                short_term_context.append({
                    "role": mem['role'], 
                    "content": mem['content']
                })
        
        # Process middle-term memory
        for mem in memory_contexts.get("middle_term", []):
            if mem['role'] in ['user', 'assistant']:
                # Keep only role and content for API compatibility
                middle_term_context.append({
                    "role": mem['role'], 
                    "content": mem['content']
                })
    
    # Prepare messages for API call using the requested pipeline format:
    # [system message, ...middle term, ...context, ...short term, recent user message]
    messages = []
    
    # 1. Add system message if specified (first in the pipeline)
    if assistant.get("system_message"):
        messages.append({"role": "system", "content": assistant["system_message"]})
    
    # 2. Add middle-term memory context
    if middle_term_context:
        messages.extend(middle_term_context)
    
    # 3. Add additional context if provided (between middle-term and short-term)
    if context:
        if isinstance(context, str):
            messages.append({"role": "system", "content": context})
        elif isinstance(context, list):
            # Ensure context messages only have role and content
            for msg in context:
                if 'role' in msg and 'content' in msg:
                    messages.append({"role": msg['role'], "content": msg['content']})
    
    # 4. Add short-term memory context
    if short_term_context:
        messages.extend(short_term_context)
    
    # 5. Add user message (last in the pipeline)
    messages.append(message_content)
    
    # Prepare API parameters
    api_params = {
        "model": assistant["model"],
        "messages": messages
    }
    
    # Add tools if available
    if assistant.get("tools"):
        api_params["tools"] = assistant["tools"]
    
    # Add schema for structured output if provided
    if schema:
        api_params["response_format"] = {
            "type": "json_schema",
            "json_schema": schema
        }
    
    # Add additional parameters
    api_params.update(assistant.get("params", {}))
    
    # Make API call to OpenAI
    response = openai.chat.completions.create(**api_params)
    
    # Extract initial response content
    assistant_message = response.choices[0].message
    
    # Handle tool calls in a loop until no more tool calls are needed
    max_tool_iterations = 5  # Safety limit to prevent infinite loops
    current_iteration = 0
    tool_conversation = []  # Track the entire tool conversation
    
    while (hasattr(assistant_message, 'tool_calls') and 
           assistant_message.tool_calls and 
           current_iteration < max_tool_iterations):
        
        current_iteration += 1
        tool_messages = []
        
        # Add assistant message with tool calls to temporary conversation
        assistant_tool_message = {
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [tool_call.model_dump() for tool_call in assistant_message.tool_calls]
        }
        tool_messages.append(assistant_tool_message)
        tool_conversation.append(assistant_tool_message)
        
        # Process tool calls
        tool_responses = []
        tool_map = assistant.get("tool_map", {})
        
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Find and execute the function
            if function_name in tool_map:
                function = tool_map[function_name]
                try:
                    function_response = function(**function_args)
                    result = str(function_response)
                except Exception as e:
                    result = f"Error: {str(e)}"
            else:
                result = f"Error: Function {function_name} not found"
            
            # Add tool response
            tool_response = {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result
            }
            tool_responses.append(tool_response)
            
            # Store tool interaction in memory if memory is available
            if memtor:
                # Store function call and result in memory with metadata
                tool_metadata = {
                    "type": "tool_call",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "function_name": function_name,
                    "iteration": current_iteration
                }
                memtor.add_memory(
                    f"Function call: {function_name} with args: {function_args}", 
                    "assistant", 
                    tool_metadata
                )
                memtor.add_memory(
                    f"Function result: {result}", 
                    "tool", 
                    tool_metadata
                )
        
        # Add tool responses to current iteration conversation
        tool_messages.extend(tool_responses)
        tool_conversation.extend(tool_responses)
        
        # Make another API call with all tool results so far
        api_params["messages"] = messages + tool_conversation
        
        response = openai.chat.completions.create(**api_params)
        assistant_message = response.choices[0].message
        
        # If we're at the max iterations and still have tool calls, log a warning
        if (current_iteration == max_tool_iterations and 
            hasattr(assistant_message, 'tool_calls') and 
            assistant_message.tool_calls):
            print(f"Warning: Reached maximum tool call iterations ({max_tool_iterations})")
            if memtor:
                memtor.add_memory(
                    f"Warning: Reached maximum tool call iterations ({max_tool_iterations})", 
                    "system", 
                    {"type": "warning", "timestamp": datetime.datetime.now().isoformat()}
                )
    
    # Update session timestamp
    session["updated_at"] = datetime.datetime.now().isoformat()
    
    # Extract usage statistics
    usage = {}
    if hasattr(response, 'usage'):
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        # Call token callback if provided
        if token_callback:
            token_callback(usage)
    
    # Store the conversation in memory
    if memtor and isinstance(message, str):
        # Extract the messages from the conversation
        last_user_msg = formatted_message
        last_assistant_msg = assistant_message.content
        
        # Common metadata for both messages
        metadata = {
            "type": "conversation", 
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Add user message
        memtor.add_memory(last_user_msg, "user", metadata)
        
        # Add assistant message
        memtor.add_memory(last_assistant_msg, "assistant", metadata)
    
    # Return response and usage
    return {
        "response": assistant_message.content,
        "usage": usage
    }


def get_conversation(session: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent conversation messages from memory.
    
    Args:
        session: Session dictionary
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries with role and content only
    """
    memtor = session.get("memory")
    if not memtor:
        return []
    
    messages = memtor._get_session_messages(token_limit=4000)  # Get most recent messages
    
    # Return only the most recent messages, limited by count
    recent_messages = messages[-limit*2:] if limit > 0 else messages
    
    # Format as API-compatible messages with only role and content
    return [{"role": msg["role"], "content": msg["content"]} for msg in recent_messages]


def add_memory(session: Dict[str, Any], message: str, role: str = "user", metadata: Dict = None):
    """
    Add a message directly to memory.
    
    Args:
        session: Session dictionary
        message: Message content
        role: Message role (user/assistant/system)
        metadata: Additional metadata
    """
    memtor = session.get("memory")
    if not memtor:
        return
    
    # Add to memory with metadata
    metadata = metadata or {}
    memtor.add_memory(message, role, metadata)


def get_memory(session: Dict[str, Any]) -> Optional[Mem4AI]:
    """
    Get the memory object from a session.
    
    Args:
        session: Session dictionary
        
    Returns:
        Mem4AI instance or None
    """
    return session.get("memory")


def update_memory(session: Dict[str, Any], content: str, metadata: Dict[str, Any] = None):
    """
    Add a new memory to the session. This is used for adding user preferences
    or facts that aren't tied directly to a conversation.
    
    Args:
        session: Session dictionary
        content: Memory content (treated as a user message)
        metadata: Additional metadata (optional)
    """
    mem = session.get("memory")
    if mem:
        # Add the fact as a user message with special metadata
        metadata = metadata or {}
        metadata["type"] = "fact"  # Mark as a fact for special handling
        
        # Add directly to Mem4AI
        mem.add_memory(content, "user", metadata)