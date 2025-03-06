"""
Core implementation of agentloop.
Provides assistant creation, session management, and message processing.
"""

import os
import json
import inspect
import datetime
from typing import List, Dict, Any, Optional, Callable, Union
import openai

from . import utils
from . import memory
from mem4ai import Memtor


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
        Session dictionary with assistant, history, and memory
    """
    db_path = utils.get_db_path()
    utils.create_db_tables(db_path)
    
    # Try to load existing session
    existing_session = utils.load_session(db_path, session_id)
    
    if existing_session:
        # Session exists, use it
        session = existing_session
        # Update assistant config in case it changed
        session["assistant"] = assistant
    else:
        # Create new session
        session = {
            "session_id": session_id,
            "assistant": assistant,
            "history": [],
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
    
    # Initialize memory for this session
    memtor = memory.get_memory_manager()
    session["memory"] = memtor
    
    # Save session to database
    utils.save_session(db_path, session_id, assistant, session.get("history", []))
    
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
    assistant = session["assistant"]
    history = session.get("history", [])
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
    
    # Search memory for relevant context
    relevant_memories = []
    if memtor and isinstance(message, str):
        query = message
        memories = memory.search_memories(memtor, query, session["session_id"])
        if memories:
            memory_text = "\n\n".join([mem.content for mem in memories])
            relevant_memories = [{"role": "system", "content": f"Relevant context from memory: {memory_text}"}]
    
    # Prepare messages for API call
    messages = []
    
    # Add system message if specified
    if assistant.get("system_message"):
        messages.append({"role": "system", "content": assistant["system_message"]})
    
    # Add memory context if available
    if relevant_memories:
        messages.extend(relevant_memories)
    
    # Add additional context if provided
    if context:
        if isinstance(context, str):
            messages.append({"role": "system", "content": context})
        elif isinstance(context, list):
            messages.extend(context)
    
    # Add conversation history
    messages.extend(history)
    
    # Add user message
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
    
    # Extract response content
    assistant_message = response.choices[0].message
    
    # Handle tool calls if present
    if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
        tool_history = []
        
        # Add assistant message with tool calls to history
        tool_history.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [tool_call.model_dump() for tool_call in assistant_message.tool_calls]
        })
        
        # Process tool calls (up to 5 iterations to prevent infinite loops)
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
            
            # Add tool response to history
            tool_responses.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result
            })
        
        # Add tool responses to history
        tool_history.extend(tool_responses)
        
        # Make second API call with tool results
        api_params["messages"] = messages + tool_history
        
        response = openai.chat.completions.create(**api_params)
        assistant_message = response.choices[0].message
        
        # Update history with tool interactions
        history.extend(tool_history)
    
    # Add final assistant response to history
    history.append({
        "role": "assistant",
        "content": assistant_message.content
    })
    
    # Save updated history to session
    session["history"] = history
    utils.save_session(utils.get_db_path(), session["session_id"], assistant, history)
    
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
    
    # Store insights in memory
    if memtor and isinstance(message, str):
        # Extract insights from the conversation and store in memory
        last_user_msg = message
        last_assistant_msg = assistant_message.content
        
        insight = f"User asked: '{last_user_msg}', Assistant answered: '{last_assistant_msg}'"
        memory.add_memory(
            memtor,
            content=insight,
            metadata={"type": "conversation", "timestamp": datetime.datetime.now().isoformat()},
            user_id=session["session_id"]
        )
    
    # Return response and usage
    return {
        "response": assistant_message.content,
        "usage": usage
    }


def get_history(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get the conversation history from a session.
    
    Args:
        session: Session dictionary
        
    Returns:
        List of message dictionaries
    """
    return session.get("history", [])


def set_history(session: Dict[str, Any], new_history: List[Dict[str, Any]]):
    """
    Set the conversation history for a session.
    
    Args:
        session: Session dictionary
        new_history: New conversation history
    """
    session["history"] = new_history
    utils.save_session(
        utils.get_db_path(),
        session["session_id"],
        session["assistant"],
        new_history
    )


def add_messages(session: Dict[str, Any], messages: List[Dict[str, Any]], prepend: bool = False):
    """
    Add messages to the conversation history.
    
    Args:
        session: Session dictionary
        messages: Messages to add
        prepend: If True, add messages to the beginning of history
    """
    history = session.get("history", [])
    
    if prepend:
        session["history"] = messages + history
    else:
        session["history"] = history + messages
    
    utils.save_session(
        utils.get_db_path(),
        session["session_id"],
        session["assistant"],
        session["history"]
    )


def get_memory(session: Dict[str, Any]) -> Optional[Memtor]:
    """
    Get the memory object from a session.
    
    Args:
        session: Session dictionary
        
    Returns:
        Memtor instance or None
    """
    return session.get("memory")


def update_memory(session: Dict[str, Any], content: str, metadata: Dict[str, Any] = None):
    """
    Add a new memory to the session.
    
    Args:
        session: Session dictionary
        content: Memory content
        metadata: Additional metadata (optional)
    """
    memtor = session.get("memory")
    if memtor:
        metadata = metadata or {}
        memory.add_memory(memtor, content, metadata, session["session_id"])