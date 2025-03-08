import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)


CONFIG_MODE = os.environ.get("CONFIG_MODE", "development")

API_TOKEN = os.environ.get("API_TOKEN", "")

DB_URI = os.environ.get("DB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "mojitoAssistant")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
PORT = int(os.environ.get("PORT", "8000"))
HOST = "0.0.0.0"
RELOAD = os.environ.get('RELOAD', 'False').lower() == 'true'

REDIS_URI = "redis://localhost:6379"

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT_PATH, "data")

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPEN_AI_MODEL = "gpt-4o-mini"
# OPEN_AI_MODEL = "gpt-4o"

MODELS = {
    "llm_what2know": "gpt-4o-mini",
    "llm_what2watch": "gpt-4o-mini",
    "openai_4o": "gpt-4o",
    "openai_4o_mini": "gpt-4o-mini",
    # "llm_what2know": "gpt-4o",
    # "llm_what2watch": "gpt-4o",
    # "openai_4o_mini": "gpt-4o",
}

TELEGRAM = {
    "TOKEN": os.environ.get('BOT_TOKEN', ''),
    "BUGS_GROUP": int(os.environ.get('BUGS_GROUP', '0'))
}

# EXTRACTION_API_KEY = os.environ['GROQ_API_KEY']
EXTRACTION_API_KEY = OPENAI_API_KEY
QUERY_API_KEY = OPENAI_API_KEY

TMDB_ACCESS_TOKEN = os.environ.get('TMDB_ACCESS_TOKEN', '')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
GOOGLE_CSE_ID = os.environ.get('GOOGLE_CSE_ID', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', 'your_api_key')

CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY', 'your_api_key')

MOVIEGLU_API_KEY = os.environ.get('MOVIEGLU_API_KEY', '')
MOVIEGLU_AUTH_KEY = MOVIEGLU_AUTH = os.environ.get('MOVIEGLU_AUTH', '')
MOVIEGLU_CLIENT_ID = "ALEP"

GEOCODING_API_KEY=os.environ.get('GEOCODING_API_KEY', '')

TOP_PICKS_DAYS = 30

DEFAULT_SWIPE_PROFILE = {
    "id": "",  # This will be set to the user's ID in the update operation
    "favorite_genre": ["Action", "Adventure", "Sci-Fi", "Comedy"],
    "movie_lists": {"Favorites": [], "Top5": []},
    "positive_movie_lists": {},
    "negative_movie_lists": {},
    "binary_likes": [],
    "binary_dislikes": [],
    "recently_viewed": [],
    "swipe_ratings": [],
    "suggested_matches": [],
    "role": "user"
}

MOJITO_DB = {
    "host": os.environ.get("MOJITO_DB_HOST", ""),
    "port": int(os.environ.get("MOJITO_DB_PORT", "0")),
    "user": os.environ.get("MOJITO_DB_USER", ""),
    "password": os.environ.get("MOJITO_DB_PWD", ""),
    "name": os.environ.get("MOJITO_DB_NAME", ""),
}

ALWAYS_CREATE_ASSISTANT = False
ALWAYS_CREATE_NEW_THREAD = False

TELEGRAM_BOT_TOKEN=os.environ.get('TELEGRAM_BOT_TOKEN', '')


REDIS_CONFIG = {
    'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'max_memory': '2gb',
    'max_memory_policy': 'allkeys-lru',
    'config_file': os.path.join(ROOT_PATH, 'redis.conf')
}