"""
Tool for suggesting movies based on user requests and preferences.
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
import tiktoken

# Import Mem4AI for suggestion memory
from agentloop.mem4ai import Mem4AI

class MovieSuggestion(BaseModel):
    name: str
    year: str
    original_language: str
    type: str  # 'movie' or 'tv-series'
    tmdb_id: Optional[str] = None

class MovieSuggestions(BaseModel):
    suggestions: List[MovieSuggestion]
    explanation: str
    status: bool

# Initialize tokenizer for token counting
tokenizer = tiktoken.get_encoding("cl100k_base")

# Maximum tokens to use for previous suggestions (to avoid overwhelming the context)
MAX_PREVIOUS_SUGGESTION_TOKENS = 1000

def get_suggestion_memory(user_id: str) -> Mem4AI:
    """
    Get or create a Mem4AI instance for storing movie suggestions.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        A Mem4AI instance configured for movie suggestions
    """
    # Create database directory if it doesn't exist
    db_dir = Path.home() / ".agentloop"
    db_dir.mkdir(exist_ok=True)
    
    # Create a dedicated database for movie suggestions
    db_path = str(db_dir / "movie_suggestions.db")
    
    # Initialize Mem4AI with a large context window for storing many suggestions
    return Mem4AI(db_path, context_window=16384)

def store_suggestion(memtor: Mem4AI, user_id: str, user_request: str, suggestion: Dict[str, Any]) -> None:
    """
    Store a movie suggestion in memory.
    
    Args:
        memtor: The Mem4AI instance
        user_id: The user's unique identifier
        user_request: The user's original query
        suggestion: The movie suggestion data
    """
    # Use user_id as the session_id for this memory system
    memtor.load_session(session_id=user_id, user_id=user_id)
    
    # Convert suggestion to string for storage
    suggestion_str = f"{suggestion['name']} ({suggestion['year']}, {suggestion['type']})"
    
    # Add to memory with metadata
    memtor.add_memory(
        message=suggestion_str,
        role="assistant",
        metadata={
            "suggestion_type": suggestion["type"],
            "year": suggestion["year"],
            "name": suggestion["name"],
            "user_request": user_request
        }
    )

def get_previous_suggestions(user_id: str) -> str:
    """
    Retrieve previous movie suggestions for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        A formatted string of previous suggestions with user queries
    """
    # Get memory system
    memtor = get_suggestion_memory(user_id)
    
    try:
        # Load the user's session
        memtor.load_session(session_id=user_id, user_id=user_id)
        
        # Get all previous suggestions
        messages = memtor.get_session_messages(token_limit=MAX_PREVIOUS_SUGGESTION_TOKENS)
        
        # Format as a list with user queries
        if not messages:
            return ""
            
        suggestions_formatted = []
        current_request = None
        current_suggestions = []
        
        # Group suggestions by user request
        for msg in messages:
            metadata = msg.get('metadata', {})
            request = metadata.get('user_request') if metadata else None
            
            # If this is a new request, add the previous group and start a new one
            if request and request != current_request and current_suggestions:
                suggestions_formatted.append(f"For query: \"{current_request}\"\nSuggested: {', '.join(current_suggestions)}")
                current_suggestions = []
            
            # Update current request and add this suggestion
            if request:
                current_request = request
            current_suggestions.append(msg['content'])
        
        # Add the last group if any
        if current_request and current_suggestions:
            suggestions_formatted.append(f"For query: \"{current_request}\"\nSuggested: {', '.join(current_suggestions)}")
        
        # Join with newlines and add header
        if suggestions_formatted:
            return "Previously suggested movies and shows:\n\n" + "\n\n".join(suggestions_formatted)
        else:
            # Fallback to simple list if grouping failed
            suggestions_list = [f"- {msg['content']}" for msg in messages]
            return "Previously suggested movies and shows:\n" + "\n".join(suggestions_list)
    
    except Exception as e:
        print(f"Error retrieving previous suggestions: {str(e)}")
        return ""
    finally:
        memtor.close()

def what2watch(
    user_request: str, 
    count: int = 5, 
    content_types: List[str] = ["movie", "tv-series"], 
    previous_suggestions: List[dict] = [],
    **context
) -> str:
    """
    Generate movie/TV show suggestions based on user request.
    
    Args:
        user_request: The user's query for content suggestions
        count: Number of content items to suggest (default: 5)
        content_types: Types of content to suggest (default: ["movie", "tv-series"])
        previous_suggestions: List of previously suggested content
        user_id: User identifier for personalization
        session_id: Current session identifier
        memtor: Memory system instance
        
    Returns:
        JSON string containing suggestions with movie/show information
    """
    # Get user_id from context
    user_id = context.get("user_id", "default_user")
    
    # Get previous suggestions from memory
    previous_suggestions_str = get_previous_suggestions(user_id)
    
    content_types_string = ", ".join(content_types)
    
    # Use OpenAI directly for specialized movie knowledge (agentloop already handles the main conversation)
    system_prompt = f"""You are a highly knowledgeable movie and TV series expert AI. 
    Your task is to suggest a number of movies or TV series based on the user's mood or request. 
    For each suggestion, provide the name, TMDB ID, release year, and type (movie or tv-series). 
    Use your vast knowledge of cinema and TV to make appropriate suggestions. 
    If the user does not specify a number, suggest {count} by default.
    If you're unsure about the exact TMDB ID, leave it blank.
    Return the suggestions in JSON format compatible with the Suggestions schema which is called `MovieSuggestions`. It has to keys:
    1/ suggestions: List[MovieSuggestion], which MovieSuggestions has these keys (name, year, original_language, type, tmdb_id if you know it).
    2/ explanation: Optional[str] - a short explanation of why you made these suggestions, in case status is False, explain why couldn't make suggestions.
    3/ status: Optional[bool] - True if suggestions are made, False if not.
    
    IMPORTANT: Avoid suggesting movies that have been previously recommended. 
    
    ## Suggestion Criteria:
    Suggest {count} {content_types_string}.
    
    ## Previously Suggested Movies:
    {previous_suggestions_str}
    
    ## Recent User Request:
    {user_request}
    """
    
    client = OpenAI()
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": system_prompt},
        ],
        response_format=MovieSuggestions,
    )
    response = completion.choices[0].message.parsed
    
    # Store successful suggestions in memory
    if response.status and response.suggestions:
        try:
            # Get memory instance
            memtor = get_suggestion_memory(user_id)
            
            # Store each suggestion
            for suggestion in response.suggestions:
                store_suggestion(
                    memtor=memtor, 
                    user_id=user_id,
                    user_request=user_request,
                    suggestion=suggestion.model_dump()
                )
            
            # Close memory connection
            memtor.close()
        except Exception as e:
            print(f"Error storing suggestions in memory: {str(e)}")
    
    # Add type information for agentloop processing
    res = {**response.model_dump(), "type": "movie_json"}
    
    return json.dumps(res)

# Tool schema definition for agentloop
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "what2watch",
        "description": "Suggest content items (movies or TV series) based on the user's query or request",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "The user's query or request for content suggestions"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of content suggestions to return (default: 5)"
                },
                "content_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["movie", "tv-series", "cartoon", "anime", "documentary", "short-film", "tv-show", "any"]
                    },
                    "description": "The type of content to suggest (default: ['movie', 'tv-series'])" 
                },
                "previous_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "description": "Movies previously suggested to the user"
                    },
                    "description": "List of movies previously suggested to the user"
                }
            },
            "required": ["user_request"]
        }
    }
}

# Export tools dictionary for dynamic loading
TOOLS = {
    "what2watch": what2watch
}

# Export schemas dictionary for dynamic loading
TOOL_SCHEMAS = {
    "what2watch": TOOL_SCHEMA
}