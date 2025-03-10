"""
Example of using the Moji assistant with the trailer finder functionality in streaming mode.
"""
import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agentloop
from moji_assistant import MojiAssistant

def main():
    """
    Test the trailer finder functionality with the Moji assistant in streaming mode.
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
        remember_tool_calls=True,
        synthesizer_model_id="gpt-3.5-turbo"  # Using the parameter for tool call synthesis
    )
    
    print("\n===== Moji Trailer Finder Streaming Example =====")
    
    # Example messages to process with streaming
    example_messages = [
        "Show me the trailer for Dune",
        "I want to see the trailer for Stranger Things",
        "Find me the latest trailer for The Batman"
    ]
    
    # Process each example message with streaming
    for i, user_message in enumerate(example_messages, 1):
        print(f"\n{i}. User: {user_message}")
        print(f"Assistant: ", end="", flush=True)
        
        response_content = ""
        final_response = None
        
        # Process message with streaming
        for stream_event in assistant.chat_stream(user_message):
            event_type = stream_event.get('type')
            data = stream_event.get('data')
            
            if event_type == 'token':
                # Print tokens as they come in
                print(data, end="", flush=True)
                response_content += data
            
            elif event_type == 'tool_start':
                # Show when tool is called
                print(f"\n[Calling tool: {data['name']} with args: {json.dumps(data['args'], indent=2)}]", end="", flush=True)
            
            elif event_type == 'tool_result':
                # Show tool result summary (not the entire result)
                result_str = data['result']
                try:
                    # Try to parse and format the JSON result
                    result_json = json.loads(result_str)
                    # Just show a summary for cleaner output
                    if result_json.get('status'):
                        trailer_data = result_json.get('data', {})
                        trailer_url = trailer_data.get('trailer_url', 'No URL found')
                        print(f"\n[Tool result: Found trailer for '{trailer_data.get('title')}': {trailer_url}]", end="", flush=True)
                    else:
                        print(f"\n[Tool result: {result_json.get('message', 'Error finding trailer')}]", end="", flush=True)
                except:
                    print(f"\n[Tool result: {result_str}]", end="", flush=True)
                
                print("\nAssistant: ", end="", flush=True)
            
            elif event_type == 'finish':
                # Print formatted response information at the end
                final_response = data.get('formatted_response')
        
        if final_response:
            print(f"\n\nResponse Type: {final_response['output_type']}")
            print(f"Response Content: {json.dumps(final_response['response'], indent=2)}")
        
        print("\n" + "-"*50)
    
    print("\n===== Streaming Example Complete =====")

if __name__ == "__main__":
    main()