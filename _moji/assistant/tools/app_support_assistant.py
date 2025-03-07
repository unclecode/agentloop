from openai import OpenAI
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from config import OPENAI_API_KEY, MODELS
import json
import os
# from time import time

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class AppSupportResponse(BaseModel):
    answer: str
    relevant_docs: List[str]


def load_knowledge_base():
    knowledge_base = []
    projects_dir = "docs"  # Assuming the knowledge base is in a 'projects' folder
    projects_dir = os.path.join(__location__, projects_dir)
    for root, dirs, files in os.walk(projects_dir):
        for file in files:
            if file.endswith(".txt") or file.endswith(".md"):
                with open(os.path.join(root, file), 'r') as f:
                    content = f.read()
                    knowledge_base.append({
                        "filename": file,
                        "content": content
                    })
    return knowledge_base


def app_support_assistant(assistant_object, 
                          **kwargs: Dict[str, Any]
                        #   user_question: str
                          ) -> str:
    db = assistant_object.db
    user_id = assistant_object.user_id
    user_question = kwargs.get('user_question', None)
    client = OpenAI(api_key=OPENAI_API_KEY)
    knowledge_base = load_knowledge_base()

    system_prompt = """You are an AI assistant for a multimedia app platform. Your role is to help users with questions about how to use the app, its features, and functionalities. Use the provided knowledge base to answer questions accurately and concisely. If you're unsure about an answer, say so and suggest where the user might find more information. Always aim to be helpful, clear, and user-friendly in your responses."""

    knowledge_base_content = json.dumps(knowledge_base)

    user_prompt = f"""Question: {user_question}

Knowledge Base:
{knowledge_base_content}

Please provide a helpful answer to the user's question based on the information in the knowledge base. Also, list the filenames of any relevant documents you used to formulate your answer."""

    completion = client.beta.chat.completions.parse(
        model=MODELS['llm_what2know'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=AppSupportResponse,
    )
    response = completion.choices[0].message.parsed
    # response_content = json.loads(completion.choices[0].message.content)

    # save log to db
    try:
        db.save_log(user_id, 'app_support_assistant', {
            "user_question": user_question,
            "response": response.model_dump_json()
        })
    except Exception as e:
        print(f"app_support_assistant > save_log: {str(e)}")

    return json.dumps({"type":"text_response", **response.model_dump()})


TOOL_SCHEMA = {
    "name": "app_support_assistant",
    "description": "Answers user questions about the app's features, functionalities, and how to use them. Use this tool when users ask about specific app operations, troubleshooting, or general app-related inquiries.",
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

TOOLS = {
    "app_support_assistant": app_support_assistant
}
