"""
Tool to find official trailers for movies and TV shows.
"""
import json
import os
import sys
from typing import Dict, List, Any, Optional, Union

# Add parent directories to path to avoid import issues
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.tmdb import TMDBService

def get_trailer(
    title: str,
    year: Optional[str] = None,
    type: str = "movie",
    **context  # Catches additional context data
) -> str:
    """
    Find the official trailer for a movie or TV show.
    
    Args:
        title: Title of the movie or TV show
        year: Optional release year to improve search accuracy
        type: Content type - "movie" or "tv"
        
    Returns:
        JSON string with trailer information and content details
    """
    try:
        # Initialize TMDB service
        tmdb_service = TMDBService()
        
        # Search for the movie/TV show
        search_result = tmdb_service.fast_search(
            title=title,
            year=year,
            item_type=type
        )
        
        if not search_result:
            return json.dumps({
                "status": False,
                "message": f"Could not find {type} '{title}'",
                "type": "trailer_info"
            })
        
        # Get the content ID
        content_id = search_result.get('id')
        
        if not content_id:
            return json.dumps({
                "status": False,
                "message": f"Could not retrieve ID for {type} '{title}'",
                "type": "trailer_info"
            })
        
        # Get videos for the content
        videos = tmdb_service.fetch_videos(content_id, type)
        
        # Filter for trailers from YouTube (best quality and most reliable)
        trailers = [video for video in videos if video['type'] == 'Trailer' and video['site'] == 'YouTube']
        
        if not trailers:
            return json.dumps({
                "status": False,
                "message": f"No trailer found for {type} '{title}'",
                "type": "trailer_info"
            })
        
        # Sort trailers by published date (newest first) or name if no date
        try:
            trailers.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        except:
            pass
        
        # Get the first (most recent) trailer
        trailer = trailers[0]
        trailer_url = f"https://www.youtube.com/watch?v={trailer['key']}"
        
        # Get basic content information
        content_title = search_result.get('title', search_result.get('name', title))
        overview = search_result.get('overview', 'No overview available')
        poster_path = search_result.get('poster_path', '')
        release_date = search_result.get('release_date', search_result.get('first_air_date', ''))
        
        # If multiple trailers are available, include them as alternatives
        alternative_trailers = []
        if len(trailers) > 1:
            alternative_trailers = [
                {
                    "name": t.get('name', 'Trailer'),
                    "url": f"https://www.youtube.com/watch?v={t['key']}",
                    "published_at": t.get('published_at', '')
                }
                for t in trailers[1:5]  # Limit to 4 alternatives
            ]
        
        return json.dumps({
            "status": True,
            "message": f"Found trailer for {content_title}",
            "type": "trailer_info",
            "data": {
                "title": content_title,
                "overview": overview,
                "poster_path": poster_path,
                "release_date": release_date,
                "trailer_name": trailer.get('name', 'Official Trailer'),
                "trailer_url": trailer_url,
                "trailer_site": trailer.get('site', 'YouTube'),
                "alternative_trailers": alternative_trailers
            }
        })
    
    except Exception as e:
        return json.dumps({
            "status": False,
            "message": f"Error finding trailer: {str(e)}",
            "type": "trailer_info"
        })

# Tool schema for agentloop
TRAILER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_trailer",
        "description": "Find the official trailer for a movie or TV show",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the movie or TV show"
                },
                "year": {
                    "type": "string",
                    "description": "Optional release year to improve search accuracy"
                },
                "type": {
                    "type": "string",
                    "enum": ["movie", "tv"],
                    "description": "Content type - movie or TV show"
                }
            },
            "required": ["title"]
        }
    }
}

# Export tool for dynamic loading
TOOLS = {
    "get_trailer": get_trailer
}

# Export schema for dynamic loading
TOOL_SCHEMAS = {
    "get_trailer": TRAILER_SCHEMA
}