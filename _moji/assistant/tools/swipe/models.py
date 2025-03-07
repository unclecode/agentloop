from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from typing import Union
from datetime import datetime


class Movie(BaseModel):
    # id: int
    id: str
    title: str
    # genre: str
    genre: List[str]
    # release_year: int
    popularity: float
    vote_average: float
    vote_count: int
    type: str = "movie"

class SwipeRating(BaseModel):
    movie_id: str
    # rating: int = Field(..., ge=-5, le=5)  # -5 to 5
    rating: Union[int, float] = Field(..., ge=-5, le=5)  # -5 to 5
    timestamp: datetime

# i need these fields to select the best movies for the user
class UserProfile(BaseModel):
    id: str
    favorite_genre: List[str]
    movie_lists: Optional[Dict[str, List[str]]] = {}
    positive_movie_lists: Dict[str, List[str]] = {}
    negative_movie_lists: Dict[str, List[str]] = {}
    binary_likes: Optional[List[str]] = []
    binary_dislikes: Optional[List[str]] = []
    recently_viewed: Optional[List[str]] = []
    swipe_ratings: Optional[List[SwipeRating]] = []
    suggested_matches: Optional[List[str]] = []
    role: Optional[str] = "user"
    # name: str = ""
    
    @validator('movie_lists', 'positive_movie_lists', 'negative_movie_lists', pre=True, each_item=True)
    def check_none_in_dict(cls, v):
        if v is None:
            return []
        return v

    @validator('binary_likes', 'binary_dislikes', 'recently_viewed', 'swipe_ratings', 'suggested_matches', pre=True)
    def check_none_in_list(cls, v):
        if v is None:
            return []
        return v

class IDManager:
    def __init__(self, movies: List[Movie]):
        self.id_to_movie: Dict[int, Movie] = {movie.id: movie for movie in movies}
        self.movie_to_id: Dict[str, int] = {movie.title: movie.id for movie in movies}

    def get_movie(self, movie_id: int) -> Movie:
        return self.id_to_movie.get(movie_id)

    def get_id(self, movie_title: str) -> int:
        return self.movie_to_id.get(movie_title)

    def add_movie(self, movie: Movie):
        self.id_to_movie[movie.id] = movie
        self.movie_to_id[movie.title] = movie.id

    def remove_movie(self, movie_id: int):
        movie = self.id_to_movie.pop(movie_id, None)
        if movie:
            self.movie_to_id.pop(movie.title, None)

    def update_movie(self, movie: Movie):
        old_movie = self.id_to_movie.get(movie.id)
        if old_movie:
            self.movie_to_id.pop(old_movie.title, None)
        self.id_to_movie[movie.id] = movie
        self.movie_to_id[movie.title] = movie.id

    def get_all_movies(self) -> List[Movie]:
        return list(self.id_to_movie.values())

    def get_all_ids(self) -> List[int]:
        return list(self.id_to_movie.keys())

    @staticmethod
    def load(movies: List[Movie]) -> 'IDManager':
        return IDManager(movies)
