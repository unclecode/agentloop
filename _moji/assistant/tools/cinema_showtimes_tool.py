
# File: cinema_showtimes_tool.py
import os, sys
# append parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Appe parent parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional, Dict, List, Tuple, Any
from pydantic import BaseModel
from config import MOVIEGLU_AUTH, MOVIEGLU_API_KEY, GEOCODING_API_KEY
from assistant.tools.share.movieglu_service import MovieGluService, FilmShowTimesResponse

import json
import requests

class ShowtimeInfo(BaseModel):
    start_time: str
    end_time: str

class CinemaInfo(BaseModel):
    cinema_id: int
    cinema_name: str
    distance: float
    logo_url: Optional[str]
    showtimes: Dict[str, List[ShowtimeInfo]]

class MovieInfo(BaseModel):
    film_id: int
    imdb_id: int
    imdb_title_id: str
    film_name: str
    synopsis: Optional[str]
    poster_url: Optional[str]

class ShowtimesResponse(BaseModel):
    movie: MovieInfo
    cinemas: List[CinemaInfo]

def geocode_city(city_name: str, country_code: str) -> Optional[Tuple[float, float]]:
    """
    Convert a city name to latitude and longitude coordinates using a geocoding service.
    
    :param city_name: Name of the city
    :param country_code: ISO country code (e.g., 'DE' for Germany)
    :return: Tuple of (latitude, longitude) if successful, None otherwise
    """
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        'q': f"{city_name}, {country_code}",
        'key': GEOCODING_API_KEY,
        'limit': 1
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            location = data['results'][0]['geometry']
            return (location['lat'], location['lng'])
        else:
            print(f"Could not find coordinates for {city_name}, {country_code}")
            return None
    except requests.RequestException as e:
        print(f"Error during geocoding: {e}")
        return None
    
def generate_showtimes_json(showtimes_response: 'FilmShowTimesResponse') -> str:
    """
    Generate a JSON representation of showtimes from a FilmShowTimesResponse object.

    :param showtimes_response: FilmShowTimesResponse object
    :return: JSON string with formatted showtimes data
    """
    film = showtimes_response.film
    
    movie_info = MovieInfo(
        film_id=film.film_id,
        imdb_id=film.imdb_id,
        imdb_title_id=film.imdb_title_id,
        film_name=film.film_name,
        synopsis=film.synopsis_long,
        poster_url=film.images.poster.get("1", {}).medium.film_image if film.images and film.images.poster else None
    )

    cinemas_info = []
    for cinema in showtimes_response.cinemas:
        showtimes = {}
        for format_type, showings in cinema.showings.items():
            showtimes[format_type] = [ShowtimeInfo(start_time=time.start_time, end_time=time.end_time) for time in showings.times]
        
        cinemas_info.append(CinemaInfo(
            cinema_id=cinema.cinema_id,
            cinema_name=cinema.cinema_name,
            distance=cinema.distance,
            logo_url=cinema.logo_url,
            showtimes=showtimes
        ))

    response = ShowtimesResponse(movie=movie_info, cinemas=cinemas_info)
    return json.dumps({"type": "text", **response.model_dump()}, indent=2)

def search_cinema_showtimes(assistant_object, 
                            **kwargs: Dict[str, Any]
                            # film_name: str, 
                            # city: str, 
                            # country_code: str = "DE"
                            ) -> str:
    api_key = MOVIEGLU_API_KEY
    client = "ALEP"
    authorization = f"Basic {MOVIEGLU_AUTH}"
    api_version = "v200"
    
    film_name = kwargs.get("film_name", "")
    city = kwargs.get("city", "Munich")
    country_code = kwargs.get("country_code", "DE")

    # Get coordinates for the city
    coordinates = geocode_city(city, country_code)
    if not coordinates:
        return json.dumps({"error": f"Could not find coordinates for {city}, {country_code}"})
    
    geolocation = f"{coordinates[0]};{coordinates[1]}"

    service = MovieGluService(
        api_key=api_key,
        client=client,
        authorization=authorization,
        territory=country_code,
        api_version=api_version,
        geolocation=geolocation
    )

    showtimes_response = service.get_film_showtimes(film_name)

    if showtimes_response:
        return generate_showtimes_json(showtimes_response)
    else:
        return json.dumps({"error": f"No showtimes found for {film_name} in {city}, {country_code}"})

# Updated Tool schema for the AI assistant
TOOL_SCHEMA = {
    "name": "search_cinema_showtimes",
    "description": "Search for cinema showtimes of a specific movie in a given city. Use this tool when users ask about movie showtimes, cinema locations, or want to find where a particular movie is playing in a specific city.",
    "parameters": {
        "type": "object",
        "properties": {
            "film_name": {
                "type": "string",
                "description": "The name of the film to search for"
            },
            "city": {
                "type": "string",
                "description": "The name of the city where to search for showtimes"
            },
            "country_code": {
                "type": "string",
                "description": "ISO code for the country (default: 'DE' for Germany)"
            }
        },
        "required": ["film_name", "city"]
    }
}

TOOLS = {
    "search_cinema_showtimes": search_cinema_showtimes
}

def test_search_cinema_showtimes():
    
    
    print("Cinema Showtimes Search Tool Test")
    print("=================================")
    
    while True:
        film_name = "Inside Out 2"  # Default to Inside Out        
        geolocation = "48.1351;11.5820"  # Default to Munich
        city = "Munich"
        territory = "DE"  # Default to Germany
        
        print("\nSearching for showtimes...")
        result = search_cinema_showtimes(film_name, geolocation, territory)
        
        # Pretty print the JSON result
        print(json.dumps(json.loads(result), indent=2))
        print("\n")

if __name__ == "__main__":
    test_search_cinema_showtimes()