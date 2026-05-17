"""Centralized model registry with provider-based grouping.

This file defines all available models grouped by provider/backend type.
It is used by:
  - server/routes/settings.py → /api/settings/models endpoint
  - server/routes/images.py  → image generation
  - server/routes/gen.py     → video/image generation
"""

# Text/LLM models grouped by provider
LLM_MODELS = {
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            {"value": "deepseek-chat", "label": "DeepSeek Chat"},
            {"value": "deepseek-reasoner", "label": "DeepSeek Reasoner"},
            {"value": "siliconflow/deepseek-v3.2", "label": "DS V3.2 (SiliconFlow)"},
            {"value": "siliconflow/deepseek-v3-0324", "label": "DS V3 (SiliconFlow)"},
            {"value": "siliconflow/deepseek-r1-0528", "label": "DS R1 (SiliconFlow)"},
        ]
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            {"value": "gpt-4o", "label": "GPT-4o"},
            {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"value": "gpt-4", "label": "GPT-4"},
            {"value": "o1", "label": "o1"},
            {"value": "o1-mini", "label": "o1 Mini"},
            {"value": "o3-mini", "label": "o3 Mini"},
            {"value": "gpt-4.5-preview", "label": "GPT-4.5 Preview"},
        ]
    },
    "claude": {
        "name": "Claude",
        "models": [
            {"value": "claude-opus-4-7", "label": "Claude Opus 4-7"},
            {"value": "claude-opus-4-5", "label": "Claude Opus 4-5"},
            {"value": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
            {"value": "claude-haiku-4-5", "label": "Claude Haiku 4-5"},
        ]
    },
    "qwen": {
        "name": "Qwen/千问",
        "models": [
            {"value": "qwen3-max", "label": "Qwen3 Max"},
            {"value": "qwen3.5-plus", "label": "Qwen3.5 Plus"},
            {"value": "qwen3.5-flash", "label": "Qwen3.5 Flash"},
            {"value": "qwen3-coder", "label": "Qwen3 Coder"},
            {"value": "qwq-plus", "label": "QWQ Plus"},
            {"value": "qvq-max", "label": "QVQ Max"},
        ]
    },
    "glm": {
        "name": "GLM/智谱",
        "models": [
            {"value": "glm-5", "label": "GLM-5"},
            {"value": "glm-4", "label": "GLM-4"},
            {"value": "glm-4-airx", "label": "GLM-4 AirX"},
            {"value": "glm-4-flash", "label": "GLM-4 Flash"},
        ]
    },
    "gemini": {
        "name": "Gemini/Google",
        "models": [
            {"value": "gemini-3-pro-preview", "label": "Gemini 3 Pro"},
            {"value": "gemini-2.5-flash-preview", "label": "Gemini 2.5 Flash"},
        ]
    },
    "kimi": {
        "name": "Kimi",
        "models": [
            {"value": "kimi-k2.5", "label": "Kimi K2.5"},
            {"value": "kimi-k2", "label": "Kimi K2"},
        ]
    },
}

# Image generation models grouped by provider
IMAGE_MODELS = {
    "seedream": {
        "name": "火山引擎",
        "models": [
            {"value": "doubao-seedream-4-5-251128", "label": "Seedream 4.5"},
            {"value": "doubao-seedream-4-0-250828", "label": "Seedream 4.0"},
        ]
    },
    "gpt_image": {
        "name": "GPT-Image",
        "models": [
            {"value": "gpt-image-1", "label": "GPT-Image-1"},
            {"value": "gpt-image-1-2025-04-15", "label": "GPT-Image-1 (Apr)"},
        ]
    },
    "dalle": {
        "name": "DALL·E",
        "models": [
            {"value": "dall-e-3", "label": "DALL-E 3"},
        ]
    },
    "midjourney": {
        "name": "Midjourney",
        "models": [
            {"value": "mj_imagine", "label": "MJ Imagine"},
            {"value": "mj_upscale", "label": "MJ Upscale"},
            {"value": "mj_variation", "label": "MJ Variation"},
            {"value": "mj_inpaint", "label": "MJ Inpaint"},
        ]
    },
    "flux": {
        "name": "Flux",
        "models": [
            {"value": "flux-2-pro", "label": "Flux 2 Pro"},
            {"value": "flux-1.1-pro", "label": "Flux 1.1 Pro"},
        ]
    },
    "wan_image": {
        "name": "Wan-Image",
        "models": [
            {"value": "wan2.7-image", "label": "Wan 2.7 Image"},
            {"value": "wan2.7-image-pro", "label": "Wan 2.7 Image Pro"},
        ]
    },
    "qwen_image": {
        "name": "Qwen-Image",
        "models": [
            {"value": "qwen-image-2.0", "label": "Qwen Image 2.0"},
            {"value": "qwen-image-2.0-pro", "label": "Qwen Image 2.0 Pro"},
        ]
    },
}

# Video generation models grouped by provider
VIDEO_MODELS = {
    "seedance": {
        "name": "火山引擎",
        "models": [
            {"value": "doubao-seedance-2-0-pro-260613", "label": "Seedance 2.0 Pro"},
            {"value": "doubao-seedance-1-5-pro-251215", "label": "Seedance 1.5 Pro"},
            {"value": "doubao-seedance-1-0-pro-250528", "label": "Seedance 1.0 Pro"},
        ]
    },
    "veo": {
        "name": "Veo/Google",
        "models": [
            {"value": "veo3.1", "label": "Veo 3.1"},
            {"value": "veo3.1-4k", "label": "Veo 3.1 4K"},
            {"value": "veo3", "label": "Veo 3"},
            {"value": "veo2", "label": "Veo 2"},
            {"value": "veo2-pro", "label": "Veo 2 Pro"},
        ]
    },
    "vidu": {
        "name": "Vidu",
        "models": [
            {"value": "viduq3-pro", "label": "Vidu Q3 Pro"},
            {"value": "viduq3", "label": "Vidu Q3"},
            {"value": "viduq3-turbo", "label": "Vidu Q3 Turbo"},
        ]
    },
    "kling": {
        "name": "Kling/可灵",
        "models": [
            {"value": "kling-video", "label": "Kling Video"},
            {"value": "kling-image", "label": "Kling Image"},
        ]
    },
    "sora": {
        "name": "Sora/OpenAI",
        "models": [
            {"value": "sora-2", "label": "Sora 2"},
        ]
    },
    "wan_video": {
        "name": "Wan-Video",
        "models": [
            {"value": "wan2.6-i2v", "label": "Wan 2.6 I2V"},
            {"value": "wan2.6-i2v-flash", "label": "Wan 2.6 I2V Flash"},
        ]
    },
}


def build_grouped_response():
    """Build the response for /api/settings/models with provider groups."""
    llm_groups = []
    for provider_id, provider in LLM_MODELS.items():
        llm_groups.append({
            "id": provider_id,
            "name": provider["name"],
            "models": provider["models"],
        })

    image_groups = []
    for provider_id, provider in IMAGE_MODELS.items():
        image_groups.append({
            "id": f"{provider_id}_img",
            "name": provider["name"],
            "models": provider["models"],
        })

    video_groups = []
    for provider_id, provider in VIDEO_MODELS.items():
        video_groups.append({
            "id": f"{provider_id}_vid",
            "name": provider["name"],
            "models": provider["models"],
        })

    return {
        "llm_groups": llm_groups,
        "image_groups": image_groups,
        "video_groups": video_groups,
    }
