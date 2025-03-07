from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from pymongo import MongoClient
from assistant import MovieAssistant
from services.mojitoApis import MojitoAPIs
from assistant.tools import ALL_TOOLS, ALL_SCHEMAS
from typing import Dict, Optional
from pydantic import BaseModel
from typing import Any
import logging
from time import time
from config import DB_URI, DB_NAME, TELEGRAM_BOT_TOKEN, MODELS, REDIS_URI
from openai import OpenAI
from assistant.tools.swipe.service import SwipeGameService
from assistant.tools.swipe.models import Movie, UserProfile
from typing import List
import asyncio
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
LOGIN, CHATTING = range(2)

# Pydantic model for assistant payload (following your test_assistant.py)
class PromptParameters(BaseModel):
    id: str = "prompt-default"
    params: Dict[str, Any] = {}

class FormattedResponse(BaseModel):
    content: str

def format_movie_response(raw_response: str, user_question: Optional[str] = None) -> str:
    """
    Format a raw AI response into an engaging, markdown-formatted response for movie fans.
    
    Args:
        raw_response (str): The original response from the movie assistant
        user_question (Optional[str]): The original user question for context
    
    Returns:
        str: Formatted response in markdown
    """
    client = OpenAI()
    
    system_prompt = """You are a response formatter specializing in movie-related content.
    Your task is to use the JSON response from the AI and generate a human readable markdown to explain the 
    and share the extracted data or the status of requested action, based on the user query.
    
    Format the response using these Telegram-compatible markdown rules:
    - Use *text* for bold
    - Use _text_ for italics
    - Use `text` for inline code
    - Use ```text``` for code blocks
    - Use bullet points with - or * 
    
    Don't:
    - Don't use nested markdown (like *_text_*)
    - Don't use unsupported markdown features
    - Keep formatting simple and clean
    
    Guidelines:
    - Use appropriate movie-related emojis 🎬 🎭 🎪 🎟️ 
    - Format text using markdown for better readability
    - Keep the tone casual but informative
    - Use bold and italics for emphasis
    - Break up long paragraphs into digestible chunks
    - Maintain the original meaning and information
    
    Don't:
    - Add new facts or information not in the original response
    - Change any movie names, dates, or technical details
    - Make movie recommendations if not in the original response
    """
    
    # Prepare the context for the formatter
    format_prompt = f"""
    ## Original user query: 
    {user_question if user_question else 'Not provided'}
    
    ## JSON response to format:
    {raw_response}
    
    Please rewrite this response in a more engaging style following the guidelines.
    """
    
    try:
        completion =  client.beta.chat.completions.parse(
            model=MODELS['llm_what2know'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": format_prompt},
            ],
            response_format=FormattedResponse,
            temperature=0.5  # Add some creativity while maintaining coherence
        )
        
        formatted_response = completion.choices[0].message.parsed
        return formatted_response.content
    
    except Exception as e:
        # If formatting fails, return the original response with basic formatting
        logger.error(f"Error formatting response: {e}")
        return f"🎬 {raw_response}"

class MojitoBot:
    def __init__(self):
        """Initialize bot with database connection and user sessions"""
        self.client = MongoClient(DB_URI)
        self.db = self.client[DB_NAME]
        self.active_sessions: Dict[int, tuple[str, MovieAssistant]] = {}
        self.token = TELEGRAM_BOT_TOKEN
        self.swipe_service = SwipeGameService(
            sentiment_model_path='assistant/tools/docs/swipe/text_classifier_model.joblib',
            redis_url= REDIS_URI
        )
        self.active_swipe_sessions: Dict[int, List[Movie]] = {}
        # Initialize movies on startup
        self._initialize_swipe_service()
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    async def reset_user_session(self, telegram_id: int) -> None:
        """Helper method to reset user session and clear database telegram_id"""
        if telegram_id in self.active_sessions:
            try:
                _, assistant = self.active_sessions[telegram_id]
                assistant.close()
                del self.active_sessions[telegram_id]
                
                # Remove telegram_id from user document
                self.db.users.update_one(
                    {"telegram_id": telegram_id},
                    {"$unset": {"telegram_id": ""}}
                )
            except Exception as e:
                logger.error(f"Error in reset_user_session: {e}")
                raise

    
    async def initialize_user_session(self, telegram_id: int, user_data: dict) -> Optional[tuple[str, MovieAssistant]]:
        """Initialize a user session with the MovieAssistant with enhanced error handling"""
        try:
            payload = PromptParameters(
                id="mojito_assistant",
                params={
                    "action": "assistant",
                    "user_id": user_data['user_id'],
                    "user_token": user_data.get('user_token', ''),
                    "user_details": {
                        "first_name": user_data.get('first_name', ''),
                        "last_name": user_data.get('last_name', ''),
                        "email": user_data.get('email', '')
                    },
                    "user_language": "en-US",
                    "user_message": "",
                }
            )

            # Initialize MojitoAPIs client
            mojito_client = MojitoAPIs(user_data['user_id'], user_data.get('user_token', ''))
            
            try:
                # Attempt to get favorite lists - this will verify the token
                user_fav_lists = mojito_client.get_favorite_lists()
                payload.params.setdefault('user_extra_data', {})['favorite_lists'] = user_fav_lists
            except Exception as api_error:
                # If there's an authentication error, reset the session
                logger.error(f"Mojito API authentication failed: {api_error}")
                await self.reset_user_session(telegram_id)
                return None

            assistant = MovieAssistant(
                user_id=user_data['user_id'],
                user_token=user_data.get('user_token', ''),
                action="assistant",
                tools=ALL_TOOLS,
                schemas=ALL_SCHEMAS,
                payload=payload,
            )
            
            return (user_data['user_id'], assistant)
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            return None

    async def get_or_create_session(self, telegram_id: int, initiate_assistant : bool= True) -> Optional[tuple[str, MovieAssistant]]:
        """Get existing session or create new one if user is already registered"""
        if telegram_id in self.active_sessions:
            return self.active_sessions[telegram_id]
        
        # Check if user exists in database with telegram_id
        user = self.db.users.find_one({
            "telegram_id": telegram_id,
            "is_test_user": True,
            "user_token": {"$exists": True, "$ne": ""}
        })
        
        if user and initiate_assistant:
            session = await self.initialize_user_session(telegram_id, user)
            if session:
                self.active_sessions[telegram_id] = session
                return session
        
        return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Enhanced start command handler with better session validation"""
        telegram_id = update.effective_user.id
        
        # Try to get or create session
        session = await self.get_or_create_session(telegram_id)
        
        if session:
            user_id, assistant = session
            try:
                # Verify the session is still valid by testing the API
                mojito_client = MojitoAPIs(user_id, assistant.payload.params['user_token'])
                mojito_client.get_favorite_lists()  # Test API call
                
                await update.message.reply_text(
                    "Welcome back! 🎉\nYou're already connected to Mojito AI. How can I help you today?"
                )
                return CHATTING
            except Exception as e:
                # If API verification fails, reset session and start fresh
                logger.error(f"Session validation failed: {e}")
                await self.reset_user_session(telegram_id)
        
        await update.message.reply_text(
            "Welcome to Mojito AI! 🎬\n"
            "Please send me your email address to get started."
        )
        return LOGIN

    async def handle_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle email input and authenticate user"""
        email = update.message.text.strip().lower()
        telegram_id = update.effective_user.id
        
        # Find user with email and ensure user_token exists and is not empty
        user = self.db.users.find_one({
            "email": email,
            "is_test_user": True,
            "user_token": {"$exists": True, "$ne": ""}
        })
        
        if not user:
            await update.message.reply_text(
                "Sorry, I couldn't find an account with that email. "
                "Please check the email and try again, or contact support."
            )
            return LOGIN
        
        if not user.get('user_token') or not user.get('user_id'):
            await update.message.reply_text(
                "Sorry, there was an issue with your account. "
                "Please contact support for assistance."
            )
            return ConversationHandler.END
        
        try:
            # Update user document with telegram_id
            self.db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"telegram_id": telegram_id}}
            )
            
            # Initialize session
            session = await self.initialize_user_session(telegram_id, user)
            if not session:
                raise Exception("Failed to initialize session")
            
            self.active_sessions[telegram_id] = session
            
            await update.message.reply_text(
                f"Welcome {user.get('first_name', 'friend')}! 🎉\n"
                "You're now connected to Mojito AI. How can I help you today?"
            )
            return CHATTING
            
        except Exception as e:
            logger.error(f"Error in handle_email: {e}")
            await update.message.reply_text(
                "Sorry, there was an error setting up your session. "
                "Please try again later or contact support."
            )
            return ConversationHandler.END

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Enhanced message handler with session validation"""
        telegram_id = update.effective_user.id
        
        # Try to get or create session if it doesn't exist
        if telegram_id not in self.active_sessions:
            session = await self.get_or_create_session(telegram_id)
            if not session:
                await update.message.reply_text(
                    "Seems like your session has expired. Please use /start to log in again."
                )
                return ConversationHandler.END
        
        try:
            user_id, assistant = self.active_sessions[telegram_id]
            
            # Verify session is still valid
            try:
                mojito_client = MojitoAPIs(user_id, assistant.payload.params['user_token'])
                mojito_client.get_favorite_lists()  # Test API call
            except Exception as api_error:
                logger.error(f"API validation failed during message handling: {api_error}")
                await self.reset_user_session(telegram_id)
                await update.message.reply_text(
                    "Your session has expired. Please use /start to log in again."
                )
                return ConversationHandler.END
            
            await update.message.reply_text("Working on it... 🕵️‍♂️")
            
            # Add start time
            start_time = time()
            response = assistant.chat(update.message.text)
            asyncio.create_task(asyncio.to_thread(assistant.add_memory, update.message.text, response))
            
            end_time = time()
            formatted_response = format_movie_response(
                raw_response=response,
                user_question=update.message.text
            )
            
            await update.message.reply_text(
                formatted_response + f"\n\nProcessing time: {end_time - start_time:.2f} seconds",
                parse_mode=ParseMode.MARKDOWN
            )
            
            return CHATTING
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            await update.message.reply_text(
                "Sorry, there was an error processing your message. "
                "Please try again or use /reset if the problem persists."
            )

    async def fallback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages from users outside the conversation handler"""
        telegram_id = update.effective_user.id
        
        # Check if user exists and try to restore session
        session = await self.get_or_create_session(telegram_id)
        
        if session:
            # Process message as normal
            try:
                user_id, assistant = session
                
                
                await update.message.reply_text("Working on it... 🕵️‍♂️")
                
                start_time = time()
                response = assistant.chat(update.message.text)
                asyncio.create_task(asyncio.to_thread(assistant.add_memory, update.message.text, response))
                end_time = time()
                
                # formatted_response = response
                formatted_response = format_movie_response(
                    raw_response=response,
                    user_question=update.message.text
                )
                
                await update.message.reply_text(
                    formatted_response + f"\n\nProcessing time: {end_time - start_time:.2f} seconds",
                    parse_mode=ParseMode.MARKDOWN
                )
                
            except Exception as e:
                logger.error(f"Error in fallback handler: {e}")
                await update.message.reply_text(
                    "Sorry, there was an error processing your message. "
                    "Please try again or use /reset if the problem persists."
                )
    
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Reset command handler - clears session and starts over"""
        telegram_id = update.effective_user.id
        
        if telegram_id in self.active_sessions:
            try:
                _, assistant = self.active_sessions[telegram_id]
                assistant.close()
                del self.active_sessions[telegram_id]
                
                # Remove telegram_id from user document
                self.db.users.update_one(
                    {"telegram_id": telegram_id},
                    {"$unset": {"telegram_id": ""}}
                )
                
                await update.message.reply_text(
                    "Session reset successfully! Use /start to log in again."
                )
            except Exception as e:
                logger.error(f"Error in reset: {e}")
                await update.message.reply_text(
                    "There was an error resetting your session. Please try again."
                )
        else:
            await update.message.reply_text(
                "No active session found. Use /start to log in."
            )
        
        return ConversationHandler.END

    def _initialize_swipe_service(self):
        """Initialize the swipe service with movies"""
        try:
            import pandas as pd
            # Load movies from MovieLens dataset
            movies_df = pd.read_csv(".data/ml-25m/movies.csv")
            ratings_df = pd.read_csv(".data/ml-25m/ratings.csv")
            
            # Calculate statistics
            movie_stats = ratings_df.groupby('movieId').agg({
                'rating': ['count', 'mean']
            }).reset_index()
            movie_stats.columns = ['movieId', 'vote_count', 'vote_average']
            
            # Calculate popularity
            max_votes = movie_stats['vote_count'].max()
            movie_stats['popularity'] = (
                movie_stats['vote_count'] / max_votes * 0.7 +
                movie_stats['vote_average'] / 5 * 0.3
            ) * 100
            
            # Process genres
            movies_df['genre'] = movies_df['genres'].str.split('|')
            
            # Create Movie objects
            movies = []
            for _, row in movies_df.merge(movie_stats, on='movieId').iterrows():
                movies.append(Movie(
                    id=str(row['movieId']),
                    title=row['title'].split(" (")[0],
                    genre=row['genre'],
                    popularity=float(row['popularity']),
                    vote_average=float(row['vote_average']),
                    vote_count=int(row['vote_count']),
                    type="movie"
                ))
            
            # Load movies into service
            # self.swipe_service.load_movies(movies)
            logger.info("SwipeGame service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing SwipeGame service: {e}")
            raise

    async def get_user_swipe_profile(self, telegram_id: int) -> Optional[UserProfile]:
        """Get or create user's swipe profile"""
        user = self.db.users.find_one({"telegram_id": telegram_id})
        if not user:
            return None
            
        swipe_profile = user.get('swipe_user_profile')
        if not swipe_profile:
            swipe_profile = {
                'id': user['user_id'],
                'favorite_genre': [],
                'binary_likes': [],
                'binary_dislikes': [],
                'swipe_ratings': [],
                'movie_lists': {},
                'positive_movie_lists': {},
                'negative_movie_lists': {},
                'recently_viewed': [],
                'suggested_matches': []
            }
            self.db.users.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"swipe_user_profile": swipe_profile}}
            )
            
        return UserProfile(**swipe_profile)

    async def format_movies_message(self, movies: List[Movie]) -> str:
        """Format movies list for Telegram message"""
        message = "🎬 *Rate these movies (1-5, or 0 if haven't seen):*\n\n"
        for i, movie in enumerate(movies, 1):
            genres = ", ".join(movie.genre)
            message += f"{i}. *{movie.title}*\n"
            message += f"   Genres: _{genres}_\n"
            message += f"   Rating: {movie.vote_average:.1f}/5 ({movie.vote_count:,} votes)\n\n"
        
        message += "\n*Reply with ratings (one per line):*\n"
        message += "Example:\n```\n3\n5\n0\n4\n```"
        return message

    async def handle_swipe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /swipe command"""
        telegram_id = update.effective_user.id
        
        # Check if user is logged in
        session = await self.get_or_create_session(telegram_id, initiate_assistant=False)
        if not session:
            await update.message.reply_text(
                "Please use /start to log in first!"
            )
            return
        
        try:
            # Get user profile
            user_profile = await self.get_user_swipe_profile(telegram_id)
            if not user_profile:
                await update.message.reply_text(
                    "Sorry, I couldn't find your profile. Please use /start to set up your account."
                )
                return
            
            # Get movies for swiping
            movies = self.swipe_service.select_movies_for_swipe(user_profile, n_movies=5)
            
            # Store movies in active session
            self.active_swipe_sessions[telegram_id] = movies
            
            # Send formatted message
            message = await self.format_movies_message(movies)
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as e:
            logger.error(f"Error in swipe command: {e}")
            await update.message.reply_text(
                "Sorry, there was an error getting movie suggestions. Please try again later."
            )

    async def handle_swipe_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ratings response for swipe session"""
        telegram_id = update.effective_user.id
        
        # Check if there's an active swipe session
        if telegram_id not in self.active_swipe_sessions:
            await update.message.reply_text(
                "No active swipe session. Use /swipe to get movie suggestions first!"
            )
            return
        
        try:
            # Parse ratings
            ratings_text = update.message.text.strip().split('\n')
            movies = self.active_swipe_sessions[telegram_id]
            
            if len(ratings_text) != len(movies):
                await update.message.reply_text(
                    f"Please provide exactly {len(movies)} ratings, one per line."
                )
                return
            
            # Convert ratings to numbers
            try:
                ratings = [int(r.strip()) for r in ratings_text]
                if not all(0 <= r <= 5 for r in ratings):
                    raise ValueError("Ratings must be between 0 and 5")
            except ValueError:
                await update.message.reply_text(
                    "Invalid ratings. Please use numbers between 0 and 5."
                )
                return
            
            # Create swipe results
            swipe_results = {
                movie.id: rating
                for movie, rating in zip(movies, ratings)
                if rating > 0  # Only include non-zero ratings
            }
            
            # Get user profile
            user_profile = await self.get_user_swipe_profile(telegram_id)
            if not user_profile:
                await update.message.reply_text(
                    "Sorry, I couldn't find your profile. Please use /start to set up your account."
                )
                return
            
            # Update user profile with ratings
            self.swipe_service.update_user_profile(user_profile, swipe_results)
            
            # Save updated profile to database
            self.db.users.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"swipe_user_profile": user_profile.dict()}}
            )
            
            # Get all users for matching
            all_users = []
            users = list(self.db.users.find({"telegram_id": {"$ne": telegram_id}}))
            for user in users:
                if 'swipe_user_profile' in user:
                    all_users.append(UserProfile(**user['swipe_user_profile']))
            
            # Find matches
            matches = self.swipe_service.find_matches(user_profile, all_users)
            
            # Format match results
            match_message = "🎯 *Based on your ratings, here are your matches:*\n\n"
            for user_id, score in matches[:3]:  # Show top 3 matches
                match_user = self.db.users.find_one({"user_id": user_id})
                if match_user:
                    name = match_user.get('user_details', {}).get('first_name', 'Anonymous')
                    match_message += f"👤 *{name}* - {score*100:.1f}% match\n"
            
            # Clear active session
            del self.active_swipe_sessions[telegram_id]
            
            await update.message.reply_text(
                match_message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as e:
            logger.error(f"Error processing swipe response: {e}")
            await update.message.reply_text(
                "Sorry, there was an error processing your ratings. Please try again."
            )
    
    
    
    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.token).build()

        # Create conversation handler for new users
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_email)],
                CHATTING: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND & ~filters.REPLY,  # Add ~filters.REPLY here
                        self.handle_message
                    )
                ]
            },
            fallbacks=[CommandHandler('reset', self.reset)],
            name="main_conversation",
            persistent=False
        )

        # Add swipe command handler first
        application.add_handler(CommandHandler('swipe', self.handle_swipe_command))
        
        # Add swipe response handler BEFORE the fallback handler
        swipe_handler = MessageHandler(
            filters.TEXT & filters.REPLY & ~filters.COMMAND,
            self.handle_swipe_response
        )
        application.add_handler(swipe_handler)

        # Add handlers
        application.add_handler(conv_handler)
        
        # Add fallback handler for messages outside conversation
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.REPLY,  # Add ~filters.REPLY here
                self.fallback_handler
            )
        )

        # Add reset command handler outside conversation
        application.add_handler(CommandHandler('reset', self.reset))

        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        bot = MojitoBot()
        logger.info("Starting bot...")
        bot.run()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")