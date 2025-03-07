import time
from openai import OpenAI
from database import Database
from typing import Dict, List, Union, Optional, Callable, Any
from openai import AssistantEventHandler
from typing_extensions import override
from assistant.response_model import *
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from config import DB_URI, DB_NAME, OPENAI_API_KEY, MODELS, ALWAYS_CREATE_NEW_THREAD, ALWAYS_CREATE_ASSISTANT
from libs.params import (PromptParameters)
from services.tmdb import TMDBService
from libs.error import Error
import os
import logging
import json
from mem4ai.memtor import Memtor
from mem4ai.strategies.knowledge_extraction import  EchoKnowledgeStrategy
# import threading

class Logger:
    def __init__(self, verbose: bool, log_file: str = 'movie_assistant.log'):
        self.verbose = verbose
        self.logger = logging.getLogger('MovieAssistant')
        self.logger.setLevel(logging.DEBUG)
        
        if self.verbose:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)
        else:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
    
    def log(self, message: str):
        self.logger.debug(message)

class MovieAssistantEventHandler(AssistantEventHandler):
    def __init__(self, movie_assistant):
        super().__init__()
        self.movie_assistant = movie_assistant
        self.logger = movie_assistant.logger

    @override
    def on_text_created(self, text) -> None:
        self.logger.log("Assistant started generating text")
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        self.logger.log(f"Received text delta: {delta.value}")
        print(delta.value, end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        self.logger.log(f"Tool call created: {tool_call.type}")
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_event(self, event):
        self.logger.log(f"Received event: {event.event}")
        if event.event == "thread.run.requires_action":
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        self.logger.log(f"Handling required action for run {run_id}")
        tool_outputs = []

        for tool_call in data.required_action.submit_tool_outputs.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            self.logger.log(f"Processing tool call: {function_name} with arguments: {arguments}")

            if function_name == "create_favorite_list":
                output = self.movie_assistant.tools[function_name](
                    self.movie_assistant.user_id,
                    self.movie_assistant.user_token,
                    **arguments
                )
            elif function_name == "add_to_favorite_list":
                output = self.movie_assistant.tools[function_name](
                    self.movie_assistant.user_id,
                    self.movie_assistant.user_token,
                    **arguments
                )
            else:
                self.logger.log(f"Unknown function: {function_name}")
                output = f"Unknown function: {function_name}"

            self.logger.log(f"Tool call output: {output}")
            tool_outputs.append(
                {"tool_call_id": tool_call.id, "output": json.dumps(output)}
            )

        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        self.logger.log(f"Submitting tool outputs for run {run_id}")
        with self.movie_assistant.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs,
            event_handler=MovieAssistantEventHandler(self.movie_assistant),
        ) as stream:
            for text in stream.text_deltas:
                self.logger.log(f"Received text delta in stream: {text}")
                print(text, end="", flush=True)
            print()

    @override
    def on_message_done(self, message) -> None:
        self.logger.log("Message generation completed")
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = self.movie_assistant.client.files.retrieve(
                    file_citation.file_id
                )
                citations.append(f"[{index}] {cited_file.filename}")
                self.logger.log(f"Added citation: {citations[-1]}")

        self.logger.log(f"Final message content: {message_content.value}")
        print(message_content.value)
        if citations:
            self.logger.log(f"Printing citations: {citations}")
            print("\n".join(citations))

class MovieAssistant:
    def __init__(
        self,
        user_id: str,
        user_token: str,
        action: str,
        payload: PromptParameters,
        assistant_files: Optional[List[str]] = None,
        thread_files: Optional[List[str]] = None,
        tools: Dict[str, Callable] = None,
        schemas: Dict[str, Dict[str, Any]] = None,
        request=None,
        verbose: bool = True
    ):
        self.logger = Logger(verbose)
        self.logger.log(f"Initializing MovieAssistant for user {user_id}")
        self.user_id = user_id
        self.user_token = user_token
        self.payload = payload
        self.action = action
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        # Do not remove this commented code, it is used as a reference for AzureOpenAI client
        # self.client = AzureOpenAI(
        #     api_key="",  
        #     api_version="2024-02-15-preview",
        #     azure_endpoint="https://crawl4ai.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-02-15-preview"
        # )
        self.db = Database(DB_URI, DB_NAME)
        self.assistant_files = assistant_files or []
        self.thread_files = thread_files or []
        self.tools = tools or {}
        self.schemas = schemas or {}
        self.assistant = self._get_or_create_assistant()
        self.thread_id = self._get_or_create_thread()
        self.last_run_id = None
        self.request = request
        self.user_kb_time = 0
        self.memtor = Memtor(
            extraction_strategy=EchoKnowledgeStrategy(),
        )
        # self.memtor.storage_strategy.clear_all()
        self.logger.log("MovieAssistant initialized successfully")

    def _get_or_create_assistant(self):
        self.logger.log("Getting or creating assistant")
        assistant_id = self.db.get_assistant_id_by_action(self.action)
        if not ALWAYS_CREATE_ASSISTANT and assistant_id:
            self.logger.log(f"Retrieved existing assistant with ID: {assistant_id}")
            assistant = self.client.beta.assistants.retrieve(assistant_id)
            current_tools = [tool.function.name for tool in assistant.tools if tool.type == 'function']
            new_tools = set(self.schemas.keys()) - set(current_tools)
            if new_tools:
                self.logger.log(f"Updating assistant with new tools: {new_tools}")
                assistant = self._update_assistant(assistant, new_tools)
            return assistant
        else:
            self.logger.log("Creating new assistant")
            return self._create_assistant()

    def _create_assistant(self):
        self.logger.log("Creating new assistant")
        action = self.payload.params.get("action", "assistant")
        prompt_name = {
            "what2watch": "mojito_assistant",
            "talk2me": "mojito_talk2me",
            "ipu_therapist": "mojito_ipuTherapist",
            "regenerate": "mojito_assistant"
        }.get(action, "mojito_assistant")
        
        param_parameters = self.payload.params
        instructions, _ = load_and_render_prompt(prompt_name, param_parameters)
        self.logger.log(f"Loaded instructions for prompt: {prompt_name}")
        
        tools = [{"type": "function", "function": schema} for schema in self.schemas.values()]
        llm_schema = Talk2MeLLMResponse if action == "talk2me" else LLMResponse
        # Fyi majority of available tools should indentify their desire final output_type, if not you should follow the definition of all available output_types in the schema.
        assistant = self.client.beta.assistants.create(
            name="Movie Expert",
            instructions=instructions,
            model=MODELS["openai_4o_mini"],
            tools=tools,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "final_llm_response",
                    "strict": True,
                    "description": "The final response schema from the assistant.",
                    "schema": {**llm_schema.model_json_schema(), "additionalProperties": False},
                },
            },
        )
        self.logger.log(f"Created new assistant with ID: {assistant.id}")
        self.db.save_assistant_id_by_action(assistant.id, self.action)
        return assistant
   
    def _update_assistant(self, assistant, new_tools):
        self.logger.log(f"Updating assistant {assistant.id} with new tools")
        current_tools = assistant.tools
        for tool_name in new_tools:
            current_tools.append({"type": "function", "function": self.schemas[tool_name]})
        
        updated_assistant = self.client.beta.assistants.update(
            assistant_id=assistant.id,
            tools=current_tools
        )
        self.logger.log(f"Assistant {assistant.id} updated successfully")
        return updated_assistant
    
    def _get_or_create_thread(self) -> str:
        self.logger.log(f"Getting or creating thread for user {self.user_id}")
        thread_action_id = f"{self.action}_{self.payload.params.get('subaction_id', '')}".strip('_')
        thread_id = self.db.get_thread_id_by_action(self.user_id, thread_action_id)
        if not ALWAYS_CREATE_NEW_THREAD and thread_id:
            self.logger.log(f"Retrieved existing thread with ID: {thread_id}")
            return thread_id
        else:
            self.logger.log("Creating new thread")
            thread = self.client.beta.threads.create()
            self.db.save_thread_id_by_action(self.user_id, thread.id, thread_action_id)

            if self.thread_files:
                self.logger.log("Attaching files to the thread")
                messages = []
                for file_path in self.thread_files:
                    with open(file_path, "rb") as file:
                        uploaded_file = self.client.files.create(
                            file=file, purpose="assistants"
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Here's an additional file for our discussion: {os.path.basename(file_path)}",
                                "attachments": [
                                    {
                                        "file_id": uploaded_file.id,
                                        "tools": [{"type": "file_search"}],
                                    }
                                ],
                            }
                        )

                if messages:
                    self.client.beta.threads.messages.create_many(
                        thread_id=thread.id, messages=messages
                    )
                    self.logger.log(f"Attached {len(messages)} files to the thread")

            return thread.id

    def chat(self, message: Union[str, Dict[str, Union[str, bytes]]]) -> str:
        self.logger.log(f"Processing chat message: {message}")
        if isinstance(message, str):
            content = [{"type": "text", "text": message}]
        else:
            content = [
                {"type": "text", "text": message.get("text", "")},
                (
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{message['image']}"
                        },
                    }
                    if "image" in message
                    else None
                ),
            ]
            content = [item for item in content if item is not None]

        try:
            self.logger.log("Creating message in thread")
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id, role="user", content=content
            )
        except Exception as e:
            # self.logger.log(f"Error creating message: {e}")
            if not self.last_run_id:
                self.last_run_id = self.client.beta.threads.runs.list(thread_id=self.thread_id).data[0].id 
            self.logger.log(f"Cancelling run {self.last_run_id}")
            tries = 2
            while tries > 0:
                try:
                    self.client.beta.threads.runs.cancel(
                        thread_id=self.thread_id,
                        run_id=self.last_run_id,
                    )
                except Exception as e:
                    # Sleep for a while
                    tries -= 1
                    time.sleep(1)
                    pass
            self.logger.log("Retrying message creation")
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id, role="user", content=content
            )

        user_details = self.payload.params.get("user_details", {})
        user_name = user_details.get("name", "")
        
        additional_instructions = f""""""
        
        if user_name:
            self.logger.log("Adding user name to instructions")
            additional_instructions += f"""# User Information
**IMPORTANT** Always make sure to address the user by their name in your responses. The user's name is: {user_name}

"""
        
        tmdb_latest_movies = self.request.app.state.tmdb_latest_movies if self.request else []
        if tmdb_latest_movies:
            self.logger.log("Adding TMDB latest movies to instructions")
            additional_instructions += f"""# TMDB Latest Movies
**IMPORTANT** Make sure to also consider the latest movies from TMDB when providing recommendations, along with your own knowledge and insights.
Ensure you do NOT only suggest among the latest movies provided from TMDB:

{json.dumps(tmdb_latest_movies, indent=4)}

"""

        if self.payload.params.get("user_language", None):
            self.logger.log("Adding language instructions")
            lang_instructions, _ = load_and_render_prompt('language', self.payload.params)
            additional_instructions += lang_instructions
            
        if self.action == 'assistant':
            self.logger.log("Adding MojitoMovieStyleGuide specific instructions")
            movie_style_instructions, _ = load_and_render_prompt('mojito_movieStyleGuide', self.payload.params)
            policy_instructions, _ = load_and_render_prompt('mojito_policy', self.payload.params)
            additional_instructions += f"""
{movie_style_instructions}
{policy_instructions}
"""

        # we need to add users's current lists to additional instructions
        if self.action == 'assistant' and self.payload.params.get('user_extra_data', {}).get('favorite_lists', []):
            self.logger.log("Adding assistant specific instructions")
            additional_instructions += f"""
# In the following list, you can see the data about all user favorite lists and the movies within those lists. Each one comes with its ID, which includes the list ID and movie ID. Therefore, this acts as a mapper for all tools wherever you need to convert a list name or movie name to a listID or movie ID. And also, whenever you need the movie ID or list ID to apply an action in a process, make sure to use this to pass the proper and correct list ID or movie ID to any tools that need this data to execute their actions. Rememebr regarding the "Big Five" list the list id ALWAYS is "BIG_FIVE".

```json
{json.dumps(self.payload.params.get('user_extra_data', {}).get('favorite_lists', []), indent=4)}
```

** REMEMBER FOR BIG FIVE LIST THE LIST ID IS ALWAYS "BIG_FIVE" **
## NEVER EVER SHOE LIST ID AND MOVIE ID TO THE USER, JUST USE THEM IN THE BACKGROUND TO EXECUTE ACTIONS.
"""

        # if self.payload.params.get("action") == "what2watch":
        #     self.logger.log("Adding what2watch specific instructions")
        #     add_instructions, _ = load_and_render_prompt('mojito_what2watchAdditional', self.payload.params)
        #     additional_instructions += add_instructions
            
        if self.payload.params.get("action") == "regenerate":
            self.logger.log("Adding regenerate specific instructions")
            user_msg = self.payload.params.get("user_message")
            agent_response = self.payload.params.get("agent_response")
            additional_instructions += f"""Your task is to act as an AI agent that regenerates responses based on prior interactions. Your responses should be consistent and reflect the context of the conversation. You are only capable of regenerating conversations and not performing any actions such as creating lists, or adding movies or TV series to lists.
**IMPORTANT** Ensure your new response is not the same as the original response. It should be a regenerated version.

## User Original Message:
{ user_msg }

## Agent Original Response:
{ agent_response }
"""
        
        elif self.payload.params.get("action") == "talk2me":
            self.logger.log("Adding talk2me specific instructions")
            add_instructions, _ = load_and_render_prompt('mojito_talk2meAdditional', self.payload.params)
            additional_instructions += add_instructions
        
        self.logger.log("Creating run")
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id, 
            assistant_id=self.assistant.id,
            additional_instructions=additional_instructions,
            tool_choice="required" if self.tools else "none",
            max_completion_tokens=5000,
        )
        self.last_run_id = run.id
        self.logger.log(f"Created run with ID: {run.id}")

        self.logger.log(f"Run status loop")
        run_status_time_start = time.time()
        while run.status not in ["completed", "failed", "expired"]:
            # self.logger.log(f"Run status: {run.status}")
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=run.id
            )
            if run.status == "requires_action":
                self.logger.log("Run requires action")
                # TIMER
                tools_time_start = time.time()
                tool_outputs = self._handle_tool_calls(
                    run.required_action.submit_tool_outputs.tool_calls
                )
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread_id, run_id=run.id, tool_outputs=tool_outputs
                )
                # TIMER
                self.logger.log(f"TIMER>> Tool calls handled in {time.time() - tools_time_start:.2f} seconds")

        if run.status != "completed":
            self.logger.log(f"Run ended with status: {run.status}")
            return f"Error: Run ended with status {run.status}"

        # TIMER
        self.logger.log(f"TIMER>> Run completed in {time.time() - run_status_time_start:.2f} seconds")
        self.logger.log("Retrieving messages")
        # TIMER
        t1 = time.time()
        messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)
        # TIMER
        self.logger.log(f"TIMER>> Retrieved messages in {time.time() - t1:.2f} seconds")
        self.logger.log("Returning latest message")
        # assistant_response = messages.data[0].content[0].text.value
        
        # def add_memory_thread():
        #     self.memtor.add_memory(
        #         user_message=message,
        #         assistant_response=assistant_response,
        #         user_id=self.user_id,
        #         session_id=self.thread_id,
        #         agent_id=self.assistant.id
        #     )

        # memory_thread = threading.Thread(target=add_memory_thread)
        # memory_thread.start()
        # memory_thread.join()
        
        return messages.data[0].content[0].text.value

    def add_memory(self, message, assistant_response):
        try:
            self.memtor.add_memory(
                user_message=message,
                assistant_response=assistant_response,
                user_id=self.user_id,
                session_id=self.thread_id,
                agent_id=self.assistant.id
            )
            return True
        except Exception as e:
            self.logger.log(f"""Moji -> Error adding memor: user_id: {self.user_id}, session_id: {self.thread_id}, agent_id: {self.assistant.id}\nError: {e}""")
            Error(f"assistant v2 api >> add_memory", e)
            return False
        
    
    def chat_stream(self, message: Union[str, Dict[str, Union[str, bytes]]]) -> None:
        self.logger.log(f"Processing streaming chat message: {message}")
        if isinstance(message, str):
            content = [{"type": "text", "text": message}]
        else:
            content = [
                {"type": "text", "text": message.get("text", "")},
                (
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{message['image']}"
                        },
                    }
                    if "image" in message
                    else None
                ),
            ]
            content = [item for item in content if item is not None]

        try:
            self.logger.log("Creating message in thread")
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id, role="user", content=content
            )
        except Exception as e:
            self.logger.log(f"Error sending message: {e}")
            self.logger.log("Cancelling previous run")
            self.client.beta.threads.runs.cancel(
                thread_id=self.thread_id,
                run_id=self.client.beta.threads.runs.list(thread_id=self.thread_id)
                .data[0]
                .id,
            )
            self.logger.log("Retrying message creation")
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id, role="user", content=content
            )

        event_handler = MovieAssistantEventHandler(self)

        self.logger.log("Starting stream")
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant.id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()
        self.logger.log("Stream completed")

    def _handle_tool_calls(self, tool_calls):
        self.logger.log("Handling tool calls")
        tool_outputs = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            self.logger.log(f"Handling tool call: {function_name} with arguments: {arguments}")
            
            if function_name in self.tools:
                # self.logger.log(f"Executing function: {function_name}")
                # output = self.tools[function_name](self.db, self.user_id, self.user_token, **arguments)
                # passing self. then tools have access to assistant object and can modify the assistant and its payload.
                output = self.tools[function_name](self, **arguments)
            else:
                self.logger.log(f"Unknown function: {function_name}")
                output = f"Unknown function: {function_name}"
            
            tool_outputs.append({"tool_call_id": tool_call.id, "output": output})
        
        self.logger.log(f"Tool calls handled. Outputs: {tool_outputs}")
        return tool_outputs
        
    def make_return(self, str_response: str) -> Dict[str, Any]:
        self.logger.log(f"Processing assistant response: {str_response[:50]}...")
        # save raw response to db
        try:
            self.db.save_response_log(self.user_id, self.payload.model_dump(), str_response)
        except Exception as e:
            pass
        try:
            json_response = LLMResponse.model_validate_json(str_response)
            return_type = json_response.type
            data = json_response.data.model_dump()
            # self.logger.log(f"Parsed response. Type: {return_type}")
        except Exception as e:
            # self.logger.log(f"Error validating response: {e}")
            json_response = json.loads(str_response)
            return_type = json_response['type']
            data = json_response['data']
        
        response = {
            "output_type": return_type
        }

        if return_type == ResponseTypeEnum.TEXT:
            response['output_type'] = "text"
            response['response'] = data#['content']
        elif return_type == ResponseTypeEnum.MOVIE_JSON:
            if 'movies' in data and data['movies']:
                movies = data['movies']
                data['movies'] = update_movie_response(movies)
            response['response'] = data
        elif return_type == ResponseTypeEnum.LIST:
            # {'items': [{'list_id': 'ea7a7884-d2d1-40ef-8d49-5625ad6e1e30', 'name': 'Movies Like La La Land'}]}
            response['response'] = data.get('items', [])
            # response['response'] = data['response']
            # response['list_id'] = data.get('list_id', None)
        elif return_type == ResponseTypeEnum.MOVIE_INFO:
            if 'related_movies' in data and data['related_movies']:
                movies = data['related_movies']
                data['related_movies'] = update_movie_response(movies)
            response['response'] = data#['answer']
        elif return_type == ResponseTypeEnum.TRAILER:
            response['response'] = data
        else:
            response['response'] = data
        
        # call to check movies against TMDB database
        self.process_movie_data(response)

        self.logger.log(f"Final response: {response}")
        return response
    
    def process_movie_data(self, response: Dict) -> Dict:
        """
        Process movie data from an API response, checking against the TMDB database.
        
        Args:
            response (Dict): API response containing movie data.
        
        Returns:
            Dict: Updated API response with processed movie data.
        """
        if response["output_type"] == "movie_json" and 'movies' in response['response'] and response['response']['movies']:
            self.logger.log("Checking recommended movies against TMDB database")
            # original_num_movies = self.payload.params.get('num_movies', 5)
            try:
                # TIMER
                t1 = time.time()
                tmdb_service = TMDBService()
                tmdb_response = tmdb_service.fast_search_many(response['response']['movies'])
                # TIMER
                self.logger.log(f"TIMER>> TMDB search time: {time.time() - t1:.2f} seconds")
                tmdb_response = [movie for movie in tmdb_response if movie]
                self.logger.log(f"TMDB response received. Number of movies: {len(tmdb_response)}")
                # if len(tmdb_response) > original_num_movies:
                #     self.logger.log(f"Trimming TMDB response to {original_num_movies} movies")
                #     tmdb_response = tmdb_response[:original_num_movies]
                response['response']['movies'] = tmdb_response
            except Exception as e:
                self.logger.log(f"Error checking movies on TMDB: {e}")
                raise Error(f"assistant v2 api >> check movies on tmdb", e)
        elif response["output_type"] == "movie_info" and 'related_movies' in response['response'] and response['response']['related_movies']:
            self.logger.log("Checking related movies against TMDB database")
            try:
                # TIMER
                t1 = time.time()
                tmdb_service = TMDBService()
                tmdb_response = tmdb_service.fast_search_many(response['response']['related_movies'])
                # TIMER
                self.logger.log(f"TIMER>> TMDB search time: {time.time() - t1:.2f} seconds")
                tmdb_response = [movie for movie in tmdb_response if movie]
                self.logger.log(f"TMDB response received. Number of movies: {len(tmdb_response)}")
                response['response']['related_movies'] = tmdb_response
            except Exception as e:
                self.logger.log(f"Error checking movies on TMDB: {e}")
                raise Error(f"assistant v2 api >> check movies on tmdb", e)
        return response
        
    def clear_and_create_thread(self):
        self.logger.log("Clearing thread")
        # thread_id = self.db.get_thread_id_by_action(self.user_id, self.action)
        # if not thread_id:
        #     self.logger.log("No thread found to clear")
        #     return
        # self.client.beta.threads.delete(thread_id=thread_id)
        self.db.delete_thread_id_by_action(self.user_id, self.action)
        
        # thread = self.client.beta.threads.create()
        # self.db.save_thread_id_by_action(self.user_id, thread.id, self.action)
        
        self.logger.log("Thread cleared")
        
    def close(self):
        self.logger.log("Closing database connection")
        self.db.close()


# Additional helper functions
def update_movie_response(movies):
    key_mapping = {'n': 'name', 'y': 'year', 't': 'type', 'l': 'original_language'}
    type_mapping = {'m': 'movie', 'v': 'tv-series', 'c': 'cartoon', 'a': 'anime', 'd': 'documentary', 's': 'short-film', 't': 'tv'}
    try:
        if type(movies) == str:
            movies = json.loads(movies)
    except:
        pass
    movies = [
        {key_mapping.get(k, k): v for k, v in movie.items()} for movie in movies
    ]
    for movie in movies:
        if 'type' in movie:
            movie['type'] = type_mapping.get(movie['type'], movie['type'])
        else:
            movie['type'] = 'movie'
    return movies

def load_and_render_prompt(prompt_name: str, parameters: Dict[str, Any]) -> str:
    """
    Loads a Jinja template and renders it with the provided parameters.

    Args:
        prompt_name (str): Name of the Jinja template file to load.
        parameters (Dict[str, Any]): Dictionary of parameters to use for rendering the template.

    Returns:
        str: Rendered template as a string.
    """
    env_chat_templates = Environment(loader=FileSystemLoader('templates/mojito/v2/chat'))
    env_completion_templates = Environment(loader=FileSystemLoader('templates/mojito/v2/completion'))
    template = None
    rendered_prompt = None
    prompt_name = f'{prompt_name}.jinja2'
    for env in [(env_chat_templates, "chat"), (env_completion_templates, "completion")]:
        try:
            if env[0].get_template(prompt_name):
                template = env[0].get_template(prompt_name)
                rendered_prompt = template.render(**parameters)
                template_type = env[1]
                return rendered_prompt, template_type
        except TemplateNotFound:
            pass
    raise Exception(f"Prompt {prompt_name} not found!")