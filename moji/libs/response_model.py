from typing import List, Union, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ResponseTypeEnum(str, Enum):
    TEXT = 'text_response'
    MOVIE_JSON = 'movie_json'
    LIST = 'list_json'
    MOVIE_INFO = 'movie_info'  # Added new type
    TRAILER = 'trailer_json'  # Added new type


class MovieItem(BaseModel):
    n: str = Field(description="Name of the movie or TV series")
    y: int = Field(description="Year of release")
    l: Optional[str] = Field(description="Language of the movie or TV series")
    t: str = Field(description="Type: 'm' for movie, 'v' for TV series")
    tmdb_id: str = Field(description="TMDB ID of the movie or TV series")
    trailer_url: Optional[str] = Field(description="URL of the movie or TV series trailer")

    class Config:
        extra = 'forbid'

class TextData(BaseModel):
    content: str = Field(description="Detailed text response")

    class Config:
        extra = 'forbid'

class TextResponseData(BaseModel):
    content: str = Field(description="Detailed text response")
    relevant_docs: Optional[List[str]] = Field(description="Optional list of relevant documents")
    
    class Config:
        extra = 'forbid'

class MoviesData(BaseModel):
    movies: List[MovieItem] = Field(description="List of movie or TV series items")
    explanation: Optional[str] = Field(description="Short explanation of the suggestions, in case status is False, explain why couldn't make suggestions")
    status: bool = Field(description="Status of the suggestions (True if suggestions are made, False if not)")

    class Config:
        extra = 'forbid'

class MovieTrailerData(BaseModel):
    trailer_url: str = Field(description="URL of the movie or TV series trailer")
    movie_title: str = Field(description="Title of the movie or TV series")
    release_date: str = Field(description="Release date of the movie or TV series")
    overview: str = Field(description="Overview of the movie or TV series")

    class Config:
        extra = 'forbid'

# To generate answer for movie-related questions
class MovieInfoData(BaseModel):
    question: str = Field(description="The original question asked by the user")
    answer: str = Field(description="The detailed answer to the movie-related question")
    sources: Optional[List[str]] = Field(description="Optional list of sources for the information")
    related_movies: Optional[List[MovieItem]] = Field(description="Optional list of movies mentioned in the answer")

    class Config:
        extra = 'forbid'


class ListData(BaseModel):
    list_id: str = Field(description="Unique ID of the updated list/collection or newly created collection")
    response: str = Field(description="Brief description of the action taken")

    class Config:
        extra = 'forbid'

# For returning list/collection information that has been modified
class ListInfoData(BaseModel):
    list_id: str = Field(description="Unique ID of the list/collection")
    name: str = Field(description="Name of the list/collection")

    class Config:
        extra = 'forbid'

class ModifiedListData(BaseModel):
    items: List[ListInfoData] = Field(description="List of items to be added or removed from the list/collection")
    
    class Config:
        extra = 'forbid'

class Talk2MeLLMResponse(BaseModel):
    type: Literal['movie_json', 'trailer_json', 'movie_info', 'text_response'] = Field(description="""Type of response: 
        'trailer_json': Response for tool `get_movie_trailer` containing trailer URL and movie details,
        'movie_json': Response `what2watch` and `get_favorite_list_items` or any tools that response contains list of movies details in JSON format (excluding trailers requests),
        'movie_info': Response for `answer_movie_question` and tools when the response contains information answering a movie-related question,
        'text_response': When the tool response is none of other types and it is a string message for the user.
        """
    )
    data: Union[MoviesData, MovieTrailerData, MovieInfoData, TextResponseData] = Field(
        description="""Response data, structure depends on type: 
        trailer_json: MovieTrailerData,
        movie_json: MoviesData,
        movie_info: MovieInfoData,
        text_response: TextResponseData
        """
    )
    class Config:
        extra = 'forbid'