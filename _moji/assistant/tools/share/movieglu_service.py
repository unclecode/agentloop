from typing import Optional, List, Dict, Union
from datetime import datetime
from pydantic import BaseModel, field_validator 
import requests


class AgeRating(BaseModel):
    rating: str
    age_rating_image: str
    age_advisory: Optional[str]


class FilmImage(BaseModel):
    film_image: str
    width: int
    height: int


class ImageDetail(BaseModel):
    image_orientation: str
    region: Optional[str] = None
    medium: FilmImage


class Images(BaseModel):
    # poster: Optional[Dict[str, ImageDetail]] = {}
    # still: Optional[Dict[str, ImageDetail]] = {}
    poster: Optional[Union[Dict[str, ImageDetail], List]] = None
    still: Optional[Union[Dict[str, ImageDetail], List]] = None

    @field_validator('poster', 'still')
    def handle_empty_images(cls, v):
        return v if v else {}


class Film(BaseModel):
    film_id: int
    imdb_id: int
    imdb_title_id: str
    film_name: str
    other_titles: Optional[Dict[str, str]]
    release_dates: Optional[List[Dict[str, str]]] = None
    age_rating: List[AgeRating]
    film_trailer: Optional[str] = None
    synopsis_long: Optional[str] = None
    images: Optional[Images] = None


class FilmsNowShowingResponse(BaseModel):
    films: List[Film]


class Showtime(BaseModel):
    start_time: str
    end_time: str


class ShowingFormat(BaseModel):
    film_id: int
    film_name: str
    times: List[Showtime]


class Cinema(BaseModel):
    cinema_id: int
    cinema_name: str
    distance: float
    logo_url: Optional[str]
    showings: Dict[str, ShowingFormat]


class FilmShowTimesResponse(BaseModel):
    film: Film
    cinemas: List[Cinema]


class MovieGluService:
    def __init__(self, api_key: str, client: str, authorization: str, territory: str, api_version: str = "v200", geolocation="48.1351;11.5820"):
        self.base_url = "https://api-gate2.movieglu.com"
        self.headers = {
            "client": client,
            "x-api-key": api_key,
            "authorization": authorization,
            "territory": territory,
            "api-version": api_version,
            "device-datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "geolocation": geolocation
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_films_now_showing(self, n: int = 10) -> FilmsNowShowingResponse:
        """
        Fetch films currently showing.

        :param n: Number of films to fetch (default 10)
        :return: FilmsNowShowingResponse object
        """
        params = {"n": n}
        data = self._make_request("filmsNowShowing/", params)
        # exclude the ones without imdb_id and filmd_id
        data["films"] = [film for film in data["films"] if film.get("imdb_id") and film.get("film_id")]
        return FilmsNowShowingResponse(films=data["films"])

    def get_film_showtimes(self, film_name: str, date: Optional[str] = None, n: int = 10) -> Optional[FilmShowTimesResponse]:
        """
        Fetch showtimes for a specific film.

        :param film_name: Name of the film to search for
        :param date: Date for which to fetch showtimes (default is today)
        :param n: Number of cinemas to fetch (default 10)
        :return: FilmShowTimesResponse object if film is found, None otherwise
        """
        films = self.get_films_now_showing(n=25).films  # Fetch more films to increase chances of finding the target
        target_film = next((film for film in films if film_name.lower() in film.film_name.lower()), None)

        if not target_film:
            print(f"Film '{film_name}' not found in currently showing films.")
            return None

        params = {
            "film_id": target_film.film_id,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "n": n
        }
        data = self._make_request("filmShowTimes/", params)
        return FilmShowTimesResponse(**data)
