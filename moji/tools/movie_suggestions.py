"""
Tool for suggesting movies based on user requests and preferences.
"""
import json
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

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

def what2watch(
    user_request: str, 
    count: int = 5, 
    content_types: List[str] = ["movie", "tv-series"], 
    previous_suggestions: List[dict] = [],
    user_id: str = None,
    session_id: str = None,
    memtor = None
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
    # Check for memories if memtor is available
    memories = []
    if memtor and user_id and session_id:
        memories = memtor.search_memories(
            top_k=10,
            user_id=user_id,
            session_id=session_id,
        )
        previous_suggestions = "\n".join([memory.content for memory in memories])
    else:
        previous_suggestions = json.dumps(previous_suggestions)
    
    content_types_string = ", ".join(content_types)
    
    # Use OpenAI directly for specialized movie knowledge (agentloop already handles the main conversation)
    system_prompt = f"""You are a highly knowledgeable movie and TV series expert AI. 
    Your task is to suggest a number of movies or TV series based on the user's mood or request. 
    For each suggestion, provide the name, TMDB ID, release year, and type (movie or tv-series). 
    Use your vast knowledge of cinema and TV to make appropriate suggestions. 
    If the user does not specify a number, suggest 5 by default.
    If you're unsure about the exact TMDB ID, leave it blank.
    Return the suggestions in JSON format compatible with the Suggestions schema which is called `MovieSuggestions`. It has to keys:
    1/ suggestions: List[MovieSuggestion], which MovieSuggestions has these keys (name, year, original_language, type, tmdb_id if you know it).
    2/ explanation: Optional[str] - a short explanation of why you made these suggestions, in case status is False, explain why couldn't make suggestions.
    3/ status: Optional[bool] - True if suggestions are made, False if not.
    
    IMPORTANT: Avoid suggesting movies that have been previously recommended. 
    
    ## Suggestion Criteria:
    Suggest {count} {content_types_string}.
    
    ## Conversation History:
    {previous_suggestions}
    
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