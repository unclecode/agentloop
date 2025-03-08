"""
Example usage of the Moji assistant with agentloop
"""
import os
import json
from moji_assistant import MojiAssistant

def main():
    """
    Demonstrate using the Moji assistant with agentloop
    """
    # Ensure OPENAI_API_KEY is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable")
        return
    
    # Create a movie assistant with example parameters
    assistant = MojiAssistant(
        user_id="test_user_123",
        model_id="gpt-4o",
        action="what2watch",
        params={
            "user_details": {
                "name": "Alex"
            },
            "user_extra_data": {
                "favorite_lists": [
                    {
                        "list_id": "list123",
                        "name": "My Favorite Sci-Fi",
                        "movies": [
                            {"movie_id": "m1", "name": "Inception", "year": "2010"},
                            {"movie_id": "m2", "name": "Interstellar", "year": "2014"}
                        ]
                    }
                ]
            }
        },
        verbose=True
    )
    
    # Simple chat example
    print("\n=== Chat Example ===")
    response = assistant.chat("Can you recommend some sci-fi movies similar to Inception?")
    
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    # Example using a tool
    print("\n=== Tool Example ===")
    response = assistant.chat("I'm in the mood for some action movies from the 90s")
    
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))
    
    # Example with memory
    print("\n=== Memory Example ===")
    assistant.add_memory("User enjoys psychological thrillers with plot twists", "system", 
                       {"type": "preference", "category": "movie_preference"})
    
    response = assistant.chat("Can you suggest a movie I might like based on what you know about me?")
    
    print("\nResponse Type:", response["output_type"])
    print("Response Content:", json.dumps(response["response"], indent=2))

if __name__ == "__main__":
    main()