"""
Example demonstrating the Moji App Support Assistant.

This example shows how to use the Moji assistant to answer
questions about the app using a knowledge base.

To run:
    OPENAI_API_KEY=your_key python moji/app_support_example.py
"""

import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MojiAssistant class
from moji.moji_assistant import MojiAssistant

def main():
    """Run the app support example."""
    # Check if OpenAI API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Example: OPENAI_API_KEY=your_key python moji/app_support_example.py")
        sys.exit(1)
        
    print("🎬 Moji App Support Example 🎬")
    print("-------------------------------")
    print("Ask questions about the Moji app's features and functionality.")
    print("Type 'exit' to quit.\n")
    
    # Initialize the Moji assistant
    # In a real app, these would be actual user credentials
    assistant = MojiAssistant(
        user_id="test_user_123",
        user_token="test_token_abc",
        model_id="gpt-4o",
        synthesizer_model_id="gpt-4o-mini",
        verbose=True
    )
    
    # Main interaction loop
    while True:
        # Get user question
        user_question = "How is to create a favorite list?" # input("\n🤔 Your question: ")
        
        # Exit condition
        if user_question.lower() in ['exit', 'quit', 'q']:
            print("\nThanks for using Moji App Support! Goodbye!")
            break
            
        # Process the question
        print("\n⏳ Searching knowledge base...")
        response = assistant.chat(user_question)
        
        # Extract and display the response
        output_type = response.get("output_type", "text")
        response_data = response.get("response", {})
        
        print("\n🤖 Moji Assistant:")
        
        if output_type == "text_response":
            # Display the answer
            print(f"\n{response_data.get('answer', 'No answer found.')}")
            
            # Display relevant documents
            relevant_docs = response_data.get('relevant_docs', [])
            if relevant_docs:
                print("\nℹ️ Sources:")
                for doc in relevant_docs:
                    print(f"  • {doc}")
        else:
            # Fallback for other response types
            print(json.dumps(response_data, indent=2))

        break
            
    # Clear memory when done
    assistant.clear_memory()

if __name__ == "__main__":
    main()