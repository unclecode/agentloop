from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import List, Dict, Any
from services.tmdb import TMDBService
from time import time
import json


def load_and_render_prompt(prompt_name: str, parameters: Dict[str, Any]) -> str:
    """
    Loads a Jinja template and renders it with the provided parameters.

    Args:
        prompt_name (str): Name of the Jinja template file to load.
        parameters (Dict[str, Any]): Dictionary of parameters to use for rendering the template.

    Returns:
        str: Rendered template as a string.
    """
    env_chat_templates = Environment(loader=FileSystemLoader('templates/mojito/v2/chat'))
    env_completion_templates = Environment(loader=FileSystemLoader('templates/mojito/v2/completion'))
    template = None
    rendered_prompt = None
    prompt_name = f'{prompt_name}.jinja2'
    for env in [(env_chat_templates, "chat"), (env_completion_templates, "completion")]:
        try:
            if env[0].get_template(prompt_name):
                template = env[0].get_template(prompt_name)
                rendered_prompt = template.render(**parameters)
                template_type = env[1]
                return rendered_prompt, template_type
        except TemplateNotFound:
            pass
    raise Exception(f"Prompt {prompt_name} not found!")


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


def filter_movies_with_tmdb(movies: List) -> Dict:
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
