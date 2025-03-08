"""
Example demonstrating the Moji assistant handling complex multi-task requests.

This example tests the assistant's capability to handle requests that require
multiple tool calls and complex reasoning in a single user message.

To run:
    OPENAI_API_KEY=your_key python moji/complex_tasks_example.py
"""

import os
import json
import time
import agentloop
from moji_assistant import MojiAssistant

def print_response(response, show_details=False):
    """Print a formatted response from the assistant."""
    output_type = response.get("output_type", "text")
    response_data = response.get("response", {})
    
    print(f"\nResponse Type: {output_type}")
    
    if show_details:
        print("Response Content:", json.dumps(response_data, indent=2))
    else:
        if output_type == "text":
            print(f"Response: {response_data.get('content', '')}")
        elif output_type == "movie_json":
            movies = response_data.get("movies", [])
            print(f"Found {len(movies)} movies")
            for idx, movie in enumerate(movies[:3]):  # Show at most 3 movies
                print(f"  {idx+1}. {movie.get('name', movie.get('title', 'Unknown'))} ({movie.get('year', 'Unknown')})")
            if len(movies) > 3:
                print(f"  ... and {len(movies) - 3} more")
        elif output_type == "list":
            items = response_data
            if isinstance(items, list):
                print(f"Lists: {', '.join([item.get('name', 'Unknown') for item in items])}")
            else:
                print(f"List operation result: {json.dumps(items, indent=2)}")
        else:
            print(f"Response: {json.dumps(response_data, indent=2)}")

def main():
    """Run the complex tasks example."""
    # Check if OpenAI API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Example: OPENAI_API_KEY=your_key python moji/complex_tasks_example.py")
        return

    # Reset all memory before starting
    print("Clearing all memory before starting...")
    agentloop.reset_all_memory()
    
    # Dummy credentials for testing
    # In production, these would come from your authentication system
    USER_ID = "9f5bfa4e-579e-4702-aa97-21c66c29e663"
    USER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiOWY1YmZhNGUtNTc5ZS00NzAyLWFhOTctMjFjNjZjMjllNjYzIiwidXNlcl9yb2xlIjoidXNlciIsImlhdCI6MTczNzM1MDA4OSwiZXhwIjoxNzUyOTAyMDg5fQ.pVhp6gd43xBuRqlB4UOrDwzXh_WWOp-N43f0Pr-7o9k'

    # Initialize the MojiAssistant
    print("Initializing MojiAssistant...")
    assistant = MojiAssistant(
        user_id=USER_ID,
        user_token=USER_TOKEN,
        model_id="gpt-4o",
        action="assistant",
        params={
            "user_details": {
                "name": "Alex"
            }
        },
        verbose=True,
        synthesizer_model_id="gpt-3.5-turbo"  # Use different model for tool processing
    )
    
    print("\n🎬 Moji Complex Tasks Example 🎬")
    print("-------------------------------")
    print("Testing the assistant's ability to handle complex multi-task requests")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Create and Populate List",
            "prompt": "Create a new list called 'Best Christopher Nolan Movies', then add Inception (2010), The Dark Knight (2008), and Interstellar (2014) to it. After that, show me what's in the list.",
            "tools_used": ["create_favorite_list", "add_to_favorite_list", "get_list_items"]
        },
        {
            "name": "Manage Multiple Lists",
            "prompt": "Create two new lists: 'Sci-Fi Classics' and 'Action Hits'. Add Star Wars (1977) and Blade Runner (1982) to the Sci-Fi list. Add Die Hard (1988) and The Matrix (1999) to the Action list. Then show me all my lists.",
            "tools_used": ["create_favorite_list", "add_to_favorite_list", "get_favorite_lists"]
        },
        {
            "name": "List Management and Big Five",
            "prompt": "Create a list called 'Oscar Winners', add The Godfather (1972) to it, and also add Avatar (2009), Titanic (1997), and Star Wars (1977) to my Big Five list. Then tell me what movies are in my Big Five list.",
            "tools_used": ["create_favorite_list", "add_to_favorite_list", "add_to_big_five_list", "get_list_items"]
        },
        {
            "name": "Combined Actions",
            "prompt": "Create a list called 'Temporary List', add The Shawshank Redemption (1994) to it, find some sci-fi movie recommendations, then delete the temporary list you created.",
            "tools_used": ["create_favorite_list", "add_to_favorite_list", "what2watch", "remove_favorite_list"]
        },
        {
            "name": "List Modification",
            "prompt": "Create a list called 'Mixed Genres', add The Godfather (1972), Jurassic Park (1993), and The Matrix (1999) to it. Then remove The Matrix from the list and show me what's left.",
            "tools_used": ["create_favorite_list", "add_to_favorite_list", "remove_from_favorite_list", "get_list_items"]
        }
    ]
    
    # Run each scenario
    for i, scenario in enumerate(scenarios):
        print(f"\n\n===== Scenario {i+1}: {scenario['name']} =====")
        print(f"Prompt: {scenario['prompt']}")
        print(f"Expected tools: {', '.join(scenario['tools_used'])}")
        print("\nProcessing request...")
        
        # Track start time to measure performance
        start_time = time.time()
        response = assistant.chat(scenario['prompt'])
        elapsed_time = time.time() - start_time
        
        # Print results
        print(f"\nCompleted in {elapsed_time:.2f} seconds")
        print_response(response)
        
        # Decide based on scenario complexity whether to show detailed response
        print("\nWould you like to see the full response details? (y/n)")
        # user_choice = input("> ")
        user_choice = "y"
        if user_choice.lower() == 'y':
            print_response(response, show_details=True)
        
        if i < len(scenarios) - 1:
            print("\nPress Enter to continue to the next scenario...")
            # input()
    
    print("\n===== All Scenarios Complete =====")
    print("Cleaning up...")
    assistant.clear_memory()
    print("Done!")

if __name__ == "__main__":
    main()