
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from config import MODELS


##################### Params for OpenAI API #####################
class ParameterHistory(BaseModel):
    """
    Represents a historical parameter, including the role and content.
    """
    role: str
    content: str

class SystemParameters(BaseModel):
    id: str = "sysmsg-default"
    params: Dict[str, Any] = {}

class PromptParameters(BaseModel):
    id: str = "prompt-default"
    params: Dict[str, Any] = {}

class ModelParams(BaseModel):
    model: Optional[str] = MODELS['openai_4o_mini']
    history: Optional[List[ParameterHistory]] = []
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False
    parser: Optional[str] = None

class PromptRequestV2(BaseModel):
    prompt: PromptParameters
    system: SystemParameters = SystemParameters()
    model: ModelParams = ModelParams()
    request_type: Optional[str] = "chat"
    return_prompt: Optional[bool] = False
    parse_json: Optional[bool] = False
    module: Optional[str] = ""

class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    # initial_response: str = Field(..., description="Initial response from the AI")
    message_id: str = Field(..., description="Message ID")
    feedback: str = Field(..., description="Feedback on the AI response")

class TopPicksRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    data: Dict[str, Any] = Field(..., description="Request data")
    suggestion_count: Optional[int] = Field(default=5, description="Number of suggestions to return")

class FavListAdditionRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    data: Dict[str, Any] = Field(..., description="Request data")
    suggestion_count: Optional[int] = Field(default=5, description="Number of suggestions to return")

# TMDB APIs
class TMDBRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    query: str = Field(..., description="Search query for TMDB API")
    max_results: Optional[int] = Field(default=5, description="Maximum number of results to return")
    