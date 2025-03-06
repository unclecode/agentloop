Text generation
===============

Learn how to generate text from a prompt.

OpenAI provides simple APIs to use a [large language model](/docs/models) to generate text from a prompt, as you might using [ChatGPT](https://chatgpt.com). These models have been trained on vast quantities of data to understand multimedia inputs and natural language instructions. From these [prompts](/docs/guides/prompt-engineering), models can generate almost any kind of text response, like code, mathematical equations, structured JSON data, or human-like prose.

Quickstart
----------

To generate text, you can use the [chat completions endpoint](/docs/api-reference/chat/) in the REST API, as seen in the examples below. You can either use the [REST API](/docs/api-reference) from the HTTP client of your choice, or use one of OpenAI's [official SDKs](/docs/libraries) for your preferred programming language.

Generate prose

Create a human-like response to a prompt

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
        { role: "developer", content: "You are a helpful assistant." },
        {
            role: "user",
            content: "Write a haiku about recursion in programming.",
        },
    ],
    store: true,
});

console.log(completion.choices[0].message);
```

```python
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "developer", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)
```

```bash
curl "https://api.openai.com/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o",
        "messages": [
            {
                "role": "developer",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Write a haiku about recursion in programming."
            }
        ]
    }'
```

Analyze an image

Describe the contents of an image

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
        {
            role: "user",
            content: [
                { type: "text", text: "What's in this image?" },
                {
                    type: "image_url",
                    image_url: {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                    },
                }
            ],
        },
    ],
    store: true,
});

console.log(completion.choices[0].message);
```

```python
from openai import OpenAI

client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                    }
                },
            ],
        }
    ],
)

print(completion.choices[0].message)
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What is in this image?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
            }
          }
        ]
      }
    ]
  }'
```

Generate JSON data

Generate JSON data based on a JSON Schema

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const completion = await openai.chat.completions.create({
    model: "gpt-4o-2024-08-06",
    messages: [
        { role: "developer", content: "You extract email addresses into JSON data." },
        {
            role: "user",
            content: "Feeling stuck? Send a message to help@mycompany.com.",
        },
    ],
    response_format: {
        // See /docs/guides/structured-outputs
        type: "json_schema",
        json_schema: {
            name: "email_schema",
            schema: {
                type: "object",
                properties: {
                    email: {
                        description: "The email address that appears in the input",
                        type: "string"
                    }
                },
                additionalProperties: false
            }
        }
    },
    store: true,
});

console.log(completion.choices[0].message.content);
```

```python
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=[
        {
            "role": "developer", 
            "content": "You extract email addresses into JSON data."
        },
        {
            "role": "user", 
            "content": "Feeling stuck? Send a message to help@mycompany.com."
        }
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "email_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "email": {
                        "description": "The email address that appears in the input",
                        "type": "string"
                    },
                    "additionalProperties": False
                }
            }
        }
    }
)

print(response.choices[0].message.content);
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "developer",
        "content": "You extract email addresses into JSON data."
      },
      {
        "role": "user",
        "content": "Feeling stuck? Send a message to help@mycompany.com."
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "email_schema",
        "schema": {
            "type": "object",
            "properties": {
                "email": {
                    "description": "The email address that appears in the input",
                    "type": "string"
                }
            },
            "additionalProperties": false
        }
      }
    }
  }'
```

Choosing a model
----------------

When making a text generation request, your first decision is which [model](/docs/models) you want to generate the response. The model you choose influences output and impacts [cost](https://openai.com/api/pricing/).

*   A **large model** like [`gpt-4o`](/docs/models#gpt-4o) offers a very high level of intelligence and strong performance, with higher cost per token.
*   A **small model** like [`gpt-4o-mini`](/docs/models#gpt-4o-mini) offers intelligence not quite on the level of the larger model, but it's faster and less expensive per token.
*   A **reasoning model** like [the `o1` family of models](/docs/models#o1) is slower to return a result, and uses more tokens to "think," but is capable of advanced reasoning, coding, and multi-step planning.

Experiment with different models [in the Playground](/playground) to see which works best for your prompts! You might also benefit from our [model selection best practices](/docs/guides/model-selection).

Building prompts
----------------

The process of crafting prompts to get the right output from a model is called **prompt engineering**. You can improve output by giving the model precise instructions, examples, and necessary context information—like private or specialized information not included in the model's training data.

Below is high-level guidance on building prompts. For more in-depth strategies and tactics, see the [prompt engineering guide](/docs/guides/prompt-engineering).

### Messages and roles

In the [chat completions API](/docs/api-reference/chat/), you create prompts by providing an array of `messages` that contain instructions for the model. Each message can have a different `role`, which influences how the model might interpret the input.

||
|user|Instructions that request some output from the model. Similar to messages you'd type in ChatGPT as an end user.|Pass your end-user's message to the model.Write a haiku about programming.|
|developer|Instructions to the model that are prioritized ahead of user messages, following chain of command. Previously called the system prompt.|Describe how the model should generally behave and respond.You are a helpful assistant
that answers programming
questions in the style of a
southern belle from the
southeast United States.Now, any response to a user message should have a southern belle personality and tone.|
|assistant|A message generated by the model, perhaps in a previous generation request (see the "Conversations" section below).|Provide examples to the model for how it should respond to the current request.For example, to get a model to respond correctly to knock-knock jokes, you might provide a full back-and-forth dialogue of a knock-knock joke.|

Message roles may help you get better responses, especially if you want a model to follow hierarchical instructions. They're not deterministic, so the best way to use them is just trying things and seeing what gives you good results.

Here's an example of a developer message that modifies the behavior of the model when generating a response to a `user` message:

```javascript
const response = await openai.chat.completions.create({
  model: "gpt-4o",
  messages: [
    {
      "role": "developer",
      "content": [
        {
          "type": "text",
          "text": `
            You are a helpful assistant that answers programming 
            questions in the style of a southern belle from the 
            southeast United States.
          `
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Are semicolons optional in JavaScript?"
        }
      ]
    }
  ],
  store: true,
});
```

This prompt returns a text output in the rhetorical style requested:

```text
Well, sugar, that's a fine question you've got there! Now, in the 
world of JavaScript, semicolons are indeed a bit like the pearls 
on a necklace – you might slip by without 'em, but you sure do look 
more polished with 'em in place. 

Technically, JavaScript has this little thing called "automatic 
semicolon insertion" where it kindly adds semicolons for you 
where it thinks they oughta go. However, it's not always perfect, 
bless its heart. Sometimes, it might get a tad confused and cause 
all sorts of unexpected behavior.
```

### Giving the model additional data to use for generation

You can also use the message types above to provide additional information to the model, outside of its training data. You might want to include the results of a database query, a text document, or other resources to help the model generate a relevant response. This technique is often referred to as **retrieval augmented generation**, or RAG. [Learn more about RAG techniques](https://help.openai.com/en/articles/8868588-retrieval-augmented-generation-rag-and-semantic-search-for-gpts).

Conversations and context
-------------------------

While each text generation request is independent and stateless (unless you're using [assistants](/docs/assistants/overview)), you can still implement **multi-turn conversations** by providing additional messages as parameters to your text generation request. Consider a "knock knock" joke:

```javascript
const response = await openai.chat.completions.create({
  model: "gpt-4o",
  messages: [
    {
      "role": "user",
      "content": [{ "type": "text", "text": "knock knock." }]
    },
    {
      "role": "assistant",
      "content": [{ "type": "text", "text": "Who's there?" }]
    },
    {
      "role": "user",
      "content": [{ "type": "text", "text": "Orange." }]
    }
  ],
  store: true,
});
```

By using alternating `user` and `assistant` messages, you capture the previous state of a conversation in one request to the model.

### Managing context for text generation

As your inputs become more complex, or you include more turns in a conversation, you'll need to consider both **output token** and **context window** limits. Model inputs and outputs are metered in [**tokens**](https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them), which are parsed from inputs to analyze their content and intent and assembled to render logical outputs. Models have limits on token usage during the lifecycle of a text generation request.

*   **Output tokens** are the tokens generated by a model in response to a prompt. Each model has different [limits for output tokens](/docs/models). For example, `gpt-4o-2024-08-06` can generate a maximum of 16,384 output tokens.
*   A **context window** describes the total tokens that can be used for both input and output tokens (and for some models, [reasoning tokens](/docs/guides/reasoning)). Compare the [context window limits](/docs/models) of our models. For example, `gpt-4o-2024-08-06` has a total context window of 128k tokens.

If you create a very large prompt (usually by including a lot of conversation context or additional data/examples for the model), you run the risk of exceeding the allocated context window for a model, which might result in truncated outputs.

Use the [tokenizer tool](/tokenizer), built with the [tiktoken library](https://github.com/openai/tiktoken), to see how many tokens are in a particular string of text.

Optimizing model outputs
------------------------

As you iterate on your prompts, you'll continually aim to improve **accuracy**, **cost**, and **latency**. Below, find techniques that optimize for each goal.

||
|Accuracy|Ensure the model produces accurate and useful responses to your prompts.|Accurate responses require that the model has all the information it needs to generate a response, and knows how to go about creating a response (from interpreting input to formatting and styling). Often, this will require a mix of prompt engineering, RAG, and model fine-tuning.Learn more about optimizing for accuracy.|
|Cost|Drive down total cost of using models by reducing token usage and using cheaper models when possible.|To control costs, you can try to use fewer tokens or smaller, cheaper models. Learn more about optimizing for cost.|
|Latency|Decrease the time it takes to generate responses to your prompts.|Optimizing for low latency is a multifaceted process including prompt engineering and parallelism in your own code. Learn more about optimizing for latency.|

Next steps
----------

There's much more to explore in text generation. Here are a few resources to go even deeper.

[

Prompt examples

Get inspired by example prompts for a variety of use cases.

](/docs/examples)[

Build a prompt in the Playground

Use the Playground to develop and iterate on prompts.

](/playground)[

Browse the Cookbook

The Cookbook has complex examples covering a variety of use cases.

](/docs/guides/https://cookbook.openai.com)[

Generate JSON data with Structured Outputs

Ensure JSON data emitted from a model conforms to a JSON schema.

](/docs/guides/structured-outputs)[

Full API reference

Check out all the options for text generation in the API reference.

](/docs/api-reference/chat)

Was this page useful?