import os
import sys
# Append parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Append parent parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import OPENAI_API_KEY, MODELS
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from openai import OpenAI
import json
from mem4ai import Memory

from ..assistant import MovieAssistant

class MovieSuggestion(BaseModel):
    name: str
    year: str
    original_language: str
    type: str  # 'movie' or 'tv-series'
    tmdb_id:  Optional[str] = None


class MovieSuggestions(BaseModel):
    suggestions: List[MovieSuggestion]
    explanation: str
    status: bool


class PersonalizedMovieSuggestion(BaseModel):
    name: str
    year: str
    type: str
    justification: str


class PersonalizedMovieSuggestions(BaseModel):
    suggestions: List[PersonalizedMovieSuggestion]


def what2watch(
    assistant_object : MovieAssistant, 
    **kwargs: Dict[str, Any]
    # user_request: str, 
    # count: int = 5, 
    # content_types: List[str] = ["movie", "tv-series"], 
    # previous_suggestions: List[dict] = []
    ) -> str:
    db = assistant_object.db
    user_id = assistant_object.user_id
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    user_request = kwargs.get("user_request", "")
    count = kwargs.get("count", 5)
    content_types = kwargs.get("content_types", ["movie", "tv-series"])
    previous_suggestions = kwargs.get("previous_suggestions", [])
    
    # System prompt to suggest both movies and TV shows
    memories : List[Memory] = assistant_object.memtor.search_memories(
        # query=user_request,
        top_k = 10,
        user_id=user_id,
        session_id=assistant_object.thread_id,
    )
    
    previous_suggestions = "\n".join([memory.content for memory in memories])
    # previous_suggestions = json.dumps(previous_suggestions)
    content_types_string = ", ".join(content_types)
    
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

    
    # user_prompt = f"Suggest {count} {content_types_string} based on this request: {user_request}"
    completion = client.beta.chat.completions.parse(
        model=MODELS['llm_what2know'],
        messages=[
            # {"role": "system", "content": system_prompt},
            {"role": "user", "content": system_prompt},
        ],
        response_format=MovieSuggestions,
    )
    response = completion.choices[0].message.parsed
    
    # save log to db
    try:
        db.save_log(user_id=user_id, action="what2watch", data={
            "user_request": user_request,
            "content_types": content_types,
            "suggestions": [s.model_dump() for s in response.suggestions]
        })
    except Exception as e:
        print(f"what2watch > save_log: {str(e)}")

    res = {**response.model_dump(), "type": "movie_json"}
    
    return json.dumps(res)

def have2watch(user_profile: dict, user_personality: str, 
                                 trendy_movies: List[dict], previously_suggested: List[dict], 
                                 suggestion_count: int = 5) -> str:
    """
    This function suggests personalized movie recommendations based on user profile, personality, and current trends.
    We call this funciton in the favorite list component to add movies to the list, based on list description and user profile
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    system_prompt = """You are a highly knowledgeable and personable movie expert AI. 
    Your task is to suggest movies based on the user's profile, personality, and current trends. 
    For each suggestion, provide the name, release year, type (movie or tv-series), and a short, 
    informal justification explaining why you think this movie is a good fit for the user. 
    Use 'you' when referring to the user in the justification. 
    Avoid suggesting movies that have been previously recommended. 
    Return the suggestions in JSON format compatible with the PersonalizedMovieSuggestions schema."""

    user_prompt = f"""User Profile: {user_profile}
User Personality: {user_personality}
Trendy Movies: {trendy_movies}
Previously Suggested Movies: {previously_suggested}

Please suggest {suggestion_count} personalized movie recommendations for this user."""

    try:
        completion = client.beta.chat.completions.parse(
            model=MODELS["llm_what2watch"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=PersonalizedMovieSuggestions
        )
        
        response = completion.choices[0].message.parsed
        suggestions = response.suggestions[:suggestion_count]

        return PersonalizedMovieSuggestions(suggestions=suggestions).model_dump_json()
    except Exception as e:
        print(f"Error in have2watch: {str(e)}")
        return json.dumps({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })
        
# "name": "suggest_movies",
TOOL_SCHEMA = {
    "name": "what2watch",
    "description": "Use this tools, Only user request is required, then Suggest 5 content items (movies or TV series or ... ) based on the user's query or request",
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
                    "type": "string",
                    "description": "List of movies previously suggested to the user and related to the user request"
                },
                "description": "List of movies previously suggested to the user"
            }
        },
        "required": ["user_request", "count", "content_types", "previous_suggestions"]
    }
}


TOOLS = {
    "what2watch": what2watch
}

# Test the new function
if __name__ == "__main__":
    class MockDB:
        def save_log(self, user_id, action, data):
            print(f"Logged: User {user_id}, Action: {action}")
            print(f"Data: {json.dumps(data, indent=2)}")

    db = MockDB()
    user_id = "test_user_123"
    user_token = "test_token_456"
    user_profile = {
        "age": 28,
        "favorite_genres": ["sci-fi", "action", "comedy"],
        "preferred_languages": ["English", "Spanish"]
    }
    user_personality = "Outgoing, adventurous, and loves thought-provoking content"
    trendy_movies = [
        {"name": "Dune", "year": "2021", "type": "movie"},
        {"name": "The Mandalorian", "year": "2019", "type": "tv-series"}
    ]
    previously_suggested = [
        {"name": "Inception", "year": "2010", "type": "movie"},
        {"name": "Breaking Bad", "year": "2008", "type": "tv-series"}
    ]

    result = have2watch(user_profile, user_personality, 
                                          trendy_movies, previously_suggested, suggestion_count=6)
    
    print("\nPersonalized Movie Suggestions:")
    parsed_result = json.loads(result)
    for suggestion in parsed_result["suggestions"]:
        print(f"\n- {suggestion['name']} ({suggestion['year']}) - {suggestion['type']}")
        print(f"  Justification: {suggestion['justification']}")
