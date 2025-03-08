"""
Tools for managing favorite movie lists in the Moji app.
"""
import json
from typing import Dict, List, Any, Optional
import os
import sys

# Add parent directories to path to avoid import issues
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.mojitoApis import MojitoAPIs

def create_favorite_list(
    list_name: str,
    list_description: str = "",
    **context  # Catches user_id and user_token from context
) -> str:
    """
    Create a new favorite list for the user.
    
    Args:
        list_name: Name of the list to create
        list_description: Optional description of the list
        
    Context Args (passed by agentloop):
        user_id: User identifier
        user_token: User access token
        
    Returns:
        JSON string with creation result including list_id
    """
    try:
        # Extract credentials from context
        user_id = context.get("user_id")
        user_token = context.get("user_token")
        
        # Validate required parameters
        if not user_id or not user_token:
            return json.dumps({
                "status": False,
                "message": "Missing required credentials",
                "type": "list"
            })
            
        # Create API client
        api_client = MojitoAPIs(user_id=user_id, token=user_token)
        
        # Call API to create list
        response = api_client.create_favorite_list(
            list_name=list_name,
            list_description=list_description
        )
        
        # Format response for agentloop
        if response.get('status'):
            list_id = response.get('data', {}).get('list_id', '')
            return json.dumps({
                "status": True,
                "message": f"List '{list_name}' created successfully",
                "type": "list",
                "data": {
                    "items": [
                        {
                            "list_id": list_id,
                            "name": list_name
                        }
                    ]
                }
            })
        else:
            return json.dumps({
                "status": False,
                "message": response.get('message', 'Failed to create list'),
                "type": "list"
            })
            
    except Exception as e:
        return json.dumps({
            "status": False, 
            "message": f"Error creating list: {str(e)}",
            "type": "list"
        })

def add_to_favorite_list(
    list_id: str,
    movies: List[Dict[str, Any]],
    **context  # Catches user_id and user_token from context
) -> str:
    """
    Add movies to a user's favorite list.
    
    Args:
        list_id: ID of the list to add movies to
        movies: List of movie objects to add to the list
        
    Context Args (passed by agentloop):
        user_id: User identifier
        user_token: User access token
        
    Returns:
        JSON string with result of the operation
    """
    try:
        # Extract credentials from context
        user_id = context.get("user_id")
        user_token = context.get("user_token")
        
        # Validate required parameters
        if not user_id or not user_token:
            return json.dumps({
                "status": False,
                "message": "Missing required credentials",
                "type": "list"
            })
        
        if not list_id:
            return json.dumps({
                "status": False,
                "message": "Missing required parameter: list_id",
                "type": "list"
            })
            
        if not movies or not isinstance(movies, list):
            return json.dumps({
                "status": False,
                "message": "Missing or invalid parameter: movies",
                "type": "list"
            })
        
        # Create API client
        api_client = MojitoAPIs(user_id=user_id, token=user_token)
        
        # Check if we're adding to the Big Five list
        if list_id.upper() == "BIG_FIVE":
            response = api_client.add_to_big_five_list(movies=movies)
        else:
            # Regular list
            response = api_client.add_movies_to_list(list_id=list_id, movies=movies)
        
        # Format response for agentloop
        if response.get('status'):
            return json.dumps({
                "status": True,
                "message": "Movies added to list successfully",
                "type": "list",
                "data": {
                    "list_id": list_id,
                    "added_movies": [movie.get('title', movie.get('name', 'Unknown')) for movie in movies]
                }
            })
        else:
            return json.dumps({
                "status": False,
                "message": response.get('message', 'Failed to add movies to list'),
                "type": "list"
            })
            
    except Exception as e:
        return json.dumps({
            "status": False, 
            "message": f"Error adding movies to list: {str(e)}",
            "type": "list"
        })

def get_favorite_lists(
    **context  # Catches user_id and user_token from context
) -> str:
    """
    Get all favorite lists for a user.
    
    Context Args (passed by agentloop):
        user_id: User identifier
        user_token: User access token
        
    Returns:
        JSON string with user's favorite lists
    """
    try:
        # Extract credentials from context
        user_id = context.get("user_id")
        user_token = context.get("user_token")
        
        # Validate required parameters
        if not user_id or not user_token:
            return json.dumps({
                "status": False,
                "message": "Missing required credentials",
                "type": "list"
            })
            
        # Create API client
        api_client = MojitoAPIs(user_id=user_id, token=user_token)
        
        # Call API to get lists
        lists = api_client.get_favorite_lists()
        
        # Format response for agentloop
        if lists:
            # Extract just the list_id and name for each list
            simplified_lists = [
                {"list_id": list_item.get("list_id", ""), 
                 "name": list_item.get("list_name", "")}
                for list_item in lists
            ]
            
            return json.dumps({
                "status": True,
                "message": f"Retrieved {len(simplified_lists)} lists",
                "type": "list",
                "data": {
                    "items": simplified_lists
                }
            })
        else:
            return json.dumps({
                "status": True,
                "message": "No favorite lists found",
                "type": "list",
                "data": {
                    "items": []
                }
            })
            
    except Exception as e:
        return json.dumps({
            "status": False, 
            "message": f"Error retrieving lists: {str(e)}",
            "type": "list"
        })

def get_list_items(
    list_id: str,
    **context  # Catches user_id and user_token from context
) -> str:
    """
    Get all movies in a specific list.
    
    Args:
        list_id: ID of the list to retrieve movies from
        
    Context Args (passed by agentloop):
        user_id: User identifier
        user_token: User access token
        
    Returns:
        JSON string with movies in the list
    """
    try:
        # Extract credentials from context
        user_id = context.get("user_id")
        user_token = context.get("user_token")
        
        # Validate required parameters
        if not user_id or not user_token:
            return json.dumps({
                "status": False,
                "message": "Missing required credentials",
                "type": "movie_json"
            })
            
        if not list_id:
            return json.dumps({
                "status": False,
                "message": "Missing required parameter: list_id",
                "type": "movie_json"
            })
            
        # Create API client
        api_client = MojitoAPIs(user_id=user_id, token=user_token)
        
        # Call API to get list items
        movies = api_client.get_list_items(list_id=list_id)
        
        # Format response for agentloop
        if movies:
            return json.dumps({
                "status": True,
                "message": f"Retrieved {len(movies)} movies from list",
                "type": "movie_json",
                "data": {
                    "movies": movies,
                    "explanation": f"Movies in the list '{list_id}'"
                }
            })
        else:
            return json.dumps({
                "status": True,
                "message": "No movies found in list",
                "type": "movie_json",
                "data": {
                    "movies": [],
                    "explanation": f"No movies found in list '{list_id}'"
                }
            })
            
    except Exception as e:
        return json.dumps({
            "status": False, 
            "message": f"Error retrieving list items: {str(e)}",
            "type": "movie_json"
        })

# Tool schemas for agentloop
CREATE_LIST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_favorite_list",
        "description": "Create a new movie favorite list for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "list_name": {
                    "type": "string",
                    "description": "Name of the list to create"
                },
                "list_description": {
                    "type": "string",
                    "description": "Optional description of the list"
                }
            },
            "required": ["list_name"]
        }
    }
}

ADD_TO_LIST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_to_favorite_list",
        "description": "Add movies to a user's favorite list",
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "ID of the list to add movies to. Use 'BIG_FIVE' for the Big Five list."
                },
                "movies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": ["string", "integer"], "description": "Movie ID"},
                            "name": {"type": "string", "description": "Movie title/name"},
                            "year": {"type": "string", "description": "Release year"},
                            "type": {"type": "string", "description": "Content type (movie, tv-series, etc.)"},
                            "poster_path": {"type": "string", "description": "Path to movie poster"},
                            "backdrop_path": {"type": "string", "description": "Path to movie backdrop"}
                        },
                        "required": ["id", "name"]
                    },
                    "description": "List of movie objects to add to the list"
                }
            },
            "required": ["list_id", "movies"]
        }
    }
}

GET_LISTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_favorite_lists",
        "description": "Get all favorite lists for a user",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

GET_LIST_ITEMS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_list_items",
        "description": "Get all movies in a specific list",
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "ID of the list to retrieve movies from"
                }
            },
            "required": ["list_id"]
        }
    }
}

# Export tools for dynamic loading
TOOLS = {
    "create_favorite_list": create_favorite_list,
    "add_to_favorite_list": add_to_favorite_list,
    "get_favorite_lists": get_favorite_lists,
    "get_list_items": get_list_items
}

# Export schemas for dynamic loading
TOOL_SCHEMAS = {
    "create_favorite_list": CREATE_LIST_SCHEMA,
    "add_to_favorite_list": ADD_TO_LIST_SCHEMA,
    "get_favorite_lists": GET_LISTS_SCHEMA,
    "get_list_items": GET_LIST_ITEMS_SCHEMA
}