from pymongo import MongoClient
from typing import Dict, List, Optional, Any
from time import time


class Database:
    def __init__(self, connection_string: str = "mongodb://localhost:27017", db_name: str = "mojitoAssistant"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]

    def save_assistant_tools(self, assistant_id: str, tools: List[Dict[str, Any]]):
        self.db.assistants.update_one(
            {"assistant_id": assistant_id},
            {"$set": {"tools": tools, "updated_at": time()}},
            upsert=True
        )

    def get_assistant_tools(self, assistant_id: str) -> List[Dict[str, Any]]:
        assistant = self.db.assistants.find_one({"assistant_id": assistant_id})
        return assistant["tools"] if assistant else []

    def get_assistant_id(self) -> Optional[str]:
        assistant = self.db.assistants.find_one()
        return assistant["assistant_id"] if assistant else None

    def get_assistant_id_by_action(self, action:str) -> Optional[str]:
        assistant = self.db.assistants.find_one({"action": action})
        return assistant["assistant_id"] if assistant else None
    
    def save_assistant_id(self, assistant_id: str):
        self.db.assistants.update_one(
            {"assistant_id": assistant_id},
            {"$set": {"updated_at": time()}},
            upsert=True
        )

    def save_assistant_id_by_action(self, assistant_id: str, action:str):
        # Remove the current assistant_id with the same action
        self.db.assistants.delete_many({ 'action': action })
        self.db.assistants.update_one(
            {"assistant_id": assistant_id, "action": action},
            {"$set": {"updated_at": time()}},
            upsert=True
        )

    def get_knowledge_base_file_id(self) -> Optional[str]:
        metadata = self.db.metadata.find_one({"key": "knowledge_base_file_id"})
        return metadata["value"] if metadata else None

    def save_knowledge_base_file_id(self, file_id: str):
        self.db.metadata.update_one(
            {"key": "knowledge_base_file_id"},
            {"$set": {"value": file_id, "updated_at": time()}},
            upsert=True
        )

    def get_or_create_user(self, user_id: str) -> str:
        result = self.db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"created_at": time()}},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else str(self.db.users.find_one({"user_id": user_id})["_id"])

    def get_thread_id(self, user_id: str) -> Optional[str]:
        thread = self.db.threads.find_one({"user_id": user_id})
        return thread["thread_id"] if thread else None

    def get_thread_id_by_action(self, user_id: str, action: str) -> Optional[str]:
        thread = self.db.threads.find_one({"user_id": user_id, "action": action})
        return thread["thread_id"] if thread else None

    def save_thread_id(self, user_id: str, thread_id: str):
        self.db.threads.update_one(
            {"user_id": user_id},
            {"$set": {"thread_id": thread_id, "updated_at": time()}},
            upsert=True
        )
        
    def save_thread_id_by_action(self, user_id: str, thread_id: str, action:str):
        self.db.threads.update_one(
            {"user_id": user_id, "action": action},
            {"$set": {"thread_id": thread_id, "updated_at": time()}},
            upsert=True
        )

    def get_or_create_thread(self, user_id: str, thread_id: str) -> str:
        self.db.threads.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"thread_id": thread_id, "created_at": time()}},
            upsert=True
        )
        return thread_id

    def save_log(self, user_id: str, action: str, data: Dict[str, Any]):
        try:
            self.db.logs.insert_one({
                "user_id": user_id,
                "action": action,
                "data": data,
                "timestamp": time()
            })
        except Exception as e:
            print(f"save_log > {str(e)}")

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        profile = self.db.users.find_one(
            {"user_id": user_id}, 
            {"_id": 0, "dob": 1, "first_name": 1, "last_name": 1, "full_name": 1, "gender": 1, "user_details": 1}
        )
        return profile if profile else {}
    
    def save_response_log(self, user_id: str, payload: Dict[str, Any], str_response: str):
        try:
            self.db.logs.insert_one({
                "action": "assistant_response",
                "user_id": user_id,
                "payload": payload,
                "response": str_response,
                "timestamp": time()
            })
        except Exception as e:
            print(f"save_response_log > {str(e)}")
    
    def delete_thread_id_by_action(self, user_id: str, action: str):
        self.db.threads.delete_one({"user_id": user_id, "action": action})

    def close(self):
        self.client.close()
