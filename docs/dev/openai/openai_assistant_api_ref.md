# OpenAI Assistants API

This document outlines the OpenAI Assistants API, which allows you to build AI assistants that can call models and use tools to perform tasks.

**Core Concepts:**

*   **Assistants:**  Represent the AI itself, configured with a model, instructions, and tools.
*   **Threads:**  Represent a conversation session with an assistant.  Think of it as a single "chat" with the assistant.
*   **Messages:**  Individual messages within a thread, either from the user or the assistant.
*   **Runs:**  An execution instance of an assistant on a thread.  This is where the assistant processes messages and potentially uses tools.

---

## 1. Assistants

Represents an assistant that can call models and use tools.

### 1.1.  `Create Assistant`

**Endpoint:** `POST https://api.openai.com/v1/assistants`

**Description:** Creates a new assistant.

**Request Body:**

| Parameter             | Type             | Required | Description                                                                                                                                                                |
| --------------------- | ---------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model`               | string           | Yes      | ID of the model to use.  (e.g., `gpt-4o`). See [List Models API](#) or [Model Overview](#) for options.                                                                 |
| `name`                | string or null   | No       | The name of the assistant (max 256 characters).                                                                                                                            |
| `description`         | string or null   | No       | A description of the assistant (max 512 characters).                                                                                                                      |
| `instructions`        | string or null   | No       | System instructions for the assistant (max 256,000 characters).  This guides the assistant's behavior.                                                                       |
| `reasoning_effort`    | string or null   | No       | (o1 and o3-mini models only) Constrains effort on reasoning. Supported: `low`, `medium`, `high`. Defaults to `medium`.                                                     |
| `tools`               | array            | No       | A list of tools enabled for the assistant (max 128).  Possible types: `code_interpreter`, `file_search`, `function`.                                                     |
| `tool_resources`       | object or null     | No         | set of resources that are used by the assistant's tools. For `code_interpreter` provide list of file IDs. For `file_search` provide a list of vector store IDs. |
| `metadata`            | map              | No       | Up to 16 key-value pairs for storing additional information (keys max 64 chars, values max 512 chars).                                                                |
| `temperature`         | number or null   | No       | Controls randomness (0-2). Higher = more random. Defaults to 1.                                                                                                           |
| `top_p`               | number or null   | No       | Nucleus sampling parameter.  Alternative to temperature. Defaults to 1.                                                                                                     |
| `response_format`     | "auto" or object | No       | Specifies the format of the model's output. Compatible with GPT-4o, GPT-4 Turbo, and GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`. Use `{ "type": "json_object" }` for JSON mode. |

**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

my_assistant = client.beta.assistants.create(
    instructions="You are a personal math tutor.  Write and run Python code to answer questions.",
    name="Math Tutor",
    tools=[{"type": "code_interpreter"}],
    model="gpt-4o",
)
print(my_assistant)
```

**Response:**

```json
{
  "id": "asst_abc123",
  "object": "assistant",
  "created_at": 1698984975,
  "name": "Math Tutor",
  "description": null,
  "model": "gpt-4o",
  "instructions": "You are a personal math tutor. When asked a question, write and run Python code to answer the question.",
  "tools": [
    {
      "type": "code_interpreter"
    }
  ],
  "metadata": {},
  "top_p": 1.0,
  "temperature": 1.0,
  "response_format": "auto"
}
```
### 1.2. `List Assistants`
**Endpoint:** `GET https://api.openai.com/v1/assistants`
**Description:** Returns a list of assistants.
**Query Parameters:**

| Parameter | Type    | Required | Description                                                                                                                                                     |
| --------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `limit`   | integer | No       | Number of objects to return (1-100, default 20).                                                                                                              |
| `order`   | string  | No       | Sort order by `created_at` (`asc` or `desc`, default `desc`).                                                                                                   |
| `after`   | string  | No       | Cursor for pagination (object ID).                                                                                                                              |
| `before`  | string  | No       | Cursor for pagination (object ID).                                                                                                                              |
... (rest of List Assistants, similar structure to Create Assistant)
**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

my_assistants = client.beta.assistants.list(
    order="desc",
    limit="20",
)
print(my_assistants.data)
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "asst_abc123",
      "object": "assistant",
      "created_at": 1698982736,
      "name": "Coding Tutor",
      "description": null,
      "model": "gpt-4o",
      "instructions": "You are a helpful assistant designed to make me better at coding!",
      "tools": [],
      "tool_resources": {},
      "metadata": {},
      "top_p": 1.0,
      "temperature": 1.0,
      "response_format": "auto"
    },
    {
      "id": "asst_abc456",
      "object": "assistant",
      "created_at": 1698982718,
      "name": "My Assistant",
      "description": null,
      "model": "gpt-4o",
      "instructions": "You are a helpful assistant designed to make me better at coding!",
      "tools": [],
      "tool_resources": {},
      "metadata": {},
      "top_p": 1.0,
      "temperature": 1.0,
      "response_format": "auto"
    },
    {
      "id": "asst_abc789",
      "object": "assistant",
      "created_at": 1698982643,
      "name": null,
      "description": null,
      "model": "gpt-4o",
      "instructions": null,
      "tools": [],
      "tool_resources": {},
      "metadata": {},
      "top_p": 1.0,
      "temperature": 1.0,
      "response_format": "auto"
    }
  ],
  "first_id": "asst_abc123",
  "last_id": "asst_abc789",
  "has_more": false
}
```

### 1.3. `Retrieve Assistant`

**Endpoint:** `GET https://api.openai.com/v1/assistants/{assistant_id}`

**Description:** Retrieves an assistant.

**Path Parameters:**

| Parameter      | Type   | Required | Description                       |
| -------------- | ------ | -------- | --------------------------------- |
| `assistant_id` | string | Yes      | The ID of the assistant to retrieve. |
... (rest of Retrieve Assistant, similar structure)

**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

my_assistant = client.beta.assistants.retrieve("asst_abc123")
print(my_assistant)
```

**Response:**

```json
{
  "id": "asst_abc123",
  "object": "assistant",
  "created_at": 1699009709,
  "name": "HR Helper",
  "description": null,
  "model": "gpt-4o",
  "instructions": "You are an HR bot, and you have access to files to answer employee questions about company policies.",
  "tools": [
    {
      "type": "file_search"
    }
  ],
  "metadata": {},
  "top_p": 1.0,
  "temperature": 1.0,
  "response_format": "auto"
}
```

### 1.4. `Modify Assistant`

**Endpoint:** `POST https://api.openai.com/v1/assistants/{assistant_id}`

**Description:** Modifies an assistant.  Allows updating most fields of an existing assistant.

**Path Parameters:**

| Parameter      | Type   | Required | Description                       |
| -------------- | ------ | -------- | --------------------------------- |
| `assistant_id` | string | Yes      | The ID of the assistant to modify. |

**Request Body:**  (Same parameters as *Create Assistant*, but all are *Optional*).
... (rest of Modify Assistant, similar structure)

**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

my_updated_assistant = client.beta.assistants.update(
  "asst_abc123",
  instructions="You are an HR bot, and you have access to files to answer employee questions about company policies. Always response with info from either of the files.",
  name="HR Helper",
  tools=[{"type": "file_search"}],
  model="gpt-4o"
)

print(my_updated_assistant)
```

**Response:**

```json
{
  "id": "asst_123",
  "object": "assistant",
  "created_at": 1699009709,
  "name": "HR Helper",
  "description": null,
  "model": "gpt-4o",
  "instructions": "You are an HR bot, and you have access to files to answer employee questions about company policies. Always response with info from either of the files.",
  "tools": [
    {
      "type": "file_search"
    }
  ],
  "tool_resources": {
    "file_search": {
      "vector_store_ids": []
    }
  },
  "metadata": {},
  "top_p": 1.0,
  "temperature": 1.0,
  "response_format": "auto"
}
```

### 1.5. `Delete Assistant`

**Endpoint:** `DELETE https://api.openai.com/v1/assistants/{assistant_id}`

**Description:** Deletes an assistant.

**Path Parameters:**

| Parameter      | Type   | Required | Description                       |
| -------------- | ------ | -------- | --------------------------------- |
| `assistant_id` | string | Yes      | The ID of the assistant to delete. |

... (rest of Delete Assistant)
**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

response = client.beta.assistants.delete("asst_abc123")
print(response)
```

**Response:**
```json
{
  "id": "asst_abc123",
  "object": "assistant.deleted",
  "deleted": true
}
```
### 1.6 The assistant object

**Description:** Represents an assistant that can call the model and use tools.
**Properties**

| Parameter             | Type             |  Description                                                                                                                                                                |
| --------------------- | ---------------- |  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`               | string           |  The identifier, which can be referenced in API endpoints.                                                                 |
| `object`                | string   | The object type, which is always assistant.                                                                                                                            |
| `created_at`         | integer   |  The Unix timestamp (in seconds) for when the assistant was created.                                                                                                                     |
| `name`                | string or null   |  The name of the assistant. The maximum length is 256 characters.                                                                                                                            |
| `description`         | string or null   |  The description of the assistant. The maximum length is 512 characters.                                                                                                                      |
| `instructions`        | string or null   |  System instructions for the assistant (max 256,000 characters).  This guides the assistant's behavior.                                                                       |
| `model`               | string           | ID of the model to use.  (e.g., `gpt-4o`). See [List Models API](#) or [Model Overview](#) for options.                                                                 |
| `tools`               | array            |  A list of tool enabled on the assistant. There can be a maximum of 128 tools per assistant. Tools can be of types code_interpreter, file_search, or function.                                                     |
| `tool_resources`       | object or null     | set of resources that are used by the assistant's tools. For `code_interpreter` provide list of file IDs. For `file_search` provide a list of vector store IDs. |
| `metadata`            | map              |  Up to 16 key-value pairs for storing additional information (keys max 64 chars, values max 512 chars).                                                                |
| `temperature`         | number or null   |  Controls randomness (0-2). Higher = more random. Defaults to 1.                                                                                                           |
| `top_p`               | number or null   |  Nucleus sampling parameter.  Alternative to temperature. Defaults to 1.                                                                                                     |
| `response_format`     | "auto" or object |  Specifies the format of the model's output. Compatible with GPT-4o, GPT-4 Turbo, and GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`. Use `{ "type": "json_object" }` for JSON mode. |

**Object Example:**

```json
{
  "id": "asst_abc123",
  "object": "assistant",
  "created_at": 1698984975,
  "name": "Math Tutor",
  "description": null,
  "model": "gpt-4o",
  "instructions": "You are a personal math tutor. When asked a question, write and run Python code to answer the question.",
  "tools": [
    {
      "type": "code_interpreter"
    }
  ],
  "metadata": {},
  "top_p": 1.0,
  "temperature": 1.0,
  "response_format": "auto"
}
```
---
## 2. Threads

Represents a conversation thread.

### 2.1. `Create Thread`
**Endpoint:** `POST https://api.openai.com/v1/threads`
**Description:** Create a thread.
**Request Body:**

| Parameter      | Type           | Required | Description                                                                                   |
| -------------- | -------------- | -------- | --------------------------------------------------------------------------------------------- |
| `messages`     | array          | No       | A list of messages to start the thread with.                                                 |
|`tool_resources`|	object or null|	No|	A set of resources that are made available to the assistant's tools in this thread|
| `metadata`     | map            | No       | Up to 16 key-value pairs for storing additional information.                                  |

... (rest of Create Thread)

**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

empty_thread = client.beta.threads.create()
print(empty_thread)
```

**Response:**
```json
{
  "id": "thread_abc123",
  "object": "thread",
  "created_at": 1699012949,
  "metadata": {},
  "tool_resources": {}
}
```

### 2.2. `Retrieve Thread`
... (similar to Retrieve Assistant)
### 2.3. `Modify Thread`
... (similar to Modify Assistant)
### 2.4. `Delete Thread`
... (similar to Delete Assistant)
### 2.5 The thread object
**Description:** Represents a thread that contains messages.

**Properties:**

| Parameter      | Type           |  Description                                                                                   |
| -------------- | -------------- |  --------------------------------------------------------------------------------------------- |
|`id`|	string	|The identifier, which can be referenced in API endpoints.|
|`object`|	string|	The object type, which is always thread.|
|`created_at`|	integer|	The Unix timestamp (in seconds) for when the thread was created.|
| `tool_resources`       | object or null     | set of resources that are made available to the assistant's tools in this thread. For `code_interpreter` provide list of file IDs. For `file_search` provide a list of vector store IDs. |
| `metadata`     | map            |  Up to 16 key-value pairs for storing additional information.                                  |

**Object Example:**

```json
{
  "id": "thread_abc123",
  "object": "thread",
  "created_at": 1698107661,
  "metadata": {}
}
```
---
## 3. Messages
Work with messages within a thread.

### 3.1. `Create Message`

**Endpoint:** `POST https://api.openai.com/v1/threads/{thread_id}/messages`

**Description:** Creates a new message within a thread.

**Path Parameters:**

| Parameter   | Type   | Required | Description                                     |
| ----------- | ------ | -------- | ----------------------------------------------- |
| `thread_id` | string | Yes      | The ID of the thread to create a message for. |

**Request Body:**

| Parameter     | Type           | Required | Description                                                                                                                               |
| ------------- | -------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `role`        | string         | Yes      | The role of the message creator (`user` or `assistant`).  Use `user` for most messages.                                                  |
| `content`     | string or array| Yes      | The content of the message.                                                                                                  |
| `attachments` | array or null  |  No      |   A list of files attached to the message, and the tools they should be added to.   |
| `metadata`    | map            | No       | Up to 16 key-value pairs for storing additional information.                                                                               |
...
**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

thread_message = client.beta.threads.messages.create(
  "thread_abc123",
  role="user",
  content="How does AI work? Explain it in simple terms.",
)
print(thread_message)
```

**Response:**
```json
{
  "id": "msg_abc123",
  "object": "thread.message",
  "created_at": 1713226573,
  "assistant_id": null,
  "thread_id": "thread_abc123",
  "run_id": null,
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": {
        "value": "How does AI work? Explain it in simple terms.",
        "annotations": []
      }
    }
  ],
  "attachments": [],
  "metadata": {}
}
```

### 3.2. `List Messages`
...
### 3.3. `Retrieve Message`
...
### 3.4. `Modify Message`
...
### 3.5. `Delete Message`
...
### 3.6 The message object
**Description:** Represents a message within a thread.

**Properties:**

| Parameter      | Type           |  Description                                                                                   |
| -------------- | -------------- |  --------------------------------------------------------------------------------------------- |
|`id`|	string	|The identifier, which can be referenced in API endpoints.|
|`object`|	string|	The object type, which is always `thread.message`.|
|`created_at`|	integer|	The Unix timestamp (in seconds) for when the message was created.|
|`thread_id`|	string	|The thread ID that this message belongs to.|
|`status`|	string	|The status of the message, which can be either `in_progress`, `incomplete`, or `completed`.|
|`incomplete_details`|	object or null	|On an incomplete message, details about why the message is incomplete.|
|`completed_at`|	integer or null|		The Unix timestamp (in seconds) for when the message was completed.|
|`incomplete_at`|	integer or null	|The Unix timestamp (in seconds) for when the message was marked as incomplete.|
|`role`|	string	|The entity that produced the message. One of `user` or `assistant`.|
|`content`|	array	|The content of the message in array of text and/or images.|
|`assistant_id`|	string or null|		If applicable, the ID of the assistant that authored this message.|
|`run_id`|	string or null	|The ID of the run associated with the creation of this message. Value is `null` when messages are created manually using the create message or create thread endpoints.|
|`attachments`| array or null | A list of files attached to the message, and the tools they were added to.                                                 |
| `metadata`     | map            |  Up to 16 key-value pairs for storing additional information.                                  |

**Object Example:**

```json
{
  "id": "msg_abc123",
  "object": "thread.message",
  "created_at": 1698983503,
  "thread_id": "thread_abc123",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": {
        "value": "Hi! How can I help you today?",
        "annotations": []
      }
    }
  ],
  "assistant_id": "asst_abc123",
  "run_id": "run_abc123",
  "attachments": [],
  "metadata": {}
}
```

---

## 4. Runs

Represents an execution of an assistant on a thread.

### 4.1. `Create Run`

**Endpoint:** `POST https://api.openai.com/v1/threads/{thread_id}/runs`

**Description:**  Starts a run of an assistant on a thread.

**Path Parameters:**

| Parameter   | Type   | Required | Description                               |
| ----------- | ------ | -------- | ----------------------------------------- |
| `thread_id` | string | Yes      | The ID of the thread to run the assistant on. |

**Request Body:**

| Parameter                 | Type             | Required | Description                                                                                                                                   |
| ------------------------- | ---------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `assistant_id`            | string           | Yes      | The ID of the assistant to use for this run.                                                                                                   |
| `model`                   | string           | No       | Override the assistant's model for this run.                                                                                                  |
| `reasoning_effort`        | string or null   | No       | (o1 and o3-mini models only) Constrains effort on reasoning. Supported: `low`, `medium`, `high`. Defaults to `medium`.                         |
| `instructions`            | string or null   | No       | Override the assistant's instructions for this run.                                                                                           |
| `additional_instructions` | string or null   | No       | Appends additional instructions.                                                                                                             |
| `additional_messages`     | array or null    | No       | Adds additional messages to the thread before creating the run.                                                                               |
| `tools`                   | array or null    | No       | Override the assistant's tools for this run.                                                                                                   |
| `metadata`                | map              | No       | Up to 16 key-value pairs for storing additional information.                                                                                  |
|`temperature`	|number or null	|No	|Defaults to 1 What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.|
|`top_p`|	number or null|		No|	Defaults to 1 An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered. We generally recommend altering this or temperature but not both.|
|`stream`|	boolean or null	|No	|If true, returns a stream of events that happen during the Run as server-sent events, terminating when the Run enters a terminal state with a data: [DONE] message.|
|`max_prompt_tokens`|	integer or null|	No	|The maximum number of prompt tokens that may be used over the course of the run. The run will make a best effort to use only the number of prompt tokens specified, across multiple turns of the run. If the run exceeds the number of prompt tokens specified, the run will end with status incomplete. See incomplete_details for more info.|
|`max_completion_tokens`|	integer or null	|No	|The maximum number of completion tokens that may be used over the course of the run. The run will make a best effort to use only the number of completion tokens specified, across multiple turns of the run. If the run exceeds the number of completion tokens specified, the run will end with status incomplete. See incomplete_details for more info.|
|`truncation_strategy`	|object	|No	|Controls for how a thread will be truncated prior to the run. Use this to control the intial context window of the run.|
|`tool_choice`|		string or object|	No|	Controls which (if any) tool is called by the model. `none` means the model will not call any tools and instead generates a message. `auto` is the default value and means the model can pick between generating a message or calling one or more tools. `required` means the model must call one or more tools before responding to the user. Specifying a particular tool like `{"type": "file_search"}` or `{"type": "function", "function": {"name": "my_function"}}` forces the model to call that tool.|
|`parallel_tool_calls`|	boolean	|No|	Defaults to `true` Whether to enable parallel function calling during tool use.|
| `response_format`     | "auto" or object | No       | Specifies the format of the model's output.  |
... (rest of Create Run, including streaming examples)
**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

run = client.beta.threads.runs.create(
  thread_id="thread_abc123",
  assistant_id="asst_abc123"
)

print(run)
```

**Response:**
```json
{
  "id": "run_abc123",
  "object": "thread.run",
  "created_at": 1699063290,
  "assistant_id": "asst_abc123",
  "thread_id": "thread_abc123",
  "status": "queued",
  "started_at": 1699063290,
  "expires_at": null,
  "cancelled_at": null,
  "failed_at": null,
  "completed_at": 1699063291,
  "last_error": null,
  "model": "gpt-4o",
  "instructions": null,
  "incomplete_details": null,
  "tools": [
    {
      "type": "code_interpreter"
    }
  ],
  "metadata": {},
  "usage": null,
  "temperature": 1.0,
  "top_p": 1.0,
  "max_prompt_tokens": 1000,
  "max_completion_tokens": 1000,
  "truncation_strategy": {
    "type": "auto",
    "last_messages": null
  },
  "response_format": "auto",
  "tool_choice": "auto",
  "parallel_tool_calls": true
}
```
### 4.2. `Create Thread and Run`
... (Combines thread creation and run initiation)
### 4.3. `List Runs`
...
### 4.4. `Retrieve Run`
...
### 4.5. `Modify Run`
... (Only allows modifying metadata)
### 4.6. `Submit Tool Outputs to Run`
... (Used when a run requires tool output)
### 4.7. `Cancel a Run`
... (Cancels a run that's in progress)
### 4.8 The run object
**Description:** Represents an execution run on a thread.

**Properties:**

| Parameter      | Type           |  Description                                                                                   |
| -------------- | -------------- |  --------------------------------------------------------------------------------------------- |
|`id`|	string|		The identifier, which can be referenced in API endpoints.|
|`object`|	string	|	The object type, which is always `thread.run`.|
|`created_at`|	integer	|	The Unix timestamp (in seconds) for when the run was created.|
|`thread_id`|		string|	The ID of the thread that was executed on as a part of this run.|
|`assistant_id`|	string	|	The ID of the assistant used for execution of this run.|
|`status`|	string	|	The status of the run, which can be either `queued`, `in_progress`, `requires_action`, `cancelling`, `cancelled`, `failed`, `completed`, `incomplete`, or `expired`.|
|`required_action`	|object or null|		Details on the action required to continue the run. Will be `null` if no action is required.|
|`last_error`|	object or null	|	The last error associated with this run. Will be `null` if there are no errors.|
|`expires_at`|	integer or null|		The Unix timestamp (in seconds) for when the run will expire.|
|`started_at`	|integer or null	|	The Unix timestamp (in seconds) for when the run was started.|
|`cancelled_at`|	integer or null		|The Unix timestamp (in seconds) for when the run was cancelled.|
|`failed_at`	|integer or null		|The Unix timestamp (in seconds) for when the run failed.|
|`completed_at`	|integer or null	|	The Unix timestamp (in seconds) for when the run was completed.|
|`incomplete_details`|	object or null		|Details on why the run is incomplete. Will be null if the run is not incomplete.|
|`model`|	string	|	The model that the assistant used for this run.|
|`instructions`|	string|		The instructions that the assistant used for this run.|
|`tools`	|array	|	The list of tools that the assistant used for this run.|
| `metadata`                | map              | Up to 16 key-value pairs for storing additional information.                                                                                  |
|`usage`|		object or null|	Usage statistics related to the run. This value will be `null` if the run is not in a terminal state (i.e. `in_progress`, `queued`, etc.).|
|`temperature`	|number or null	| The sampling temperature used for this run. If not set, defaults to 1.|
|`top_p`|	number or null|	 The nucleus sampling value used for this run. If not set, defaults to 1.|
|`max_prompt_tokens`|	integer or null|	The maximum number of prompt tokens specified to have been used over the course of the run.|
|`max_completion_tokens`|	integer or null	|The maximum number of completion tokens specified to have been used over the course of the run.|
|`truncation_strategy`	|object	|Controls for how a thread will be truncated prior to the run. Use this to control the intial context window of the run.|
|`tool_choice`|		string or object|	Controls which (if any) tool is called by the model. `none` means the model will not call any tools and instead generates a message. `auto` is the default value and means the model can pick between generating a message or calling one or more tools. `required` means the model must call one or more tools before responding to the user. Specifying a particular tool like `{"type": "file_search"}` or `{"type": "function", "function": {"name": "my_function"}}` forces the model to call that tool.|
|`parallel_tool_calls`|	boolean	| Whether to enable parallel function calling during tool use.|
| `response_format`     | "auto" or object | Specifies the format of the model's output.  |

---
