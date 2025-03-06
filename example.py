"""
Example usage of agentloop for creating an AI assistant.
"""

import os
import json
import sys
from typing import Dict, Any

# Add the parent directory to the Python path to import the local agentloop package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from agentloop import agentloop


def get_weather(city: str) -> str:
    """
    Return the weather for a given city.
    
    Args:
        city: The name of the city to get weather for
        
    Returns:
        A string with the weather information
    """
    # This is a mock implementation
    weather_data = {
        "new york": "Sunny, 72°F",
        "london": "Rainy, 59°F",
        "paris": "Cloudy, 65°F",
        "tokyo": "Clear, 80°F",
        "sydney": "Partly cloudy, 68°F"
    }
    
    return f"Weather in {city.title()}: {weather_data.get(city.lower(), 'No data available')}"


def book_flight(origin: str, destination: str, date: str) -> Dict[str, Any]:
    """
    Search for available flights.
    
    Args:
        origin: Departure city
        destination: Arrival city
        date: Travel date (YYYY-MM-DD)
        
    Returns:
        Dictionary with flight options
    """
    # This is a mock implementation
    return {
        "flights": [
            {
                "airline": "Mock Airlines",
                "flight_number": "MA123",
                "departure": f"{origin} 09:00",
                "arrival": f"{destination} 11:30",
                "price": "$350"
            },
            {
                "airline": "Example Airways",
                "flight_number": "EA456",
                "departure": f"{origin} 13:45",
                "arrival": f"{destination} 16:15",
                "price": "$420"
            }
        ]
    }


def main():
    # Set OpenAI API key from environment variable
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    # Create travel assistant
    assistant = agentloop.create_assistant(
        model_id="gpt-4o",
        template="Hello, {{name}}! I'm your {{role}} assistant. I can help you plan trips, check weather, and book flights.",
        template_params={"name": "User", "role": "travel"},
        tools=[get_weather, book_flight],
        guardrail="Do not discuss sensitive topics like politics or religion.",
        params={"temperature": 0.7}
    )
    
    # Start a session
    session = agentloop.start_session(assistant, "travel_session_001")
    
    # Add a memory for the user
    agentloop.update_memory(
        session,
        "User prefers to travel in business class and likes window seats.",
        {"preference": "travel_class", "value": "business"}
    )
    
    # Example conversation with templating
    print("Example 1: Simple text query with memory integration")
    response = agentloop.process_message(
        session,
        "What's the weather in Paris?",
        user_template="Query from {{name}}: {{message}}",
        template_params={"name": "User"},
        token_callback=lambda usage: print(f"Token usage: {usage}")
    )
    print(f"Assistant: {response['response']}\n")
    
    # Example with tool usage
    print("Example 2: Tool usage for flight booking")
    response = agentloop.process_message(
        session,
        "I want to fly from New York to London on 2023-12-15."
    )
    print(f"Assistant: {response['response']}\n")
    
    # Example with JSON schema for structured output
    print("Example 3: Structured output")
    schema = {
        "name": "travel_recommendation",
        "schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "season": {"type": "string"},
                "activities": {"type": "array", "items": {"type": "string"}},
                "budget_category": {"type": "string"}
            },
            "required": ["destination", "season", "activities", "budget_category"],
            "additionalProperties": False
        },
        "strict": True
    }
    
    response = agentloop.process_message(
        session,
        "Recommend a beach vacation destination.",
        schema=schema
    )
    print(f"Structured response: {response['response']}\n")
    
    # View conversation history
    print("Conversation History:")
    history = agentloop.get_history(session)
    for i, message in enumerate(history):
        role = message["role"]
        content = message.get("content", "")
        print(f"{i+1}. {role.capitalize()}: {content[:50]}..." if len(content) > 50 else f"{i+1}. {role.capitalize()}: {content}")


if __name__ == "__main__":
    main()