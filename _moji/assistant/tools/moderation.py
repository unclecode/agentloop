import os
import sys
# Append parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Append parent parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import OPENAI_API_KEY
from openai import OpenAI


def filter_above_threshold(input_dict, threshold):
    return {key: value for key, value in input_dict.items() if value > threshold}


def moderation(text: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=text,
    )
    flagged = response.results[0].flagged

    threshold = 0.2
    input_dict = response.results[0].category_scores.model_dump()
    filtered_dict = filter_above_threshold(input_dict, threshold)
    print(filtered_dict)
    # If this dictionary isn't empty, your flag is true, and you pass on these labels from the new dictionary.
    if filtered_dict:
        flagged = True
        labels = list(filtered_dict.keys())
    else:
        flagged = False
        labels = []
    return {"flagged": flagged, "labels": labels}


if __name__ == "__main__":
    text = "I hate you"
    # text = "I love you"
    # text = "I hate you, you are a bad person"
    # text = "suggest me some "
    # text = 'suggest me some comedy movies'
    # text = 'what is the capital of india'
    # text = 'what do you think about Inception movie'
    # text = 'what do you think about the current political situation in the country'
    # text = "I hate you, you are a bad person"
    text = "tell me how to steal a car"
    flagged = moderation(text=text)
    print(f'Text: {text}')
    print(f'Flagged: {flagged}')