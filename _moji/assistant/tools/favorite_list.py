import os, sys

# Append parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Append parent parent directory to import path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from config import OPENAI_API_KEY, MODELS
from pydantic import BaseModel
from openai import OpenAI
from services.tmdb import TMDBService
from libs.error import Error
from services.mojitoApis import MojitoAPIs
from typing import List, Dict, Any
from assistant.assistant import MovieAssistant
import json


class MovieSuggestion(BaseModel):
    name: str
    year: str
    type: str
    relevancy_score: int


class ListSuggestions(BaseModel):
    suggestions: List[MovieSuggestion]


def suggest_movie_for_list(
    list_name: str,
    list_description: str,
    current_movies: List[Dict[str, Any]],
    suggestion_count: int = 5,
) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = f"""You are a highly knowledgeable movie expert AI. Your task is to suggest {suggestion_count} movies to be added to a user's favorite list based on the list's description and current contents. For each suggestion, provide the name, release year, type (movie or tv-series), and a relevancy score from 1 to 10 (where 10 is a perfect match). Use your vast knowledge of cinema to make appropriate suggestions that align with the list's theme and existing movies. Return the suggestions in JSON format compatible with the ListSuggestions schema."""

    current_movies_str = ", ".join(
        [f"{movie['name']} ({movie['year']})" for movie in current_movies]
    )
    user_prompt = f"""List Name: {list_name}
List Description: {list_description}
Current Movies in the List: {current_movies_str}

Please suggest {suggestion_count} new movies to add to this list that align with its description and current contents. Provide a relevancy score for each suggestion."""

    try:
        completion = client.beta.chat.completions.parse(
            model=MODELS["openai_4o_mini"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ListSuggestions,
        )

        response = completion.choices[0].message.parsed
        suggestions = response.suggestions[:suggestion_count]

        return json.dumps(
            {"success": True, "suggestions": [s.model_dump() for s in suggestions]}
        )
    except Exception as e:
        Error(f"suggest_movie_for_list", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})


def create_favorite_list(
    assistant_object: MovieAssistant, 
    **kwargs: Dict[str, Any]
    # name: str, description: str = ""
) -> str:
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        name = kwargs.get("name", "")
        description = kwargs.get("description", "")
        res = MojitoAPIs(user_id=user_id, token=user_token).create_favorite_list(
            list_name=name, list_description=description
        )
        # {'status': True, 'message': 'Favorite list created successfully', 'data': {'list_id': '6591bcd0-8e8f-4ec4-bf10-72f76a70e969'}}

        # print(res)
        # save log to db
        try:
            db.save_log(
                user_id,
                "create_favorite_list",
                {"name": name, "description": description, "response": res},
            )
        except Exception as e:
            # Error(f"create_favorite_list > save_log", e)
            pass
        if not res["status"]:
            Error.send_raw_message(
                f"MOJITO API > Failed to create the list: {res.get('message', 'Unknown error')}"
            )
            return json.dumps(
                {
                    "success": False,
                    "message": res.get("message", "Failed to create the list."),
                }
            )

        # need to add the new created list to assistant_object['user_extra_data']['favorite_lists']
        assistant_object.payload.params.setdefault("user_extra_data", {})
        assistant_object.payload.params["user_extra_data"].setdefault("favorite_lists", [])
        assistant_object.payload.params["user_extra_data"]["favorite_lists"] = assistant_object.payload.params["user_extra_data"]["favorite_lists"] or []
        assistant_object.payload.params["user_extra_data"]["favorite_lists"].append(
            {
                "list_id": res["data"]["list_id"],
                "list_name": name,
                "movies": [],
            }
        )

        return json.dumps(
            {
                "success": True, 
                "lists": [{"list_id": res["data"]["list_id"], "name": name}], 
                "type": "list_json"
            }
        )
    except Exception as e:
        Error(f"create_favorite_list", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})


def add_to_favorite_list(
    assistant_object: MovieAssistant, 
    **kwargs: Dict[str, Any]
    # list_id: str, items: List[Dict[str, Any]]
) -> str:
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        list_id = kwargs.get("list_id", "")
        items = kwargs.get("items", [])
        filtered_movies = TMDBService().fast_search_many(items)
        if not filtered_movies:
            return json.dumps({"success": False, "message": "No valid movies found."})

        resp = MojitoAPIs(user_id=user_id, token=user_token).add_movies_to_list(
            list_id=list_id, movies=filtered_movies
        )
        # print(resp)
        # save log to db
        try:
            db.save_log(
                user_id=user_id,
                action="add_to_favorite_list",
                data={"list_id": list_id, "items": items, "response": resp},
            )
        except Exception as e:
            # Error(f"add_to_favorite_list > save_log", e)
            pass

        if not resp["status"]:
            Error.send_raw_message(
                f"MOJITO API > Failed to add movies to the list: {resp.get('message', 'Unknown error')}"
            )
            return json.dumps(
                {
                    "success": False,
                    "message": resp.get("message", "Failed to add items to the list."),
                }
            )
        
        # add inserted movie_id to filtered_movies
        for i, m in enumerate(filtered_movies):
            try:
                m['id'] = resp['data']['movie_ids'][i]
            except:
                pass
        # Update the assistant_object's user_extra_data with the new list
        if "user_extra_data" in assistant_object.payload.params:
            favorite_lists = assistant_object.payload.params["user_extra_data"].get("favorite_lists", [])
            for lst in favorite_lists:
                if lst.get("list_id") == list_id:
                    # lst["movies"].extend([{"movie_id": m["id"], "movie_name": m["name"]} for m in filtered_movies])
                    lst['movies'] = lst.get('movies', []) or []
                    lst["movies"].extend([{"movie_id": m["id"], "movie_name": m.get('title', '') or m.get('name', '')} for m in filtered_movies])
                    break
            
            assistant_object.payload.params["user_extra_data"]["favorite_lists"] = favorite_lists    
        
        return json.dumps(
            {
                "success": True,
                "lists": [{"list_id": list_id, "name": resp.get("list_name", "")}],
                "type": "list_json",
            }
        )
    except Exception as e:
        Error(f"add_to_favorite_list", e)
        return json.dumps({"success": False, "message": f"Some error occurred!"})


def get_favorite_lists(assistant_object: MovieAssistant) -> str:
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        # lists = MojitoAPIs(user_id=user_id, token=user_token).get_user_lists_names()
        lists = MojitoAPIs(user_id=user_id, token=user_token).get_favorite_lists()

        # exclude big five list
        BIG_FIVE_LIST_ID = "BIG_FIVE"
        lists = [lst for lst in lists if lst.get('list_id') != BIG_FIVE_LIST_ID]

        # for list in lists:
        #     list['collection_id'] = list.pop('list_id')

        # save log to db
        try:
            db.save_log(
                user_id=user_id, action="get_favorite_lists", data={"response": lists}
            )
        except Exception as e:
            print(f"get_favorite_lists > save_log: {str(e)}")

        if not lists:
            Error.send_raw_message(f"MOJITO API > Failed to get favorite lists")
            return json.dumps(
                {"success": False, "message": "Failed to get favorite lists."}
            )
        return json.dumps({"success": True, "lists": lists, "type": "list_json"})
    except Exception as e:
        Error(f"get_favorite_lists", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})


def get_favorite_list_items(assistant_object: MovieAssistant, 
                            **kwargs: Dict[str, Any]
                            # list_id: str
                            ) -> str:
    db = assistant_object.db
    user_id = assistant_object.user_id
    user_token = assistant_object.user_token
    list_id = kwargs.get("list_id", "")

    response = MojitoAPIs(user_id=user_id, token=user_token).get_list_items(list_id)

    # save log to db
    try:
        db.save_log(
            user_id=user_id,
            action="get_favorite_list_items",
            data={
                "list_id": list_id
                # "response": response
            },
        )
    except Exception as e:
        print(f"get_favorite_list_items > save_log: {str(e)}")

    return json.dumps({"success": True, "items": response, "type": "movie_json"})


def add_to_big_five_list(
    assistant_object: MovieAssistant, 
    **kwargs: Dict[str, Any]
    # items: List[Dict[str, Any]]
) -> str:
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        BIG_FIVE_LIST_ID = "BIG_FIVE"
        items = kwargs.get("items", [])
        max_items = 5

        filtered_movies = TMDBService().fast_search_many(items)
        if not filtered_movies:
            return json.dumps({"success": False, "message": "No valid movies found."})

        # Limit the number of movies to 5
        filtered_movies = filtered_movies[:max_items]

        resp = MojitoAPIs(user_id=user_id, token=user_token).add_movies_to_list(
            list_id=BIG_FIVE_LIST_ID, movies=filtered_movies
        )

        # save log to db
        try:
            db.save_log(
                user_id=user_id,
                action="add_to_big_five_list",
                data={"items": items, "response": resp},
            )
        except Exception as e:
            print(f"add_to_big_five_list > save_log: {str(e)}")

        if not resp["status"]:
            Error.send_raw_message(
                f"MOJITO API > Failed to add movies to the Big Five list: {resp.get('message', 'Unknown error')}"
            )
            return json.dumps(
                {
                    "success": False,
                    "message": "Moji :( => " + resp.get(
                        "message", "Failed to add items to the Big Five list."
                    ),
                }
            )
        
        # add inserted movie_id to filtered_movies
        for i, m in enumerate(filtered_movies):
            try:
                m['id'] = resp['data']['movie_ids'][i]
            except:
                pass
        # Update the assistant_object's user_extra_data with the new list
        if "user_extra_data" in assistant_object.payload.params:
            favorite_lists = assistant_object.payload.params["user_extra_data"].get("favorite_lists", [])
            for lst in favorite_lists:
                if lst.get("list_id") == BIG_FIVE_LIST_ID:
                    lst['movies'] = lst.get('movies', []) or []
                    lst["movies"].extend([{"movie_id": m["id"], "movie_name": m.get('title', '') or m.get('name', '')} for m in filtered_movies])
                    break
            assistant_object.payload.params["user_extra_data"]["favorite_lists"] = favorite_lists   
            
        return json.dumps(
            {"success": True, "lists": [{"list_id": BIG_FIVE_LIST_ID, "name": "Big Five"}], "type": "list_json"}
        )
    except Exception as e:
        Error(f"add_to_big_five_list", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})


def remove_favorite_list(assistant_object: MovieAssistant, 
                         **kwargs: Dict[str, Any]
                        #  list_id: str
                         ) -> str:
    """
    Remove an entire favorite list.
    
    Args:
        assistant_object: MovieAssistant instance containing user info and db connection
        list_id: ID of the list to remove
        
    Returns:
        str: JSON response indicating success or failure
    """
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        list_id = kwargs.get("list_id", "")
        
        resp = MojitoAPIs(user_id=user_id, token=user_token).remove_favorite_list(list_id=list_id)
        
        # Log the action
        try:
            db.save_log(
                user_id=user_id,
                action="remove_favorite_list",
                data={"list_id": list_id, "response": resp}
            )
        except Exception as e:
            print(f"remove_favorite_list > save_log: {str(e)}")
            
        if not resp["status"]:
            Error.send_raw_message(
                f"MOJITO API > Failed to remove the list: {resp.get('message', 'Unknown error')}"
            )
            return json.dumps({
                "success": False,
                "message": resp.get("message", "Failed to remove the list.")
            })
            
        # Remove the list from assistant_object's user_extra_data if it exists
        if "user_extra_data" in assistant_object.payload.params:
            favorite_lists = assistant_object.payload.params["user_extra_data"].get("favorite_lists", [])
            assistant_object.payload.params["user_extra_data"]["favorite_lists"] = [
                lst for lst in favorite_lists if lst.get("list_id") != list_id
            ]
            
        return json.dumps({
            "success": True,
            "lists": [{"list_id": list_id, "name": resp.get("list_name", "")}],
            "type": "list_json"
        })
        
    except Exception as e:
        Error(f"remove_favorite_list", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})


def remove_from_favorite_list(
    assistant_object: MovieAssistant,
    **kwargs: Dict[str, Any]
    # list_id: str,
    # movie_ids: List[str]
) -> str:
    """
    Remove specific movies from a favorite list.
    
    Args:
        assistant_object: MovieAssistant instance containing user info and db connection
        list_id: ID of the list to remove movies from
        items: List of movies to remove, each containing name, year, and type
        
    Returns:
        str: JSON response indicating success or failure
    """
    try:
        db = assistant_object.db
        user_id = assistant_object.user_id
        user_token = assistant_object.user_token
        list_id = kwargs.get("list_id", "")
        movie_ids = kwargs.get("movie_ids", [])
        
        resp = MojitoAPIs(user_id=user_id, token=user_token).remove_movies_from_list(
            list_id=list_id,
            movie_ids=movie_ids
        )
        
        success_removals = resp['data'].get('success', [])
        failed_removals = resp['data'].get('failed', [])
        
        # Log the action
        try:
            db.save_log(
                user_id=user_id,
                action="remove_from_favorite_list",
                data={"list_id": list_id, "items": movie_ids, "response": resp}
            )
        except Exception as e:
            print(f"remove_from_favorite_list > save_log: {str(e)}")
            
        if not resp["status"]:
            Error.send_raw_message(
                f"MOJITO API > Failed to remove movies from the list: {resp.get('message', 'Unknown error')}"
            )
            return json.dumps({
                "success": False,
                "message": resp.get("message", "Failed to remove items from the list.")
            })
            
        # Update the assistant_object's user_extra_data with the new list
        if "user_extra_data" in assistant_object.payload.params:
            favorite_lists = assistant_object.payload.params["user_extra_data"].get("favorite_lists", [])
            for lst in favorite_lists:
                if lst.get("list_id") == list_id:
                    lst["movies"] = [m for m in lst["movies"] if m.get("movie_id") not in movie_ids]
                    break
            
            assistant_object.payload.params["user_extra_data"]["favorite_lists"] = favorite_lists
            
        return json.dumps({
            "success": True,
            "lists": [{"list_id": list_id, "name": resp.get("list_name", "")}],
            "success_removals": success_removals,
            "failed_removals": failed_removals,
            "type": "list_json"
        })
        
    except Exception as e:
        Error(f"remove_from_favorite_list", e)
        return json.dumps({"success": False, "message": f"An error occurred: {str(e)}"})



TOOL_SCHEMAS = {
    "create_favorite_list": {
        "name": "create_favorite_list",
        "description": "Create a new favorite list for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the favorite list"},
                "description": {
                    "type": "string",
                    "description": "Description of the favorite list (optional)",
                },
            },
            "required": ["name"],
        },
    },
    "add_to_favorite_list": {
        "name": "add_to_favorite_list",
        "description": "Add movies or tv series to a favorite list",
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ID of the favorite list"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "year": {"type": "string"},
                            "type": {"type": "string", "description": "movie or tv-series or ... Make sure to use the correct type."},
                        },
                    },
                    "description": "List of movies or tv series to add to the favorite list",
                },
            },
            "required": ["list_id", "items"],
        },
    },
    "get_favorite_lists": {
        "name": "get_favorite_lists",
        "description": "Get all favorite lists of the user",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_favorite_list_items": {
        "name": "get_favorite_list_items",
        "description": "Get items of a favorite list",
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ID of the favorite list"}
            },
            "required": ["list_id"],
        },
    },
    "add_to_big_five_list": {
        "name": "add_to_big_five_list",
        "description": "Add up to 5 movies to the user's Big Five list",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "year": {"type": "string"},
                            "type": {"type": "string",  "description": "movie or tv-series or ... Make sure to use the correct type."},
                        },
                    },
                    "description": "List of movies to add to the Big Five list (maximum 5 items)",
                }
            },
            "required": ["items"],
        },
    },
}

TOOL_SCHEMAS["remove_favorite_list"] = {
    "name": "remove_favorite_list",
    "description": "Remove an entire favorite list",
    "parameters": {
        "type": "object",
        "properties": {
            "list_id": {
                "type": "string",
                "description": "ID of the favorite list to remove"
            }
        },
        "required": ["list_id"]
    }
}

TOOL_SCHEMAS["remove_from_favorite_list"] = {
    "name": "remove_from_favorite_list",
    "description": "Remove specific movies or TV series from a favorite list",
    "parameters": {
        "type": "object",
        "properties": {
            "list_id": {
                "type": "string",
                "description": "ID of the favorite list"
            },
            "movie_ids": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of movie IDs to remove from the list"
            }
        },
        "required": ["list_id", "movie_ids"]
    }
}

TOOLS = {
    "create_favorite_list": create_favorite_list,
    "add_to_favorite_list": add_to_favorite_list,
    "get_favorite_lists": get_favorite_lists,
    "get_favorite_list_items": get_favorite_list_items,
    "add_to_big_five_list": add_to_big_five_list,
}
TOOLS["remove_favorite_list"] = remove_favorite_list
TOOLS["remove_from_favorite_list"] = remove_from_favorite_list
