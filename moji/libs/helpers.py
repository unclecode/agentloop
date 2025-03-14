from typing import List, Dict
from services.tmdb import TMDBService
from time import time
import json


def update_movie_response(movies):
    key_mapping = {'n': 'name', 'y': 'year', 't': 'type', 'l': 'original_language'}
    type_mapping = {'m': 'movie', 'v': 'tv-series', 'c': 'cartoon', 'a': 'anime', 'd': 'documentary', 's': 'short-film', 't': 'tv'}
    try:
        if type(movies) == str:
            movies = json.loads(movies)
    except:
        pass
    movies = [
        {key_mapping.get(k, k): v for k, v in movie.items()} for movie in movies
    ]
    for movie in movies:
        if 'type' in movie:
            movie['type'] = type_mapping.get(movie['type'], movie['type'])
        else:
            movie['type'] = 'movie'
    return movies


def filter_movies_with_tmdb(movies: List) -> List:
    """
    Process movie data from an API response, checking against the TMDB database.

    Args:
        response (Dict): API response containing movie data.

    Returns:
        Dict: Updated API response with processed movie data.
    """
    try:
        # TIMER
        t1 = time()
        tmdb_service = TMDBService()
        tmdb_response = tmdb_service.fast_search_many(movies)
        # TIMER
        print(f"TIMER>> TMDB search time: {time() - t1:.2f} seconds")
        tmdb_response = [movie for movie in tmdb_response if movie]
        print(f"TMDB response received. Number of movies: {len(tmdb_response)}")
        # if len(tmdb_response) > original_num_movies:
        #     print(f"Trimming TMDB response to {original_num_movies} movies")
        #     tmdb_response = tmdb_response[:original_num_movies]
        return tmdb_response
    except Exception as e:
        print(f"Error checking movies on TMDB: {e}")
        raise e