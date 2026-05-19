from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class StyleConfigRequest(BaseModel):
    story_type: str
    genre: str
    writing_style: str
    visual_style: str
    art_style: str
    screen_aspect: str
    script_style: str
    script_format: str = ""
    duration_mode: str
    episode_count: str = ""
    episode_duration: str = ""
    custom_requirements: str = ""
    visual_reference: str = ""
    action_reference: str = ""


class CreateProjectRequest(BaseModel):
    name: str
    story_idea: str
    style: StyleConfigRequest
    duration_line: str = ""


class ProjectListItem(BaseModel):
    name: str
    status: str
    created_at: str
    updated_at: str
    current_phase: int
    total_phases: int
    phases: List[Dict[str, Any]]


class SettingsResponse(BaseModel):
    llm_backend: str
    deepseek_api_key: str
    deepseek_model: str
    openai_api_key: str
    openai_model: str
    claude_api_key: str
    claude_model: str
    seedance_api_key: str
    image_backend: str = "seedream"
    custom_image_base_url: str = ""
    custom_image_model: str = "gpt-image-1"
    banana2_api_key: str = ""
    banana2_base_url: str = ""
    banana2_model: str = "nano-banana-2"
    aggregated_enabled: str = ""
    aggregated_base_url: str = ""
    aggregated_api_key: str = ""
    aggregated_llm_model: str = ""
    aggregated_image_model: str = ""
    aggregated_video_model: str = ""


class SettingsUpdateRequest(BaseModel):
    llm_backend: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    deepseek_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    seedance_api_key: Optional[str] = None
    image_backend: Optional[str] = None
    custom_image_base_url: Optional[str] = None
    custom_image_model: Optional[str] = None
    banana2_api_key: Optional[str] = None
    banana2_base_url: Optional[str] = None
    banana2_model: Optional[str] = None
    aggregated_enabled: Optional[str] = None
    aggregated_base_url: Optional[str] = None
    aggregated_api_key: Optional[str] = None
    aggregated_llm_model: Optional[str] = None
    aggregated_image_model: Optional[str] = None
    aggregated_video_model: Optional[str] = None


class TestLLMRequest(BaseModel):
    backend: str
    api_key: str
    model: str


class AggregatedConfigItem(BaseModel):
    id: str = ""
    name: str = ""
    base_url: str = ""
    api_key: str = ""
    type: str = ""  # "llm" | "image" | "video"
    model: str = ""
    active: bool = False


class AggregatedConfigCreate(BaseModel):
    name: str
    base_url: str
    api_key: str
    type: str
    model: str = ""


class AggregatedConfigUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class ProviderConfigCreate(BaseModel):
    provider_id: str
    api_key: str
    model: str = ""
    base_url: str = ""
    name: str = ""


class ProviderConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
