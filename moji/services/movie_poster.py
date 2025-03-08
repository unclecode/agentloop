import requests
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID


def get_movie_poster(movie_name, db=None):
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': f'{movie_name} movie poster',
        'cx': GOOGLE_CSE_ID,
        'key': GOOGLE_API_KEY,
        'searchType': 'image',
        'num': 1
    }
    response = requests.get(search_url, params=params)
    search_results = response.json()

    if 'items' in search_results:
        return search_results['items'][0]['link']
    else:
        return None


# if __name__ == "__main__":
#     movie_name = "Inception"
#     movie_name = "Goodbye"
#     poster_url = get_movie_poster(movie_name)
#     print(f'Poster URL for {movie_name}: {poster_url}')
