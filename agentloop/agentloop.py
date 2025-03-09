"""
Core implementation of agentloop.
Provides assistant creation, session management, and message processing.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional, Callable, Union, Tuple

from . import utils
from .mem4ai import Mem4AI  # Import the memory implementation directly

# Memory reset functions
def reset_all_memory():
    """
    Reset the entire memory database by deleting and recreating it.
    This is useful for testing or clearing all conversations.
    
    Returns:
        bool: True if successful, False otherwise
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

def reset_memory(session_id=None, agent_id=None):
    """
    Reset memory for a specific session, agent, or both.
    
    Args:
        session_id: Optional ID of the session to clear
        agent_id: Optional ID of the agent to clear
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not session_id and not agent_id:
        # If no specific IDs provided, reset everything
        return reset_all_memory()
    
    home_dir = os.path.expanduser("~")
    memory_db_path = os.path.join(home_dir, ".agentloop", "memory.db")
    
    if not os.path.exists(memory_db_path):
        # No database to reset
        return True
        
    try:
        # Create an instance of Mem4AI directly
        from .mem4ai import Mem4AI
        mem = Mem4AI(memory_db_path)
        
        if session_id and agent_id:
            # Clear memory for specific session and agent
            return mem.clear_memory(session_id=session_id, agent_id=agent_id)
        elif session_id:
            # Clear memory for specific session
            return mem.clear_memory(session_id=session_id)
        elif agent_id:
            # Clear memory for specific agent
            return mem.clear_memory(agent_id=agent_id)
        
        return True
    except Exception as e:
        print(f"Error resetting memory: {str(e)}")
        return False


def create_assistant(
    model_id: str,
    system_message: Optional[str] = None,
    tools: List[Callable] = [],
    params: Dict[str, Any] = {},
    template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    guardrail: Optional[str] = None,
    tool_schemas: Optional[List[Dict[str, Any]]] = None, # If this is provided, tools will be ignored
    remember_tool_calls: bool = False,  # Whether to include tool calls in future prompts
    synthesizer_model_id: Optional[str] = None  # Model to use for tool call synthesis, defaults to model_id if not provided
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
        tool_schemas: Optional list of tool schema dictionaries (if provided, tools will be ignored)
        remember_tool_calls: Reserved for future use - will enable including tool calls in context (current implementation stores but doesn't include in context)
        synthesizer_model_id: Model to use for tool call synthesis, defaults to model_id if not provided
        
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
    tool_schemas = tool_schemas or []
    if tools and not tool_schemas:
        for tool in tools:
            schema = utils.get_function_schema(tool)
            tool_schemas.append(schema)
    
    # Create assistant configuration
    assistant = {
        "model": model_id,
        "system_message": final_system_message,
        "tools": tool_schemas,
        "tool_map": {tool.__name__: tool for tool in tools},
        "params": params,
        "remember_tool_calls": remember_tool_calls,
        "synthesizer_model_id": synthesizer_model_id or model_id
    }
    
    return assistant


def _prepare_api_call(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    stream: bool = False
) -> Tuple[Dict[str, Any], str]:
    """
    Helper function to prepare messages and API parameters for OpenAI calls.
    
    Args:
        session: Session dictionary from start_session
        message: Text message or dict with text and image_url for vision
        user_template: Jinja2 template for the user message
        template_params: Variables to render the template
        context: Additional context to include
        schema: JSON schema for structured output
        stream: Whether to enable streaming mode
        
    Returns:
        Tuple containing:
        - Dictionary of API parameters to pass to OpenAI
        - Formatted user message for memory storage
    """
    assistant = session["assistant"]
    memtor : Mem4AI = session.get("memory")
    
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
            # Include only user and assistant messages for now
            # Tool calls need special handling to satisfy OpenAI's requirements
            if mem['role'] in ['user', 'assistant']:
                # Keep only role and content for API compatibility
                short_term_context.append({
                    "role": mem['role'], 
                    "content": mem['content']
                })
        
        # Process middle-term memory
        for mem in memory_contexts.get("middle_term", []):
            # Include only user and assistant messages for now
            # Tool calls need special handling to satisfy OpenAI's requirements
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
    
    # Add stream parameter if requested
    if stream:
        api_params["stream"] = True
    
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
    
    return api_params, formatted_message


def start_session(assistant: Dict[str, Any], session_id: str, user_id:str = None) -> Dict[str, Any]:
    """
    Start or resume a session with the given assistant.
    
    Args:
        assistant: Assistant configuration from create_assistant
        session_id: Unique identifier for the session
        user_id: Optional user identifier
        
    Returns:
        Session dictionary with assistant and memory
    """
    # Create new session with just essential information
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "assistant": assistant,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "metadata": {},
        "memory": None
    }
    
    # Initialize memory for this session with the session ID
    # Create path to memory database
    home_dir = os.path.expanduser("~")
    memory_db_path = os.path.join(home_dir, ".agentloop", "memory.db")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(memory_db_path), exist_ok=True)
    
    # Initialize Mem4AI directly
    mem = Mem4AI(memory_db_path)
    mem.load_session(session_id=session_id, user_id=user_id)
    session["memory"] = mem
    
    return session


def process_message(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    token_callback: Optional[Callable[[Dict[str, int]], None]] = None,
    context_data: Dict[str, Any] = None
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
        context_data: Additional data to pass to tools (not part of conversation)
        
    Returns:
        Dictionary with response and usage statistics
    """
    import openai

    assistant = session["assistant"]
    memtor : Mem4AI = session.get("memory")
    
    api_params, formatted_message = _prepare_api_call(
        session, message, user_template, template_params, context, schema
    )
    
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
                    # Pass context_data to the function if available
                    if context_data:
                        function_response = function(**function_args, **context_data)
                    else:
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
                    "tool_call_id": tool_call.id,
                    "iteration": current_iteration
                }
                
                # Store function call in memory
                memtor.add_memory(
                    f"Function call: {function_name} with args: {function_args}", 
                    "assistant", 
                    tool_metadata
                )
                
                # Always store tool result in memory for potential future reference
                memtor.add_memory(
                    f"Function result: {result}", 
                    "tool", 
                    tool_metadata
                )
        
        # Add tool responses to current iteration conversation
        tool_messages.extend(tool_responses)
        tool_conversation.extend(tool_responses)
        
        # Make another API call with all tool results so far
        api_params["messages"] = api_params['messages'] + tool_conversation
        
        # Use synthesizer model for tool call processing
        api_params['model'] = assistant.get("synthesizer_model_id")
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


def streamed_process_message(
    session: Dict[str, Any],
    message: Union[str, Dict[str, Any]],
    user_template: Optional[str] = None,
    template_params: Dict[str, Any] = {},
    context: Optional[Union[str, List[Dict[str, Any]]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    context_data: Dict[str, Any] = None
):
    """
    Process a user message in the given session and yield streaming updates.
    
    This generator function yields dictionaries with updates during processing.
    The yielded dictionaries have a 'type' key that can be one of:
    - 'token': A token from the LLM response with 'content' as the token text
    - 'tool_start': When a tool starts executing with 'name' and 'args'
    - 'tool_result': When a tool finishes with 'name' and 'result'
    - 'finish': When processing is complete with 'response' and 'usage'
    
    Args:
        session: Session dictionary from start_session
        message: Text message or dict with text and image_url for vision
        user_template: Jinja2 template for the user message
        template_params: Variables to render the template
        context: Additional context to include
        schema: JSON schema for structured output
        context_data: Additional data to pass to tools (not part of conversation)
        
    Yields:
        Dictionaries with streaming updates during processing
    """
    import openai
    
    assistant = session["assistant"]
    memtor : Mem4AI = session.get("memory")
    
    api_params, formatted_message = _prepare_api_call(
        session, message, user_template, template_params, context, schema, stream=True
    )
    
    # Make streaming API call to OpenAI
    response_stream = openai.chat.completions.create(**api_params)
    
    # Variables to accumulate the response
    collected_content = []
    assistant_message = None
    tool_calls = []
    
    # Process the initial streaming response
    for chunk in response_stream:
        if hasattr(chunk.choices[0], 'delta'):
            delta = chunk.choices[0].delta
            
            # Handle content
            if delta.content is not None:
                collected_content.append(delta.content)
                yield {"type": "token", "data": delta.content}
            
            # Handle tool calls (this is more complex in streaming mode)
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # In streaming, tool calls come in fragments
                    # We need to accumulate them
                    if tool_call.index is not None:
                        # New or update to existing tool call
                        idx = tool_call.index
                        
                        # Ensure we have space in our tool_calls list
                        while len(tool_calls) <= idx:
                            tool_calls.append({
                                "id": None,
                                "function": {"name": "", "arguments": ""},
                                "type": "function"
                            })
                        
                        # Update tool call data
                        if tool_call.id:
                            tool_calls[idx]["id"] = tool_call.id
                        
                        if hasattr(tool_call, 'function'):
                            if tool_call.function.name:
                                tool_calls[idx]["function"]["name"] = tool_call.function.name
                            
                            if tool_call.function.arguments:
                                # Append to arguments - they might come in chunks
                                tool_calls[idx]["function"]["arguments"] += tool_call.function.arguments
    
    # Handle tool calls if any were detected
    if tool_calls:
        # At this point, we have the complete tool calls
        # Similar to process_message, now we execute them one by one
        max_tool_iterations = 5  # Safety limit to prevent infinite loops
        current_iteration = 0
        tool_conversation = []  # Track the entire tool conversation
        
        # Reconstruct the assistant message with tool calls
        from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
        message_content = ''.join([c for c in collected_content if c is not None])
        
        # Create proper ChatCompletionMessageToolCall objects from our accumulated data
        formatted_tool_calls = []
        for tc in tool_calls:
            if tc['id'] and tc['function']['name']:  # Only include complete tool calls
                formatted_tool_calls.append(
                    ChatCompletionMessageToolCall(
                        id=tc['id'],
                        type="function",
                        function={
                            "name": tc['function']['name'],
                            "arguments": tc['function']['arguments']
                        }
                    )
                )
        
        assistant_message = ChatCompletionMessage(
            role="assistant",
            content=message_content,
            tool_calls=formatted_tool_calls if formatted_tool_calls else None
        )
        
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
                
                # Notify about tool execution starting
                yield {"type": "tool_start", "data": {
                    "name": function_name,
                    "args": function_args,
                    "id": tool_call.id
                }}
                
                # Find and execute the function
                if function_name in tool_map:
                    function = tool_map[function_name]
                    try:
                        # Pass context_data to the function if available
                        if context_data:
                            function_response = function(**function_args, **context_data)
                        else:
                            function_response = function(**function_args)
                        result = str(function_response)
                    except Exception as e:
                        result = f"Error: {str(e)}"
                else:
                    result = f"Error: Function {function_name} not found"
                
                # Notify about tool execution result
                yield {"type": "tool_result", "data": {
                    "name": function_name,
                    "result": result,
                    "id": tool_call.id
                }}
                
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
                        "tool_call_id": tool_call.id,
                        "iteration": current_iteration
                    }
                    
                    # Store function call in memory
                    memtor.add_memory(
                        f"Function call: {function_name} with args: {function_args}", 
                        "assistant", 
                        tool_metadata
                    )
                    
                    # Always store tool result in memory for potential future reference
                    memtor.add_memory(
                        f"Function result: {result}", 
                        "tool", 
                        tool_metadata
                    )
            
            # Add tool responses to current iteration conversation
            tool_messages.extend(tool_responses)
            tool_conversation.extend(tool_responses)
            
            # Make another API call with all tool results so far
            api_params["messages"] = api_params["messages"] + tool_conversation
            
            # Use synthesizer model for tool call processing
            api_params['model'] = assistant.get("synthesizer_model_id")
            
            # Stream the next response
            collected_tool_content = []
            tool_call_response_stream = openai.chat.completions.create(**api_params)
            
            new_tool_calls = []
            for chunk in tool_call_response_stream:
                if hasattr(chunk.choices[0], 'delta'):
                    delta = chunk.choices[0].delta
                    
                    # Handle content
                    if delta.content is not None:
                        collected_tool_content.append(delta.content)
                        yield {"type": "token", "data": delta.content}
                    
                    # Handle tool calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        # Same accumulation logic as above
                        for tool_call in delta.tool_calls:
                            if tool_call.index is not None:
                                idx = tool_call.index
                                
                                while len(new_tool_calls) <= idx:
                                    new_tool_calls.append({
                                        "id": None,
                                        "function": {"name": "", "arguments": ""},
                                        "type": "function"
                                    })
                                
                                if tool_call.id:
                                    new_tool_calls[idx]["id"] = tool_call.id
                                
                                if hasattr(tool_call, 'function'):
                                    if tool_call.function.name:
                                        new_tool_calls[idx]["function"]["name"] = tool_call.function.name
                                    
                                    if tool_call.function.arguments:
                                        new_tool_calls[idx]["function"]["arguments"] += tool_call.function.arguments
            
            # Create new assistant message from the tool call response
            message_content = ''.join([c for c in collected_tool_content if c is not None])
            
            # Process new tool calls if any
            formatted_new_tool_calls = []
            for tc in new_tool_calls:
                if tc['id'] and tc['function']['name']:  # Only include complete tool calls
                    formatted_new_tool_calls.append(
                        ChatCompletionMessageToolCall(
                            id=tc['id'],
                            type="function",
                            function={
                                "name": tc['function']['name'],
                                "arguments": tc['function']['arguments']
                            }
                        )
                    )
            
            assistant_message = ChatCompletionMessage(
                role="assistant",
                content=message_content,
                tool_calls=formatted_new_tool_calls if formatted_new_tool_calls else None
            )
            
            # If we're at the max iterations and still have tool calls, log a warning
            if (current_iteration == max_tool_iterations and 
                hasattr(assistant_message, 'tool_calls') and 
                assistant_message.tool_calls):
                warning_msg = f"Warning: Reached maximum tool call iterations ({max_tool_iterations})"
                print(warning_msg)
                yield {"type": "warning", "data": warning_msg}
                if memtor:
                    memtor.add_memory(
                        warning_msg, 
                        "system", 
                        {"type": "warning", "timestamp": datetime.datetime.now().isoformat()}
                    )
    else:
        # No tool calls, just a regular response
        # We've already streamed it, just reconstruct the final message
        from openai.types.chat import ChatCompletionMessage
        message_content = ''.join([c for c in collected_content if c is not None])
        assistant_message = ChatCompletionMessage(role="assistant", content=message_content)
    
    # Update session timestamp
    session["updated_at"] = datetime.datetime.now().isoformat()
    
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
    
    # Send final completion event with full response
    yield {
        "type": "finish", 
        "data": {
            "response": assistant_message.content,
            "usage": None  # Usage stats aren't available in streaming mode
        }
    }


