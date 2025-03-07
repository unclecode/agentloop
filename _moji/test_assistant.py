# from libs.MojiAssistant.assistantv2 import MovieAssistant
# from mojito_tools import ALL_TOOLS, ALL_SCHEMAS

from assistant import MovieAssistant
from assistant.tools import ALL_TOOLS, ALL_SCHEMAS
from assistant.tools.movie_suggestions import what2watch



from pydantic import BaseModel
from typing import Dict, Any
import pprint

USER_ID = '9f5bfa4e-579e-4702-aa97-21c66c29e663'
USER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiOWY1YmZhNGUtNTc5ZS00NzAyLWFhOTctMjFjNjZjMjllNjYzIiwidXNlcl9yb2xlIjoidXNlciIsImlhdCI6MTcyNzAxMDI2NCwiZXhwIjoxNzQyNTYyMjY0fQ.tTenvs3QLrnRiqHu1Ako0hQZv9Mx0QCXLjBMSu6MIY0'

USER_ID = "c46d74d1-8d1c-4845-a474-483706592c87"
USER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYzQ2ZDc0ZDEtOGQxYy00ODQ1LWE0NzQtNDgzNzA2NTkyYzg3IiwidXNlcl9yb2xlIjoidXNlciIsImlhdCI6MTcyOTQ5NDgyNSwiZXhwIjoxNzQ1MDQ2ODI1fQ.5s3N3f2Mkzx9BSD_jPxR51I8oRCp9_oH4lYsGZuu0VQ'

    
USER_PROFILE = {
    'name': 'Unclecode',
    'hobbies': ['Reading', 'Traveling', 'Watching Movies', "Coding"],
    # 'gender': 'male',
    # 'age': 32,
    # 'location': 'Malaysia',
    # 'favourite_genres': ['Comedy', 'Sci Fi', 'Fantasy'],
    # 'favourite_movies': ['The Shawshank Redemption', "Harry Potter and the Sorcerer's Stone", 'Lord of the Rings'],
    # 'favourite_tv_shows': ['Game of Thrones', 'The Big Bang Theory', 'How I Met Your Mother']
}
USER_LANGUAGE = 'en-US'

class PromptParameters(BaseModel):
    id: str = "prompt-default"
    params: Dict[str, Any] = {}


def main():
    action = "assistant"
    # action = "what2watch"
    # action = "talk2me"
    
    payload = PromptParameters(
        id="mojito_assistant",
        params={
            "action": "assistant",
            "user_id": USER_ID,
            "user_token": USER_TOKEN,
            "user_details": USER_PROFILE,
            "user_language": USER_LANGUAGE,
            "user_message": "",
            "user_extra_data": {
                "favorite_lists" : [
                    {"name": "sci fi movies", "list_id": "d2dc2c8f-a0df-43a4-b281-452b0ca29e05"}, 
                    {"name": "Summer vibes", "list_id": "222e0d2e-5d5f-4e02-bbc2-7ee1d9b95a0b"}, 
                    {"name": "Winter", "list_id": "bfbd96ff-d62c-4cff-8785-b137a80ae682"}
                ]
            },
        }
    )
    if action == 'what2watch':
        payload.params['action'] = 'what2watch'
    elif action == 'talk2me':
        payload.id = 'mojito_talk2me'
        movie_name = "Harry Potter and the Sorcerer's Stone"
        character_name = "Harry Potter"
        payload.params['action'] = 'talk2me'
        payload.params['movie_name'] = movie_name
        payload.params['character_name'] = character_name

    # we only need to have 2 different assistants for now, one for assistant and one for talk2me. for what2watch, we can use the "assistant" assistant.
    # that's why we have this mapping here.
    assistant_action = {
        "what2watch": "assistant",
        "talk2me": "talk2me",
        "regenerate": "assistant",
        "assistant": "assistant"
    }.get(action, "assistant")
    assistant = MovieAssistant(
        user_id=USER_ID,
        user_token=USER_TOKEN,
        action=assistant_action,
        tools=ALL_TOOLS,
        schemas=ALL_SCHEMAS,
        payload=payload,
    )

    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            break
        
        payload.params['user_message'] = user_input
        response = assistant.chat(user_input)
        result = assistant.make_return(response)
        print("AI:")
        pprint.pprint(result)

    assistant.close()


if __name__ == "__main__":
    main()
