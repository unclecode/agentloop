import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))                

from config import TMDB_ACCESS_TOKEN
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
# from tools.search_image import get_movie_poster
# from libs.app_redis import AppRedisDB
from fuzzywuzzy import fuzz
import urllib.parse

import requests
import json, pprint
from redis import Redis

FUZZ_VAL = 70

def clean_search_query(query):
    return urllib.parse.quote(query)


# Helper function to remove duplicates based on 'id'
def remove_duplicates(items):
    unique_items = {}
    for item in items:
        unique_items[item['id']] = item
    return list(unique_items.values())


class TMDBService:
    def __init__(self):
        self.headers = {
            'Authorization': f'Bearer {TMDB_ACCESS_TOKEN}',
            'Content-Type': 'application/json;charset=utf-8'
        }
        self.base_url = "https://api.themoviedb.org/3"
        self.genre_dict = self.cache_genre_ids()
        self.redis_db = Redis(host='localhost', port=6379, db=0)
        
    def cache_genre_ids(self, force=False):
        """
        Cache the genre ids from TMDB API to a file.

        Args:
            force (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        
        # first check if the file exists
        if not force:
            try:
                with open('tmdb_genre_ids.json', 'r') as file:
                    genre_dict = json.load(file)
                    return genre_dict
            except FileNotFoundError:
                pass

        # Get the list of genres
        genre_url = 'https://api.themoviedb.org/3/genre/movie/list?language=en-US'
        response = requests.get(genre_url, headers=self.headers)
        genres = response.json()

        genre_dict = {genre['name'].lower(): genre['id'] for genre in genres['genres']}

        # Save to file
        with open('tmdb_genre_ids.json', 'w') as file:
            json.dump(genre_dict, file)

        return genre_dict

    def fetch_results(self, url, max_results = 20):
        """
        Fetch results from the TMDB API.

        Args:
            url (_type_): _description_
            max_results (_type_): _description_

        Returns:
            _type_: _description_
        """
        results = []
        page = 1

        while len(results) < max_results:
            response = requests.get(f"{url}&page={page}", headers=self.headers)
            data = response.json()
            results.extend(data.get('results', []))
            if len(results) >= data['total_results']:
                break
            page += 1

        return results[:max_results]

    def check_movies(self, movies, genre_dict=None, redis_db=None):
        """
        Check if the movies or TV shows are in the database.

        Args:
            movies (list): List of movies or TV shows with their details.
            genre_dict (dict): Dictionary containing genre mappings.
            redis_db (Redis): Redis database instance for caching.

        Returns:
            list: List of matched movies or TV shows.
        """
        redis_db = redis_db or self.redis_db
        genre_dict = genre_dict or self.genre_dict
        # Define mappings for different types
        type_mapping = {
            'movie': {'search_key': 'title', 'date_key': 'release_date', 'tmdb_key': 'movie'},
            'tv': {'search_key': 'name', 'date_key': 'first_air_date', 'tmdb_key': 'tv'},
            'tv-series': {'search_key': 'name', 'date_key': 'first_air_date', 'tmdb_key': 'tv'},
            'tv-show': {'search_key': 'name', 'date_key': 'first_air_date', 'tmdb_key': 'tv'},
        }
        
        # Search the TMDB API with ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            futures = []
            for movie in movies:
                future = executor.submit(self.search_tmdb, movie['name'], genre_dict, year=movie['year'], redis_db=redis_db)
                futures.append(future)

            results = [future.result() for future in futures]

        new_results = []
        for ix, m in enumerate(results):
            movie_type = movies[ix]['type']
            query_type = m.get('query_type', 'movie')

            # Determine type-specific keys
            # mapping = type_mapping.get(movie_type, type_mapping['movie'])
            mapping = type_mapping.get(query_type, type_mapping['movie'])
            tmdb_key = mapping['tmdb_key']
            search_key = mapping['search_key']
            date_key = mapping['date_key']
            
            item_type = 'movie' if tmdb_key == 'movie' else 'tv-series'
            
            search_name = movies[ix]['name'].lower()
            search_year = str(movies[ix]['year'])

            selected_items = [
                item for item in m.get(tmdb_key, [])
                if fuzz.partial_ratio(item[search_key].lower(), search_name) > FUZZ_VAL and item[date_key].split('-')[0] == search_year
            ]
            
            if selected_items:
                selected_item = selected_items[0]
                if selected_item['poster_path']:
                    new_result = {
                        "id": selected_item['id'],
                        "name": selected_item[search_key],  # Use the correct key for name/title
                        "overview": selected_item['overview'],
                        "poster_path": selected_item['poster_path'],
                        "backdrop_path": selected_item['backdrop_path'],
                        "release_date": selected_item[date_key],
                        "vote_average": selected_item['vote_average'],
                        "vote_count": selected_item['vote_count'],
                        "popularity": selected_item['popularity'],
                        "video": selected_item.get('video', False),
                        "year": movies[ix]['year'],
                        "type": item_type
                    }
                # # Poster handling
                # try:
                #     update_redis = False
                #     if not selected_item['poster_path']:
                #         image_url = None
                #         redis_key = 'original_title' if movie_type == 'movie' else 'original_name'
                #         if redis_db:
                #             image_url = AppRedisDB(redis_db).get_movie_poster(selected_item[redis_key])
                #         if not image_url:
                #             image_url = get_movie_poster(selected_item[redis_key])
                #             update_redis = True
                #         new_result['poster_path'] = image_url
                #         if redis_db and update_redis:
                #             AppRedisDB(redis_db).set_movie_poster(selected_item[redis_key], image_url)
                # except Exception as e:
                #     print(f"Error getting poster: {str(e)}")
                
                new_results.append(new_result)

        # Sort the results by popularity
        try:
            new_results = sorted(new_results, key=lambda x: x['popularity'], reverse=True)
        except Exception as e:
            print(f"Error sorting results: {str(e)}")
        
        return new_results

    def get_latest_movies(self, max_results=20):
        """
        Get the latest movies from the TMDB API.

        Args:
            max_results (_type_): _description_
            
        Returns:
            _type_: _description_
        """

        url = "https://api.themoviedb.org/3/movie/now_playing?language=en-US"
        response = self.fetch_results(url, max_results)
        
        needed_keys = ['genres', 'original_language', 'original_title', 'overview', 'popularity', 'release_date']
        genres = self.cache_genre_ids()
        filtered_response = []
        for r in response:
            r['genres'] = [genre for genre, value in genres.items() if value in r['genre_ids']]
            r.pop('genre_ids', None)
            r = {k: v for k, v in r.items() if k in needed_keys}
            filtered_response.append(r)
        
        # sort them based on popularity
        filtered_response = sorted(filtered_response, key=lambda x: x['popularity'], reverse=True)
        return filtered_response

    def search_tmdb(self, query, genre_dict=None, max_results=20, year=None, redis_db=None):
        """
        Search the TMDB API for movies, people, and TV shows. version 2

        Args:
            query (_type_): _description_
            genre_dict (_type_): _description_
            max_results (int, optional): _description_. Defaults to 20.
            year (_type_, optional): _description_. Defaults to None.
            redis_db (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        redis_db = redis_db or self.redis_db
        genre_dict = genre_dict or self.genre_dict
        def fetch_results(url, max_count):
            results = []
            page = 1
            while len(results) < max_count:
                response = requests.get(f"{url}&page={page}", headers=self.headers)
                data = response.json()
                results.extend(data.get('results', []))
                if page >= data.get('total_pages', 1) or len(results) >= data.get('total_results', 0):
                    break
                page += 1
            return results[:max_count]

        def search_multi():
            if year:
                url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&primary_release_year={year}"
            else:
                url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US"
            return fetch_results(url, max_results)

        def search_person():
            url = f"https://api.themoviedb.org/3/search/person?query={query}&include_adult=false&language=en-US"
            return fetch_results(url, 1)  # We only need the top person result

        def get_person_credits(person_id):
            url = f"https://api.themoviedb.org/3/person/{person_id}/combined_credits?language=en-US"
            response = requests.get(url, headers=self.headers)
            return response.json()

        def discover_movies_by_genre(genre_name):
            genre_id = genre_dict.get(genre_name.lower())
            if genre_id:
                if year:
                    url = f'https://api.themoviedb.org/3/discover/movie?with_genres={genre_id}&primary_release_year={year}'
                else:
                    url = f'https://api.themoviedb.org/3/discover/movie?with_genres={genre_id}'
                return self.fetch_results(url, max_results)
            return []

        query = query.strip()
        # Perform initial multi-search to determine query type
        multi_results = search_multi()

        # Determine the most likely query type
        query_type = 'unknown'
        if multi_results:
            query_type = multi_results[0]['media_type']

        # If it's a person, get their details and credits
        if query_type == 'person':
            person_results = search_person()
            if person_results:
                person = person_results[0]
                person_id = person['id']
                with ThreadPoolExecutor() as executor:
                    credits_future = executor.submit(get_person_credits, person_id)
                    genre_future = executor.submit(discover_movies_by_genre, query)

                    credits = credits_future.result()
                    genre_results = genre_future.result()

                response = {
                    'query_type': 'person',
                    'people': [person],
                    'movie': credits.get('cast', []) + credits.get('crew', []),
                    'tv': [item for item in credits.get('cast', []) + credits.get('crew', []) if item['media_type'] == 'tv'],
                    'genre': genre_results
                }
                # if any movie inside movies does not have a title, we can remove it
                response['movie'] = [item for item in response['movie'] if 'title' in item]
                response['tv'] = [item for item in response['tv'] if 'name' in item]
                return response

        # For other query types, use the multi-search results
        with ThreadPoolExecutor() as executor:
            genre_future = executor.submit(discover_movies_by_genre, query)
            genre_results = genre_future.result()

        response = {
            'query_type': query_type,
            'movie': [item for item in multi_results if item['media_type'] == 'movie'],
            'tv': [item for item in multi_results if item['media_type'] == 'tv'],
            'people': [item for item in multi_results if item['media_type'] == 'person'],
            'genre': genre_results
        }
        
        # for each category, sort by popularity
        try:
            if 'movie' in response:
                response['movie'] = sorted(response['movie'], key=lambda x: x['popularity'], reverse=True)
            if 'tv' in response:
                response['tv'] = sorted(response['tv'], key=lambda x: x['popularity'], reverse=True)
        except:
            pass
        if 'movie' in response:
            filtered_movies = []
            # we need to check if the poster_path is not available
            for movie in response['movie']:
                if 'title' not in movie:
                    movie['title'] = movie['original_title']
                if movie['poster_path']:
                    filtered_movies.append(movie)
                # try:
                #     if not movie['poster_path']:
                #         image_url = None
                #         update_redis = False
                #         if redis_db:
                #             image_url = AppRedisDB(redis_db).get_movie_poster(movie['original_title'])
                #         if not image_url:
                #             image_url = get_movie_poster(movie['original_title'])
                #             update_redis = True
                #         movie['poster_path'] = image_url
                #         if redis_db and update_redis:
                #             AppRedisDB(redis_db).set_movie_poster(movie['original_title'], image_url)
                # except Exception as e:
                #     print(f"Error get movie poster: {str(e)}")
        if 'tv' in response:
            filtered_tv = []
            for tv in response['tv']:
                if tv['poster_path']:
                    filtered_tv.append(tv)
            # try:
            #     # we need to check if the poster_path is available, if not we need to search for the poster
            #     for tv in response['tv']:
            #         if not tv['poster_path']:
            #             image_url = None
            #             update_redis = False
            #             if redis_db:
            #                 image_url = AppRedisDB(redis_db).get_movie_poster(tv['original_name'])
            #             if not image_url:
            #                 image_url = get_movie_poster(tv['original_name'])
            #                 update_redis = True
            #             tv['poster_path'] = image_url
            #             if redis_db and update_redis:
            #                 AppRedisDB(redis_db).set_movie_poster(tv['original_name'], image_url)
            # except Exception as e:
            #     print(f"Error get tv show poster: {str(e)}")
        return response

    def search_tmdb_v2(self, query, genre_dict, max_results=20, year=None, include_trailer=False):
        """
        Search the TMDB API for movies, people, and TV shows. version 2

        Args:
            query (_type_): _description_
            genre_dict (_type_): _description_
            max_results (int, optional): _description_. Defaults to 20.
            year (_type_, optional): _description_. Defaults to None.
            redis_db (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        def fetch_results(url, max_count):
            results = []
            page = 1
            while len(results) < max_count:
                response = requests.get(f"{url}&page={page}", headers=self.headers)
                data = response.json()
                results.extend(data.get('results', []))
                if page >= data.get('total_pages', 1) or len(results) >= data.get('total_results', 0):
                    break
                page += 1
            return results[:max_count]

        def search_multi():
            if year:
                url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US&primary_release_year={year}"
            else:
                url = f"https://api.themoviedb.org/3/search/multi?query={query}&include_adult=false&language=en-US"
            return fetch_results(url, max_results)

        def search_person():
            url = f"https://api.themoviedb.org/3/search/person?query={query}&include_adult=false&language=en-US"
            return fetch_results(url, 1)  # We only need the top person result

        def get_person_credits(person_id):
            url = f"https://api.themoviedb.org/3/person/{person_id}/combined_credits?language=en-US"
            response = requests.get(url, headers=self.headers)
            return response.json()

        def discover_movies_by_genre(genre_name):
            genre_id = genre_dict.get(genre_name.lower())
            if genre_id:
                if year:
                    url = f'https://api.themoviedb.org/3/discover/movie?with_genres={genre_id}&primary_release_year={year}'
                else:
                    url = f'https://api.themoviedb.org/3/discover/movie?with_genres={genre_id}'
                return self.fetch_results(url, max_results)
            return []
        
        def fetch_trailers_for_batch(items, media_type):
            """Fetch trailers for a batch of items in parallel."""
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self.add_trailer, item, media_type): item 
                    for item in items
                }
                
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        # Update the item with trailer info
                        updated_item = future.result()
                        if updated_item:
                            item.update(updated_item)
                    except Exception as e:
                        print(f"Error fetching trailer for {media_type} {item.get('id')}: {e}")
                        continue

        query = clean_search_query(query.strip())
        # Perform initial multi-search to determine query type
        multi_results = search_multi()
        
        # Categorize results into person, movie, and tv lists
        people_results = [item for item in multi_results if item['media_type'] == 'person']
        movie_results = [item for item in multi_results if item['media_type'] == 'movie']
        tv_results = [item for item in multi_results if item['media_type'] == 'tv']

        # Prepare the response structure
        response = {
            'query_type': 'multi',  # We are handling multiple types
            'movie': movie_results,
            'tv': tv_results,
            'people': people_results,
            'genre': []
        }

        # If there are people results, fetch the credits for the top person
        if people_results:
            person_results = search_person()
            if person_results:
                person = person_results[0]
                person_id = person['id']
                
                with ThreadPoolExecutor() as executor:
                    # Fetch the person's credits (movies and TV shows they've worked on)
                    credits_future = executor.submit(get_person_credits, person_id)
                    genre_future = executor.submit(discover_movies_by_genre, query)

                    credits = credits_future.result()
                    genre_results = genre_future.result()

                # Merge person's movie/TV credits with general multi search results
                person_movies = credits.get('cast', []) + credits.get('crew', [])
                person_tv = [item for item in person_movies if item['media_type'] == 'tv']
                person_movies = [item for item in person_movies if item['media_type'] == 'movie']

                # Add the person's movies and TV shows to the general results
                response['movie'].extend(person_movies)
                response['tv'].extend(person_tv)
                response['genre'] = genre_results

        # Sort movies and TV shows by popularity
        try:
            if 'movie' in response:
                response['movie'] = sorted(response['movie'], key=lambda x: x['popularity'], reverse=True)
            if 'tv' in response:
                response['tv'] = sorted(response['tv'], key=lambda x: x['popularity'], reverse=True)
        except Exception as e:
            print(f"Error sorting results: {str(e)}")

        # Filter out entries without a poster path and ensure titles are present
        response['movie'] = [item for item in response['movie'] if 'title' in item and item.get('poster_path')]
        response['tv'] = [item for item in response['tv'] if 'name' in item and item.get('poster_path')]
        
        # Remove duplicates in movies, tv shows, and people before returning
        response['movie'] = remove_duplicates(response['movie'])
        response['tv'] = remove_duplicates(response['tv'])
        response['people'] = remove_duplicates(response['people'])
        
        if include_trailer:
            with ThreadPoolExecutor() as executor:
                # Start both movie and TV trailer fetching concurrently
                movie_future = executor.submit(fetch_trailers_for_batch, response['movie'], 'movie')
                tv_future = executor.submit(fetch_trailers_for_batch, response['tv'], 'tv')
                
                # Wait for both to complete
                movie_future.result()
                tv_future.result()

        return response

    def get_movie(self, movie_id):
        """
        Get the movie details from the TMDB API.

        Args:
            movie_id (_type_): _description_
            
        Returns:
            _type_: _description_
        """
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        try:
            response = requests.get(url, headers=self.headers)

            # Check if the response was successful
            if response.status_code == 200:
                return response.json()
            else:
                # Handle different status codes
                if response.status_code == 404:
                    return {"error": "Movie not found."}
                elif response.status_code == 401:
                    return {"error": "Unauthorized. Check your API key."}
                else:
                    return {"error": f"Failed to retrieve movie details. Status code: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            # Handle any request exceptions (e.g., network issues, timeout)
            return {"error": f"An error occurred: {str(e)}"}
    
    def get_tv_show(self, tv_id):
        """
        Get the TV show details from the TMDB API.

        Args:
            tv_id (_type_): _description_
            
        Returns:
            _type_: _description_
        """
        url = f"https://api.themoviedb.org/3/tv/{tv_id}"
        try:
            response = requests.get(url, headers=self.headers)

            # Check if the response was successful
            if response.status_code == 200:
                return response.json()
            else:
                # Handle different status codes
                if response.status_code == 404:
                    return {"error": "TV show not found."}
                elif response.status_code == 401:
                    return {"error": "Unauthorized. Check your API key."}
                else:
                    return {"error": f"Failed to retrieve TV show details. Status code: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            # Handle any request exceptions (e.g., network issues, timeout)
            return {"error": f"An error occurred: {str(e)}"}

    def fetch_videos(self, id, media_type):
        """
        Fetch videos for a movie or TV show.

        Args:
            id (int): The TMDB ID of the movie or TV show.
            media_type (str): Either 'movie' or 'tv'.

        Returns:
            list: A list of video dictionaries.
        """
        video_url = f"{self.base_url}/{media_type}/{id}/videos"
        try:
            response = requests.get(video_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Error fetching videos: {e}")
            return []
    
    def add_trailer(self, result, media_type):
        """
        Add trailer information to the result.
        
        Args:
            result (dict): Movie or TV show data
            media_type (str): Either 'movie' or 'tv'
        
        Returns:
            dict: Updated result with trailer information
        """
        try:
            videos = self.fetch_videos(result['id'], media_type)
            trailers = [video for video in videos if video['type'] == 'Trailer' and video['site'] == 'YouTube']
            if trailers:
                result['trailer'] = f"https://www.youtube.com/watch?v={trailers[0]['key']}"
            return result
        except Exception as e:
            print(f"Error in add_trailer for {media_type} {result.get('id')}: {e}")
            return result
    
    def safe_request(self, url):
        """Make a safe API request."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error in API request: {e}")
            return None

    def filter_by_language(self, results, lang):
        """Filter results by original language."""
        return [r for r in results if r.get('original_language') == lang]
       
    def fast_fuzzy_search(self, title, year = None, original_language=None, item_type=None):
        """
        Fast search the TMDB API for movies or TV shows with fuzzy title matching.

        Args:
            title (str): The title of the movie or TV show.
            year (int): The release year.
            tmdb_id (int): The TMDB ID of the movie or TV show.
            original_language (str, optional): The original language of the content. Defaults to None.
            item_type (str, optional): Type of content to search for ('movie', 'tv', or None for both). Defaults to None.

        Returns:
            dict or list: If item_type is specified, returns a dict with details of the found content.
                        If item_type is None, returns a list of all found movies and TV shows.
                        Returns None if nothing is found or an error occurred.
        """
        def normalize_title(text):
            """Normalize title for comparison by removing common articles and lowercasing"""
            if not text:
                return ""
            # Remove common articles and special characters, convert to lowercase
            text = text.lower()
            # Remove 'the', 'a', 'an' from start of string
            prefixes = ['the ', 'a ', 'an ']
            for prefix in prefixes:
                if text.startswith(prefix):
                    text = text[len(prefix):]
            # Remove special characters and extra spaces
            text = ''.join(c for c in text if c.isalnum() or c.isspace())
            return ' '.join(text.split())

        def title_similarity(title1, title2):
            """
            Compare two titles and return True if they are similar enough.
            This includes checking if one title contains the other, or if they're similar
            after normalization.
            """
            title1_norm = normalize_title(title1)
            title2_norm = normalize_title(title2)
            
            # Direct containment check (case insensitive)
            if title1_norm in title2_norm or title2_norm in title1_norm:
                return True
                
            # Check if titles are similar after normalization
            return title1_norm == title2_norm

        search_params = {
            "query": title,
            "include_adult": "false"
        }
        if year:
            search_params["year"] = year
            
        if original_language:
            search_params["with_original_language"] = original_language

        def search_content(content_type):
            url = f"{self.base_url}/search/{content_type}?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
            try:
                results = self.fetch_results(url)
                if results:
                    # Filter and sort results by title similarity
                    matching_results = []
                    search_title = title
                    
                    for result in results[:10]:  # Check first 10 results
                        result_title = result.get('title') if content_type == 'movie' else result.get('name')
                        
                        if title_similarity(search_title, result_title):
                            # Get full details for the matching result
                            content_id = result["id"]
                            full_result = self.safe_request(f"{self.base_url}/{content_type}/{content_id}")
                            if full_result:
                                full_result = self.add_trailer(full_result, content_type)
                                matching_results.append(full_result)
                    
                    return matching_results
                    
            except Exception as e:
                print(f"Error in {content_type} search: {e}")
            return None

        # If item_type is specified, search only that type
        if item_type in ['movie', 'tv']:
            results = search_content(item_type)
            return results[0] if results else None  # Return first match for single type search
        
        # If no item_type specified, search both types and return all results
        all_results = []
        
        movie_results = search_content('movie')
        if movie_results:
            all_results.extend(movie_results)
            
        tv_results = search_content('tv')
        if tv_results:
            all_results.extend(tv_results)
            
        return all_results if all_results else None       
          
    def fast_fuzzy_search1(self, title, year = None,  original_language=None, item_type=None):
        """
        Fast search the TMDB API for movies or TV shows using TMDB's built-in fuzzy search.

        Args:
            title (str): The title of the movie or TV show.
            year (int): The release year.
            original_language (str, optional): The original language of the content. Defaults to None.
            item_type (str, optional): Type of content to search for ('movie', 'tv', or None for both). Defaults to None.

        Returns:
            dict or list: If item_type is specified, returns a dict with details of the found content.
                        If item_type is None, returns a list of all found movies and TV shows.
                        Returns None if nothing is found or an error occurred.
        """
        search_params = {
            "query": title,
            "include_adult": "false",
            "search_type": "ngram"  # Enable TMDB's fuzzy search
        }
        if year:
            search_params["year"] = year
            
        if original_language:
            search_params["with_original_language"] = original_language

        def search_content(content_type):
            url = f"{self.base_url}/search/{content_type}?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
            try:
                results = self.fetch_results(url)
                if results:
                    matching_results = []
                    for result in results[:5]:  # Get top 5 matches
                        content_id = result["id"]
                        full_result = self.safe_request(f"{self.base_url}/{content_type}/{content_id}")
                        if full_result:
                            full_result = self.add_trailer(full_result, content_type)
                            matching_results.append(full_result)
                    return matching_results
            except Exception as e:
                print(f"Error in {content_type} search: {e}")
            return None

        # If item_type is specified, search only that type
        if item_type in ['movie', 'tv']:
            results = search_content(item_type)
            return results[0] if results else None  # Return first match for single type search
        
        # If no item_type specified, search both types and return all results
        all_results = []
        
        movie_results = search_content('movie')
        if movie_results:
            all_results.extend(movie_results)
            
        tv_results = search_content('tv')
        if tv_results:
            all_results.extend(tv_results)
            
        return all_results if all_results else None    
    
    def fast_search(self, title, year = None, tmdb_id=None, original_language=None, item_type=None):
        """
        Fast search the TMDB API for movies or TV shows.

        Args:
            title (str): The title of the movie or TV show.
            year (int): The release year.
            tmdb_id (int): The TMDB ID of the movie or TV show.
            original_language (str, optional): The original language of the content. Defaults to None.
            item_type (str, optional): Type of content to search for ('movie', 'tv', or None for both). Defaults to None.

        Returns:
            dict or list: If item_type is specified, returns a dict with details of the found content.
                        If item_type is None, returns a list of all found movies and TV shows.
                        Returns None if nothing is found or an error occurred.
        """
        if item_type == "tv-series" or item_type == "tv-show":
            item_type = "tv"
            
        search_params = {
            "query": title,
            "include_adult": "false"
        }
        if year:
            search_params["year"] = year
            
        if original_language and False:
            search_params["with_original_language"] = original_language

        def search_content(content_type):
            url = f"{self.base_url}/search/{content_type}?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
            try:
                results = self.fetch_results(url)
                if results:
                    content_id = results[0]["id"]
                    result = self.safe_request(f"{self.base_url}/{content_type}/{content_id}")
                    return self.add_trailer(result, content_type) if result else None
            except Exception as e:
                print(f"Error in {content_type} search: {e}")
            return None

        # If item_type is specified, search only that type
        if item_type in ['movie', 'tv']:
            return search_content(item_type)
        
        # If no item_type specified, search both types and return all results
        result = {}
        
        movie_result = search_content('movie')
        if movie_result:
            result = movie_result
            # results.append(movie_result)
            
        tv_result = search_content('tv')
        if tv_result:
            result = tv_result
            # results.append(tv_result)
            
        # return results if results else None
        return result if result else None
    
    def fast_search1(self, title, year, tmdb_id=None, original_language=None, item_type=None):
        """
        Fast search the TMDB API for movies or TV shows.

        Args:
            title (str): The title of the movie or TV show.
            year (int): The release year.
            tmdb_id (int): The TMDB ID of the movie or TV show.
            original_language (str, optional): The original language of the content. Defaults to None.

        Returns:
            dict: Full details of the found movie or TV show, or None if not found or an error occurred.
        """
        # First, try to fetch the movie/TV show by TMDB ID
        if tmdb_id and False:
            movie_result = self.safe_request(f"{self.base_url}/movie/{tmdb_id}")
            if movie_result and (not original_language or movie_result.get('original_language') == original_language):
                return self.add_trailer(movie_result, 'movie')
            
            tv_result = self.safe_request(f"{self.base_url}/tv/{tmdb_id}")
            if tv_result and (not original_language or tv_result.get('original_language') == original_language):
                return self.add_trailer(tv_result, 'tv')

        # If TMDB ID doesn't exist or wasn't provided, search by title, year, and optionally original language
        search_params = {
            "query": title,
            "include_adult": "false"
        }
        if year:
            search_params["year"] = year
            
        if original_language and False:
            search_params["with_original_language"] = original_language

        # Search for movies
        movie_url = f"{self.base_url}/search/movie?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
        try:
            movie_results = self.fetch_results(movie_url)
            if original_language and False:
                movie_results = self.filter_by_language(movie_results, original_language)
            if movie_results:
                movie_id = movie_results[0]["id"]
                movie_result = self.safe_request(f"{self.base_url}/movie/{movie_id}")
                return self.add_trailer(movie_result, 'movie') if movie_result else None
        except Exception as e:
            print(f"Error in movie search: {e}")

        # If not found in movies, search for TV shows
        tv_url = f"{self.base_url}/search/tv?{'&'.join([f'{k}={v}' for k, v in search_params.items()])}"
        try:
            tv_results = self.fetch_results(tv_url)
            if original_language and False:
                tv_results = self.filter_by_language(tv_results, original_language)
            if tv_results:
                tv_id = tv_results[0]["id"]
                tv_result = self.safe_request(f"{self.base_url}/tv/{tv_id}")
                return self.add_trailer(tv_result, 'tv') if tv_result else None
        except Exception as e:
            print(f"Error in TV show search: {e}")

        # If no results found or an error occurred, return None
        return None
    
    def fast_search_many(self, search_list):
        """
        Perform fast search for multiple items concurrently.

        Args:
            search_list (list): List of dictionaries, each containing:
                                'name', 'year', 'type', 'tmdb_id', 'original_language'

        Returns:
            list: List of search results corresponding to the input list.
        """
        def update_items_type(items):
            type_mapping = {'m': 'movie', 'v': 'tv-series', 'c': 'cartoon', 'a': 'anime', 'd': 'documentary', 's': 'short-film', 't': 'tv'}
            try:
                for item in items:
                    if 'type' in item and item.get('type') in type_mapping:
                        item['type'] = type_mapping.get(item['type'], item['type'])
            except Exception as e:
                print(f"Error updating items type: {e}")
            return items
        
        #TODO for some reason, the movies that are coming from add to favorites, have abbreviated type!!
        # Update the item types in case they are abbreviated
        search_list = update_items_type(search_list)
        
        def search_item(item):
            result = self.fast_search(
                title=item['name'],
                year=item['year'],
                tmdb_id=item.get('tmdb_id', None),
                original_language=item.get('original_language', None),
                item_type=item.get('type', None)
            )
            # # Nasrin added this: we need to filter the result to only include the needed keys
            needed_keys =['id', 'title', 'name', 'overview', 'poster_path', 'backdrop_path', 
                          'release_date', 'first_air_date', 'vote_average', 'vote_count', 'popularity', 'video']
            if result:
                result = {k: v for k, v in result.items() if k in needed_keys}
                result['year'] = item['year']
                result['type'] = item.get('type', 'movie')
                if item.get('justification'):
                    result['justification'] = item['justification']
                if item.get('trailer_url'):
                    result['trailer_url'] = item['trailer_url']
            return result

        # results = []
        # for item in search_list:
        #     results.append(search_item(item))
        
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(search_item, search_list))

        return results
    
# Sample of fast search output:
"""
```json
{'adult': False,
 'backdrop_path': '/icmmSD4vTTDKOq2vvdulafOGw93.jpg',
 'belongs_to_collection': {'backdrop_path': '/bRm2DEgUiYciDw3myHuYFInD7la.jpg',
                           'id': 2344,
                           'name': 'The Matrix Collection',
                           'poster_path': '/bV9qTVHTVf0gkW0j7p7M0ILD4pG.jpg'},
 'budget': 63000000,
 'genres': [{'id': 28, 'name': 'Action'},
            {'id': 878, 'name': 'Science Fiction'}],
 'homepage': 'http://www.warnerbros.com/matrix',
 'id': 603,
 'imdb_id': 'tt0133093',
 'origin_country': ['US'],
 'original_language': 'en',
 'original_title': 'The Matrix',
 'overview': 'Set in the 22nd century, The Matrix tells the story of a '
             'computer hacker who joins a group of underground insurgents '
             'fighting the vast and powerful computers who now rule the earth.',
 'popularity': 120.684,
 'poster_path': '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg',
 'production_companies': [{'id': 79,
                           'logo_path': '/at4uYdwAAgNRKhZuuFX8ShKSybw.png',
                           'name': 'Village Roadshow Pictures',
                           'origin_country': 'US'},
                          {'id': 372,
                           'logo_path': None,
                           'name': 'Groucho II Film Partnership',
                           'origin_country': ''},
                          {'id': 1885,
                           'logo_path': '/xlvoOZr4s1PygosrwZyolIFe5xs.png',
                           'name': 'Silver Pictures',
                           'origin_country': 'US'},
                          {'id': 174,
                           'logo_path': '/zhD3hhtKB5qyv7ZeL4uLpNxgMVU.png',
                           'name': 'Warner Bros. Pictures',
                           'origin_country': 'US'}],
 'production_countries': [{'iso_3166_1': 'US',
                           'name': 'United States of America'}],
 'release_date': '1999-03-31',
 'revenue': 463517383,
 'runtime': 136,
 'spoken_languages': [{'english_name': 'English',
                       'iso_639_1': 'en',
                       'name': 'English'}],
 'status': 'Released',
 'tagline': 'The fight for the future begins.',
 'title': 'The Matrix',
 'trailer': 'https://www.youtube.com/watch?v=d0XTFAMmhrE',
 'video': False,
 'vote_average': 8.218,
 'vote_count': 25497}
```
"""

# def update_movie_response(movies):
#     key_mapping = {'n': 'name', 'y': 'year', 't': 'type', 'l': 'original_language'}
#     type_mapping = {'m': 'movie', 'v': 'tv-series', 'c': 'cartoon', 'a': 'anime', 'd': 'documentary', 's': 'short-film', 't': 'tv'}
#     try:
#         if type(movies) == str:
#             movies = json.loads(movies)
#     except:
#         pass
#     movies = [
#         {key_mapping.get(k, k): v for k, v in movie.items()} for movie in movies
#     ]
#     # for movie in movies:
#     #     movie['type'] = type_mapping.get(movie['type'], 'movie')
#     return movies


if __name__ == "__main__":
    tmdb = TMDBService()
    # res = tmdb.fast_fuzzy_search("Foundation", item_type='tv')
    # res = tmdb.fast_search1("Foundation", item_type='tv')
    # res =tmdb.search_tmdb_v2("Foundation", tmdb.genre_dict, max_results=20, year=None, include_trailer=True)
    
    # d = {"type":"movie_json","data":{"movies":[{"n":"How I Met Your Mother","y":2005,"l":"en","t":"tv-series","tmdb_id":"141","trailer_url":None},{"n":"Brooklyn Nine-Nine","y":2013,"l":"en","t":"tv-series","tmdb_id":"195","trailer_url":None}]},"additional_info":"Enjoy these fan-favorites! 🎉"}
    # resp = update_movie_response(d['data']['movies'])
    # res = tmdb.fast_search_many(resp)
    
    # print(res)