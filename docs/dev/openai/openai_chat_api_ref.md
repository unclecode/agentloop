# OpenAI Chat Completions API

This document describes the OpenAI Chat Completions API, which allows you to generate model responses for a given chat conversation.

---

## 1. Create Chat Completion

**Endpoint:** `POST https://api.openai.com/v1/chat/completions`

**Description:** Creates a model response for the given chat conversation.  Supports text, vision, and audio generation, depending on the model.

**Request Body:**

| Parameter          | Type             | Required | Description                                                                                                                                                                                                                                                           |
| ------------------ | ---------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `messages`         | array            | Yes      | A list of messages comprising the conversation so far.  Different models support different message types (text, images, audio).                                                                                                                                    |
| `model`            | string           | Yes      | ID of the model to use. See the [model endpoint compatibility table](#) for details.                                                                                                                                                                                    |
| `store`            | boolean or null  | No       | Whether to store the output of this completion for model distillation/evals. Defaults to `false`.                                                                                                                                                                 |
| `reasoning_effort` | string or null  | No       | (o1 and o3-mini models only) Constrains effort on reasoning.  Values: `low`, `medium`, `high`. Defaults to `medium`.                                                                                                                                                  |
| `metadata`         | map              | No       | Up to 16 key-value pairs for storing additional information (keys max 64 chars, values max 512 chars).                                                                                                                                                             |
| `frequency_penalty`| number or null  | No       | Number between -2.0 and 2.0.  Positive values penalize new tokens based on frequency, decreasing repetition. Defaults to 0.                                                                                                                                          |
| `logit_bias`       | map              | No       | Modifies the likelihood of specified tokens appearing.  Maps token IDs to bias values (-100 to 100).                                                                                                                                                                  |
| `logprobs`         | boolean or null  | No       | Whether to return log probabilities of output tokens. Defaults to `false`.                                                                                                                                                                                           |
| `top_logprobs`     | integer or null  | No       | If `logprobs` is true, specifies the number of most likely tokens to return (0-20).                                                                                                                                                                                    |
| `max_tokens`       | integer or null  | No       | *Deprecated*. Use `max_completion_tokens` instead.  The maximum number of tokens to generate.                                                                                                                                                                      |
| `max_completion_tokens` | integer or null | No     | An upper bound for the number of tokens generated for completion, including visible and reasoning tokens.                                                                                                                                               |
| `n`                | integer or null  | No       | How many completion choices to generate.  Defaults to 1.  You are charged for all generated tokens.                                                                                                                                                                 |
| `modalities`        | array or null     | No          | Output modalities.  Most models support `["text"]` (default). `gpt-4o-audio-preview` also supports `["audio"]`.  Example: `["text", "audio"]`                                                                        |
|`prediction`|	object|	No|	Configuration for a Predicted Output.|
|`audio`|	object or null|	No|	Parameters for audio output. Required when audio output is requested with modalities: `["audio"]`.|
| `presence_penalty` | number or null  | No       | Number between -2.0 and 2.0.  Positive values penalize new tokens based on presence, encouraging new topics. Defaults to 0.                                                                                                                                           |
| `response_format`  | object           | No       | Specifies the output format. Use `{ "type": "json_schema", "json_schema": {...} }` for Structured Outputs, or  `{ "type": "json_object" }` for JSON mode.  *Requires instructing the model to produce JSON.*                                                             |
| `seed`             | integer or null  | No       | (Beta) If specified, attempts deterministic sampling.                                                                                                                                                                                                            |
| `service_tier`    | string or null   | No      |  Specifies latency tier. `auto` (default) or `default`.                                                                                                                                               |
| `stop`             | string / array / null | No       | Up to 4 sequences where the API will stop generating tokens. Defaults to `null`.                                                                                                                                                                                 |
| `stream`           | boolean or null  | No       | If set, sends partial message deltas as server-sent events. Defaults to `false`.                                                                                                                                                                                   |
| `stream_options`    | object or null | No      |  Options for streaming response. Set only when `stream: true`.                                                                                                                                               |
| `temperature`      | number or null  | No       | Sampling temperature (0-2). Higher = more random. Defaults to 1.  Alter this *or* `top_p`, but not both.                                                                                                                                                              |
| `top_p`            | number or null  | No       | Nucleus sampling parameter. Defaults to 1.  Alter this *or* `temperature`, but not both.                                                                                                                                                                            |
| `tools`            | array            | No       | A list of tools the model may call (currently only functions). Max 128 functions.                                                                                                                                                                                 |
| `tool_choice`      | string or object | No       | Controls which tool is called. `none` (default if no tools), `auto` (default if tools), `required`, or `{"type": "function", "function": {"name": "my_function"}}`.                                                                                                |
| `parallel_tool_calls` | boolean      | No       | Defaults to `true`.  Whether to enable parallel function calling.                                                                                                                                                                                               |
| `user`             | string           | No       | A unique identifier representing your end-user, for abuse monitoring.                                                                                                                                                                                            |
| `function_call`    | string or object | No       | *Deprecated*. Use `tool_choice` instead.                                                                                                                                                                                                                         |
| `functions`        | array            | No       | *Deprecated*. Use `tools` instead.                                                                                                                                                                                                                               |

**Python Example:**

```python
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},  # Changed "developer" to "system"
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message)
```

**Response:**

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "\n\nHello there, how may I assist you today?",
    },
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21,
    "completion_tokens_details": {
      "reasoning_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  }
}
```

---

## 2. Get Chat Completion

**Endpoint:** `GET https://api.openai.com/v1/chat/completions/{completion_id}`

**Description:** Retrieves a *stored* chat completion (created with `store=true`).

**Path Parameters:**

| Parameter       | Type   | Required | Description                                |
| --------------- | ------ | -------- | ------------------------------------------ |
| `completion_id` | string | Yes      | The ID of the chat completion to retrieve. |

... (Python Example and Response similar to provided example)
---
## 3. Get Chat Messages
**Endpoint:** `GET https://api.openai.com/v1/chat/completions/{completion_id}/messages`
**Description:** Get the messages in a stored chat completion. Only chat completions that have been created with the `store` parameter set to `true` will be returned.
**Path Parameters:**

| Parameter       | Type   | Required | Description                                |
| --------------- | ------ | -------- | ------------------------------------------ |
| `completion_id` | string | Yes      | The ID of the chat completion to retrieve messages from. |
**Query Parameters:**

| Parameter | Type    |  Description                                                                                   |
| -------------- | -------------- |  --------------------------------------------------------------------------------------------- |
|`after`|	string	|Identifier for the last message from the previous pagination request.|
|`limit`	|integer	|Number of messages to retrieve. Defaults to 20|
|`order`	|string|	Sort order for messages by timestamp. Use `asc` for ascending order or `desc` for descending order. Defaults to `asc`.|
... (Python Example and Response similar to provided example)
---
## 4. List Chat Completions

**Endpoint:** `GET https://api.openai.com/v1/chat/completions`

**Description:** Lists *stored* chat completions (created with `store=true`).

**Query Parameters:**

| Parameter   | Type    |  Description                                                                                   |
| -------------- | -------------- |  --------------------------------------------------------------------------------------------- |
|`model`|	string	|The model used to generate the chat completions.|
|`metadata`|	*No description*	|A list of metadata keys to filter the chat completions by. Example:  `metadata[key1]=value1&metadata[key2]=value2`|
|`after`|	string	|Identifier for the last chat completion from the previous pagination request.|
|`limit`	|integer|	Number of chat completions to retrieve. Defaults to 20|
|`order`	|string|	Sort order for chat completions by timestamp. Use `asc` for ascending order or `desc` for descending order. Defaults to `asc`.|

... (Python Example and Response similar to provided example)

---

## 5. Update Chat Completion

**Endpoint:** `POST https://api.openai.com/v1/chat/completions/{completion_id}`

**Description:** Modifies a *stored* chat completion (created with `store=true`).  Currently, only `metadata` can be updated.

**Path Parameters:**

| Parameter       | Type   | Required | Description                               |
| --------------- | ------ | -------- | ----------------------------------------- |
| `completion_id` | string | Yes      | The ID of the chat completion to update. |

**Request Body:**

| Parameter  | Type | Required | Description                                                                         |
| ---------- | ---- | -------- | ----------------------------------------------------------------------------------- |
| `metadata` | map  | Yes      | Up to 16 key-value pairs for storing additional information (max 64/512 chars). |

... (Python Example and Response similar to provided example)

---

## 6. Delete Chat Completion

**Endpoint:** `DELETE https://api.openai.com/v1/chat/completions/{completion_id}`

**Description:** Deletes a *stored* chat completion (created with `store=true`).

**Path Parameters:**

| Parameter       | Type   | Required | Description                               |
| --------------- | ------ | -------- | ----------------------------------------- |
| `completion_id` | string | Yes      | The ID of the chat completion to delete. |

... (Python Example and Response similar to provided example)

---
## 7. The Chat Completion Object

**Description:** Represents a chat completion response.

**Properties:**

| Parameter          | Type   | Description                                                                                                                  |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `id`               | string | A unique identifier for the chat completion.                                                                               |
| `choices`          | array  | A list of chat completion choices.  Multiple choices if `n > 1`.                                                             |
| `created`          | integer | The Unix timestamp (in seconds) of when the completion was created.                                                          |
| `model`            | string | The model used for the chat completion.                                                                                     |
|`service_tier`|	string or null|	The service tier used for processing the request.|
| `system_fingerprint` | string | Represents the backend configuration.  Use with `seed` to monitor for changes impacting determinism.                         |
| `object`           | string | The object type, which is always `chat.completion`.                                                                         |
| `usage`            | object | Usage statistics for the completion request.                                                                                |

**Object Example:**

```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1728933352,
  "model": "gpt-4o-2024-08-06",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hi there! How can I assist you today?",
        "refusal": null
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 19,
    "completion_tokens": 10,
    "total_tokens": 29,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  },
  "system_fingerprint": "fp_6b68a8204b"
}
```
---
## 8. The Chat Completion Chunk Object
**Description:** Represents a streamed chunk of a chat completion response returned by model, based on the provided input.
**Properties:**

| Parameter          | Type   | Description                                                                                                                  |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
|`id`|	string	|A unique identifier for the chat completion. Each chunk has the same ID.|
|`choices`|	array	|A list of chat completion choices. Can contain more than one elements if `n` is greater than 1. Can also be empty for the last chunk if you set `stream_options`: `{"include_usage": true}`.|
|`created`|	integer	|The Unix timestamp (in seconds) of when the chat completion was created. Each chunk has the same timestamp.|
|`model`|	string	|The model to generate the completion.|
|`service_tier`|	string or null	|The service tier used for processing the request.|
|`system_fingerprint`|	string	|This fingerprint represents the backend configuration that the model runs with. Can be used in conjunction with the `seed` request parameter to understand when backend changes have been made that might impact determinism.|
|`object`	|string	|The object type, which is always `chat.completion.chunk`.|
|`usage`	|object or null|		An optional field that will only be present when you set `stream_options`: `{"include_usage": true}` in your request. When present, it contains a `null` value except for the last chunk which contains the token usage statistics for the entire request.|

**Object Example:**

```json
{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}
```
---
## 9. The Chat Completion List Object
**Description:** An object representing a list of chat completions.
**Properties:**

| Parameter          | Type   | Description                                                                                                                  |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
|`object`|	string	|The type of this object. It is always set to `"list"`.|
|`data`	|array	|An array of chat completion objects.|
|`first_id`|	string	|The identifier of the first chat completion in the data array.|
|`last_id`|	string	|The identifier of the last chat completion in the data array.|
|`has_more`|	boolean	|Indicates whether there are more chat completions available.|
**Object Example:**

```json
{
  "object": "list",
  "data": [
    {
      "object": "chat.completion",
      "id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2",
      "model": "gpt-4o-2024-08-06",
      "created": 1738960610,
      "request_id": "req_ded8ab984ec4bf840f37566c1011c417",
      "tool_choice": null,
      "usage": {
        "total_tokens": 31,
        "completion_tokens": 18,
        "prompt_tokens": 13
      },
      "seed": 4944116822809979520,
      "top_p": 1.0,
      "temperature": 1.0,
      "presence_penalty": 0.0,
      "frequency_penalty": 0.0,
      "system_fingerprint": "fp_50cad350e4",
      "input_user": null,
      "service_tier": "default",
      "tools": null,
      "metadata": {},
      "choices": [
        {
          "index": 0,
          "message": {
            "content": "Mind of circuits hum,  \nLearning patterns in silence—  \nFuture's quiet spark.",
            "role": "assistant",
            "tool_calls": null,
            "function_call": null
          },
          "finish_reason": "stop",
          "logprobs": null
        }
      ],
      "response_format": null
    }
  ],
  "first_id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2",
  "last_id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2",
  "has_more": false
}
```

---
## 10. The Chat Completion Message List Object
**Description:** An object representing a list of chat completion messages.

**Properties:**

| Parameter          | Type   | Description                                                                                                                  |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
|`object`|	string	|The type of this object. It is always set to "list".|
|`data`|	array|		An array of chat completion message objects.|
|`first_id`|	string	|The identifier of the first chat message in the data array.|
|`last_id`|	string	|The identifier of the last chat message in the data array.|
|`has_more`|	boolean|	Indicates whether there are more chat messages available.|

**Object Example:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2-0",
      "role": "user",
      "content": "write a haiku about ai",
      "name": null,
      "content_parts": null
    }
  ],
  "first_id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2-0",
  "last_id": "chatcmpl-AyPNinnUqUDYo9SAdA52NobMflmj2-0",
  "has_more": false
}
```

---
