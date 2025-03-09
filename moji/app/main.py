import os, sys
import json
import time
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
import agentloop

from config import DB_URI, DB_NAME, OPENAI_API_KEY, MODELS
from moji_assistant import MojiAssistant
from pymongo import MongoClient

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize Flask app
app = Flask(__name__, 
            static_folder='assets',
            static_url_path='/assets',
            template_folder='template')
CORS(app)

# Connect to MongoDB
client = MongoClient(DB_URI)
db = client[DB_NAME]

# Dictionary to store active assistant instances
active_assistants = {}

def get_user_token(email: str) -> tuple[Optional[str], Optional[str]]:
    """
    Get user token and ID from email address.
    
    Args:
        email: User's email address
        
    Returns:
        Tuple of (user_token, user_id) or (None, None) if not found
    """
    user = db.users.find_one({
        "email": email,
        "is_test_user": {"$exists": False},
        "user_token": {"$exists": True, "$ne": ""}
    })
    if user:
        return user.get('user_token'), user.get('user_id')
    return None, None

def get_assistant(user_id: str, user_token: str) -> MojiAssistant:
    """
    Get or create a MojiAssistant instance for a user.
    
    Args:
        user_id: User ID
        user_token: User auth token
        
    Returns:
        MojiAssistant instance
    """
    # Check if we already have an active assistant for this user
    if user_id in active_assistants:
        return active_assistants[user_id]
        
    # Create a new assistant
    assistant = MojiAssistant(
        user_id=user_id,
        user_token=user_token,
        model_id=MODELS.get("openai_4o", "gpt-4o"),
        action="assistant",
        params={
            "user_details": {
                "name": "User" # Could fetch from database if needed
            }
        },
        verbose=True,
        remember_tool_calls=True,
        synthesizer_model_id=MODELS.get("openai_4o_mini", "gpt-3.5-turbo")
    )
    
    # Store in active assistants
    active_assistants[user_id] = assistant
    return assistant

def log_bug_report(user_id: str, report_data: Dict[str, Any]) -> None:
    """
    Log a bug report to the database.
    
    Args:
        user_id: User ID
        report_data: Bug report data
    """
    try:
        # Get conversation history if possible
        conversation = []
        if user_id in active_assistants:
            assistant = active_assistants[user_id]
            if hasattr(assistant, 'session') and assistant.session:
                # Try to extract some conversation history
                memory = assistant.session.get('memory')
                if memory:
                    # This is a simplified approach - real implementation would 
                    # need to consider the memory model's actual API
                    try:
                        conversation = memory.search_memory("", limit=10) or []
                    except:
                        pass
        
        # Prepare bug report with additional server info
        bug_report = {
            "user_id": user_id,
            "client_info": report_data,
            "server_info": {
                "timestamp": datetime.now().isoformat(),
                "server_time": time.time(),
                "conversation_history": conversation
            }
        }
        
        # Save to database
        db.bug_reports.insert_one(bug_report)
        return True
    except Exception as e:
        print(f"Error logging bug report: {str(e)}")
        traceback.print_exc()
        return False

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/auth', methods=['POST'])
def authenticate():
    """Authenticate a user by email"""
    email = request.json.get('email')
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    
    # Get user token and ID
    user_token, user_id = get_user_token(email)
    if not user_token or not user_id:
        return jsonify({"success": False, "error": "User not found or not authorized"}), 404
    
    return jsonify({
        "success": True, 
        "user_id": user_id,
        "user_token": user_token
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message and return a regular response"""
    user_id = request.json.get('user_id')
    user_token = request.json.get('user_token')
    message = request.json.get('message')
    
    if not user_id or not user_token or not message:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400
    
    try:
        # Get assistant for this user
        assistant = get_assistant(user_id, user_token)
        
        # Process message
        result = assistant.chat(message)
        
        return jsonify({
            "success": True,
            "response": result
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@app.route('/api/chat/stream', methods=['GET'])
def chat_stream():
    """Process a chat message and return a streaming response via SSE"""
    # Get parameters from query string
    user_id = request.args.get('user_id')
    user_token = request.args.get('user_token')
    message = request.args.get('message')
    
    # If no message, this is just establishing a connection
    if not message or not user_id or not user_token:
        def keep_alive():
            # Send a connection ready event
            yield "event: ready\ndata: {\"type\":\"connection_ready\",\"data\":{}}\n\n"
            # Keep the connection open with empty comments
            while True:
                yield ": keep-alive\n\n"
                time.sleep(15)  # Send a keep-alive comment every 15 seconds
        
        resp = Response(stream_with_context(keep_alive()),
                      content_type='text/event-stream')
        # Add CORS headers
        resp.headers['Cache-Control'] = 'no-cache'
        resp.headers['X-Accel-Buffering'] = 'no'
        return resp
    
    # Process the message
    def generate():
        try:
            # First yield a keep-alive event to confirm connection is ready
            yield "retry: 1000\ndata: {\"type\":\"connection_ready\"}\n\n"
            
            # Log for debugging
            print(f"Processing streaming message for user {user_id}")
            
            # Get assistant for this user
            assistant = get_assistant(user_id, user_token)
            
            # Process message with streaming
            for stream_event in assistant.chat_stream(message):
                # Debug logging
                # print(f"Stream event: {json.dumps(stream_event)[:100]}...")
                
                # Ensure the correct SSE format with data: prefix and double newline
                yield f"data: {json.dumps(stream_event)}\n\n"
                
        except Exception as e:
            print(f"Streaming error: {str(e)}")
            traceback.print_exc()
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    resp = Response(stream_with_context(generate()), 
                   content_type='text/event-stream')
    # Add headers to prevent caching and buffering
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp

@app.route('/api/clear-memory', methods=['POST'])
def clear_memory():
    """Clear the memory for a user's session"""
    user_id = request.json.get('user_id')
    user_token = request.json.get('user_token')
    reset_all = request.json.get('reset_all', False)
    
    if not user_id or not user_token:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400
    
    try:
        # Check if we have an active assistant for this user
        if user_id in active_assistants:
            assistant = active_assistants[user_id]
            result = assistant.clear_memory(reset_all=reset_all)
            
            # Recreate the assistant to ensure a fresh state
            active_assistants[user_id] = get_assistant(user_id, user_token)
            
            return jsonify({
                "success": True,
                "message": "Memory cleared successfully"
            })
        else:
            # No active assistant, nothing to clear
            return jsonify({
                "success": True,
                "message": "No active session to clear"
            })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@app.route('/api/report-bug', methods=['POST'])
def report_bug():
    """Report a bug with the assistant"""
    user_id = request.json.get('user_id')
    report_data = request.json.get('report_data', {})
    
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"}), 400
    
    try:
        result = log_bug_report(user_id, report_data)
        return jsonify({
            "success": result,
            "message": "Bug report submitted successfully" if result else "Failed to submit bug report"
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)