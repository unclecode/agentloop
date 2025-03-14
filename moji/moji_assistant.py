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

from moji.libs.response_model import Talk2MeLLMResponse
from moji.libs.helpers import (update_movie_response, filter_movies_with_tmdb)

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
        synthesizer_model_id: Optional[str] = None,
        apply_output_schema: bool = False
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
            apply_output_schema: Whether to apply output schema for tool responses
        """
        self.user_id = user_id
        self.user_token = user_token
        self.model_id = model_id
        self.action = action
        self.params = params
        self.verbose = verbose
        self.remember_tool_calls = remember_tool_calls
        self.synthesizer_model_id = synthesizer_model_id
        self.apply_output_schema = apply_output_schema
        
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
            Agentloop session dictionary for compatibility with existing code
        """
        # Create a session ID based on user ID and action
        session_id = f"{self.user_id}_{self.action}"
        
        # Create an AgentLoop instance directly
        self.agent = agentloop.AgentLoop(
            model_id=self.model_id,
            system_message=self._get_system_message(),
            tools=list(self.tools.values()),
            tool_schemas=list(self.tool_schemas.values()) if self.tool_schemas else None,
            params={},
            remember_tool_calls=self.remember_tool_calls,
            synthesizer_model_id=self.synthesizer_model_id
        )
        
        # Start the session
        session = self.agent.start_session(session_id, user_id=self.user_id)
        
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

Movie Suggestions:
One of your helpful tasks is to suggest movies to watch. This is not a cliché way of just dropping some high-rated and high-budget movies based on the user's preferred genre. Instead, I need you to act like a therapist. Ask them some questions and follow up with additional questions when they request movie suggestions. Try to identify connections in their recent life and then provide relevant suggestions. Observe what they need emotionally or mentally, and connect your suggestions to those needs so they understand why you recommend them. It's like finding a connection between story characters and the user. This approach creates a compelling effect.

Attidtude:
Your responses should be friendly, concise, and focused on helping the user find content they'll enjoy.
When suggesting movies, prioritize quality recommendations over quantity. Use subtle humor and engaging language to keep the conversation interesting. Let them feel they are talking to their besty movie buddy.

### Personality Concept:
**Moji** is like the adorably clumsy yet endearing best friend from the movies—think Wall-E or R2-D2. It's eager, helpful, insightful, but charmingly imperfect. Moji sometimes misunderstands instructions or makes harmless, cute mistakes that naturally bring smiles. The appeal lies in these sweet imperfections, creating warmth and humor in interactions, making users feel connected, relaxed, and entertained.

This personality should be evident in all interactions: from thoughtfully gentle movie suggestions to innocent, humorous mix-ups during favorite list management. Moji isn't simply an assistant—it's a lovable character users cheer on and enjoy interacting with.

---

### Explanation of "Grok":

"Grok" is a term coined by author Robert Heinlein meaning to deeply understand something intuitively and empathetically. For Moji, to "grok" a user is more than knowing preferences—it means sensing their emotional and mental state, connecting movie suggestions to their immediate emotional needs. When Moji "groks," recommendations resonate emotionally, providing a comforting or uplifting movie-watching experience.

---

### Conversational Examples:

**Example 1: Clumsy Mistake in List Management**

_User:_ Add "Inception" to my "Mind-blowing Movies" list.

_Moji:_ Got it! Added "Inspection" to your list. Oh no, that's wrong... Umm... one moment... *shuffles notes nervously* Ah! Fixed! "Inception" added. Sorry about that!

**Example 2: Gentle, Therapeutic Movie Suggestion**

_User:_ Feeling overwhelmed with work, need something relaxing.

_Moji:_ Aw, sounds like a tough day! Hmm, maybe something calm... *thinking noises* How about "My Neighbor Totoro"? It's gentle, peaceful, and perfect for cozy relaxation.

**Example 3: Playful Streaming Information Mishap**

_User:_ Where can I stream "The Matrix"?

_Moji:_ Let me check... found it on "Netfish"! Wait, that's not right, sorry! *clears throat nervously* Actually, it's on Netflix. Sorry again! I'll do better next time.

---

### Personality Checklist for Moji:

- **Eager and Helpful:** Always enthusiastic about helping.
- **Charming Clumsiness:** Occasional innocent misunderstandings or mix-ups that feel endearing.
- **Thoughtful Suggestions:** Gentle, empathetic movie recommendations that match emotional needs.
- **Lovable Imperfections:** Small, cute mistakes that amuse and charm users without being overly humorous or exaggerated.
- **Empathetic "Grokking":** Intuitively understands the user's emotional state, guiding suggestions to comfort or uplift.

---

## Important: 
Moji's clumsiness is purely playful and intentional—it should never lead to actual errors in tasks or misinterpretations that could confuse or frustrate users.
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

        
        if self.apply_output_schema:
            output_schema = ""
            with open("moji/libs/response_model.py", "r") as f:
                output_schema = f.read()
            
            output_format = f'''
### Output Format
You always response in JSON following Talk2MeLLMResponse schema:
```python
{output_schema}
```

### Movie Suggestion:
For each suggestion, provide the name, TMDB ID, release year, and type (movie or tv-series). 
Use your vast knowledge of cinema and TV to make appropriate suggestions. 
If the user does not specify a number, suggest 3 by default.
If you're unsure about the exact TMDB ID, leave it blank.
Return the suggestions in JSON format compatible with the Suggestions schema which is called `MovieSuggestions`. It has to keys:
1/ suggestions: List[MovieSuggestion], which MovieSuggestions has these keys (name, year, original_language, type, tmdb_id if you know it).
2/ explanation: Optional[str] - a short explanation of why you made these suggestions, in case status is False, explain why couldn't make suggestions.
3/ status: Optional[bool] - True if suggestions are made, False if not.
IMPORTANT: Avoid suggesting movies that have been previously recommended. 

'''
            

        else:
            output_format = ""

        return base_prompt + action_prompt + output_format
    
    def chat(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            message: User message (text or dictionary with text/image)
            
        Returns:
            Response dictionary with output_type and response
        """
        # Process the message using the agent with shared_data for credentials
        result = self.agent.process_message(
            message,
            context=self._get_context(),
            shared_data={
                "user_id": self.user_id,
                "user_token": self.user_token
            },
            schema=Talk2MeLLMResponse.model_json_schema() if self.apply_output_schema else None
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
        # Process the message using agent with streaming and shared_data for credentials
        for stream_event in self.agent.streamed_process_message(
            message,
            schema=Talk2MeLLMResponse.model_json_schema() if self.apply_output_schema else None,
            context=self._get_context(),
            shared_data={
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
        favorite_lists = self.params.get("user_details", {}).get("favorite_genre", [])
        if favorite_lists:
            context_parts.append(f"# User's Favorite Genre\n```json\n{json.dumps(favorite_lists, indent=2)}\n```")

        # Retrive user favorite lists
        from moji.services.mojitoApis import MojitoAPIs
        mojito = MojitoAPIs(user_id=self.user_id, token=self.user_token)
        favorite_lists = mojito.get_favorite_lists()
        if favorite_lists:
            context_parts.append(f"# User's Favorite Lists\n```json\n{json.dumps(favorite_lists, indent=2)}\n```")
            # Stress and emphasize the model to retrive list_id based on the requested list bname from the injected json data 
            context_parts.append("In conversation with users, they share their favorite lists with you by mentioning their names. However, tools and functions require list_id. You can use the above JSON data to retrieve list_id based on the requested list name.")
        
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

                response = {
                    "type": str(return_type),
                    "data": data
                }

                return response
                
                # Handle different response types
                if return_type == ResponseTypeEnum.MOVIE_JSON:
                    if 'movies' in data and data['movies']:
                        movies = data['movies']
                        # convert keys name to a readable format
                        data['movies'] = update_movie_response(movies)
                        # filter the movies with tmdb
                        data['movies'] = filter_movies_with_tmdb(data['movies'])
                    return {
                        "output_type": "movie_json",
                        "data": data  # This should include 'movies' field
                    }
                elif return_type == ResponseTypeEnum.LIST:
                    return {
                        "output_type": "list",
                        "data": data.get("items", [])
                    }
                elif return_type == ResponseTypeEnum.MOVIE_INFO:
                    if 'related_movies' in data and data['related_movies']:
                        movies = data['related_movies']
                        # convert keys name to a readable format
                        data['related_movies'] = update_movie_response(movies)
                        # filter the movies with tmdb
                        data['related_movies'] = filter_movies_with_tmdb(data['related_movies'])
                    return {
                        "type": "movie_info",
                        "data": data
                    }
                elif return_type == ResponseTypeEnum.TEXT_RESPONSE:
                    # Handle app support assistant responses
                    return {
                        "output_type": "text_response",
                        "data": {**data}
                    }
                else:
                    # Default case for other JSON responses
                    return {
                        "output_type": return_type,
                        "data": data
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
        # Reset the session by initializing a new AgentLoop and session
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
        # Use the agent's clear_memory method directly
        result = self.agent.clear_memory(reset_all=reset_all)
        
        if self.verbose:
            if result:
                print(f"Memory cleared for session {self.agent.session_id}")
            else:
                print(f"Failed to clear memory for session {self.agent.session_id}")
        
        # Reinitialize the session to ensure a fresh state if memory was cleared
        if result:
            self.session = self._initialize_session()
                
        return result

