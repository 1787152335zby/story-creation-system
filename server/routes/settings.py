import os
import json
import uuid
import requests
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..schemas import SettingsUpdateRequest, TestLLMRequest, AggregatedConfigItem, AggregatedConfigCreate, AggregatedConfigUpdate, ProviderConfigCreate, ProviderConfigUpdate


class TestAggRequest(BaseModel):
    base_url: str = ""
    api_key: str = ""


router = APIRouter()
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
AGG_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "aggregated_configs.json"


def _read_agg_configs() -> list[dict]:
    if not AGG_CONFIG_PATH.exists():
        return []
    try:
        return json.loads(AGG_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        return []


def _write_agg_configs(configs: list[dict]):
    AGG_CONFIG_PATH.write_text(json.dumps(configs, ensure_ascii=False, indent=2), encoding="utf-8")


def _mask_key(key: str) -> str:
    if not key or "your-key-here" in key:
        return ""
    if len(key) <= 8:
        return key[:4] + "****"
    return key[:8] + "****" + key[-4:]


def _read_env() -> dict:
    config = {
        "LLM_BACKEND": "deepseek",
        "DEEPSEEK_API_KEY": "",
        "DEEPSEEK_MODEL": "deepseek-chat",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "gpt-4o",
        "CLAUDE_API_KEY": "",
        "CLAUDE_MODEL": "claude-sonnet-4-20250514",
        "SEEDANCE_API_KEY": "",
        "IMAGE_BACKEND": "seedream",
        "CUSTOM_IMAGE_BASE_URL": "",
        "CUSTOM_IMAGE_MODEL": "gpt-image-1",
        "BANANA2_API_KEY": "",
        "BANANA2_BASE_URL": "https://api.laozhang.ai/v1",
        "BANANA2_MODEL": "nano-banana-2",
        "AGGREGATED_ENABLED": "",
        "AGGREGATED_BASE_URL": "",
        "AGGREGATED_API_KEY": "",
        "AGGREGATED_LLM_MODEL": "",
        "AGGREGATED_IMAGE_MODEL": "",
        "AGGREGATED_VIDEO_MODEL": "",
    }
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().split("#")[0].strip()
                config[key] = val
    return config


@router.get("/settings")
def get_settings():
    env = _read_env()
    return {
        "llm_backend": env.get("LLM_BACKEND", "deepseek"),
        "deepseek_api_key": _mask_key(env.get("DEEPSEEK_API_KEY", "")),
        "deepseek_model": env.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "openai_api_key": _mask_key(env.get("OPENAI_API_KEY", "")),
        "openai_model": env.get("OPENAI_MODEL", "gpt-4o"),
        "claude_api_key": _mask_key(env.get("CLAUDE_API_KEY", "")),
        "claude_model": env.get("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        "seedance_api_key": _mask_key(env.get("SEEDANCE_API_KEY", "")),
        "image_backend": env.get("IMAGE_BACKEND", "seedream"),
        "custom_image_base_url": env.get("CUSTOM_IMAGE_BASE_URL", ""),
        "custom_image_model": env.get("CUSTOM_IMAGE_MODEL", "gpt-image-1"),
        "banana2_api_key": _mask_key(env.get("BANANA2_API_KEY", "")),
        "banana2_base_url": env.get("BANANA2_BASE_URL", "https://api.laozhang.ai/v1"),
        "banana2_model": env.get("BANANA2_MODEL", "nano-banana-2"),
        "aggregated_enabled": env.get("AGGREGATED_ENABLED", ""),
        "aggregated_base_url": env.get("AGGREGATED_BASE_URL", ""),
        "aggregated_api_key": _mask_key(env.get("AGGREGATED_API_KEY", "")),
        "aggregated_llm_model": env.get("AGGREGATED_LLM_MODEL", ""),
        "aggregated_image_model": env.get("AGGREGATED_IMAGE_MODEL", ""),
        "aggregated_video_model": env.get("AGGREGATED_VIDEO_MODEL", ""),
    }


@router.put("/settings")
def update_settings(req: SettingsUpdateRequest):
    env = _read_env()

    field_map = {
        "llm_backend": "LLM_BACKEND",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "deepseek_model": "DEEPSEEK_MODEL",
        "openai_api_key": "OPENAI_API_KEY",
        "openai_model": "OPENAI_MODEL",
        "claude_api_key": "CLAUDE_API_KEY",
        "claude_model": "CLAUDE_MODEL",
        "seedance_api_key": "SEEDANCE_API_KEY",
        "image_backend": "IMAGE_BACKEND",
        "custom_image_base_url": "CUSTOM_IMAGE_BASE_URL",
        "custom_image_model": "CUSTOM_IMAGE_MODEL",
        "banana2_api_key": "BANANA2_API_KEY",
        "banana2_base_url": "BANANA2_BASE_URL",
        "banana2_model": "BANANA2_MODEL",
        "aggregated_enabled": "AGGREGATED_ENABLED",
        "aggregated_base_url": "AGGREGATED_BASE_URL",
        "aggregated_api_key": "AGGREGATED_API_KEY",
        "aggregated_llm_model": "AGGREGATED_LLM_MODEL",
        "aggregated_image_model": "AGGREGATED_IMAGE_MODEL",
        "aggregated_video_model": "AGGREGATED_VIDEO_MODEL",
    }

    for req_field, env_key in field_map.items():
        val = getattr(req, req_field, None)
        if val is not None and "****" not in val:
            env[env_key] = val

    lines = [
        "# ===== 大模型配置 =====",
        "# 至少配置一个后端",
        f"LLM_BACKEND={env.get('LLM_BACKEND', 'deepseek')}",
        "",
        f"DEEPSEEK_API_KEY={env.get('DEEPSEEK_API_KEY', '')}",
        f"DEEPSEEK_MODEL={env.get('DEEPSEEK_MODEL', 'deepseek-chat')}",
        "",
        f"OPENAI_API_KEY={env.get('OPENAI_API_KEY', '')}",
        f"OPENAI_MODEL={env.get('OPENAI_MODEL', 'gpt-4o')}",
        "",
        f"CLAUDE_API_KEY={env.get('CLAUDE_API_KEY', '')}",
        f"CLAUDE_MODEL={env.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')}",
        "",
        "# ===== 视频生成配置 =====",
        f"SEEDANCE_API_KEY={env.get('SEEDANCE_API_KEY', '')}",
        "",
        "# ===== 图像生成配置 =====",
        f"IMAGE_BACKEND={env.get('IMAGE_BACKEND', 'seedream')}",
        f"BANANA2_API_KEY={env.get('BANANA2_API_KEY', '')}",
        f"BANANA2_BASE_URL={env.get('BANANA2_BASE_URL', 'https://api.laozhang.ai/v1')}",
        f"BANANA2_MODEL={env.get('BANANA2_MODEL', 'nano-banana-2')}",
        "",
        "# ===== 自定义后端配置 =====",
        f"CUSTOM_IMAGE_BASE_URL={env.get('CUSTOM_IMAGE_BASE_URL', '')}",
        f"CUSTOM_IMAGE_MODEL={env.get('CUSTOM_IMAGE_MODEL', 'gpt-image-1')}",
        "",
        "# ===== 聚合平台配置 =====",
        f"AGGREGATED_ENABLED={env.get('AGGREGATED_ENABLED', '')}",
        f"AGGREGATED_BASE_URL={env.get('AGGREGATED_BASE_URL', '')}",
        f"AGGREGATED_API_KEY={env.get('AGGREGATED_API_KEY', '')}",
        f"AGGREGATED_LLM_MODEL={env.get('AGGREGATED_LLM_MODEL', '')}",
        f"AGGREGATED_IMAGE_MODEL={env.get('AGGREGATED_IMAGE_MODEL', '')}",
        f"AGGREGATED_VIDEO_MODEL={env.get('AGGREGATED_VIDEO_MODEL', '')}",
    ]
    try:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

    for env_key, val in env.items():
        os.environ[env_key] = val

    return {"saved": True}


def categorize_model(model_id: str) -> str:
    """按模型名称关键词判断类型: llm / image / video。"""
    ml = model_id.lower()
    if any(x in ml for x in ["image", "mj_", "flux", "dall-e", "seedream", "kling-image",
                              "wan2.7-image", "midjourney", "mj_imagine", "mj_upscale",
                              "gemini"]) and "video" not in ml:
        return "image"
    if any(x in ml for x in ["video", "viduq", "veo", "kling-video", "sora", "seedance",
                              "i2v", "t2v", "happyhorse"]):
        return "video"
    return "llm"


@router.get("/settings/models")
def get_available_models():
    """返回实时拉取的模型列表，按 owned_by 分组，按类型分类"""
    from collections import defaultdict
    env = _read_env()
    aggregated = env.get("AGGREGATED_ENABLED", "") == "1" or env.get("AGGREGATED_ENABLED", "") == "true"
    agg_base = env.get("AGGREGATED_BASE_URL", "")
    agg_key = env.get("AGGREGATED_API_KEY", "")
    agg_has_key = bool(agg_key) and agg_key != "your-key-here" and "****" not in agg_key

    # Provider display name mapping
    OWNER_LABELS = {
        "deepseek": "DeepSeek", "openai": "OpenAI", "ali": "阿里千问",
        "awsboto3": "AWS/Claude", "baidu": "百度文心", "coze": "Coze",
        "custom": "社区/其他", "midjourney": "Midjourney",
        "minimax": "MiniMax", "mistral": "Mistral", "moonshot": "Moonshot/月之暗面",
        "perplexity": "Perplexity", "siliconflow": "SiliconFlow",
        "vertex-ai": "Vertex AI(Google)", "volcengine": "火山引擎",
        "xai": "xAI/Grok", "xunfei": "讯飞星火", "zhipu_4v": "智谱GLM",
    }

    # Fetch live models from aggregate platform
    live_groups = {"llm": [], "image": [], "video": []}
    
    # 收集各类型的配置：优先用激活的，没有激活的就用全部
    agg_configs = _read_agg_configs()
    configs_by_type: dict[str, list[dict]] = {}
    for c in agg_configs:
        ct = c.get("type", "llm")
        configs_by_type.setdefault(ct, []).append(c)
    
    # 先看有没有激活的，没有就用该类型所有配置
    query_configs: dict[str, list[dict]] = {}
    active_types: set[str] = set()
    for ct, configs in configs_by_type.items():
        active = [c for c in configs if c.get("active")]
        query_configs[ct] = active if active else configs
        if active:
            active_types.add(ct)

    for cfg_type, configs in query_configs.items():
        for cfg in configs:
            try:
                base = cfg.get("base_url", "").rstrip("/")
                if not base:
                    continue
                models_url = base + "/models" if "/v1" in base else base + "/v1/models"
                resp = requests.get(models_url, headers={"Authorization": f"Bearer {cfg.get('api_key', '')}"}, timeout=5)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("data", data) if isinstance(data, dict) else data
                if not isinstance(items, list):
                    continue
                # 成功获取到模型列表，处理并跳出（一个类型只用一个平台的数据）
                by_owner = defaultdict(list)
                for m in items:
                    mid = m.get("id", "") if isinstance(m, dict) else str(m)
                    owner = m.get("owned_by", "custom") if isinstance(m, dict) else "custom"
                    if mid:
                        by_owner[owner].append(mid)
                NAME_OWNER_MAP = [
                    ("deepseek", "deepseek"),
                    ("gpt", "openai"), ("o1", "openai"), ("o3", "openai"), ("o4", "openai"),
                    ("dall-e", "openai"), ("whisper", "openai"), ("tts", "openai"),
                    ("claude", "awsboto3"),
                    ("qwen", "ali"), ("qwq", "ali"), ("qvq", "ali"),
                    ("glm", "zhipu_4v"), ("chatglm", "zhipu_4v"),
                    ("gemini", "vertex-ai"),
                    ("kimi", "moonshot"),
                    ("veo", "openai"), ("sora", "openai"),
                    ("seedream", "volcengine"), ("seedance", "volcengine"),
                    ("grok", "xai"),
                ]

                def get_effective_owner(model_id: str, raw_owner: str) -> str:
                    if raw_owner not in ("custom", "coze", ""):
                        return raw_owner
                    ml = model_id.lower()
                    for keyword, target_owner in NAME_OWNER_MAP:
                        if keyword in ml:
                            return target_owner
                    return raw_owner

                merged = defaultdict(set)
                for raw_owner, mids in by_owner.items():
                    for mid in mids:
                        effective = get_effective_owner(mid, raw_owner)
                        merged[effective].add(mid)

                for owner, model_ids in sorted(merged.items()):
                    label = OWNER_LABELS.get(owner, owner.capitalize())
                    models_list = [{"value": mid, "label": mid} for mid in sorted(model_ids)]
                    llm_models = [m for m in models_list if categorize_model(m["value"]) == "llm"]
                    image_models = [m for m in models_list if categorize_model(m["value"]) == "image"]
                    video_models = [m for m in models_list if categorize_model(m["value"]) == "video"]
                    if llm_models:
                        live_groups["llm"].append({"id": owner, "name": label, "models": llm_models, "configured": True})
                    if image_models:
                        live_groups["image"].append({"id": f"{owner}_img", "name": label, "models": image_models, "configured": True})
                    if video_models:
                        live_groups["video"].append({"id": f"{owner}_vid", "name": label, "models": video_models, "configured": True})
                if cfg_type in active_types:
                     # 有激活配置，用激活的数据就够了
                     break
            except Exception:
                pass

    result = {}
    from tools.model_registry import build_grouped_response
    hardcoded = build_grouped_response()
    for hc_type in ("llm_groups", "image_groups", "video_groups"):
        hc = hardcoded.get(hc_type, [])
        lv = live_groups.get(hc_type.replace("_groups", ""), [])
        # 始终优先用 live 数据；live 为空时用硬编码兜底
        result_groups = list(lv) if lv else list(hc)
        # 按名称合并：live 已有的分组，补充硬编码中同名分组缺失的模型
        if lv:
            name_to_group = {g.get("name"): g for g in result_groups}
            for g in hc:
                hname = g.get("name")
                if hname and hname in name_to_group:
                    existing = name_to_group[hname]
                    existing_vals = {m["value"] for m in existing["models"]}
                    for m in g.get("models", []):
                        if m["value"] not in existing_vals:
                            existing_vals.add(m["value"])
                            existing["models"].append(m)
                else:
                    result_groups.append(g)
        result[hc_type] = result_groups

    # 合并同名组（按 id）+ 去重
    for group_type in ("llm_groups", "image_groups", "video_groups"):
        seen_ids = {}
        merged_groups = []
        for group in result.get(group_type, []):
            gid = group.get("id", "")
            if gid in seen_ids:
                existing = seen_ids[gid]
                existing_vals = {m["value"] for m in existing["models"]}
                for m in group.get("models", []):
                    if m["value"] not in existing_vals:
                        existing_vals.add(m["value"])
                        existing["models"].append(m)
            else:
                seen_ids[gid] = group
                merged_groups.append(group)
        result[group_type] = merged_groups

    result["aggregated"] = {
        "enabled": aggregated,
        "has_key": agg_has_key,
        "base_url": agg_base,
    }
    return result


@router.get("/settings/aggregated-configs")
def list_aggregated_configs(type: str = ""):
    """列出某类型的聚合平台配置"""
    configs = _read_agg_configs()
    if type:
        configs = [c for c in configs if c.get("type") == type]
    return {"configs": configs}


FAMILY_NAMES: dict[str, str] = {
    "seedance": "Seedance",
    "seedream": "Seedream",
    "gpt-image": "GPT-Image",
    "gpt": "GPT",
    "dall-e": "DALL-E",
    "flux": "Flux",
    "midjourney": "Midjourney",
    "qwen-image": "Qwen-Image",
    "qwen": "Qwen",
    "deepseek": "DeepSeek",
    "veo": "Veo",
    "sora": "Sora",
    "viduq": "Vidu",
    "kling": "Kling",
    "wan": "Wan",
    "gemini": "Gemini",
    "claude": "Claude",
    "grok": "Grok",
    "happyhorse": "HappyHorse",
    "minimax": "MiniMax",
}


def parse_model_family(mid: str) -> tuple[str, str, str]:
    """解析模型 ID → (家族id, 家族名, 版本标签)"""
    ml = mid.lower()
    best_fid = "other"
    best_label = ""
    for keyword, fname in sorted(FAMILY_NAMES.items(), key=lambda x: -len(x[0])):
        if keyword in ml:
            best_fid = keyword
            best_label = fname
            break
    if not best_label:
        best_label = best_fid.capitalize()
    version = mid
    if best_fid != "other":
        idx = ml.find(best_fid)
        if idx >= 0:
            version = mid[idx + len(best_fid):].lstrip("-/_ ")
    if not version:
        version = mid
    return (best_fid, best_label, version)


def group_models_to_families(model_ids: list[str]) -> list[dict]:
    """将模型 ID 列表按家族分组。"""
    families: dict[str, dict] = {}
    for mid in model_ids:
        fid, fname, version = parse_model_family(mid)
        if fid not in families:
            families[fid] = {"id": fid, "name": fname, "versions": []}
        families[fid]["versions"].append({"value": mid, "label": version})
    result = sorted(families.values(), key=lambda f: f["name"].lower())
    # 把 "Other" 放最后
    other = [f for f in result if f["id"] == "other"]
    non_other = [f for f in result if f["id"] != "other"]
    return non_other + other


@router.get("/settings/models/families")
def get_models_families(type: str = "image"):
    """按类型返回聚合平台上所有可用模型的家族+版本分组。"""
    from collections import defaultdict
    agg_configs = _read_agg_configs()
    # 收集该类型所有激活的配置
    targets = [c for c in agg_configs if c.get("type") == type and c.get("active") and c.get("base_url") and c.get("api_key")]
    if not targets:
        # 没激活的，用该类型第一个有 key 的配置
        targets = [c for c in agg_configs if c.get("type") == type and c.get("base_url") and c.get("api_key")][:1]
    all_model_ids: set[str] = set()
    for cfg in targets:
        try:
            base = cfg["base_url"].rstrip("/")
            models_url = base + "/models" if "/v1" in base else base + "/v1/models"
            resp = requests.get(models_url, headers={"Authorization": f"Bearer {cfg['api_key']}"}, timeout=5)
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                continue
            for m in items:
                mid = m.get("id", "") if isinstance(m, dict) else str(m)
                if mid and categorize_model(mid) == type:
                    all_model_ids.add(mid)
        except Exception:
            continue
    families = group_models_to_families(sorted(all_model_ids))
    return {"families": families}


@router.get("/settings/aggregated-configs/{config_id}/models")
def get_aggregated_config_models(config_id: str):
    """获取某个聚合平台配置专属的模型列表，按家族+版本分组。"""
    configs = _read_agg_configs()
    cfg = next((c for c in configs if c.get("id") == config_id), None)
    if not cfg:
        return {"families": []}
    base = cfg.get("base_url", "").rstrip("/")
    key = cfg.get("api_key", "")
    if not base or not key:
        return {"families": []}
    try:
        models_url = base + "/models" if "/v1" in base else base + "/v1/models"
        resp = requests.get(models_url, headers={"Authorization": f"Bearer {key}"}, timeout=8)
        if resp.status_code != 200:
            return {"families": []}
        data = resp.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return {"families": []}
        model_ids = sorted([m.get("id", "") if isinstance(m, dict) else str(m) for m in items if m])

        # 按配置类型过滤（image 只看生图模型, video 只看视频模型）
        cfg_type = cfg.get("type", "llm")
        if cfg_type != "llm":
            model_ids = [m for m in model_ids if categorize_model(m) == cfg_type]

        families = group_models_to_families(model_ids)
        return {"families": families}
    except Exception:
        return {"families": []}


@router.post("/settings/aggregated-configs")
def create_aggregated_config(req: AggregatedConfigCreate):
    configs = _read_agg_configs()
    new_id = f"agg_{uuid.uuid4().hex[:8]}"
    # If no active config of this type, activate it
    has_active = any(c.get("active") and c.get("type") == req.type for c in configs)
    configs.append({
        "id": new_id,
        "name": req.name,
        "base_url": req.base_url,
        "api_key": req.api_key,
        "type": req.type,
        "model": req.model,
        "active": not has_active,
    })
    _write_agg_configs(configs)
    return {"id": new_id, "saved": True}


@router.put("/settings/aggregated-configs/{config_id}")
def update_aggregated_config(config_id: str, req: AggregatedConfigUpdate):
    configs = _read_agg_configs()
    for c in configs:
        if c["id"] == config_id:
            if req.name is not None: c["name"] = req.name
            if req.base_url is not None: c["base_url"] = req.base_url
            if req.api_key is not None and "****" not in req.api_key: c["api_key"] = req.api_key
            if req.model is not None: c["model"] = req.model
            _write_agg_configs(configs)
            return {"saved": True}
    raise HTTPException(status_code=404, detail="配置未找到")


@router.delete("/settings/aggregated-configs/{config_id}")
def delete_aggregated_config(config_id: str):
    configs = _read_agg_configs()
    configs = [c for c in configs if c["id"] != config_id]
    _write_agg_configs(configs)
    return {"deleted": True}


@router.post("/settings/aggregated-configs/{config_id}/activate")
def activate_aggregated_config(config_id: str):
    configs = _read_agg_configs()
    found = False
    target_type = None
    for c in configs:
        if c["id"] == config_id:
            target_type = c.get("type")
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="配置未找到")
    # Deactivate all configs of same type, activate only the target
    for c in configs:
        if c.get("type") == target_type:
            c["active"] = c["id"] == config_id
    _write_agg_configs(configs)
    return {"activated": True}


@router.post("/settings/aggregated-configs/type/{config_type}/deactivate")
def deactivate_aggregated_type(config_type: str):
    """Deactivate all aggregated configs of a type (so local provider is used)."""
    configs = _read_agg_configs()
    for c in configs:
        if c.get("type") == config_type:
            c["active"] = False
    _write_agg_configs(configs)
    return {"deactivated": True}


@router.get("/settings/active-config/{config_type}")
def get_active_config(config_type: str):
    """返回当前激活的配置（聚合平台或官网追加 Key）"""
    from .gen import _get_active_agg_config
    agg = _get_active_agg_config(config_type)
    if agg:
        return agg
    # Fall back to .env
    if config_type == "image":
        backend = os.getenv("IMAGE_BACKEND", "seedream")
        return {"type": "image", "model": "seedream-v1", "api_key": os.getenv("SEEDANCE_API_KEY", ""), "base_url": "https://api.volcengine.com/ark/v1"}
    if config_type == "video":
        return {"type": "video", "api_key": os.getenv("SEEDANCE_API_KEY", ""), "base_url": "https://api.volcengine.com/ark/v1"}
    return {"type": config_type, "active": False}


@router.post("/settings/test-llm")
def test_llm(req: TestLLMRequest):
    from openai import OpenAI
    api_key = req.api_key
    if not api_key or "****" in api_key:
        env = _read_env()
        key_map = {"deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY", "claude": "CLAUDE_API_KEY"}
        api_key = env.get(key_map.get(req.backend, ""), "")
    if not api_key:
        return {"success": False, "error": "未配置 API Key，请先输入并保存"}
    try:
        base_url = "https://api.deepseek.com" if req.backend == "deepseek" else None
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "请回复: 连接成功"}],
            max_tokens=20,
            timeout=15,
        )
        return {"success": True, "response": response.choices[0].message.content}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/settings/provider-configs")
def list_provider_configs(provider_id: str = ""):
    """列出某 provider 的多配置"""
    configs = _read_agg_configs()
    configs = [c for c in configs if c.get("type") == "provider" and (not provider_id or c.get("provider_id") == provider_id)]
    return {"configs": configs}


@router.post("/settings/provider-configs")
def create_provider_config(req: ProviderConfigCreate):
    configs = _read_agg_configs()
    new_id = f"prov_{uuid.uuid4().hex[:8]}"
    has_active = any(c.get("active") and c.get("type") == "provider" and c.get("provider_id") == req.provider_id for c in configs)
    configs.append({
        "id": new_id,
        "name": req.name or req.provider_id,
        "provider_id": req.provider_id,
        "api_key": req.api_key,
        "model": req.model,
        "base_url": req.base_url,
        "type": "provider",
        "active": not has_active,
    })
    _write_agg_configs(configs)
    return {"id": new_id, "saved": True}


@router.put("/settings/provider-configs/{config_id}")
def update_provider_config(config_id: str, req: ProviderConfigUpdate):
    configs = _read_agg_configs()
    for c in configs:
        if c["id"] == config_id and c.get("type") == "provider":
            if req.api_key is not None and "****" not in req.api_key:
                c["api_key"] = req.api_key
            if req.model is not None:
                c["model"] = req.model
            if req.base_url is not None:
                c["base_url"] = req.base_url
            _write_agg_configs(configs)
            return {"saved": True}
    raise HTTPException(status_code=404, detail="配置未找到")


@router.delete("/settings/provider-configs/{config_id}")
def delete_provider_config(config_id: str):
    configs = _read_agg_configs()
    configs = [c for c in configs if not (c["id"] == config_id and c.get("type") == "provider")]
    _write_agg_configs(configs)
    return {"deleted": True}


@router.post("/settings/provider-configs/{config_id}/activate")
def activate_provider_config(config_id: str):
    configs = _read_agg_configs()
    found = False
    target_provider = None
    for c in configs:
        if c["id"] == config_id and c.get("type") == "provider":
            target_provider = c.get("provider_id")
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="配置未找到")
    for c in configs:
        if c.get("type") == "provider" and c.get("provider_id") == target_provider:
            c["active"] = c["id"] == config_id
    _write_agg_configs(configs)
    return {"activated": True}


@router.post("/settings/test-aggregated")
def test_aggregated(req: TestAggRequest):
    """测试聚合平台连接 — 优先使用服务器端保存的 Key"""
    env = _read_env()
    base = req.base_url or env.get("AGGREGATED_BASE_URL", "")
    key = req.api_key or env.get("AGGREGATED_API_KEY", "")
    if not key:
        return {"success": False, "error": "API Key 未配置，请先保存"}
    if "****" in key:
        key = env.get("AGGREGATED_API_KEY", "")
    if not key or "****" in key:
        return {"success": False, "error": "API Key 未配置，请先保存"}
    try:
        models_url = base.rstrip("/")
        models_url += "/models" if "/v1" in models_url else "/v1/models"
        resp = requests.get(models_url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
        if resp.status_code == 200:
            body = resp.text.strip()
            if not body:
                # 200 但响应体为空，用客户端 chat API 做二次验证
                chat_url = base.rstrip("/") + "/chat/completions"
                chat_resp = requests.post(chat_url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}, timeout=15)
                if chat_resp.status_code == 200:
                    return {"success": True, "message": "连接成功（模型列表不可用，Chat API 正常）"}
                error_detail = chat_resp.text[:200]
                return {"success": False, "error": f"模型列表接口返回空，Chat API 状态码 {chat_resp.status_code}: {error_detail}"}
            data = json.loads(body)
            items = data.get("data", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else 0
            return {"success": True, "message": f"连接成功，可用模型 {count} 个"}
        else:
            err_text = resp.text[:200]
            return {"success": False, "error": f"HTTP {resp.status_code}: {err_text}"}
    except Exception as e:
        return {"success": False, "error": f"错误: {str(e)}"}
