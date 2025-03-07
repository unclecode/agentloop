from typing import Dict, Any
from services.tmdb import TMDBService
from openai import OpenAI
from config import MODELS
from assistant.assistant import MovieAssistant
import json


def get_movie_trailer(assistant_object: MovieAssistant, movie_title: str, year: int = None, item_type: str = None) -> str:
    """
    Retrieve the trailer for a given movie using TMDB.

    Args:
        assistant_object (MovieAssistant): The MovieAssistant object
        movie_title (str): Title of the movie
        year (int, optional): Release year of the movie
        item_type (str, optional): Type of content to search for ('movie', 'tv', or None for both)

    Returns:
        str: JSON string containing the trailer URL and movie details
    """
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        tmdb_service = TMDBService()
        movie_data = tmdb_service.fast_search(title=movie_title, year=year, item_type=item_type)

        if not movie_data:
            return json.dumps({
                "success": False,
                "message": "Movie not found."
            })

        trailer_url = movie_data.get('trailer')
        if not trailer_url:
            return json.dumps({
                "success": False,
                "message": "No trailer available for this movie."
            })

        # Log the action
        try:
            db.save_log(user_id=user_id, action="get_movie_trailer", data={
                "movie_title": movie_title,
                "year": year,
                "trailer_url": trailer_url
            })
        except Exception as e:
            print(f"Error logging get_movie_trailer action: {str(e)}")

        return json.dumps({
            "success": True,
            "type": "trailer_json",
            "trailer_url": trailer_url,
            "movie_title": movie_data.get('title', movie_data.get('original_name', '')),
            "release_date": movie_data.get('release_date', movie_data.get('first_air_date', '')),
            "overview": movie_data.get('overview', '')
        })

    except Exception as e:
        print(f"Error in get_movie_trailer: {str(e)}")
        return json.dumps({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })

def answer_movie_question(
    assistant_object: MovieAssistant, 
    **kwargs: Dict[str, Any]
    # question: str
    ) -> str:
    """
    Answers general questions about movies, actors, directors, film history, or cinema concepts.
    This function specifically handles informational queries rather than movie suggestions
    or action requests.

    Args:
        assistant_object (MovieAssistant): The MovieAssistant object
        question (str): The user's movie-related question

    Returns:
        str: JSON string containing the answer and relevant information
    """
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        question = kwargs.get('question', '')
        client = OpenAI()

        system_prompt = """You are a knowledgeable movie expert AI focused on answering questions about cinema.
        Your role is to provide informative answers about movies, actors, directors, film history, 
        production details, cinema concepts, and other movie-related topics.
        Important: Do NOT suggest movies or provide recommendations - that's handled by a different tool.
        Focus solely on providing factual information and explanations.
        If the user's question seems to be asking for movie suggestions, indicate that in your response
        so the appropriate tool can be used instead."""

        completion = client.chat.completions.create(
            model=MODELS['llm_what2know'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ]
        )
        
        answer = completion.choices[0].message.content

        # Log the action
        try:
            db.save_log(user_id=user_id, action="answer_movie_question", data={
                "question": question,
                "answer": answer
            })
        except Exception as e:
            print(f"Error logging answer_movie_question action: {str(e)}")

        return json.dumps({
            "success": True,
            "type": "movie_info",
            "question": question,
            "answer": answer
        })

    except Exception as e:
        print(f"Error in answer_movie_question: {str(e)}")
        return json.dumps({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })
        
def tmdb_search(
    assistant_object: MovieAssistant, 
    **kwargs: Dict[str, Any]
    # query: str, 
    # year: int = None, 
    # item_type: str = None, 
    # include_trailer: bool = False
    ) -> str:
    """
    Search TMDB database for movies, TV shows, or people.
    
    Args:
        assistant_object: Assistant object containing db and user_id
        query (str): Search query (movie/show title or person name)
        year (int, optional): Release year to filter results
        item_type (str, optional): Type of content to search for ('movie', 'tv', or None for both)
        include_trailer (bool, optional): Whether to include trailer URLs in the results
        
    Returns:
        str: JSON string containing search results
    """
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        query = kwargs.get('query', '')
        year = kwargs.get('year', None)
        item_type = kwargs.get('item_type', None)
        include_trailer = kwargs.get('include_trailer', False)
        
        tmdb_service = TMDBService()
        
        # Perform the search
        search_results = tmdb_service.search_tmdb_v2(
            query=query,
            genre_dict=tmdb_service.genre_dict,
            year=year,
            max_results=10,
            include_trailer=include_trailer
        )
        
        if not search_results or (not search_results.get('movie') and not search_results.get('tv')):
            # call answer_movie_question to get the answer
            return answer_movie_question(assistant_object=assistant_object, question=query)
            return json.dumps({
                "success": False,
                "message": "No results found."
            })
            
        # Filter by item_type if specified
        if item_type:
            if item_type == 'movie':
                content = search_results.get('movie', [])
            elif item_type in ['tv', 'tv-series', 'tv-show']:
                content = search_results.get('tv', [])
            else:
                content = []
        else:
            content = search_results.get('movie', []) + search_results.get('tv', [])
            
        # Format the results
        formatted_results = []
        for item in content:
            result = {
                'n': item.get('title') or item.get('name'),
                'y': int(item.get('release_date', '').split('-')[0]) if item.get('release_date') else 
                    int(item.get('first_air_date', '').split('-')[0]) if item.get('first_air_date') else None,
                'l': item.get('original_language'),
                't': 'm' if 'title' in item else 'v',
                'tmdb_id': str(item.get('id')),
                'trailer_url': item.get('trailer')
            }
            # Only include movies have names and release years
            if result['n'] and result['y']:
                formatted_results.append(result)

        # Filter those their title is same as query
        formatted_results = [result for result in formatted_results if result['n'].lower() == query.lower()]
        
        # Log the action
        try:
            db.save_log(user_id=user_id, action="tmdb_search", data={
                "query": query,
                "year": year,
                "item_type": item_type,
                "results_count": len(formatted_results)
            })
        except Exception as e:
            print(f"Error logging tmdb_search action: {str(e)}")

        if not formatted_results:
            return answer_movie_question(assistant_object=assistant_object, question=query)
        
        return json.dumps({
            "success": True,
            "type": "movie_json",
            "data": {
                "movies": formatted_results
            }
        })

    except Exception as e:
        print(f"Error in tmdb_search: {str(e)}")
        return json.dumps({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })
        
TOOL_SCHEMAS = {}
TOOLS = {}

# Add the new tool to TOOL_SCHEMAS
# TOOL_SCHEMAS["get_movie_trailer"] = {
#     "name": "get_movie_trailer",
#     "description": "Retrieve the trailer URL and basic information for a given movie",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "movie_title": {
#                 "type": "string",
#                 "description": "Title of the movie"
#             },
#             "year": {
#                 "type": "integer",
#                 "description": "Release year of the movie (optional)"
#             },
#             "item_type": {
#                 "type": "string",
#                 "enum": ["movie", "tv"],
#                 "description": "Type of content to search for. Use 'movie' for films, 'tv' for television content. Leave empty to search both. (optional)"
#             }
#         },
#         "required": ["movie_title"]
#     }
# }

TOOL_SCHEMAS["answer_movie_question"] = {
    "name": "answer_movie_question",
    "description": """Answer informational questions about movies, actors, directors, film history, 
                     or cinema concepts. This tool is ONLY for answering questions and providing information.
                     Do NOT use this tool for movie suggestions or recommendations - use what2watch instead.
                     Do NOT use this tool for question about the app itself - use app_support_assistant instead.
                     Example questions:
                     - "Who directed Inception?"
                     - "What is method acting?"
                     - "When did the first Star Wars movie come out?"
                     - "How are special effects created?"
                     - "What awards did Parasite win?"
                     """,
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": """The user's question about movies, actors, directors, film history,
                                or cinema concepts. Must be an informational question, not a request
                                for movie suggestions."""
            }
        },
        "required": ["question"]
    }
}

TOOL_SCHEMAS["tmdb_search"] = {
    "name": "tmdb_search",
    "description": """Search the TMDB database to find movies, TV shows, or verify the existence of specific content. 
                     Use this tool when:
                     1. You need to verify which version of a movie/show the user is referring to
                     2. You need to disambiguate between similarly named content
                     3. You need to confirm the existence of a movie or TV show
                     4. You need to gather basic information about multiple pieces of content
                     
                     The tool returns standardized information including:
                     - Title/Name
                     - Release Year
                     - Original Language
                     - Content Type (movie/TV)
                     - TMDB ID
                     - Trailer URL (if available)
                     """,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (movie/show title or person name)"
            },
            "year": {
                "type": "integer",
                "description": "Release year to filter results (optional)"
            },
            "item_type": {
                "type": "string",
                "enum": ["movie", "tv", "tv-series", "tv-show"],
                "description": "Type of content to search for. Use 'movie' for films, 'tv'/'tv-series'/'tv-show' for television content. Leave empty to search both. (optional)"
            },
            "include_trailer": {
                "type": "boolean",
                "description": "Whether to include trailer URLs in the results (optional)"
            }
        },
        "required": ["query"]
    }
}

# Add the new tool to TOOLS
# TOOLS["get_movie_trailer"] = get_movie_trailer
TOOLS["answer_movie_question"] = answer_movie_question
TOOLS["tmdb_search"] = tmdb_search


