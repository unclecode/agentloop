"""
Example of using the Moji assistant with favorite lists functionality.
"""
import os
import json
import agentloop
from moji_assistant import MojiAssistant

def main():
    """
    Test the favorite lists functionality with the Moji assistant.
    """
    # Ensure OPENAI_API_KEY is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable")
        return
    
    # Reset all memory before starting the test
    print("Clearing all memory before starting...")
    agentloop.reset_all_memory()
    
    # Dummy credentials for testing
    # In production, these would come from your authentication system
    USER_ID = "9f5bfa4e-579e-4702-aa97-21c66c29e663"
    USER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiOWY1YmZhNGUtNTc5ZS00NzAyLWFhOTctMjFjNjZjMjllNjYzIiwidXNlcl9yb2xlIjoidXNlciIsImlhdCI6MTczNzM1MDA4OSwiZXhwIjoxNzUyOTAyMDg5fQ.pVhp6gd43xBuRqlB4UOrDwzXh_WWOp-N43f0Pr-7o9k'

    user_id = USER_ID
    user_token = USER_TOKEN
    
    # Create a movie assistant with the dummy credentials
    assistant = MojiAssistant(
        user_id=user_id,
        user_token=user_token,
        model_id="gpt-4o",
        action="assistant",
        params={
            "user_details": {
                "name": "Alex"
            }
        },
        verbose=True,
        remember_tool_calls=True
    )
    
    print("\n===== Moji Favorite Lists Example =====")
    
    # Example 1: Creating a list
    print("\n1. Creating a new favorite list")
    response = assistant.chat("Can you create a new list for sci-fi movies called 'My Sci-Fi Favorites'?")
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    # Example 2: Getting all lists
    print("\n2. Getting all favorite lists")
    response = assistant.chat("What lists do I have?")
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    # Example 3: Adding movies to a list
    # This would typically happen after a list is created and we have its ID
    print("\n3. Adding movies to a list")
    # In a real example, we would use the list_id from a previous response
    # For testing, you might need to substitute a real list ID if available
    response = assistant.chat("Add The Matrix to my 'My Sci-Fi Favorites' list")
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    # Example 4: Getting movies from a list
    print("\n4. Getting movies from a list")
    response = assistant.chat("What movies are in my 'My Sci-Fi Favorites' list?")
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    print("\n===== Example Complete =====")

if __name__ == "__main__":
    main()