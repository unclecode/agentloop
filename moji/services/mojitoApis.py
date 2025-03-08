import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))   

from requests import post
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from libs.error import Error
from typing import List


class MojitoAPIs:

    def __init__(self, user_id: str, token: str) -> None:
        self.user_id = user_id
        self.token = token
        # self.base_url = "https://api.mojitofilms.de"
        self.base_url = "https://api-prod.mojitofilms.com"
        self.action_url = "/ai-assistant/action"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def create_post(self, feeds_post: str) -> dict:
        request_data = {
            "type": "create_feeds_post",
            "data": {
                "post": feeds_post
            }
        }
        response = post(
            f"{self.base_url}{self.action_url}",
            json=request_data,
            headers=self.headers
        )
        response = response.json()
        if response['status']:
            return {"status": "success", "message": "Post created successfully"}
        
        return {"status": "error", "message": "An error occurred while creating the post"}
    
    def create_favorite_list(self, list_name: str, list_description: str="") -> dict:
        """ Call the API to create a favorite list.

        Args:
            list_name (str): _description_
            list_description (str): _description_

        Returns:
            dict: _description_
        """
        try:
            request_data = {
                "type": "create_favorite_list",
                "data": {
                    "list_name": list_name,
                    "list_description": list_description
                }
            }
            response = post(
                f"{self.base_url}{self.action_url}",
                json=request_data,
                headers=self.headers
            )
            response = response.json()
            if not response.get('status'):
                Error.send_raw_message(f"MojitoAPIs.create_favorite_list\n{str(response)}")
            # {'status': True, 'message': 'Favorite list created successfully', 'data': {'list_id': '6a4b64e3-0322-4b9a-8c54-7166fbca0049'}}
            return response
        except Exception as e:
            Error("MojitoAPIs.create_favorite_list", e)
            raise e
    
    def add_movies_to_list(self, list_id: str, movies: list) -> dict:
        """ Call the API to add the movie to the list.

        Args:
            list_id (str): _description_
            movies (list): _description_

        Returns:
            dict: _description_
        """
        try:
            request_data = {
                "type": "add_to_favorite_list",
                "data": {
                    "list_id": list_id,
                    "movies": movies,
                }
            }
            print(request_data)
            response = post(
                f"{self.base_url}{self.action_url}",
                json=request_data,
                headers=self.headers
            )
            response = response.json()
            # print(request_data)
            # print(response)
            # Error.send_raw_message(f"LOG >> MojitoAPIs.add_movie_to_list\n{str(request_data)}\n{str(response)}")
            if not response.get('status'):
                Error.send_raw_message(f"ERROR >> add_movie_to_list\n{str(request_data)}\n{str(response)}")
            # {'status': True, 'message': 'Movies added to list successfully', 'data': None}
            return response
        except Exception as e:
            Error("MojitoAPIs.add_movies_to_list", e)
            raise e

    def add_to_big_five_list(self, movies: list) -> dict:
        """ Call the API to add the movie to the Big Five list.

        Args:
            movies (list): _description_

        Returns:
            dict: _description_
        """
        # return {'status': False, 'message': 'You can only add maximum 5 movies to Big Five, please remove some movies to add new ones'}
        # print("add_to_big_five_list")
        # print(self.headers)
        try:
            request_data = {
                "type": "add_to_big_five_list",
                "data": {
                    "movies": movies,
                }
            }
            # print(request_data)
            response = post(
                f"{self.base_url}{self.action_url}",
                json=request_data,
                headers=self.headers
            )
            response = response.json()
            Error.send_raw_message(f"LOG >> MojitoAPIs.add_to_big_five_list\n{str(request_data)}\n{str(response)}")
            if not response.get('status'):
                Error.send_raw_message(f"BUG >> calling api add_to_big_five_list\n{str(request_data)}\n{str(response)}")
            # print("add to big five", response)
            # {"status": True, "message": "Movies added to list successfully", "data": None}
            return response
        except Exception as e:
            Error("MojitoAPIs.add_to_big_five_list", e)
            raise e

    def get_user_profile(self) -> dict:
        """Call the API to get the user profile.

        Returns:
            dict: The user profile data
        """
        
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("Invalid user_id. It must be a non-empty string.")
        
        url = f"{self.base_url}/external/user/profile"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "user_id": self.user_id
        }
        
        try:
            response = post(url, headers=headers, json=data)
            response.raise_for_status()  # Raises HTTPError for bad responses
            response_data = response.json()
            if response_data.get('status') and 'data' in response_data and len(response_data['data']):
                return response_data['data'][0]
            # Error.send_raw_message(f"MojitoAPIs.get_user_profile\n{str(self.user_id)}\n{str(response_data)}")
            return {}

        except HTTPError as http_err:
            self.log_error("MojitoAPIs > get_user_profile", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_user_profile", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_user_profile", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_user_profile", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_user_profile", "An unexpected error occurred", e)
            raise
    
    def get_user_lists_names(self) -> List[str]:
        """Call the API to get the user's lists names.

        Returns:
            list: The user's lists names
        """
        
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("Invalid user_id. It must be a non-empty string.")
        
        url = f"{self.base_url}/external/user/profile"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "user_id": self.user_id
        }
        
        try:
            response = post(url, headers=headers, json=data)
            response.raise_for_status()  # Raises HTTPError for bad responses
            response_data = response.json()
            if response_data.get('status') and 'data' in response_data and len(response_data['data']) and 'favorite_lists' in response_data['data'][0]:
                return response_data['data'][0]['favorite_lists'] or []
            # Error.send_raw_message(f"MojitoAPIs.get_user_lists_names\n{str(self.user_id)}\n{str(response_data)}")
            return []

        except HTTPError as http_err:
            self.log_error("MojitoAPIs > get_user_lists_names", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_user_lists_names", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_user_lists_names", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_user_lists_names", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_user_lists_names", "An unexpected error occurred", e)
            raise
    
    def get_user_movies_names(self) -> List[str]:
        """Call the API to get the user's movies names.

        Returns:
            list: The user's movies names
        """
        
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("Invalid user_id. It must be a non-empty string.")
        
        url = f"{self.base_url}/external/user/profile"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "user_id": self.user_id
        }
        
        try:
            response = post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('status') and 'data' in response_data and len(response_data['data']) and 'favorite_lists' in response_data['data'][0]:
                favorite_movies = response_data['data'][0].get('favorite_movies', {})
                movies_names = [movie['name'] for movie in favorite_movies] if favorite_movies else []
                return movies_names or []
            # Error.send_raw_message(f"MojitoAPIs.get_user_movies_names\n{str(self.user_id)}\n{str(response_data)}")
            return []

        except HTTPError as http_err:
            self.log_error("MojitoAPIs > get_user_movies_names", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_user_movies_names", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_user_movies_names", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_user_movies_names", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_user_movies_names", "An unexpected error occurred", e)
            raise
    
    def get_user_favorite_lists(self) -> List[str]:
        """Call the API to get the user's favorite lists.

        Returns:
            list: The user's favorite lists
        """
        
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("Invalid user_id. It must be a non-empty string.")
        
        url = f"{self.base_url}/external/user/profile"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "user_id": self.user_id
        }
        
        try:
            response = post(url, headers=headers, json=data)
            response.raise_for_status()  # Raises HTTPError for bad responses
            response_data = response.json()
            if response_data.get('status') and 'data' in response_data and len(response_data['data']) and 'user_favorite_lists' in response_data['data'][0]:
                items = response_data['data'][0]['user_favorite_lists'] or []
                # change 'id' to 'list_id' for consistency
                for item in items:
                    item['list_id'] = item.pop('id')
                return items
            # Error.send_raw_message(f"MojitoAPIs.get_user_favorite_lists\n{str(self.user_id)}\n{str(response_data)}")
            return []

        except HTTPError as http_err:
            # if the satatus code is 400, it means no user found
            if response.status_code == 400:
                return []
            self.log_error("MojitoAPIs > get_user_favorite_lists", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_user_favorite_lists", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_user_favorite_lists", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_user_favorite_lists", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_user_favorite_lists", "An unexpected error occurred", e)
            raise

    def get_favorite_lists(self) -> List[str]:
        url = f"{self.base_url}{self.action_url}"
        data = {
            "type": "get_favorite_lists"
        }
        
        try:
            response = post(url, headers=self.headers, json=data)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('status'):
                if 'data' in response_data and len(response_data['data']):
                    big_five_list = [{
                        "list_id": "BIG_FIVE",
                        "list_name": "Big Five",
                        "movies": response_data['data'][0].get('big_five_movies', []) or []
                    }]
                    user_favorite_lists = response_data['data'][0].get('user_favorite_lists', []) or []
                    user_favorite_lists.extend(big_five_list)
                    return user_favorite_lists
            # Error.send_raw_message(f"MojitoAPIs.get_favorite_lists\n{str(list_id)}\n{str(response_data)}")
            return []

        except HTTPError as http_err:
            self.log_error("MojitoAPIs > get_favorite_lists", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_favorite_lists", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_favorite_lists", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_favorite_lists", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_favorite_lists", "An unexpected error occurred", e)
            raise
    
    
    def get_list_items(self, list_id: str) -> List[str]:
        """Call the API to get the list's movies.

        Args:
            list_id (str): _description_

        Returns:
            list: The list's movies
        """
        
        if not isinstance(list_id, str) or not list_id:
            raise ValueError("Invalid list_id. It must be a non-empty string.")
        
        url = f"{self.base_url}{self.action_url}"
        data = {
            "type": "get_favorite_list_movies",
            "data":{
                "list_id": list_id
            }
        }
        
        try:
            response = post(url, headers=self.headers, json=data)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('status'):
                return response_data['data']
            # Error.send_raw_message(f"MojitoAPIs.get_list_items\n{str(list_id)}\n{str(response_data)}")
            return []

        except HTTPError as http_err:
            self.log_error("MojitoAPIs > get_list_items", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_list_items", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_list_items", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_list_items", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_list_items", "An unexpected error occurred", e)
            raise
        
    def log_error(self, location: str, message: str, error: Exception) -> None:
        """Log the error details.

        Args:
            location (str): The location where the error occurred
            message (str): A descriptive error message
            error (Exception): The caught exception
        """
        # Implement your logging mechanism here
        print(f"{location} >> {message}: {error}")
        Error(location, error)

    def remove_favorite_list(self, list_id: str) -> dict:
        """Call the API to remove a favorite list.

        Args:
            list_id (str): ID of the list to remove

        Returns:
            dict: Response from the API containing status and message
        """
        try:
            request_data = {
                "type": "delete_favorite_list",
                "data": {
                    "list_id": list_id
                }
            }
            response = post(
                f"{self.base_url}{self.action_url}",
                json=request_data,
                headers=self.headers
            )
            response = response.json()
            if not response.get('status'):
                Error.send_raw_message(f"MojitoAPIs.remove_favorite_list\n{str(response)}")
            return response
        except Exception as e:
            Error("MojitoAPIs.remove_favorite_list", e)
            raise e

    def remove_movies_from_list(self, list_id: str, movie_ids: list) -> dict:
        """Call the API to remove specific movies from a favorite list.

        Args:
            list_id (str): ID of the list to remove movies from
            movie_ids (list): List of movie IDs to remove

        Returns:
            dict: Response from the API containing status and message
        """
        try:
            success, failed = [], []
            for movie_id in movie_ids:
                request_data = {
                    "type": "delete_movie_from_favorite_list",
                    "data": {
                        "list_id": list_id,
                        "movie_id": movie_id
                    }
                }
                response = post(
                    f"{self.base_url}{self.action_url}",
                    json=request_data,
                    headers=self.headers
                )
                response = response.json()
                print(response)
                if not response.get('status'):
                    failed.append(movie_id)
                    # Error.send_raw_message(f"ERROR >> remove_movies_from_list\n{str(request_data)}\n{str(response)}")
                else:
                    success.append(movie_id)
            return {"status": True, "message": "Movies removed successfully", "data": {"success": success, "failed": failed}}
        except Exception as e:
            Error("MojitoAPIs.remove_movies_from_list", e)
            raise e
        
    def get_user_list(self) -> List[dict]:
        """Call the API to get the user's movie lists.
        
        Returns:
            List[dict]: List of user's movie lists containing list_id, list_name, and movies
        """
        
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("Invalid user_id. It must be a non-empty string.")
        
        url = f"{self.base_url}/external/user/list"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "user_id": self.user_id
        }
        
        try:
            response = post(url, headers=headers, json=data)
            response.raise_for_status()  # Raises HTTPError for bad responses
            response_data = response.json()
            
            if response_data.get('status') and 'data' in response_data:
                if not response_data['data'] or len(response_data['data']) == 0:
                    return []
                # Transform the response to match the format shown in the screenshot
                user_lists = []
                for list_item in response_data['data'][0].get('user_favorite_lists', []):
                    transformed_list = {
                        'id': list_item.get('list_id'),
                        'name': list_item.get('list_name'),
                        'movies': list_item.get('movies', [])
                    }
                    user_lists.append(transformed_list)
                return user_lists
                
            return []

        except HTTPError as http_err:
            # If status code is 400, it means no user found
            if response.status_code == 400:
                return []
            self.log_error("MojitoAPIs > get_user_list", "HTTP error occurred", http_err)
            raise
        except ConnectionError as conn_err:
            self.log_error("MojitoAPIs > get_user_list", "Connection error occurred", conn_err)
            raise
        except Timeout as timeout_err:
            self.log_error("MojitoAPIs > get_user_list", "Timeout error occurred", timeout_err)
            raise
        except RequestException as req_err:
            self.log_error("MojitoAPIs > get_user_list", "Request exception occurred", req_err)
            raise
        except Exception as e:
            self.log_error("MojitoAPIs > get_user_list", "An unexpected error occurred", e)
            raise
    
    
if __name__ == "__main__":
    user_id = "c46d74d1-8d1c-4845-a474-483706592c87"
    user_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYzQ2ZDc0ZDEtOGQxYy00ODQ1LWE0NzQtNDgzNzA2NTkyYzg3IiwidXNlcl9yb2xlIjoidXNlciIsImlhdCI6MTcyOTc4MTAzNCwiZXhwIjoxNzQ1MzMzMDM0fQ.PMhrrKvdLLBNga4Lp1zNsP5ZpwLlyoO87whJCkpCQp0'
    
    # p = {'type': 'add_to_favorite_list', 'data': {'list_id': '222e0d2e-5d5f-4e02-bbc2-7ee1d9b95a0b', 'movies': [{'backdrop_path': '/qJeU7KM4nT2C1WpOrwPcSDGFUWE.jpg', 'id': 313369, 'overview': 'Mia, an aspiring actress, serves lattes to movie stars in between auditions and Sebastian, a jazz musician, scrapes by playing cocktail party gigs in dingy bars, but as success mounts they are faced with decisions that begin to fray the fragile fabric of their love affair, and the dreams they worked so hard to maintain in each other threaten to rip them apart.', 'popularity': 85.426, 'poster_path': '/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg', 'release_date': '2016-11-29', 'title': 'La La Land', 'video': False, 'vote_average': 7.9, 'vote_count': 16762, 'year': '2016', 'type': 'movie'}]}}
    filtered_movies =[{'backdrop_path': '/qJeU7KM4nT2C1WpOrwPcSDGFUWE.jpg', 'id': 313369, 'overview': 'Mia, an aspiring actress, serves lattes to movie stars in between auditions and Sebastian, a jazz musician, scrapes by playing cocktail party gigs in dingy bars, but as success mounts they are faced with decisions that begin to fray the fragile fabric of their love affair, and the dreams they worked so hard to maintain in each other threaten to rip them apart.', 'popularity': 85.426, 'poster_path': '/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg', 'release_date': '2016-11-29', 'title': 'La La Land', 'video': False, 'vote_average': 7.9, 'vote_count': 16762, 'year': '2016', 'type': 'movie'}]
    resp = MojitoAPIs(user_id=user_id, token=user_token).add_movies_to_list(
        list_id='222e0d2e-5d5f-4e02-bbc2-7ee1d9b95a0b', movies=filtered_movies
    )
        
    # {'type': 'add_to_big_five_list', 'data': {'movies': [{'id': 603, 'name': 'The Matrix', 'overview': 'Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.', 'poster_path': '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', 'backdrop_path': '/ncEsesgOJDNrTUED89hYbA117wo.jpg', 'release_date': '1999-03-31', 'vote_average': 8.218, 'vote_count': 25115, 'popularity': 104.333, 'video': False, 'year': '1999', 'type': 'movie'}, {'id': 313369, 'name': 'La La Land', 'overview': 'Mia, an aspiring actress, serves lattes to movie stars in between auditions and Sebastian, a jazz musician, scrapes by playing cocktail party gigs in dingy bars, but as success mounts they are faced with decisions that begin to fray the fragile fabric of their love affair, and the dreams they worked so hard to maintain in each other threaten to rip them apart.', 'poster_path': '/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg', 'backdrop_path': '/nofXR1TN1vgGjdfnwGQwFaAWBaY.jpg', 'release_date': '2016-11-29', 'vote_average': 7.901, 'vote_count': 16447, 'popularity': 67.448, 'video': False, 'year': '2016', 'type': 'movie'}]}}
    # movies = [{'id': 313369, 'name': 'La La Land', 'overview': 'Mia, an aspiring actress, serves lattes to movie stars in between auditions and Sebastian, a jazz musician, scrapes by playing cocktail party gigs in dingy bars, but as success mounts they are faced with decisions that begin to fray the fragile fabric of their love affair, and the dreams they worked so hard to maintain in each other threaten to rip them apart.', 'poster_path': '/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg', 'backdrop_path': '/nofXR1TN1vgGjdfnwGQwFaAWBaY.jpg', 'release_date': '2016-11-29', 'vote_average': 7.901, 'vote_count': 16447, 'popularity': 67.448, 'video': False, 'year': '2016', 'type': 'movie'}]
    # resp = MojitoAPIs(user_id=user_id, token=user_token).add_to_big_five_list(movies=movies)
    
    # resp = MojitoAPIs(user_id=user_id, token=user_token).get_user_favorite_lists()
    # print(resp)
    # [{'id': 'd2dc2c8f-a0df-43a4-b281-452b0ca29e05', 'name': 'sci fi movies'}]
    
    # resp = MojitoAPIs(user_id=user_id, token=user_token).get_list_items(list_id="d2dc2c8f-a0df-43a4-b281-452b0ca29e05")
    # resp = MojitoAPIs(user_id=user_id, token=user_token).get_user_list()
    # resp = MojitoAPIs(user_id=user_id, token=user_token).get_favorite_lists()
    # print(resp)
    
    # resp = MojitoAPIs(user_id=user_id, token=user_token).get_user_favorite_lists()
    
    # create a new list
    # resp = MojitoAPIs(user_id=user_id, token=user_token).create_favorite_list(list_name="comedies", list_description="My favorite comedies")
    print(resp)