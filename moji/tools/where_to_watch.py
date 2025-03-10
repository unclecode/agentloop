"""
Tool to find where to watch movies and TV shows online.
"""
import json
import os
import sys
from typing import Dict, List, Any, Optional, Union

# Add parent directories to path to avoid import issues
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.tmdb import TMDBService

def get_watch_providers(
    movie_name: str,
    year: Optional[str] = None,
    region: str = "US",
    type: str = "movie",
    **context  # Catches additional context data
) -> str:
    """
    Find where to watch a movie or TV show online in a specific region.
    
    Args:
        movie_name: Name of the movie or TV show to look up
        year: Optional release year to improve search accuracy
        region: Region code for watch providers (e.g., "US", "GB", "CA")
        type: Content type - "movie" or "tv"
        
    Returns:
        JSON string with watch provider information
    """
    try:
        # Initialize TMDB service
        tmdb_service = TMDBService()
        
        # Search for the movie/TV show to get its ID
        search_result = tmdb_service.fast_search(
            title=movie_name,
            year=year,
            item_type=type
        )
        
        if not search_result:
            return json.dumps({
                "status": False,
                "message": f"Could not find {type} '{movie_name}'",
                "type": "watch_info"
            })
        
        # Get the ID and use it to fetch watch providers
        content_id = search_result.get('id')
        
        if not content_id:
            return json.dumps({
                "status": False,
                "message": f"Could not retrieve ID for {type} '{movie_name}'",
                "type": "watch_info"
            })
        
        # Get watch providers
        providers_url = f"{tmdb_service.base_url}/{type}/{content_id}/watch/providers"
        response = tmdb_service.safe_request(providers_url)
        
        if not response or 'results' not in response:
            return json.dumps({
                "status": False,
                "message": f"No watch provider information available for {type} '{movie_name}'",
                "type": "watch_info"
            })
        
        # Extract the watch providers for the specified region
        region_providers = response['results'].get(region.upper(), {})
        
        if not region_providers:
            # Search for providers in other regions if the specified region has none
            all_regions = response['results']
            if all_regions:
                region_providers = next(iter(all_regions.values()), {})
                region = next(iter(all_regions.keys()), "unknown")
        
        # Format our response
        formatted_providers = {}
        
        # Get basic movie/show information
        title = search_result.get('title', search_result.get('name', movie_name))
        overview = search_result.get('overview', 'No overview available')
        poster_path = search_result.get('poster_path', '')
        backdrop_path = search_result.get('backdrop_path', '')
        release_date = search_result.get('release_date', search_result.get('first_air_date', ''))
        
        # Organize providers by type
        if region_providers:
            if 'flatrate' in region_providers:
                formatted_providers['streaming'] = [
                    {
                        "provider_name": provider.get('provider_name', 'Unknown'),
                        "logo_path": provider.get('logo_path', ''),
                        "provider_id": provider.get('provider_id', 0)
                    }
                    for provider in region_providers['flatrate']
                ]
            
            if 'rent' in region_providers:
                formatted_providers['rent'] = [
                    {
                        "provider_name": provider.get('provider_name', 'Unknown'),
                        "logo_path": provider.get('logo_path', ''),
                        "provider_id": provider.get('provider_id', 0)
                    }
                    for provider in region_providers['rent']
                ]
                
            if 'buy' in region_providers:
                formatted_providers['buy'] = [
                    {
                        "provider_name": provider.get('provider_name', 'Unknown'),
                        "logo_path": provider.get('logo_path', ''),
                        "provider_id": provider.get('provider_id', 0)
                    }
                    for provider in region_providers['buy']
                ]
            
            # Add link to JustWatch if available
            if 'link' in region_providers:
                formatted_providers['justwatch_link'] = region_providers['link']
        
        return json.dumps({
            "status": True,
            "message": f"Found watch providers for {title}",
            "type": "watch_info",
            "data": {
                "title": title,
                "overview": overview,
                "poster_path": poster_path,
                "backdrop_path": backdrop_path,
                "release_date": release_date,
                "region": region,
                "providers": formatted_providers
            }
        })
    
    except Exception as e:
        return json.dumps({
            "status": False,
            "message": f"Error finding watch providers: {str(e)}",
            "type": "watch_info"
        })

# Tool schema for agentloop
WATCH_PROVIDERS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_watch_providers",
        "description": "Find where to watch a movie or TV show online (streaming, rental, or purchase options)",
        "parameters": {
            "type": "object",
            "properties": {
                "movie_name": {
                    "type": "string",
                    "description": "Name of the movie or TV show to look up"
                },
                "year": {
                    "type": "string",
                    "description": "Optional release year to improve search accuracy"
                },
                "region": {
                    "type": "string",
                    "description": "Region code for watch providers (e.g., 'US', 'GB', 'CA', 'FR'). Defaults to 'US'."
                },
                "type": {
                    "type": "string",
                    "enum": ["movie", "tv"],
                    "description": "Content type - movie or TV show"
                }
            },
            "required": ["movie_name"]
        }
    }
}

# Export tool for dynamic loading
TOOLS = {
    "get_watch_providers": get_watch_providers
}

# Export schema for dynamic loading
TOOL_SCHEMAS = {
    "get_watch_providers": WATCH_PROVIDERS_SCHEMA
}