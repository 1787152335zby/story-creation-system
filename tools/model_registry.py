"""Centralized model registry with provider-based grouping and resolution inference.

This file defines all available models grouped by provider/backend type.
It is used by:
  - server/routes/settings.py → /api/settings/models endpoint
  - server/routes/images.py  → image generation
  - server/routes/gen.py     → video/image generation, resolution lookup

Resolution lookup is fully rule-based — ANY model from ANY aggregated platform
is handled automatically without hardcoding.
"""


def _res(*sizes: str) -> list[str]:
    """Helper to define model resolutions."""
    return list(sizes)


# Text/LLM models grouped by provider
LLM_MODELS = {
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            {"value": "deepseek-chat", "label": "DeepSeek Chat（稳定版）"},
            {"value": "deepseek-v4-flash", "label": "DeepSeek V4 Flash（实验版）"},
            {"value": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
            {"value": "deepseek-reasoner", "label": "DeepSeek Reasoner"},
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
            {"value": "doubao-seedream-4-5-251128", "label": "Seedream 4.5", "resolutions": _res(
                "512x512", "768x768", "1024x1024", "1280x720", "1440x900")},
            {"value": "doubao-seedream-4-0-250828", "label": "Seedream 4.0", "resolutions": _res(
                "512x512", "768x768", "1024x1024", "1280x720")},
        ]
    },
    "gpt_image": {
        "name": "GPT-Image",
        "models": [
            {"value": "gpt-image-1", "label": "GPT-Image-1", "resolutions": _res(
                "1024x1024", "1024x576", "1024x768", "1792x1024", "1024x1792",
                "2048x2048", "2560x1440", "3072x3072")},
            {"value": "gpt-image-1-2025-04-15", "label": "GPT-Image-1 (Apr)", "resolutions": _res(
                "1024x1024", "1024x576", "1024x768", "1792x1024", "1024x1792",
                "2048x2048", "2560x1440", "3072x3072")},
        ]
    },
    "dalle": {
        "name": "DALL·E",
        "models": [
            {"value": "dall-e-3", "label": "DALL-E 3", "resolutions": _res(
                "1024x1024", "1792x1024", "1024x1792")},
        ]
    },
    "midjourney": {
        "name": "Midjourney",
        "models": [
            {"value": "mj_imagine", "label": "MJ Imagine", "resolutions": _res(
                "1024x1024", "768x768", "2048x2048", "2048x1152")},
            {"value": "mj_upscale", "label": "MJ Upscale"},
            {"value": "mj_variation", "label": "MJ Variation"},
            {"value": "mj_inpaint", "label": "MJ Inpaint"},
        ]
    },
    "flux": {
        "name": "Flux",
        "models": [
            {"value": "flux-2-pro", "label": "Flux 2 Pro", "resolutions": _res(
                "1024x1024", "768x768", "1440x900", "2048x2048", "2048x1152")},
            {"value": "flux-1.1-pro", "label": "Flux 1.1 Pro", "resolutions": _res(
                "1024x1024", "768x768", "1440x900", "2048x2048")},
        ]
    },
    "wan_image": {
        "name": "Wan-Image",
        "models": [
            {"value": "wan2.7-image", "label": "Wan 2.7 Image", "resolutions": _res(
                "1024x1024", "768x768", "1280x720")},
            {"value": "wan2.7-image-pro", "label": "Wan 2.7 Image Pro", "resolutions": _res(
                "1024x1024", "768x768", "1280x720", "1440x900")},
        ]
    },
    "qwen_image": {
        "name": "Qwen-Image",
        "models": [
            {"value": "qwen-image-2.0", "label": "Qwen Image 2.0", "resolutions": _res(
                "1024x1024", "768x768", "1440x900", "2048x2048", "2048x1152")},
            {"value": "qwen-image-2.0-pro", "label": "Qwen Image 2.0 Pro", "resolutions": _res(
                "1024x1024", "768x768", "1440x900", "2048x2048", "2048x1152")},
        ]
    },
    "gemini_image": {
        "name": "Gemini/Google",
        "models": [
            {"value": "gemini-3-pro-preview", "label": "Gemini 3 Pro", "resolutions": _res(
                "1024x1024", "1024x576", "576x1024", "1024x768", "768x1024",
                "1024x683", "683x1024", "1024x820", "820x1024", "1024x440",
                "2048x2048", "2048x1152", "1152x2048", "2048x1536", "1536x2048",
                "2048x1365", "1365x2048", "2048x1638", "1638x2048", "2048x878",
                "3072x3072", "3840x2160", "2160x3840", "3840x3840")},
            {"value": "gemini-2.5-flash-preview", "label": "Gemini 2.5 Flash", "resolutions": _res(
                "1024x1024", "1024x576", "576x1024", "1024x768", "768x1024",
                "1024x683", "683x1024", "1024x820", "820x1024", "1024x440")},
        ]
    },
}

# Video generation models grouped by provider
VIDEO_MODELS = {
    "seedance": {
        "name": "火山引擎",
        "models": [
            {"value": "doubao-seedance-2-0-pro-260613", "label": "Seedance 2.0 Pro", "durations": [5, 10, 15], "resolutions": _res(
                "1024x1024", "540x960", "720x1280", "1280x720", "1920x1080")},
            {"value": "doubao-seedance-2-0-fast-260128", "label": "Seedance 2.0 Fast", "durations": [5, 10, 15], "resolutions": _res(
                "1024x1024", "540x960", "720x1280", "1280x720")},
            {"value": "doubao-seedance-1-5-pro-251215", "label": "Seedance 1.5 Pro", "durations": [5, 10, 15], "resolutions": _res(
                "1024x1024", "540x960", "720x1280", "1280x720", "1920x1080")},
            {"value": "doubao-seedance-1-0-pro-250528", "label": "Seedance 1.0 Pro", "durations": [5, 10], "resolutions": _res(
                "1024x1024", "540x960", "720x1280", "1280x720", "1920x1080")},
            {"value": "doubao-seedance-1-0-pro-fast-251015", "label": "Seedance 1.0 Pro Fast", "durations": [5, 10], "resolutions": _res(
                "1024x1024", "540x960", "720x1280", "1280x720", "1920x1080")},
        ]
    },
    "veo": {
        "name": "Veo/Google",
        "models": [
            {"value": "veo3.1", "label": "Veo 3.1", "resolutions": _res(
                "540x960", "1280x720", "1920x1080")},
            {"value": "veo3.1-4k", "label": "Veo 3.1 4K", "resolutions": _res(
                "540x960", "1280x720", "1920x1080", "3840x2160")},
            {"value": "veo3", "label": "Veo 3", "resolutions": _res(
                "540x960", "1280x720", "1920x1080")},
            {"value": "veo2", "label": "Veo 2", "resolutions": _res(
                "540x960", "1280x720")},
            {"value": "veo2-pro", "label": "Veo 2 Pro", "resolutions": _res(
                "540x960", "1280x720")},
        ]
    },
    "vidu": {
        "name": "Vidu",
        "models": [
            {"value": "viduq3-pro", "label": "Vidu Q3 Pro", "resolutions": _res(
                "540x960", "720x1280", "1280x720", "1920x1080")},
            {"value": "viduq3", "label": "Vidu Q3", "resolutions": _res(
                "540x960", "720x1280", "1280x720")},
            {"value": "viduq3-turbo", "label": "Vidu Q3 Turbo", "resolutions": _res(
                "540x960", "720x1280")},
        ]
    },
    "kling": {
        "name": "Kling/可灵",
        "models": [
            {"value": "kling-video", "label": "Kling Video", "resolutions": _res(
                "540x960", "720x1280", "1280x720", "1920x1080")},
            {"value": "kling-image", "label": "Kling Image", "resolutions": _res(
                "1024x1024", "768x768")},
        ]
    },
    "sora": {
        "name": "Sora/OpenAI",
        "models": [
            {"value": "sora-2", "label": "Sora 2", "resolutions": _res(
                "540x960", "1280x720", "1920x1080")},
        ]
    },
    "wan_video": {
        "name": "Wan-Video",
        "models": [
            {"value": "wan2.6-i2v", "label": "Wan 2.6 I2V", "resolutions": _res(
                "540x960", "1280x720")},
            {"value": "wan2.6-i2v-flash", "label": "Wan 2.6 I2V Flash", "resolutions": _res(
                "540x960")},
        ]
    },
}


# =============================================================================
#  Standard resolution lists — fallback for unknown models
#  Covers ~99% of models in the wild. A model will error if unsupported.
# =============================================================================

STANDARD_IMAGE_RESOLUTIONS = [
    "512x512", "768x768", "1024x1024", "2048x2048",
    "1024x576", "1280x720", "1920x1080", "2048x1152", "2560x1440", "3840x2160",
    "576x1024", "720x1280", "1080x1920", "1152x2048", "2160x3840",
    "1024x768", "768x1024", "2048x1536", "1536x2048",
    "1024x683", "683x1024", "2048x1365", "1365x2048",
    "1024x820", "820x1024", "2048x1638", "1638x2048",
    "1024x440", "2048x878",
    "3840x3840", "3072x3072",
    "1792x1024", "1024x1792",
]

STANDARD_VIDEO_RESOLUTIONS = [
    "1024x1024",
    "540x960", "720x1280",
    "1280x720", "1920x1080", "1080x1920",
    "3840x2160",
]


def _lookup_model_resolutions(model_id: str, models_dict: dict) -> list[str] | None:
    """Look up hardcoded resolutions for a known model. Returns None if not found."""
    if not model_id:
        return None
    ml = model_id.lower()
    for provider in models_dict.values():
        for m in provider.get("models", []):
            v = m.get("value", "")
            if v == model_id or v == ml:
                if "resolutions" in m and m["resolutions"]:
                    return m["resolutions"]
    for provider in models_dict.values():
        for m in provider.get("models", []):
            v = m.get("value", "")
            if v and (v in ml or ml in v):
                if "resolutions" in m and m["resolutions"]:
                    return m["resolutions"]
    return None


def get_image_resolutions(model_id: str) -> tuple[list[str], str]:
    """Return (resolutions, source). source is 'known' (exact) or 'standard' (fallback)."""
    hardcoded = _lookup_model_resolutions(model_id, IMAGE_MODELS)
    if hardcoded:
        return (hardcoded, "known")
    return (list(STANDARD_IMAGE_RESOLUTIONS), "standard")


def get_video_resolutions(model_id: str) -> tuple[list[str], str]:
    hardcoded = _lookup_model_resolutions(model_id, VIDEO_MODELS)
    if hardcoded:
        return (hardcoded, "known")
    return (list(STANDARD_VIDEO_RESOLUTIONS), "standard")


def get_video_durations(model_id: str) -> list[int]:
    """Return supported durations for a video model, defaults to [5, 10]."""
    model_id_l = model_id.lower()
    for provider_id, provider in VIDEO_MODELS.items():
        if provider_id in model_id_l or any(kw in model_id_l for kw in provider_id.split("_")):
            for m in provider["models"]:
                if m["value"] == model_id or (m["value"] in model_id_l or model_id_l in m["value"]):
                    return m.get("durations", [5, 10])
    for provider in VIDEO_MODELS.values():
        for m in provider["models"]:
            if any(kw in model_id_l for kw in m["value"].lower().split("-")[:3]):
                return m.get("durations", [5, 10])
    return [5, 10]


# =============================================================================
#  Legacy: model registry for display in Settings UI
#  NOTE: Resolution lookup now uses the inference engine above, NOT this map.
# =============================================================================


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
