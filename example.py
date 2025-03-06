"""
Example usage of agentloop demonstrating conversation flow with memory persistence.
"""

import os
import json
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
        "sydney": "Partly cloudy, 68°F",
        "rome": "Sunny, 75°F",
        "berlin": "Cloudy, 62°F",
        "madrid": "Sunny, 78°F",
        "amsterdam": "Light rain, 60°F",
        "dubai": "Hot and sunny, 95°F",
        "singapore": "Thunderstorms, 82°F"
    }
    
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
    # Generate different prices based on class
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


def check_hotel_availability(city: str, check_in: str, check_out: str, guests: int = 2) -> List[Dict[str, Any]]:
    """
    Check hotel availability in a given city.
    
    Args:
        city: The city to search in
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        guests: Number of guests
        
    Returns:
        List of available hotels
    """
    # This is a mock implementation
    mock_hotels = {
        "new york": [
            {"name": "Grand Hyatt", "stars": 5, "price_per_night": 299, "address": "Park Avenue"},
            {"name": "Holiday Inn Express", "stars": 3, "price_per_night": 150, "address": "Times Square"}
        ],
        "london": [
            {"name": "The Savoy", "stars": 5, "price_per_night": 450, "address": "Strand"},
            {"name": "Premier Inn", "stars": 3, "price_per_night": 120, "address": "Leicester Square"}
        ],
        "paris": [
            {"name": "Hotel de Crillon", "stars": 5, "price_per_night": 850, "address": "Place de la Concorde"},
            {"name": "Ibis Paris", "stars": 3, "price_per_night": 95, "address": "Eiffel Tower District"}
        ],
        "tokyo": [
            {"name": "Park Hyatt Tokyo", "stars": 5, "price_per_night": 550, "address": "Shinjuku"},
            {"name": "APA Hotel", "stars": 3, "price_per_night": 85, "address": "Ginza"}
        ]
    }
    
    if city.lower() not in mock_hotels:
        return [{"message": f"No hotels found in {city}"}]
    
    # Add availability info
    hotels = mock_hotels[city.lower()]
    for hotel in hotels:
        hotel["available"] = True
        hotel["total_price"] = hotel["price_per_night"] * guests
    
    return hotels


def get_attractions(city: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get tourist attractions in a city.
    
    Args:
        city: The city to search in
        category: Optional category filter (museums, landmarks, parks, etc.)
        
    Returns:
        List of attractions
    """
    # This is a mock implementation
    attractions_by_city = {
        "paris": {
            "museums": [
                {"name": "Louvre Museum", "rating": 4.8, "price": "€15"},
                {"name": "Musée d'Orsay", "rating": 4.7, "price": "€12"}
            ],
            "landmarks": [
                {"name": "Eiffel Tower", "rating": 4.6, "price": "€25"},
                {"name": "Arc de Triomphe", "rating": 4.5, "price": "€10"}
            ],
            "parks": [
                {"name": "Luxembourg Gardens", "rating": 4.7, "price": "Free"},
                {"name": "Tuileries Garden", "rating": 4.5, "price": "Free"}
            ]
        },
        "new york": {
            "museums": [
                {"name": "Metropolitan Museum of Art", "rating": 4.8, "price": "$25"},
                {"name": "Museum of Modern Art", "rating": 4.7, "price": "$25"}
            ],
            "landmarks": [
                {"name": "Statue of Liberty", "rating": 4.7, "price": "$24"},
                {"name": "Empire State Building", "rating": 4.6, "price": "$42"}
            ],
            "parks": [
                {"name": "Central Park", "rating": 4.8, "price": "Free"},
                {"name": "High Line", "rating": 4.7, "price": "Free"}
            ]
        },
        "tokyo": {
            "museums": [
                {"name": "Tokyo National Museum", "rating": 4.6, "price": "¥1000"},
                {"name": "Ghibli Museum", "rating": 4.8, "price": "¥1000"}
            ],
            "landmarks": [
                {"name": "Tokyo Skytree", "rating": 4.5, "price": "¥2000"},
                {"name": "Senso-ji Temple", "rating": 4.7, "price": "Free"}
            ],
            "parks": [
                {"name": "Shinjuku Gyoen", "rating": 4.6, "price": "¥500"},
                {"name": "Ueno Park", "rating": 4.5, "price": "Free"}
            ]
        }
    }
    
    if city.lower() not in attractions_by_city:
        return [{"message": f"No attractions information available for {city}"}]
    
    city_attractions = attractions_by_city[city.lower()]
    
    if category and category.lower() in city_attractions:
        return city_attractions[category.lower()]
    
    # If no category specified or invalid category, return all attractions
    all_attractions = []
    for cat, attractions in city_attractions.items():
        for attraction in attractions:
            attraction["category"] = cat
            all_attractions.append(attraction)
    
    return all_attractions


def get_currency_exchange(from_currency: str, to_currency: str, amount: float = 1.0) -> Dict[str, Any]:
    """
    Get currency exchange rates.
    
    Args:
        from_currency: Source currency code (USD, EUR, etc.)
        to_currency: Target currency code
        amount: Amount to convert (default: 1.0)
        
    Returns:
        Exchange rate information
    """
    # This is a mock implementation with realistic exchange rates
    exchange_rates = {
        "USD": {"EUR": 0.91, "GBP": 0.78, "JPY": 143.8, "AUD": 1.47, "CAD": 1.35, "CHF": 0.88},
        "EUR": {"USD": 1.10, "GBP": 0.86, "JPY": 157.7, "AUD": 1.62, "CAD": 1.49, "CHF": 0.97},
        "GBP": {"USD": 1.27, "EUR": 1.16, "JPY": 184.2, "AUD": 1.88, "CAD": 1.73, "CHF": 1.13},
        "JPY": {"USD": 0.0070, "EUR": 0.0063, "GBP": 0.0054, "AUD": 0.0102, "CAD": 0.0094, "CHF": 0.0061},
        "AUD": {"USD": 0.68, "EUR": 0.62, "GBP": 0.53, "JPY": 97.9, "CAD": 0.92, "CHF": 0.60},
        "CAD": {"USD": 0.74, "EUR": 0.67, "GBP": 0.58, "JPY": 106.5, "AUD": 1.09, "CHF": 0.65},
        "CHF": {"USD": 1.14, "EUR": 1.03, "GBP": 0.89, "JPY": 163.4, "AUD": 1.67, "CAD": 1.53}
    }
    
    # Standardize currency codes
    from_code = from_currency.upper()
    to_code = to_currency.upper()
    
    if from_code not in exchange_rates:
        return {"error": f"Currency {from_currency} not supported"}
    
    if to_code not in exchange_rates[from_code] and to_code != from_code:
        return {"error": f"Currency {to_currency} not supported"}
    
    # Same currency
    if from_code == to_code:
        rate = 1.0
    else:
        rate = exchange_rates[from_code][to_code]
    
    converted_amount = amount * rate
    
    return {
        "from": from_code,
        "to": to_code,
        "rate": rate,
        "amount": amount,
        "converted_amount": converted_amount,
        "date": "2023-07-01"  # Mock date
    }


def run_test_session(session_id: str = "travel_session_123", new_session: bool = True):
    """Run a test conversation session"""
    # Create travel assistant
    assistant = agentloop.create_assistant(
        model_id="gpt-4o",
        system_message="""You are a knowledgeable travel assistant who can help with trip planning, 
weather information, flight booking, hotel reservations, local attractions, and currency exchange.
Always be friendly, concise, and helpful. When you need to gather information, use the available 
tools rather than making assumptions. For flights and hotels, always confirm the details before booking.""",
        tools=[get_weather, book_flight, check_hotel_availability, get_attractions, get_currency_exchange],
        params={"temperature": 0.7}
    )
    
    # Start or resume a session
    if new_session:
        print(f"\n{'='*80}\nStarting new session: {session_id}\n{'='*80}")
        session = agentloop.start_session(assistant, session_id)
    else:
        print(f"\n{'='*80}\nResuming existing session: {session_id}\n{'='*80}")
        session = agentloop.start_session(assistant, session_id)
    
    # Function to process and display a message
    def process_and_show(user_message):
        print(f"\nUser: {user_message}")
        response = agentloop.process_message(session, user_message)
        print(f"Assistant: {response['response']}\n")
        return response
    
    if new_session:
        # Part 1: Simple questions that don't trigger functions
        process_and_show("Hi there! I'm planning a trip soon.")
        process_and_show("What kind of recommendations do you have for a first-time international traveler?")
        process_and_show("How far in advance should I book flights for the best prices?")
        
        # Part 2: Questions that trigger a single function
        process_and_show("What's the weather like in Paris right now?")
        process_and_show("I'd like to book a flight from New York to London on 2023-12-15.")
        process_and_show("Can you tell me about some attractions in Tokyo?")
        
        # Part 3: Complex queries that trigger multiple functions
        process_and_show("I'm planning a trip to Paris next week. I want to know the weather, find a hotel for 3 nights from 2023-07-15 to 2023-07-18, and learn about the top museums.")
        process_and_show("I need to book a business class flight from London to Tokyo on 2023-11-20, and I also want to know the current exchange rate from GBP to JPY.")
        
        # Part 4: Follow-up questions to test conversation continuity
        process_and_show("What was that flight number again for the London to Tokyo trip?")
        process_and_show("And how much was the hotel in Paris?")
        
        # Part 5: Simple closing questions
        process_and_show("Thank you for your help! Any final travel tips you can give me?")
        process_and_show("Goodbye for now!")
    else:
        # Memory test questions when resuming the session
        process_and_show("Hello again! Can you remind me which cities we discussed in our previous conversation?")
        process_and_show("What were some of the attractions in Tokyo you mentioned earlier?")
        process_and_show("Did we look up any flight information before? What was it?")
        process_and_show("What was the weather like in Paris when we checked?")
        process_and_show("Thanks for helping me remember our previous conversation!")
    
    # Display recent conversation from memory
    print(f"\n{'='*80}\nRecent Conversation from Memory:\n{'='*80}")
    conversation = agentloop.get_conversation(session, limit=10)
    for i, message in enumerate(conversation):
        role = message["role"]
        content = message.get("content", "")
        print(f"{i+1}. {role.capitalize()}: {content[:100]}..." if len(content) > 100 else f"{i+1}. {role.capitalize()}: {content}")
    
    # Close memory connection
    if session.get('memory'):
        session['memory'].close()
    
    return session


def main():
    # Set OpenAI API key from environment variable
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    session_id = "travel_session_123"
    
    # Reset memory for a clean start
    print("Resetting memory for a clean start...")
    agentloop.reset_memory()
    
    # Test 1: Run a new session with various queries
    run_test_session(session_id, new_session=True)
    
    # Small pause to ensure all memory operations are complete
    time.sleep(1)
    
    # Test 2: Resume the same session to test memory persistence
    run_test_session(session_id, new_session=False)
    
    print("\nMemory persistence test complete!")


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