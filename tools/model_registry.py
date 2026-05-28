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
                "1024x1024", "768x768", "2048x2048", "2560x1440", "3072x3072", "3840x2160", "3840x3840")},
            {"value": "gemini-2.5-flash-preview", "label": "Gemini 2.5 Flash", "resolutions": _res(
                "1024x1024", "768x768", "2048x2048", "2560x1440", "3072x3072")},
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
#  Resolution inference engine — fully rule-based, NO hardcoded model IDs
#  Any model from any aggregated platform is handled automatically.
# =============================================================================

# Base resolutions shared across all image models
IMAGE_BASE_RESOLUTIONS = [
    "512x512", "768x768",
    "1024x576", "1024x768", "1024x1024",
    "1280x720", "1280x1024",
    "1440x900",
    "1920x1080",
]

# Base resolutions shared across all video models
VIDEO_BASE_RESOLUTIONS = [
    "1024x1024",
    "540x960",
    "720x1280",
    "1280x720",
]

# Resolution tiers for pattern matching
IMAGE_RES_TIERS = {
    "low":     ["512x512", "768x768"],
    "mid":     ["1024x576", "1024x768", "1024x1024"],
    "hd":      ["1280x720", "1280x1024", "1440x900"],
    "full_hd": ["1920x1080"],
    "2k":      ["2048x2048", "2048x1152", "2560x1440"],
    "3k":      ["2560x1920", "3072x3072"],
    "4k":      ["3840x2160", "3840x3840"],
    "dalle_wide": ["1792x1024", "1024x1792"],
}

VIDEO_RES_TIERS = {
    "p480":  ["854x480", "540x960"],
    "p720":  ["720x1280", "1280x720"],
    "p1080": ["1920x1080"],
    "p4k":   ["3840x2160"],
    "square": ["1024x1024"],
}


def _collect(matches: list[str]) -> list[str]:
    """Collect unique resolutions from named tiers."""
    seen: set[str] = set()
    result: list[str] = []
    for label in matches:
        for r in (_get_image_tier(label) if _get_image_tier(label) else _get_video_tier(label) or []):
            if r not in seen:
                seen.add(r)
                result.append(r)
    return result


def _get_image_tier(name: str) -> list[str] | None:
    return IMAGE_RES_TIERS.get(name)


def _get_video_tier(name: str) -> list[str] | None:
    return VIDEO_RES_TIERS.get(name)


# =============================================================================
#  Video resolution inference
# =============================================================================

def _infer_video_resolutions(model_id: str) -> list[str]:
    """Infer supported video resolutions purely from model name patterns."""
    ml = model_id.lower()

    # === Model family detection ===
    # Detect the model family and its baseline capabilities

    families_baseline: list[tuple[list[str], list[str]]] = [
        # (keywords, baseline tier names)
        (["veo"], ["square", "p480", "p720"]),
        (["kling"], ["square", "p480", "p720"]),
        (["seedance"], ["square", "p480", "p720"]),
        (["sora"], ["square", "p480", "p720"]),
        (["vidu"], ["square", "p480", "p720"]),
        (["wan"], ["square", "p480", "p720"]),
        (["pixverse"], ["square", "p480", "p720"]),
        (["minimax"], ["square", "p480", "p720"]),
        (["mochi"], ["square", "p480", "p720"]),
        (["cogvideo"], ["square", "p480", "p720"]),
        (["runway", "gen-"], ["square", "p480", "p720"]),
    ]

    # Default baseline for unknown video models
    baseline = ["square", "p480", "p720"]
    for keywords, tiers in families_baseline:
        if any(k in ml for k in keywords):
            baseline = tiers
            break

    # === Edition modifiers ===
    # "fast", "turbo", "lite" → capped at 720p (no 1080p)
    # "pro", "plus", "hd", "2k" → add 1080p
    # "4k", "ultra", "max" → add 4K

    has_speed_edition = any(k in ml for k in ["fast", "turbo", "lite", "draft"])
    has_pro_edition = any(k in ml for k in ["pro", "plus", "hd", "high", "2k", "1080p"])
    has_4k_edition = any(k in ml for k in ["4k", "ultra", "max", "2160p", "8k"])
    has_3d = any(k in ml for k in ["3d", "360"])

    # === Assemble resolutions ===
    tiers: list[str] = list(baseline)

    # Add p1080 unless it's a speed edition that explicitly doesn't support it
    if has_pro_edition or has_4k_edition:
        if "p1080" not in tiers:
            tiers.append("p1080")
    elif not has_speed_edition:
        tiers.append("p1080")

    # Add 4K
    if has_4k_edition:
        tiers.append("p4k")

    # Add extra for 3D/360
    if has_3d:
        tiers.extend(["p1080", "p4k"])

    # Build final resolution list
    result: list[str] = []
    seen: set[str] = set()
    for t in tiers:
        res_list = VIDEO_RES_TIERS.get(t, [])
        for r in res_list:
            if r not in seen:
                seen.add(r)
                result.append(r)
    return result


# =============================================================================
#  Image resolution inference
# =============================================================================

def _infer_image_resolutions(model_id: str) -> list[str]:
    """Infer supported image resolutions purely from model name patterns."""
    ml = model_id.lower()

    # === Capability tiers (highest supported resolution) ===
    # Each tier builds on the previous one

    families: list[tuple[list[str], list[str]]] = [
        # (keywords, extra tiers beyond baseline)
        # Level 0: baseline (512p ~ 1080p)
        # Level 1: +2K
        (["flux", "midjourney", "mj_", "qwen-image", "sdxl"], ["2k"]),
        # Level 2: +2K + DALL-E wide ratios
        (["dall-e", "dalle"], ["dalle_wide", "2k"]),
        # Level 3: +3K
        (["gpt-image", "gpt_image"], ["2k", "3k"]),
        # Level 4: +4K
        (["gemini", "banana"], ["2k", "3k", "4k"]),
    ]

    # Baseline: low + mid + hd + full_hd
    baseline = ["low", "mid", "hd", "full_hd"]
    extras: list[str] = []
    has_seedream = "seedream" in ml
    has_wan = "wan" in ml and "video" not in ml and "i2v" not in ml

    if has_seedream:
        extras = ["hd"]
    elif has_wan:
        extras = []
    else:
        for keywords, extra_tiers in families:
            if any(k in ml for k in keywords):
                extras = list(extra_tiers)
                break

    # Edition modifiers
    if "turbo" in ml or "fast" in ml:
        extras = [t for t in extras if t not in ("3k", "4k")]

    if "4k" in ml or "ultra" in ml or "max" in ml:
        if "4k" not in extras and "4k" in IMAGE_RES_TIERS:
            extras.append("4k")

    # Build result
    result: list[str] = []
    seen: set[str] = set()
    for t in baseline + extras:
        res_list = IMAGE_RES_TIERS.get(t, [])
        for r in res_list:
            if r not in seen:
                seen.add(r)
                result.append(r)
    return result


def get_image_resolutions(model_id: str) -> list[str]:
    return _infer_image_resolutions(model_id)


def get_video_resolutions(model_id: str) -> list[str]:
    return _infer_video_resolutions(model_id)


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
