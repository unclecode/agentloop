"""
Example usage of agentloop's streaming functionality.
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional

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
    
    # Add a small delay to simulate API call
    time.sleep(1)
    
    return f"Weather in {city.title()}: {weather_data.get(city.lower(), 'No data available')}"


def book_flight(origin: str, destination: str, date: str, class_type: str = "economy") -> Dict[str, Any]:
    """
    Search for available flights.
    
    Args:
        origin: Departure city
        destination: Arrival city
        date: Travel date (YYYY-MM-DD)
        class_type: Class type (economy, business, first)
        
    Returns:
        Dictionary with flight options
    """
    # This is a mock implementation
    # Add a small delay to simulate API call
    time.sleep(2)
    
    price_multiplier = {
        "economy": 1,
        "business": 2.5,
        "first": 4
    }
    
    base_price = 300
    multiplier = price_multiplier.get(class_type.lower(), 1)
    
    return {
        "flights": [
            {
                "airline": "Mock Airlines",
                "flight_number": "MA123",
                "departure": f"{origin} 09:00",
                "arrival": f"{destination} 11:30",
                "class": class_type,
                "price": f"${int(base_price * multiplier)}"
            },
            {
                "airline": "Example Airways",
                "flight_number": "EA456",
                "departure": f"{origin} 13:45",
                "arrival": f"{destination} 16:15",
                "class": class_type,
                "price": f"${int((base_price + 70) * multiplier)}"
            }
        ]
    }


def run_streaming_session():
    """Run a test conversation session with streaming"""
    # Create travel assistant
    assistant = agentloop.create_assistant(
        model_id="gpt-4o",
        system_message="""You are a knowledgeable travel assistant who can help with trip planning, 
        weather information, and flight booking. Always be friendly, concise, and helpful.
        When you need to gather information, use the available tools rather than making assumptions.
        For flights, always confirm the details before booking.""",
        tools=[get_weather, book_flight],
        params={"temperature": 0.7}
    )
    
    # Start a session
    session_id = "streaming_travel_session"
    print(f"\n{'='*80}\nStarting streaming session: {session_id}\n{'='*80}")
    session = agentloop.start_session(assistant, session_id)
    
    # Define example messages
    messages = [
        "Hi there! I'm planning a trip soon.",
        "What's the weather like in Paris right now?",
        "I'd like to book a flight from New York to London on 2023-12-15.",
        "I want to fly business class.",
        "Thank you for your help!"
    ]
    
    # Process each message with streaming
    for user_message in messages:
        print(f"\nUser: {user_message}")
        print(f"Assistant: ", end="", flush=True)
        
        # Process message with streaming
        response_content = ""
        for stream_event in agentloop.streamed_process_message(session, user_message):
            event_type = stream_event.get('type')
            data = stream_event.get('data')
            
            if event_type == 'token':
                # Print tokens as they come in
                print(data, end="", flush=True)
                response_content += data
            
            elif event_type == 'tool_start':
                # Show tool execution
                print(f"\n[Calling tool: {data['name']} with args: {data['args']}]", end="", flush=True)
            
            elif event_type == 'tool_result':
                # Show tool result
                print(f"\n[Tool result: {data['name']} => {data['result']}]", end="", flush=True)
                print("\nAssistant: ", end="", flush=True)
        
        print("\n")
    
    # Close memory connection
    if session.get('memory'):
        session['memory'].close()


def main():
    # Set OpenAI API key from environment variable
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    # Reset memory for a clean start
    print("Resetting memory for a clean start...")
    agentloop.reset_memory()
    
    # Run streaming session
    run_streaming_session()
    
    print("\nStreaming example complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"Error occurred: {str(e)}")
        traceback.print_exc()
        
        # Clean up memory resources if there was an error
        print("Cleaning up resources...")
        try:
            # Close any open memory connections
            from agentloop.mem4ai import Mem4AI
            Mem4AI("/Users/unclecode/.agentloop/memory.db").close()
        except:
            pass