from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from .models import Movie, UserProfile, SwipeRating
from scipy.spatial.distance import cosine
import numpy as np
import threading
import random
import redis
import json
from joblib import load


class SwipeGameService:
    def __init__(self, sentiment_model_path: str, redis_url: str):
        """Initialize service with Redis and minimal memory footprint"""
        self._redis = redis.from_url(redis_url)
        self._genre_index: Dict[str, int] = {}
        self._movie_metadata: Dict[str, tuple] = {}  # id -> (popularity, vote_avg, vote_count)
        self._lock = threading.Lock()
        self._vector_cache_ttl = 300  # 5 minutes
        # self._model = self._load_model(sentiment_model_path)
        self._executor = ThreadPoolExecutor(max_workers=32)
        
        # Load genre index from Redis
        self._load_genre_index()
        # Load movie metadata into memory
        self._load_movie_metadata()
        
        # Cleanup stale data on initialization
        self.cleanup_stale_data()

    # def _load_model(self, path: str):
    #     """Load the sentiment analysis model"""
    #     return load(path)
    
    def _check_redis_connection(self):
        """Verify Redis connection is healthy"""
        try:
            self._redis.ping()
            return True
        except redis.RedisError:
            return False
        
    def cleanup_stale_data(self):
        """Remove expired user vectors"""
        try:
            for key in self._redis.scan_iter("user_vector:*"):
                if not self._redis.ttl(key):
                    self._redis.delete(key)
        except redis.RedisError as e:
            print(f"Error cleaning stale data: {e}")

    def _prefilter_movies(self, movies: List[Movie]) -> List[Movie]:
        """Filter out low-quality movies before processing"""
        return [
            movie for movie in movies
            if (movie.vote_count >= 1000 and
                movie.vote_average >= 1.5 and
                movie.popularity >= 5.0)
        ]

    def _check_and_reload(self):
        """Attempt to reload data if Redis connection was lost"""
        if not self._movie_metadata or not self._genre_index:
            self._load_genre_index()
            self._load_movie_metadata()
            
    @lru_cache(maxsize=1000)
    def _calculate_movie_score(self, movie_id: str) -> float:
        """Calculate movie score using metadata from memory"""
        if movie_id not in self._movie_metadata:
            return 0.0
            
        popularity, vote_avg, vote_count = self._movie_metadata[movie_id]
        
        return (0.4 * (popularity / 100) +
                0.4 * (vote_avg / 10) +
                0.2 * (min(vote_count, 10000) / 10000))

    def _load_genre_index(self):
        """Load genre index from Redis"""
        genre_index = self._redis.get("genre_index")
        if not genre_index:
            raise RuntimeError("Genre index not found in Redis. Please run the data loader first.")
        self._genre_index = json.loads(genre_index)

    def _load_movie_metadata(self):
        """Load minimal movie metadata into memory with pipelining"""
        self._movie_metadata = {}
        pipe = self._redis.pipeline()
        movie_keys = []
        
        # Queue all gets
        for key in self._redis.scan_iter("movie:*"):
            movie_id = key.decode().split(':')[1]
            movie_keys.append(movie_id)
            pipe.hget(key, "data")
        
        # Execute in one batch
        results = pipe.execute()
        
        # Process results
        for movie_id, movie_data in zip(movie_keys, results):
            if movie_data:
                movie = json.loads(movie_data)
                self._movie_metadata[movie_id] = (
                    movie['popularity'],
                    movie['vote_average'],
                    movie['vote_count']
                )

    def _get_movie(self, movie_id: str) -> Optional[Movie]:
        """Retrieve movie data from Redis with error handling"""
        try:
            movie_data = self._redis.hget(f"movie:{movie_id}", "data")
            if not movie_data:
                return None
            return Movie(**json.loads(movie_data))
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Error retrieving movie {movie_id}: {e}")
            return None

    def _get_user_vector(self, user: UserProfile) -> np.ndarray:
        try:
            cache_key = f"user_vector:{user.id}"
            cached_vector = self._redis.get(cache_key)
            
            if cached_vector:
                vector = np.frombuffer(cached_vector)
                return vector.reshape((len(self._genre_index),))
                
            vector = self._create_user_vector(user)
            self._redis.setex(
                cache_key,
                self._vector_cache_ttl,
                vector.tobytes()
            )
            return vector
        except redis.RedisError as e:
            print(f"Redis error for user {user.id}: {e}")
            return self._create_user_vector(user)

    def _create_user_vector(self, user: UserProfile) -> np.ndarray:
        """Create a vector representation of user's genre preferences"""
        genre_vec = np.zeros(len(self._genre_index))
        
        # Process favorite genres
        for genre in user.favorite_genre:
            if genre in self._genre_index:
                genre_vec[self._genre_index[genre]] = 1
        
        # Process liked movies' genres
        for movie_id in user.binary_likes:
            genres = self._redis.smembers(f"movie_genres:{movie_id}")
            for genre in genres:
                genre = genre.decode()
                if genre in self._genre_index:
                    genre_vec[self._genre_index[genre]] += 0.5
        
        # Normalize the vector
        if np.sum(genre_vec) > 0:
            genre_vec = genre_vec / np.sum(genre_vec)
            
        return genre_vec

    def select_movies_for_swipe(
        self,
        user_profile: UserProfile,
        n_movies: int = 10,
        min_vote_count: int = 1000,
        min_popularity: float = 10.0
    ) -> List[Movie]:
        """Select movies for the swipe game using Redis-based filtering"""
        if not self._check_redis_connection():
            raise RuntimeError("Lost connection to Redis")
        
        # Get seen movies
        seen_movies = set(
            user_profile.binary_likes +
            user_profile.binary_dislikes +
            [r.movie_id for r in user_profile.swipe_ratings] +
            list(sum(user_profile.movie_lists.values(), [])) +
            user_profile.recently_viewed
        )
        
        # Get qualified movies using metadata
        qualified_movies = [
            movie_id for movie_id, (pop, vote_avg, vote_count) 
            in self._movie_metadata.items()
            if (movie_id not in seen_movies and
                vote_count >= min_vote_count and
                pop >= min_popularity)
        ]
        
        if not qualified_movies:
            qualified_movies = [
                movie_id for movie_id, (pop, vote_avg, vote_count)
                in self._movie_metadata.items()
                if (movie_id not in seen_movies and
                    vote_count >= min_vote_count // 2 and
                    pop >= min_popularity / 2)
            ]
        
        # Sort by score
        sorted_movies = sorted(
            qualified_movies,
            key=self._calculate_movie_score,
            reverse=True
        )
        
        # Split by genre preference
        user_favorite_genres = set(user_profile.favorite_genre)
        favorite_genre_movies = []
        other_movies = []
        
        for movie_id in sorted_movies:
            movie_genres = {
                g.decode() for g in 
                self._redis.smembers(f"movie_genres:{movie_id}")
            }
            if movie_genres & user_favorite_genres:
                favorite_genre_movies.append(movie_id)
            else:
                other_movies.append(movie_id)
        
        # Select movies with genre balance
        selected_ids = []
        genre_quota = n_movies // 2
        
        selected_ids.extend(favorite_genre_movies[:genre_quota])
        selected_ids.extend(other_movies[:n_movies - len(selected_ids)])
        
        # Get full movie objects for selected IDs
        return [
            self._get_movie(movie_id)
            for movie_id in selected_ids
            if movie_id
        ]

    def find_matches(
        self,
        target_user: UserProfile,
        all_users: List[UserProfile],
        n_matches: int = 5
    ) -> List[Tuple[str, float]]:
        """Find matching users based on genre preferences"""
        if not self._check_redis_connection():
            raise RuntimeError("Lost connection to Redis")
        
        target_vector = self._get_user_vector(target_user)
        
        def process_user(user):
            if user.id in target_user.suggested_matches or user.id == target_user.id:
                return (user.id, -1.0)
            user_vector = self._get_user_vector(user)
            similarity = 1 - cosine(target_vector, user_vector)
            return (user.id, similarity)
        
        # Process users in parallel
        futures = [self._executor.submit(process_user, user) for user in all_users]
        matches = [result for future in futures if (result := future.result()) is not None]
        
        # Handle no matches case
        if not matches:
            matches = [
                (user.id, random.random())
                for user in random.sample(all_users, min(n_matches, len(all_users)))
                if user.id not in target_user.suggested_matches
            ]
            
        if not matches or len(matches) < n_matches:
            # Randome fallback
            matches.extend([
                (user.id, random.random())
                for user in random.sample(all_users, n_matches - len(matches))
                if user.id not in target_user.suggested_matches
            ])
        
        return sorted(matches, key=lambda x: x[1], reverse=True)[:n_matches]

    def update_user_profile(
        self,
        user: UserProfile,
        swipe_results: Optional[Dict[str, int]] = None,
        suggested_matches: Optional[List[str]] = None
    ):
        """Update user profile and invalidate cache"""
        if swipe_results:
            for movie_id, rating in swipe_results.items():
                user.swipe_ratings.append(
                    SwipeRating(
                        movie_id=movie_id,
                        rating=rating,
                        timestamp=datetime.now()
                    )
                )
                if rating > 0:
                    user.binary_likes.append(movie_id)
                elif rating < 0:
                    user.binary_dislikes.append(movie_id)
        
        if suggested_matches:
            user.suggested_matches.extend(suggested_matches)
            
        # Invalidate user vector cache
        self._redis.delete(f"user_vector:{user.id}")