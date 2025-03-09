"""
Moji Movie Assistant implementation using agentloop.

This assistant provides movie recommendations, information about movies,
and manages user favorite lists.
"""

import os
import json
import importlib
from typing import Dict, Any, Optional, Union
from glob import glob

# Import agentloop components
import agentloop

# Response type definitions
class ResponseTypeEnum:
    TEXT = "text"
    MOVIE_JSON = "movie_json"
    LIST = "list"
    MOVIE_INFO = "movie_info"
    TRAILER = "trailer"
    TEXT_RESPONSE = "text_response"

class MojiAssistant:
    """
    Movie assistant for the Moji application using agentloop.
    """
    
    def __init__(
        self,
        user_id: str,
        user_token: Optional[str] = None,
        model_id: str = "gpt-4o",
        action: str = "assistant",
        params: Dict[str, Any] = {},
        tools_path: str = None,
        verbose: bool = True,
        remember_tool_calls: bool = False,
        synthesizer_model_id: Optional[str] = None
    ):
        """
        Initialize the Moji assistant.
        
        Args:
            user_id: Unique identifier for the user
            user_token: Authentication token for the user
            model_id: OpenAI model to use
            action: Action type (assistant, what2watch, etc.)
            params: Additional parameters for the assistant
            tools_path: Path to tool modules
            verbose: Whether to print debug information
            remember_tool_calls: Reserved for future use - tool calls are stored but not included in context
            synthesizer_model_id: Model to use for tool call synthesis, defaults to model_id if not provided
        """
        self.user_id = user_id
        self.user_token = user_token
        self.model_id = model_id
        self.action = action
        self.params = params
        self.verbose = verbose
        self.remember_tool_calls = remember_tool_calls
        self.synthesizer_model_id = synthesizer_model_id
        
        # Load tools and schemas from the tools directory
        self.tools, self.tool_schemas = self._load_tools(tools_path)
        
        # Initialize the assistant with agentloop
        self.session = self._initialize_session()
        
        if verbose:
            print(f"Initialized MojiAssistant for user {user_id}")
    
    def _load_tools(self, tools_path: Optional[str] = None) -> tuple:
        """
        Dynamically load tools from Python modules in the tools directory.
        
        Args:
            tools_path: Path to the tools directory. If None, uses default.
            
        Returns:
            Tuple of (tools_dict, schemas_dict)
        """
        all_tools = {}
        all_schemas = {}
        
        # Default to the 'tools' directory in the same directory as this file
        if not tools_path:
            tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
        
        # Find all Python files in the tools directory
        tool_files = glob(os.path.join(tools_path, "*.py"))
        
        for file_path in tool_files:
            if os.path.basename(file_path) == "__init__.py":
                continue
                
            try:
                # Convert file path to module path
                module_name = os.path.basename(file_path).replace(".py", "")
                module_path = f"moji.tools.{module_name}"
                
                # Import the module
                module = importlib.import_module(module_path)
                
                # Extract TOOLS dictionary if it exists
                if hasattr(module, "TOOLS"):
                    all_tools.update(module.TOOLS)
                
                # Extract TOOL_SCHEMAS dictionary if it exists
                if hasattr(module, "TOOL_SCHEMAS"):
                    all_schemas.update(module.TOOL_SCHEMAS)
                    
                if self.verbose:
                    print(f"Loaded tools from {module_path}")
                    
            except Exception as e:
                print(f"Error loading tools from {file_path}: {str(e)}")
        
        return all_tools, all_schemas
    
    def _initialize_session(self) -> Dict[str, Any]:
        """
        Initialize or resume an agentloop session for this user.
        
        Returns:
            Agentloop session dictionary
        """
        # Create a session ID based on user ID and action
        session_id = f"{self.user_id}_{self.action}"
        
        # Create an assistant with the appropriate configuration
        assistant = agentloop.create_assistant(
            model_id=self.model_id,
            system_message=self._get_system_message(),
            tools=list(self.tools.values()),
            tool_schemas=list(self.tool_schemas.values()) if self.tool_schemas else None,
            params={},
            remember_tool_calls=self.remember_tool_calls,
            synthesizer_model_id=self.synthesizer_model_id
        )
        
        # Start the session
        session = agentloop.start_session(assistant, session_id, user_id=self.user_id)
        
        return session
    
    def _get_system_message(self) -> str:
        """
        Generate the system message based on the action and parameters.
        
        Returns:
            System message for the assistant
        """
        # This would ideally use template loading similar to the original implementation
        # For now, using a simplified approach
        
        action = self.action
        base_prompt = """You are Moji, a friendly and knowledgeable movie assistant.
You help users discover movies and TV shows based on their preferences.
You can suggest content, provide information about movies, and manage user favorite lists.

Your responses should be friendly, concise, and focused on helping the user find content they'll enjoy.
When suggesting movies, prioritize quality recommendations over quantity.
"""
        
        # Add action-specific instructions
        if action == "what2watch":
            action_prompt = """
Your primary goal is to suggest movies and TV shows that match the user's request.
Use the what2watch tool when the user asks for recommendations.
"""
        elif action == "talk2me":
            action_prompt = """
Your primary goal is to engage in friendly conversation about movies and TV shows.
Focus on being conversational rather than just providing information.
"""
        else:
            action_prompt = """
Your primary goal is to assist the user with their movie-related needs.
You can provide recommendations, information, or help manage their favorite lists.
"""
        
        return base_prompt + action_prompt
    
    def chat(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            message: User message (text or dictionary with text/image)
            
        Returns:
            Response dictionary with output_type and response
        """
        # Process the message using agentloop with context_data for credentials
        result = agentloop.process_message(
            self.session,
            message,
            context=self._get_context(),
            context_data={
                "user_id": self.user_id,
                "user_token": self.user_token
            }
        )
        
        # Convert the response to the expected format
        return self._format_response(result)
        
    def chat_stream(self, message: Union[str, Dict[str, Any]]):
        """
        Process a user message and generate a streaming response.
        
        Args:
            message: User message (text or dictionary with text/image)
            
        Yields:
            Streaming event dictionaries from agentloop
        """
        # Process the message using agentloop with streaming and context_data for credentials
        for stream_event in agentloop.streamed_process_message(
            self.session,
            message,
            context=self._get_context(),
            context_data={
                "user_id": self.user_id,
                "user_token": self.user_token
            }
        ):
            # For 'finish' events, format the final response
            if stream_event['type'] == 'finish':
                stream_event['data']['formatted_response'] = self._format_response({
                    "response": stream_event['data']['response']
                })
                
            yield stream_event
    
    def _get_context(self) -> str:
        """
        Get additional context for the current conversation.
        
        Returns:
            Context string
        """
        context_parts = []
        
        # Add user details if available
        user_details = self.params.get("user_details", {})
        user_name = user_details.get("name", "")
        if user_name:
            context_parts.append(f"# User Information\nThe user's name is: {user_name}")
        
        # Add favorite lists if available
        favorite_lists = self.params.get("user_extra_data", {}).get("favorite_lists", [])
        if favorite_lists:
            context_parts.append(f"# User's Favorite Lists\n```json\n{json.dumps(favorite_lists, indent=2)}\n```")
        
        # Combine all context parts
        return "\n\n".join(context_parts)
    
    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the agentloop response to match the expected output format.
        
        Args:
            result: Agentloop response dictionary
            
        Returns:
            Formatted response with output_type and response fields
        """
        response_text = result["response"]
        
        # Check if the response is a JSON string
        try:
            # Parse the JSON response
            json_response = json.loads(response_text)
            
            # Check if it has a 'type' field
            if 'type' in json_response:
                return_type = json_response['type']
                data = json_response.get('data', {})
                
                # Handle different response types
                if return_type == ResponseTypeEnum.MOVIE_JSON:
                    return {
                        "output_type": "movie_json",
                        "response": data  # This should include 'movies' field
                    }
                elif return_type == ResponseTypeEnum.LIST:
                    return {
                        "output_type": "list",
                        "response": data.get("items", [])
                    }
                elif return_type == ResponseTypeEnum.MOVIE_INFO:
                    return {
                        "output_type": "movie_info",
                        "response": data
                    }
                elif return_type == ResponseTypeEnum.TEXT_RESPONSE:
                    # Handle app support assistant responses
                    return {
                        "output_type": "text_response",
                        "response": {
                            "answer": json_response.get("answer", ""),
                            "relevant_docs": json_response.get("relevant_docs", [])
                        }
                    }
                else:
                    # Default case for other JSON responses
                    return {
                        "output_type": return_type,
                        "response": data
                    }
            
            # If we have JSON but no type field, check for specific structures
            if 'suggestions' in json_response:
                # Likely a movie suggestion response
                return {
                    "output_type": "movie_json",
                    "response": {
                        "movies": json_response.get("suggestions", []),
                        "explanation": json_response.get("explanation", "")
                    }
                }
            
        except json.JSONDecodeError:
            # Not a JSON response, treat as text
            pass
        
        # Default case: return as text
        return {
            "output_type": "text",
            "response": {"content": response_text}
        }
    
    def clear_thread(self):
        """
        Clear the current conversation thread.
        """
        # Reset the session by creating a new one
        self.session = self._initialize_session()
        
        if self.verbose:
            print(f"Thread cleared for user {self.user_id}")
    
    def clear_memory(self, reset_all: bool = False):
        """
        Clear memory for this assistant.
        
        Args:
            reset_all: If True, clear all memory. If False, only clear this session's memory.
            
        Returns:
            bool: True if successful, False otherwise
        """
        session_id = self.session.get("session_id")
        
        if reset_all:
            result = agentloop.reset_all_memory()
        else:
            # Reset just this session's memory
            result = agentloop.reset_memory(session_id=session_id)
            
        if self.verbose:
            if result:
                print(f"Memory cleared for session {session_id}")
            else:
                print(f"Failed to clear memory for session {session_id}")
                
        return result

