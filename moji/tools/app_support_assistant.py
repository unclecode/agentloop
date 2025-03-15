"""
Tool for answering user questions about the Moji app platform.
Uses a knowledge base to provide accurate information about app features and usage.
"""
import json
import os
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional


class AppSupportResponse(BaseModel):
    answer: str
    relevant_docs: Optional[List[str]] = []


def load_knowledge_base():
    """
    Load the knowledge base from the docs directory.

    Returns:
        List of dictionaries with filename and content
    """
    knowledge_base = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.join(current_dir, "docs")

    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".txt") or file.endswith(".md"):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        knowledge_base.append({
                            "filename": file,
                            "content": content
                        })
                except Exception as e:
                    print(f"Error loading {file}: {str(e)}")

    return knowledge_base


def app_support_assistant(
    user_question: str,
    **context  # Catches credentials from context
) -> str:
    """
    Answer user questions about the app using the knowledge base.

    Args:
        user_question: User's question about the app

    Context Args (passed by agentloop):
        user_id: User identifier

    Returns:
        JSON string with the answer and relevant documents
    """
    try:
        # Get OpenAI client (assuming API key is set in environment variable)
        client = OpenAI()

        # Load knowledge base
        knowledge_base = load_knowledge_base()

        # Create prompts
        system_prompt = """You are an AI assistant for a multimedia app platform called Moji. 
Your role is to help users with questions about how to use the app, its features, and functionalities. 
Use the provided knowledge base to answer questions accurately and concisely. 
If you're unsure about an answer, say so and suggest where the user might find more information. 
Always aim to be helpful, clear, and user-friendly in your responses."""

        # Convert knowledge base to string representation
        knowledge_base_content = json.dumps(knowledge_base)

        user_prompt = f"""Question: {user_question}

Knowledge Base:
{knowledge_base_content}

Please provide a helpful answer to the user's question based on the information in the knowledge base. 
Also, list the filenames of any relevant documents you used to formulate your answer.

### Output Format:
Always return a JSON object with the following structure:
{{
    "answer": "Your answer here",
    "relevant_docs": ["filename1", "filename2"]
}}

"""

        # Get response from OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        completion = client.chat.completions.create(
            model="gpt-4o",  # Or other appropriate model
            messages=messages,
            response_format={"type": "json_object"}
        )

        # Parse the response
        response_text = completion.choices[0].message.content
        # make sure there is no ``` in the response
        response_text = response_text.replace('```json', "").replace('```', "").strip()
        response_data = json.loads(response_text)

        # Create AppSupportResponse
        response = AppSupportResponse(
            answer=response_data.get("answer", ""),
            relevant_docs=response_data.get("relevant_docs", [])
        )

        # Format as expected by MojiAssistant
        return json.dumps({
            "type": "text_response",
            "answer": response.answer,
            "relevant_docs": response.relevant_docs
        })

    except Exception as e:
        print(f"Error in app_support_assistant: {str(e)}")
        return json.dumps({
            "type": "text_response",
            "answer": f"I encountered an error while trying to answer your question: {str(e)}",
            "relevant_docs": []
        })


# Tool schema for agentloop
APP_SUPPORT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "app_support_assistant",
        "description": "Answers user questions ONLY about the Moji app features. Use this tool when users ask about specific app operations, troubleshooting, or general app-related inquiries. DO NOT USE FOR OTHER QUESTIONS.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_question": {
                    "type": "string",
                    "description": "The user's question or inquiry about the app"
                }
            },
            "required": ["user_question"]
        }
    }
}

# Export tools for dynamic loading
TOOLS = {
    "app_support_assistant": app_support_assistant
}

# Export schemas for dynamic loading
TOOL_SCHEMAS = {
    "app_support_assistant": APP_SUPPORT_SCHEMA
}
