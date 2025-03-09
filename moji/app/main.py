import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_URI, DB_NAME, DEFAULT_SWIPE_PROFILE, TELEGRAM_BOT_TOKEN, MODELS, REDIS_URI
from moji.moji_assistant import MojiAssistant


# Example of checking the user
# user = self.db.users.find_one({
#             "email": email,
#             "is_test_user": True,
#             "user_token": {"$exists": True, "$ne": ""}
# })
# user.get('user_token'), user.get('user_id')

# I want to create a simple web application where users can enter their email. We will query our database to extract the user token, and then we can test our Moji Assistant app using that token. The user will enter their email, we will retrieve the token, and they will proceed to a second page, which is a simple chat application that allows them to communicate with Moji Assistant. You can refer to the example files we created to remind yourself how to work with Moji Assistant. I also created a folder named "app," and within that folder, I included the required files. Your task is to work on main.py. This will be a simple single HTML app that contains all the CSS and JS, along with one server backend in a single file to manage the communication. We support streaming, so the server will use streaming mode when working with the Moji systems. We will get the token and send it back using the streaming protocol, and on the client side, we will display the messages as they are received.