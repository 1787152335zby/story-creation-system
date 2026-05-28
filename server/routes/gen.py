import re
import base64, random
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
import os, json, uuid, time, requests, shutil, threading
from tools.video_api_seedance import SeedanceBackend
from tools.video_api import create_video_backend
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

router = APIRouter()

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_UPLOAD_DIR = GENERATED_DIR / "_uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

from core.project_manager import PROJECTS_DIR

QUALITY_NEGATIVE = "bad hands, missing fingers, extra fingers, fused fingers, mutated hands, poorly drawn face, asymmetric eyes, distorted background, warped perspective, impossible architecture, Escher, disproportional, bad anatomy, blurry, low quality, jpeg artifacts, watermark, text, signature"

MODEL_VIDEO_BACKEND = {
    "seedance": "seedance",
    "doubao-seedance": "seedance",
    "kling": "kling",
    "kling-v1": "kling",
    "kling-v1-6": "kling",
    "kling-v2": "kling",
    "kling-v2-master": "kling",
    "kling-v2-1-master": "kling",
    "kling-v2-5-turbo": "kling",
    "kling-video-o1": "kling",
    "runway": "runway",
    "gen3": "runway",
    "gen3-alpha": "runway",
    "gen4": "runway",
    "pika": "pika",
    "pika-2": "pika",
    "pika-2.2": "pika",
    "luma": "luma",
    "dream-machine": "luma",
    "ray": "luma",
    "ray2": "luma",
}


def _detect_video_backend(model_name: str) -> str:
    """根据模型名检测使用哪个视频 backend"""
    if not model_name:
        return "seedance"
    ml = model_name.lower()
    for key, backend in MODEL_VIDEO_BACKEND.items():
        if key in ml:
            return backend
    return "seedance"

def _enrich_negative(negative: str) -> str:
    if QUALITY_NEGATIVE in negative:
        return negative
    return f"{negative}, {QUALITY_NEGATIVE}" if negative else QUALITY_NEGATIVE

AGG_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "aggregated_configs.json"

# 版本号生成锁，防并发覆盖
_version_lock = threading.Lock()

# 取消标志字典：task_id -> threading.Event
_cancel_events: dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()

# Resolution lookup is now centralized in tools.model_registry
from tools.model_registry import get_image_resolutions, get_video_resolutions


def _get_image_resolutions(model: str) -> list[str]:
    return get_image_resolutions(model)


def _get_video_resolutions(model: str) -> list[str]:
    return get_video_resolutions(model)


def _aspect_ratio(w: int, h: int) -> str:
    """Compute approximate aspect ratio label from width and height."""
    r = round(w / h, 3) if h else 0
    if abs(r - 1.0) < 0.01:
        return "1:1"
    if abs(r - 1.333) < 0.01:
        return "4:3"
    if abs(r - 1.25) < 0.01:
        return "5:4"
    if abs(r - 1.6) < 0.01:
        return "16:10"
    if abs(r - 1.778) < 0.01:
        return "16:9"
    if abs(r - 0.5625) < 0.02:
        return "9:16"
    if abs(r - 0.75) < 0.01:
        return "3:4"
    # DALL-E 7:4 ratio
    if abs(r - 1.75) < 0.01:
        return "7:4"
    if abs(r - 0.571) < 0.01:
        return "4:7"
    return f"{w}:{h}"


def _group_by_ratio(resolutions: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    order = ["1:1", "4:3", "5:4", "16:10", "16:9", "3:4", "9:16"]
    for res in resolutions:
        try:
            w, h = res.split("x")
            r = _aspect_ratio(int(w), int(h))
            groups.setdefault(r, []).append(res)
        except Exception:
            groups.setdefault("自定义", []).append(res)
    # Sort groups by predefined order
    sorted_groups: dict[str, list[str]] = {}
    for key in order:
        if key in groups:
            sorted_groups[key] = groups[key]
    for key in groups:
        if key not in sorted_groups:
            sorted_groups[key] = groups[key]
    return sorted_groups


class StitchRequest(BaseModel):
    image_paths: list[str]
    save_to: str = ""

class FreeImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""
    reference_url: str = ""
    reference_urls: list[str] = []
    reference_urls_by_type: dict = {}
    extra_params: dict = {}


class ProjectImageRequest(BaseModel):
    project_name: str
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""
    character_names: list[str] = []
    scene_names: list[str] = []
    prop_names: list[str] = []
    reference_url: str = ""
    reference_urls: list[str] = []
    reference_urls_by_type: dict = {}
    version: str = ""
    extra_params: dict = {}


def _call_seedream(prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1,
                   api_key: str | None = None, base_url: str | None = None) -> list[str]:
    api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 未配置，请先在设置页配置 SEEDANCE_API_KEY")
    url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "seedream-v1", "prompt": prompt, "n": n, "size": size}
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return [img["url"] for img in data.get("data", [])]


def _call_seedance_image_to_video(image_paths: list[str], prompt: str,
                                  resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False,
                                  api_key: str | None = None, base_url: str | None = None,
                                  model: str = "", negative_prompt: str = "") -> str:
    backend = SeedanceBackend()
    if api_key:
        backend.api_key = api_key
    if model:
        backend.model = model
    if not image_paths:
        raise HTTPException(status_code=400, detail="请上传至少一张参考图片")
    return backend.image_to_video(image_paths[0], prompt, resolution, duration, generate_audio,
                                   model or backend.model, negative_prompt,
                                   last_frame_path=image_paths[1] if len(image_paths) >= 2 else "")


def _poll_seedance(task_id: str, timeout: int = 300) -> dict:
    api_key = os.getenv("SEEDANCE_API_KEY", "")
    query_url = f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(query_url, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "running")
        if status == "succeeded":
            return {"video_url": result.get("video_url", ""), "last_frame_url": result.get("last_frame_url", "")}
        elif status in ("failed", "expired"):
            err = result.get("error") or result.get("status") or "未知错误"
            raise RuntimeError(f"视频生成失败: {err}")
        time.sleep(10)
    raise TimeoutError("视频生成超时")


def _download_file(url: str, save_dir: Path, prefix: str = "") -> str:
    # If it's already a local file (Gemini images saved locally), just copy it
    if os.path.exists(url):
        ext = os.path.splitext(url)[1] or ".png"
        file_name = f"{prefix}{uuid.uuid4().hex[:8]}{ext}"
        save_path = save_dir / file_name
        shutil.copy2(url, str(save_path))
        return str(save_path)
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    ext = "mp4" if "video" in resp.headers.get("content-type", "") else "png"
    file_name = f"{prefix}{uuid.uuid4().hex[:8]}.{ext}"
    save_path = save_dir / file_name
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return str(save_path)


PROVIDER_TO_TYPE = {
    "deepseek": "llm",
    "openai": "llm",
    "claude": "llm",
    "seedream": "image",
    "gpt-image": "image",
    "banana2": "image",
    "seedance": "video",
}


def _get_active_agg_config(config_type: str) -> dict | None:
    """Get the active aggregated config for a given type (llm/image/video).
    Checks exact type match first, then provider configs."""
    if not AGG_CONFIG_PATH.exists():
        return None
    try:
        configs = json.loads(AGG_CONFIG_PATH.read_text(encoding="utf-8"))
        for c in configs:
            if c.get("type") == config_type and c.get("active"):
                return c
        for c in configs:
            if c.get("type") == "provider" and c.get("active"):
                pid = c.get("provider_id", "").lower()
                if PROVIDER_TO_TYPE.get(pid) == config_type:
                    return c
    except Exception:
        pass
    return None


def _resolve_ref_url(ref_url: str) -> str:
    """Resolve a reference URL to something the downstream API can consume.
    - data: URIs pass through as-is
    - http/https pass through as-is
    - /api/gen-files/ paths are resolved to local GENERATED_DIR paths
    - other values are treated as local file paths
    """
    if ref_url.startswith("data:") or ref_url.startswith("http"):
        return ref_url
    if ref_url.startswith("/api/gen-files/"):
        local_rel = ref_url.replace("/api/gen-files/", "")
        return str(GENERATED_DIR / local_rel)
    return ref_url


def _build_ref_prefix(reference_urls_by_type: dict) -> str:
    prefix = ""
    if reference_urls_by_type.get("style"):
        prefix += "参考以下图片的整体视觉风格：色彩体系、渲染质感、光影倾向和艺术手法。不复制画面内容、构图或具体物体。\n"
    if reference_urls_by_type.get("character"):
        prefix += "参考以下角色的艺术呈现风格：面部刻画的细腻程度、皮肤与服装的材质质感、光影在人物身上的处理方式，以及整体的人物视觉品质。不要求复刻该角色的具体身份或外貌特征。\n"
    if reference_urls_by_type.get("scene"):
        prefix += "参考以下场景的艺术呈现风格：空间层次的构建方式、材质在环境中的表现质感、氛围与光影的空间处理手法。不要求复刻具体的场景布局或建筑结构。\n"
    if reference_urls_by_type.get("prop"):
        prefix += "参考以下道具的艺术呈现风格：材质质感与表面光泽的表现精度、细节雕刻的细腻程度、道具与光线的交互关系。不要求复刻该道具的具体形态或功能设定。\n"
    return prefix


def _call_image_api(req, agg: dict | None) -> tuple[list[str], int]:
    """Generate images using the user's selected config. Returns (image_urls, actual_seed)."""
    if not agg or not agg.get("api_key"):
        raise HTTPException(status_code=400, detail="未配置图片 API，请在设置页配置")

    api_key = agg["api_key"]
    base_url = agg.get("base_url", "").rstrip("/")
    model = (req.model if req.model and req.model != "default" else agg.get("model")) or "gpt-image-1"
    prompt = req.prompt
    negative = getattr(req, "negative_prompt", "")
    n = req.n or 1
    size = req.size or "1024x1024"
    reference_url = getattr(req, "reference_url", "") or ""
    reference_urls = getattr(req, "reference_urls", []) or []
    reference_urls_by_type = getattr(req, "reference_urls_by_type", {}) or {}
    if reference_url and not reference_urls:
        reference_urls = [reference_url]

    if reference_urls and not reference_urls_by_type:
        reference_urls_by_type = {"character": list(reference_urls)}

    extra_params = dict(getattr(req, "extra_params", {}) or {})

    # 如果用户没填 seed，自动生成一个
    sd = extra_params.get("seed")
    if not sd:
        sd = random.randint(0, 2147483647)
        extra_params["seed"] = sd

    model_lower = model.lower()

    # 路径 1: Seedream / SeedEdit — 原生图生图，走 /images/generations + image 参数
    if "seedream" in model_lower or "seededit" in model_lower or "qwen-image-edit" in model_lower or "qwen-image-2" in model_lower:
        import requests as req_http
        per_prompt = _build_ref_prefix(reference_urls_by_type) + prompt
        payload = {
            "model": model,
            "prompt": per_prompt,
            "n": n,
            "size": size,
        }
        if negative:
            payload["negative_prompt"] = negative
        if reference_urls:
            resolved = []
            for r in reference_urls:
                resolved.append(_resolve_ref_url(r))
            payload["image"] = resolved
        cfg = extra_params.get("cfg_scale")
        if cfg is not None:
            payload["cfg_scale"] = float(cfg)
        sd = extra_params.get("seed")
        if sd is not None:
            payload["seed"] = int(sd)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = req_http.post(f"{base_url}/images/generations", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return [img["url"] for img in resp.json().get("data", [])], sd

    # 路径 2: Gemini — 参考图作为独立消息（控制台式编辑）
    if "gemini" in model_lower:
        urls = []
        reference_content_parts = []
        for ref_url in reference_urls:
            try:
                resolved = _resolve_ref_url(ref_url)
                if resolved.startswith("data:"):
                    img_data = base64.b64decode(resolved.split(",", 1)[1])
                elif resolved.startswith("http"):
                    resp_ref = requests.get(resolved, timeout=30)
                    img_data = resp_ref.content
                else:
                    img_data = Path(resolved).read_bytes()
                b64 = base64.b64encode(img_data).decode()
                reference_content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
            except Exception:
                pass

        for i in range(n):
            if i > 0:
                time.sleep(3)
            per_prompt = prompt
            if n > 1:
                per_prompt = f"（第{i+1}/{n}张）{prompt}"
            try:
                messages = []
                if reference_content_parts:
                    messages.append({"role": "user", "content": reference_content_parts})
                    user_text = _build_ref_prefix(reference_urls_by_type) + per_prompt
                    if negative:
                        user_text = f"{user_text}\n\n避免：{negative}"
                    messages.append({"role": "user", "content": user_text})
                else:
                    user_text = per_prompt
                    if negative:
                        user_text = f"{per_prompt}\n\n避免：{negative}"
                    messages.append({"role": "user", "content": user_text})

                resp = requests.post(
                    f"{base_url}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages},
                    timeout=300,
                )
                if resp.status_code == 400:
                    detail = resp.json().get("error", {}).get("message", str(resp.text))
                    raise HTTPException(status_code=400, detail=f"生图请求失败: {detail}")
                if resp.status_code in (408, 504):
                    raise HTTPException(status_code=504, detail="生图请求超时，API 响应时间超过 300 秒，请稍后重试")
                if resp.status_code == 429:
                    detail = resp.json().get("error", {}).get("message", "请求频率过高")
                    raise HTTPException(status_code=429, detail=f"API 请求频率限制（429 Too Many Requests）: {detail}。请等待 30 秒后重试")
                resp.raise_for_status()
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                matches = re.findall(r'data:image/[^;]+;base64,([^")\s]+)', content)
                for b64 in matches:
                    try:
                        img_data = base64.b64decode(b64)
                        file_path = GENERATED_DIR / f"gemini_{uuid.uuid4().hex[:8]}.png"
                        file_path.write_bytes(img_data)
                        urls.append(str(file_path))
                    except Exception:
                        continue
            except requests.exceptions.Timeout:
                raise HTTPException(status_code=504, detail="生图请求超时，API 响应时间超过 5 分钟，请稍后重试或换一个小模型")
            except requests.exceptions.ConnectionError as e:
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    raise HTTPException(status_code=504, detail="生图请求超时，API 响应时间超过 5 分钟，请稍后重试")
                raise HTTPException(status_code=502, detail=f"无法连接到图片 API 服务器: {str(e)[:200]}")
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=502, detail=f"图片 API 请求失败: {str(e)[:200]}")
        if not urls:
            raise HTTPException(status_code=500, detail="Gemini 模型返回了内容但没有解析到图片数据")
        return urls, sd

    # 路径 3: 通用聚合平台图生模型 — 走 /v1/chat/completions 出图
    # 支持 flux、sdxl、playground、recraft、ideogram 等任何聚合平台上的图片模型
    import requests as req_http
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    image_prompt = prompt
    if negative:
        image_prompt = f"{prompt}\n\n避免以下内容：{negative}"
    if reference_urls:
        image_prompt = _build_ref_prefix(reference_urls_by_type) + image_prompt

    urls = []
    for i in range(n):
        try:
            messages = []
            if reference_urls and i == 0:
                content_parts = [{"type": "text", "text": image_prompt}]
                for ref_url in reference_urls[:3]:
                    try:
                        resolved = _resolve_ref_url(ref_url)
                        if resolved.startswith("data:"):
                            content_parts.insert(0, {"type": "image_url", "image_url": {"url": resolved}})
                        elif resolved.startswith("http"):
                            content_parts.insert(0, {"type": "image_url", "image_url": {"url": resolved}})
                        else:
                            with open(resolved, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode()
                            content_parts.insert(0, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
                    except Exception:
                        pass
                messages.append({"role": "user", "content": content_parts})
            else:
                per_prompt = image_prompt if n == 1 else f"（第{i+1}/{n}张）{image_prompt}"
                messages.append({"role": "user", "content": per_prompt})

            resp = req_http.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages, "max_tokens": 4096},
                timeout=300,
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            b64_matches = re.findall(r'data:image/[^;]+;base64,([^")\s]+)', content)
            for b64_match in b64_matches:
                try:
                    img_data = base64.b64decode(b64_match)
                    file_path = GENERATED_DIR / f"agg_{uuid.uuid4().hex[:8]}.png"
                    file_path.write_bytes(img_data)
                    urls.append(str(file_path))
                except Exception:
                    continue
            url_matches = re.findall(r'(https?://[^\s<>"]+\.(?:png|jpg|jpeg|webp|gif))', content)
            for img_url in url_matches:
                try:
                    local_path = _download_file(img_url, GENERATED_DIR, "agg_")
                    urls.append(local_path)
                except Exception:
                    continue
            if len(urls) >= n:
                break
        except Exception:
            continue

    if urls:
        return urls, sd

    # /v1/chat/completions 没出图，尝试 /v1/images/generations（OpenAI DALL-E 格式）
    try:
        payload = {"model": model, "prompt": prompt, "n": n, "size": size}
        if negative:
            payload["negative_prompt"] = negative
        sd_val = extra_params.get("seed")
        if sd_val is not None:
            payload["seed"] = int(sd_val)
        resp = req_http.post(f"{base_url}/v1/images/generations", headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return [img["url"] for img in resp.json().get("data", [])], sd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型 {model} 不支持图片生成或调用失败: {str(e)[:200]}")


@router.post("/image-gen/free")
def free_image_gen(req: FreeImageRequest):
    req.negative_prompt = _enrich_negative(req.negative_prompt)
    """自由文生图 — 按用户选择的 API/模型生成"""
    agg = _get_active_agg_config("image")
    task_id = f"free_{uuid.uuid4().hex[:8]}"
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_events[task_id] = cancel_event
    try:
        if cancel_event.is_set():
            raise HTTPException(status_code=499, detail="生成已取消")
        urls, actual_seed = _call_image_api(req, agg)
        if cancel_event.is_set():
            raise HTTPException(status_code=499, detail="生成已取消")
        saved = []
        for url in urls:
            if os.path.exists(url) and GENERATED_DIR in Path(url).parents:
                saved.append({"url": url, "local": url})
            else:
                local_path = _download_file(url, GENERATED_DIR, "free_")
                saved.append({"url": url, "local": local_path})
        meta_dir = GENERATED_DIR / "_meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        for item in saved:
            local_path = item["local"]
            filename = os.path.basename(local_path)
            meta = {
                "filename": filename,
                "mode": "free",
                "prompt": req.prompt,
                "negative_prompt": req.negative_prompt,
                "model": req.model,
                "size": req.size,
                "count": req.n,
                "seed": actual_seed,
                "reference_urls": req.reference_urls,
                "reference_urls_by_type": req.reference_urls_by_type or {},
                "timestamp": datetime.now().isoformat(),
            }
            meta_path = meta_dir / f"{filename}.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        return {"images": saved, "task_id": task_id, "seed": actual_seed}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"生图失败: {e}")
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)[:300]}")
    finally:
        with _cancel_lock:
            _cancel_events.pop(task_id, None)


@router.post("/image-gen/project-demand-batch")
def project_demand_batch_gen(req: ProjectImageRequest):
    req.negative_prompt = _enrich_negative(req.negative_prompt)
    agg = _get_active_agg_config("image")
    task_id = f"proj_{uuid.uuid4().hex[:8]}"
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_events[task_id] = cancel_event

    import json
    try:
        demand_path = PROJECTS_DIR / req.project_name / "06_生图需求" / "生图清单.json"
        if not demand_path.exists():
            demand_path = PROJECTS_DIR / req.project_name / "07_生图需求" / "生图清单.json"
        demands = None
        if demand_path.exists():
            demands = json.loads(demand_path.read_text(encoding="utf-8"))
        if not demand_path.exists():
            if not req.prompt.strip():
                raise HTTPException(status_code=404, detail="找不到生图需求清单，请先运行生图准备阶段")

        all_chars = (demands or {}).get("characters", [])
        all_scenes = (demands or {}).get("scenes", [])

        if not req.character_names and not req.scene_names and not req.prop_names:
            if not req.prompt.strip():
                raise HTTPException(status_code=400, detail="请指定要生成的角色或场景，或输入提示词")

        results = []
        to_gen = []

        if req.character_names:
            for ch_name in req.character_names:
                ch = next((c for c in all_chars if c["name"] == ch_name), None)
                if ch:
                    to_gen.append(("character", ch_name, ch.get("prompt", req.prompt)))

        if req.scene_names:
            for sc_name in req.scene_names:
                sc = next((s for s in all_scenes if s["name"] == sc_name), None)
                if sc:
                    prompt = sc.get("prompt", req.prompt)
                    if "不要出现人物" not in prompt:
                        prompt += "\n\n纯场景环境图，不得出现任何人物。"
                    to_gen.append(("scene", sc_name, prompt))

        if req.prop_names:
            all_props = demands.get("key_props", [])
            for prop_name in req.prop_names:
                prop = next((p for p in all_props if p["name"] == prop_name), None)
                if prop:
                    to_gen.append(("prop", prop_name, prop.get("prompt", req.prompt)))

        if not to_gen:
            to_gen = [("custom", "custom", req.prompt)]

        for entity_type, name, prompt in to_gen:
            if cancel_event.is_set():
                raise HTTPException(status_code=499, detail="生成已取消")

            gen_req = ProjectImageRequest(
                project_name=req.project_name,
                prompt=prompt,
                negative_prompt=req.negative_prompt,
                size=req.size,
                n=req.n or 1,
                model=req.model,
                character_names=[name] if entity_type == "character" else [],
                scene_names=[name] if entity_type == "scene" else [],
                prop_names=[name] if entity_type == "prop" else [],
                reference_urls=req.reference_urls or [],
                reference_urls_by_type=req.reference_urls_by_type or {},
                version=req.version,
            )

            urls, seed = _call_image_api(gen_req, agg)
            saved = []
            for url in urls:
                if os.path.exists(url) and GENERATED_DIR in Path(url).parents:
                    old_path = Path(url)
                    new_name = f"proj_{uuid.uuid4().hex[:8]}{old_path.suffix}"
                    new_path = old_path.with_name(new_name)
                    old_path.rename(new_path)
                    saved.append({"url": url, "local": str(new_path)})
                else:
                    local = _download_file(url, GENERATED_DIR, "proj_")
                    saved.append({"url": url, "local": local})

            entity_cn = "角色" if entity_type == "character" else ("场景" if entity_type == "scene" else "道具")
            entity_dir = PROJECTS_DIR / req.project_name / "07_生成素材" / entity_cn / name
            with _version_lock:
                version = _next_version(entity_dir)
            folder = f"{entity_cn}/{name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                fn = f"{entity_type}_{uuid.uuid4().hex[:8]}{ext}"
                cp = _copy_to_project_folder(img["local"], req.project_name, folder, fn)
                copies.append({"url": img["url"], "local": cp})

            results.append({"type": entity_type, "name": name, "folder": folder, "images": copies, "version": version})

        return {"results": results, "task_id": task_id, "seed": seed}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"生图失败: {e}")
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)[:300]}")
    finally:
        with _cancel_lock:
            _cancel_events.pop(task_id, None)


@router.get("/image-gen/resolutions")
def list_image_resolutions(model: str = Query(default="")):
    """根据模型返回支持的分辨率及比例分组。不同模型支持不同级别。"""
    resolutions = _get_image_resolutions(model)
    return {"resolutions": resolutions, "groups": _group_by_ratio(resolutions)}


def _next_version(dir_path: Path) -> int:
    """Find next version number for a project entity folder."""
    if not dir_path.exists():
        return 1
    max_v = 0
    for d in dir_path.iterdir():
        if d.is_dir() and d.name.startswith("v"):
            try:
                v = int(d.name[1:])
                max_v = max(max_v, v)
            except:
                pass
    return max_v + 1


def _scan_images(dir_path: Path, project_name: str, entity_type: str, subpath: str) -> list[dict]:
    """Scan a directory for image files and return as API response list."""
    images = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            images.append({
                "name": f.name,
                "url": f"/api/gen-files/projects/{project_name}/{entity_type}/{subpath}/{f.name}"
            })
    return images


@router.post("/image-gen/project")
def project_image_gen(req: ProjectImageRequest):
    req.negative_prompt = _enrich_negative(req.negative_prompt)
    """项目模式生图 — 按角色/场景分版本文件夹保存"""
    agg = _get_active_agg_config("image")
    task_id = f"proj_{uuid.uuid4().hex[:8]}"
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_events[task_id] = cancel_event

    try:
        if cancel_event.is_set():
            raise HTTPException(status_code=499, detail="生成已取消")
        urls, actual_seed = _call_image_api(req, agg)
        if cancel_event.is_set():
            raise HTTPException(status_code=499, detail="生成已取消")
        saved = []
        project_images = []
        version_map = {}

        for url in urls:
            if os.path.exists(url) and GENERATED_DIR in Path(url).parents:
                saved.append({"url": url, "local": url})
            else:
                local_path = _download_file(url, GENERATED_DIR, "proj_")
                saved.append({"url": url, "local": local_path})

        for char_name in req.character_names:
            char_dir = PROJECTS_DIR / req.project_name / "07_生成素材" / "角色" / char_name
            with _version_lock:
                version = _next_version(char_dir)
            folder = f"角色/{char_name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                file_name = f"char_{uuid.uuid4().hex[:8]}{ext}"
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, file_name)
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})
            version_map[f"角色/{char_name}"] = version

        for scene_name in req.scene_names:
            scene_dir = PROJECTS_DIR / req.project_name / "07_生成素材" / "场景" / scene_name
            if req.version:
                version = int(req.version)
            else:
                with _version_lock:
                    version = _next_version(scene_dir)
            folder = f"场景/{scene_name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                file_name = f"scene_{uuid.uuid4().hex[:8]}{ext}"
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, file_name)
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})
            version_map[f"场景/{scene_name}"] = version

        for prop_name in req.prop_names:
            prop_dir = PROJECTS_DIR / req.project_name / "07_生成素材" / "道具" / prop_name
            if req.version:
                version = int(req.version)
            else:
                with _version_lock:
                    version = _next_version(prop_dir)
            folder = f"道具/{prop_name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                file_name = f"prop_{uuid.uuid4().hex[:8]}{ext}"
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, file_name)
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})
            version_map[f"道具/{prop_name}"] = version

        meta_dir = GENERATED_DIR / "_meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        for item in saved:
            local_path = item["local"]
            filename = os.path.basename(local_path)
            meta = {
                "filename": filename,
                "mode": "project",
                "prompt": req.prompt,
                "negative_prompt": req.negative_prompt,
                "model": req.model,
                "size": req.size,
                "count": req.n,
                "reference_urls": req.reference_urls,
                "project_name": req.project_name,
                "character_names": req.character_names,
                "scene_names": req.scene_names,
                "prop_names": req.prop_names,
                "version": req.version or "1",
                "seed": actual_seed,
                "timestamp": datetime.now().isoformat(),
            }
            meta_path = meta_dir / f"{filename}.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

        # 自动确认版本：对每个生成了图片的角色/场景写入 _confirmed
        for folder_name, v in version_map.items():
            confirmed_path = PROJECTS_DIR / req.project_name / "07_生成素材" / folder_name / f"v{v}" / "_confirmed"
            confirmed_path.parent.mkdir(parents=True, exist_ok=True)
            confirmed_path.touch()

        return {"images": saved, "project_images": project_images, "versions": version_map, "task_id": task_id, "seed": actual_seed}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)}")
    finally:
        with _cancel_lock:
            _cancel_events.pop(task_id, None)


def _copy_to_project_folder(src_path: str, project_name: str, subfolder: str, file_name: str) -> str:
    dest_dir = PROJECTS_DIR / project_name / "07_生成素材" / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_name
    import shutil
    shutil.copy2(src_path, str(dest_path))
    return str(dest_path)


@router.post("/image-gen/stitch")
def stitch_images(req: StitchRequest):
    """Stitch 4 images into a 2x2 grid and draw angle labels."""
    paths = req.image_paths[:4]
    if len(paths) != 4:
        raise HTTPException(status_code=400, detail="需要4张图片进行拼合")

    images = []
    for p in paths:
        p = p.lstrip("/")
        full = Path(p) if os.path.exists(p) else GENERATED_DIR / p
        if not full.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {p}")
        images.append(Image.open(full).convert("RGB"))

    w, h = images[0].size
    canvas_w, canvas_h = w * 2, h * 2
    composite = Image.new("RGB", (canvas_w, canvas_h), (30, 30, 30))
    labels = ["正视图", "左侧面", "背面", "右侧面"]
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    for i, (img, label) in enumerate(zip(images, labels)):
        x = (i % 2) * w
        y = (i // 2) * h
        composite.paste(img, (x, y))
        draw = ImageDraw.Draw(composite)
        tw = draw.textlength(label, font=font) if hasattr(draw, "textlength") else len(label) * 16
        lx = x + w // 2 - tw // 2
        ly = y + 12
        draw.rectangle([lx - 6, ly - 4, lx + tw + 6, ly + 30 + 4], fill=(0, 0, 0))
        draw.text((lx, ly), label, fill="white", font=font)

    save_name = f"stitch_{uuid.uuid4().hex[:8]}.png"
    save_path = GENERATED_DIR / save_name
    composite.save(str(save_path))
    result = {"url": f"/api/gen-files/{save_name}", "local": str(save_path), "name": save_name}
    if req.save_to:
        dest = PROJECTS_DIR / req.save_to / "07_生成素材" / save_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        composite.save(str(dest))
        result["saved_to"] = f"/api/gen-files/projects/{req.save_to}/{save_name}"
    return result


def _list_entity_versions(base_dir: Path, project_name: str, entity_type: str) -> dict:
    result = {}
    entity_type_cn = "角色" if entity_type == "characters" else "场景"
    entities_dir = base_dir / entity_type_cn
    if not entities_dir.exists():
        return result
    for folder in sorted(entities_dir.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name
        confirmed = []
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                confirmed.append({
                    "name": f.name,
                    "url": f"/api/gen-files/projects/{project_name}/{entity_type_cn}/{name}/{f.name}"
                })
        versions = {}
        for vdir in sorted(folder.iterdir(), key=lambda x: x.name):
            if vdir.is_dir() and vdir.name.startswith("v"):
                vnum = vdir.name[1:]
                confirmed_fn = folder / "_confirmed"
                is_confirmed = confirmed_fn.exists() and confirmed_fn.read_text().strip() == vdir.name
                images = _scan_images(vdir, project_name, entity_type_cn, f"{name}/{vdir.name}")
                versions[vnum] = {"confirmed": is_confirmed, "images": images}
        if confirmed or versions:
            result[name] = {"images": confirmed, "versions": versions}
    return result


@router.get("/image-gen/project-images/{project_name}")
def list_project_images(project_name: str):
    base_dir = PROJECTS_DIR / project_name / "07_生成素材"
    if not base_dir.exists():
        return {"characters": {}, "scenes": {}}
    return {
        "characters": _list_entity_versions(base_dir, project_name, "characters"),
        "scenes": _list_entity_versions(base_dir, project_name, "scenes"),
    }


@router.get("/image-gen/confirmed-images/{project_name}")
def list_confirmed_images(project_name: str):
    base_dir = PROJECTS_DIR / project_name / "07_生成素材"
    if not base_dir.exists():
        return {"characters": {}, "scenes": {}}
    result = {"characters": {}, "scenes": {}}
    for entity_type in ("characters", "scenes"):
        entity_type_cn = "角色" if entity_type == "characters" else "场景"
        entities_dir = base_dir / entity_type_cn
        if not entities_dir.exists():
            continue
        for folder in sorted(entities_dir.iterdir()):
            if not folder.is_dir():
                continue
            name = folder.name
            confirmed_fn = folder / "_confirmed"
            if not confirmed_fn.exists():
                continue
            images = []
            for f in sorted(folder.iterdir()):
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    images.append({
                        "name": f.name,
                        "url": f"/api/gen-files/projects/{project_name}/{entity_type_cn}/{name}/{f.name}"
                    })
            if images:
                result[entity_type][name] = images
    return result


@router.delete("/image-gen/delete")
def delete_generated_file(file_path: str = Query(...)):
    full = Path(file_path)
    if not full.exists():
        clean = file_path.replace("/api/gen-files/", "").lstrip("/")
        full = GENERATED_DIR / clean
        if not full.exists():
            full = PROJECTS_DIR / "07_生成素材" / clean
            if not full.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
    try:
        full.unlink()
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/image-gen/clear-folder")
def clear_project_folder(project_name: str = Query(...), subfolder: str = Query(...)):
    target = PROJECTS_DIR / project_name / "07_生成素材" / subfolder
    if not target.exists():
        return {"deleted": 0}
    count = 0
    for f in list(target.iterdir()):
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            try:
                f.unlink()
                count += 1
            except:
                pass
    return {"deleted": count}


@router.post("/image-gen/confirm-version")
def confirm_version(project_name: str = Query(...), entity_type: str = Query(...), entity_name: str = Query(...), version: str = Query(...)):
    src = PROJECTS_DIR / project_name / "07_生成素材" / entity_type / entity_name / f"v{version}"
    dst = PROJECTS_DIR / project_name / "07_生成素材" / entity_type / entity_name
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"版本 v{version} 不存在")
    for f in list(dst.iterdir()):
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.name != ".gitkeep":
            try:
                f.unlink()
            except Exception:
                logger.warning(f"清理旧版本图片失败: {f}")
    for f in src.iterdir():
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            import shutil
            shutil.copy2(str(f), str(dst / f.name))
    (dst / "_confirmed").write_text(f"v{version}")

    _sync_demand_confirmation(project_name, entity_type, entity_name)

    return {"confirmed": True, "version": version}


def _sync_demand_confirmation(project_name: str, entity_type: str, entity_name: str):
    import json
    demand_dir = PROJECTS_DIR / project_name / "06_生图需求"
    if not demand_dir.exists():
        demand_dir = PROJECTS_DIR / project_name / "07_生图需求"
    if not demand_dir.exists():
        return
    confirmed_file = demand_dir / "_confirmed.json"
    confirmed = {}
    if confirmed_file.exists():
        try:
            confirmed = json.loads(confirmed_file.read_text(encoding="utf-8"))
        except Exception:
            confirmed = {}
    confirmed[entity_name] = {
        "type": entity_type,
        "confirmed_at": __import__("datetime").datetime.now().isoformat(),
    }
    confirmed_file.write_text(json.dumps(confirmed, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/image-gen/delete-version")
def delete_version(project_name: str = Query(...), entity_type: str = Query(...), entity_name: str = Query(...), version: str = Query(...)):
    target = PROJECTS_DIR / project_name / "07_生成素材" / entity_type / entity_name / f"v{version}"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"版本 v{version} 不存在")
    import shutil
    shutil.rmtree(str(target))
    dst = PROJECTS_DIR / project_name / "07_生成素材" / entity_type / entity_name
    confirmed_fn = dst / "_confirmed"
    if confirmed_fn.exists() and confirmed_fn.read_text().strip() == f"v{version}":
        try:
            confirmed_fn.unlink()
        except Exception:
            logger.warning(f"清除确认标记失败: {confirmed_fn}")
    return {"deleted": True, "version": version}


@router.get("/image-gen/backends")
def list_image_backends():
    import os
    backends = {
        "seedream": {"name": "Seedream", "models": ["seedream-v1"]},
    }
    return {"backends": backends}


@router.post("/image-gen/cancel")
def cancel_image_generation(data: dict):
    """取消正在进行的生成任务"""
    task_id = data.get("task_id", "")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    with _cancel_lock:
        event = _cancel_events.get(task_id)
        if event:
            event.set()
            return {"status": "cancelled", "task_id": task_id}
    return {"status": "not_found", "task_id": task_id}


@router.post("/video-gen/free")
async def free_video_gen(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=None),
    model: str = Form(default=""),
    resolution: str = Form(default="1280x720"),
    duration: int = Form(default=5),
    generate_audio: bool = Form(default=False),
    negative_prompt: str = Form(default=""),
):
    saved_paths = []
    if files:
        for f in files:
            ext = f.filename.split(".")[-1] if "." in (f.filename or "") else "png"
            temp_path = TEMP_UPLOAD_DIR / f"upload_{uuid.uuid4().hex[:8]}.{ext}"
            content = await f.read()
            temp_path.write_bytes(content)
            saved_paths.append(str(temp_path))

    agg = _get_active_agg_config("video")
    agg_key = agg.get("api_key") if agg else None
    agg_base = agg.get("base_url") if agg else None
    effective_model = model or (agg.get("model") if agg else "") or ""
    backend_name = _detect_video_backend(effective_model)

    try:
        if backend_name != "seedance" and agg_key and agg_base:
            backend = create_video_backend(backend_name)
            backend.api_key = agg_key
            backend.base_url = agg_base
            if not saved_paths:
                task_id = backend.text_to_video(prompt, resolution, duration, generate_audio, model=effective_model, negative_prompt=negative_prompt)
            else:
                task_id = backend.image_to_video(saved_paths[0], prompt, resolution, duration, generate_audio, model=effective_model, negative_prompt=negative_prompt)
            poll_result = backend.wait_for_result(task_id, timeout=600)
        else:
            if not saved_paths:
                if agg_key and agg_base:
                    task_id = _call_seedance_text_to_video(prompt, resolution, duration, generate_audio, api_key=agg_key, base_url=agg_base, model=model, negative_prompt=negative_prompt)
                else:
                    task_id = _call_seedance_text_to_video(prompt, resolution, duration, generate_audio, model=model, negative_prompt=negative_prompt)
            else:
                if agg_key and agg_base:
                    task_id = _call_seedance_image_to_video(saved_paths, prompt, resolution, duration, generate_audio, api_key=agg_key, base_url=agg_base, model=model, negative_prompt=negative_prompt)
                else:
                    task_id = _call_seedance_image_to_video(saved_paths, prompt, resolution, duration, generate_audio, model=model, negative_prompt=negative_prompt)
            poll_result = _poll_seedance(task_id, timeout=300)
        video_url = poll_result["video_url"]
        local_path = _download_file(video_url, GENERATED_DIR, "video_")

        for sp in saved_paths:
            try:
                os.remove(sp)
            except Exception:
                logger.warning(f"清理临时图片失败: {sp}")

        # 写入视频元数据
        try:
            meta_dir = GENERATED_DIR / "_meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            video_filename = os.path.basename(local_path)
            meta = {
                "filename": video_filename,
                "mode": "free",
                "prompt": prompt,
                "model": model,
                "resolution": resolution,
                "duration": duration,
                "negative_prompt": negative_prompt,
                "timestamp": datetime.now().isoformat(),
                "reference_files": [os.path.basename(p) for p in saved_paths] if saved_paths else [],
            }
            meta_path = meta_dir / f"{video_filename}.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"写入视频元数据失败: {e}")

        return {"video_url": video_url, "local": local_path, "task_id": task_id}
    except Exception as e:
        for sp in saved_paths:
            try:
                os.remove(sp)
            except Exception:
                logger.warning(f"清理失败临时图片失败: {sp}")
        return {"error": str(e), "task_id": task_id if "task_id" in dir() else ""}


def _call_seedance_text_to_video(prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False,
                                 api_key: str | None = None, base_url: str | None = None,
                                 model: str = "", negative_prompt: str = "") -> str:
    backend = SeedanceBackend()
    if api_key:
        backend.api_key = api_key
    if model:
        backend.model = model
    return backend.text_to_video(prompt, resolution, duration, generate_audio, model or backend.model, negative_prompt)


def _call_agg_text_to_video(prompt: str, resolution: str, duration: int,
                             model: str, api_key: str, base_url: str,
                             negative_prompt: str = "") -> str:
    """通用聚合平台文生视频 — 提交任务，返回 task_id"""
    base = base_url.rstrip("/")
    payload = {"model": model, "prompt": prompt, "resolution": resolution, "duration": duration}
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    resp = requests.post(
        f"{base}/v1/video/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code == 404:
        resp = requests.post(
            f"{base}/video/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json().get("task_id") or resp.json().get("id", "")


def _call_agg_image_to_video(image_paths: list[str], prompt: str, resolution: str,
                              duration: int, model: str, api_key: str, base_url: str,
                              negative_prompt: str = "") -> str:
    """通用聚合平台图生视频 — 提交任务，返回 task_id"""
    import base64 as b64mod
    base = base_url.rstrip("/")
    images_b64 = []
    for p in image_paths[:1]:
        with open(p, "rb") as f:
            images_b64.append(b64mod.b64encode(f.read()).decode())
    payload = {
        "model": model, "prompt": prompt, "resolution": resolution,
        "duration": duration, "images": images_b64,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    resp = requests.post(
        f"{base}/v1/video/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code == 404:
        resp = requests.post(
            f"{base}/video/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json().get("task_id") or resp.json().get("id", "")


def _poll_agg_video(api_key: str, base_url: str, task_id: str, timeout: int = 600) -> dict:
    """轮询聚合平台视频任务直到完成"""
    base = base_url.rstrip("/")
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{base}/v1/video/result/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code == 404:
            resp = requests.get(
                f"{base}/video/result/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "")
            if status in ("completed", "succeeded", "done"):
                video_url = data.get("video_url") or data.get("url") or ""
                if not video_url:
                    outputs = data.get("output", {}) or data.get("results", [])
                    if isinstance(outputs, list) and outputs:
                        video_url = outputs[0].get("video_url") or outputs[0].get("url", "")
                    elif isinstance(outputs, dict):
                        video_url = outputs.get("video_url") or outputs.get("url", "")
                if video_url:
                    return {"video_url": video_url}
            elif status in ("failed", "error"):
                raise Exception(f"视频生成失败: {data.get('error', '')}")
        time.sleep(5)
    raise Exception(f"视频生成超时 ({timeout}s)，task_id: {task_id}")


@router.get("/video-gen/resolutions")
def list_video_resolutions(model: str = Query(default="")):
    resolutions = _get_video_resolutions(model)
    from tools.model_registry import get_video_durations
    durations = get_video_durations(model) if model else [5, 10]
    return {"resolutions": resolutions, "groups": _group_by_ratio(resolutions), "durations": durations}


@router.get("/gen-files/projects/{project_name}/{subpath:path}")
def get_project_generated_file(project_name: str, subpath: str):
    file_path = PROJECTS_DIR / project_name / "07_生成素材" / subpath
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    from fastapi.responses import FileResponse
    import mimetypes
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type)


@router.get("/gen-files/{filename}")
def get_generated_file(filename: str):
    file_path = GENERATED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    from fastapi.responses import FileResponse
    import mimetypes
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type)


@router.get("/generated-history")
def list_generated_history():
    """Return list of generated images and videos, newest first."""
    images_free = []
    images_project = []
    videos_free = []
    videos_project = []
    all_videos = []
    for f in sorted(GENERATED_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_dir() or f.name.startswith("_"):
            continue
        ext = f.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"):
            continue
        entry = {"name": f.name, "url": f"/api/gen-files/{f.name}"}
        meta_path = GENERATED_DIR / "_meta" / f"{f.name}.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
            except:
                pass
        entry = {**meta, **entry}
        if ext in (".mp4", ".webm", ".mov"):
            all_videos.append(entry)
            if meta.get("mode") == "project":
                videos_project.append(entry)
            else:
                videos_free.append(entry)
        elif f.name.startswith("free_") or f.name.startswith("gemini_"):
            images_free.append(entry)
        elif f.name.startswith("proj_") or f.name.startswith("stitch_"):
            images_project.append(entry)

    # Scan project asset directories
    if PROJECTS_DIR.exists():
        for proj_dir in sorted(PROJECTS_DIR.iterdir(), reverse=True):
            if not proj_dir.is_dir():
                continue
            proj_name = proj_dir.name
            asset_base = proj_dir / "07_生成素材"
            if not asset_base.exists():
                continue

            # Scan characters
            chars_dir = asset_base / "角色"
            if chars_dir.exists():
                for char_dir in sorted(chars_dir.iterdir()):
                    if not char_dir.is_dir():
                        continue
                    for vdir in sorted(char_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                        if not vdir.is_dir() or not vdir.name.startswith("v"):
                            continue
                        if (vdir / "_confirmed").exists():
                            for img_file in sorted(vdir.glob("*.png")):
                                rel = img_file.relative_to(asset_base).as_posix()
                                images_project.append({
                                    "name": img_file.name,
                                    "url": f"/api/gen-files/projects/{proj_name}/{rel}",
                                    "mode": "project",
                                    "project_name": proj_name,
                                })
                            break
            # Scan scenes
            scenes_dir = asset_base / "场景"
            if scenes_dir.exists():
                for scene_dir in sorted(scenes_dir.iterdir()):
                    if not scene_dir.is_dir():
                        continue
                    for vdir in sorted(scene_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                        if not vdir.is_dir() or not vdir.name.startswith("v"):
                            continue
                        if (vdir / "_confirmed").exists():
                            for img_file in sorted(vdir.glob("*.png")):
                                rel = img_file.relative_to(asset_base).as_posix()
                                images_project.append({
                                    "name": img_file.name,
                                    "url": f"/api/gen-files/projects/{proj_name}/{rel}",
                                    "mode": "project",
                                    "project_name": proj_name,
                                })
                            break
            # Scan videos
            video_dir = asset_base / "视频"
            if video_dir.exists():
                for vid_file in sorted(video_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
                    rel = vid_file.relative_to(asset_base).as_posix()
                    videos_project.append({
                        "name": vid_file.name,
                        "url": f"/api/gen-files/projects/{proj_name}/{rel}",
                        "mode": "project",
                        "project_name": proj_name,
                    })
                    all_videos.append(videos_project[-1])

    return {
        "images_free": images_free[:50],
        "images_project": images_project[:50],
        "videos_free": videos_free[:20],
        "videos_project": videos_project[:20],
        "videos": all_videos[:30],
    }


@router.get("/generated-history/{filename}")
def get_generated_history_item(filename: str):
    meta_path = GENERATED_DIR / "_meta" / f"{filename}.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding='utf-8'))
        except:
            pass
    return {"filename": filename, "url": f"/api/gen-files/{filename}"}


@router.post("/upload-reference")
async def upload_reference(file: UploadFile = File(...)):
    ref_dir = GENERATED_DIR / "_refs"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    content = await file.read()
    (ref_dir / filename).write_bytes(content)
    return {"url": f"/api/gen-files/_refs/{filename}"}


@router.get("/image-presets")
def list_image_presets():
    """返回风格预设列表"""
    presets_path = Path(__file__).resolve().parent.parent.parent / "config" / "image_presets.json"
    if not presets_path.exists():
        return []
    try:
        return json.loads(presets_path.read_text(encoding="utf-8"))
    except:
        return []


# =============================================================================
#  Project video shot generation API
# =============================================================================

from core.project_manager import ProjectManager


@router.post("/projects/{project_name}/video/shots/generate")
async def generate_project_shot(project_name: str, data: dict):
    """Generate a single video shot for a project"""
    shot_index = data.get("shot_index", 1)
    custom_prompt = data.get("custom_prompt", "") or data.get("prompt", "")
    resolution = data.get("resolution", "1280x720")
    generate_audio = data.get("generate_audio", False)
    scene_name = data.get("scene_name", "")
    seed = data.get("seed", -1)
    camera_fixed = data.get("camera_fixed", False)
    duration = data.get("duration", 5)
    episode = data.get("episode", "默认")
    scene_label = data.get("scene_label", "默认场")

    from tools.video_api import create_video_backend
    model = data.get("model", "")
    agg = _get_active_agg_config("video")
    agg_model = agg.get("model", "") if agg else ""
    backend_name = _detect_video_backend(model or agg_model)
    backend = create_video_backend(backend_name)
    if agg and agg.get("api_key"):
        backend.api_key = agg["api_key"]
    if agg and agg.get("base_url"):
        backend.base_url = agg["base_url"].rstrip("/")

    project = ProjectManager(project_name)

    prompt = custom_prompt
    if not prompt:
        prompts_dirs = [project.project_dir / "06_提示词", project.project_dir / "05_分镜脚本"]
        for prompts_dir in prompts_dirs:
            if not prompts_dir.exists():
                continue
            prompt_files = sorted(prompts_dir.glob("提示词_*.md"))
            if not prompt_files:
                prompt_files = sorted(prompts_dir.glob("分镜提示词*.md"))
            if not prompt_files:
                prompt_files = sorted(prompts_dir.glob("*.md"))
            for f in prompt_files:
                content = f.read_text(encoding="utf-8")
                markers = [f"镜头{shot_index}", f"### 镜头{shot_index}"]
                for m in markers:
                    idx = content.find(m)
                    if idx >= 0:
                        prompt = content[idx:idx+800]
                        break
                if prompt:
                    break
            if prompt:
                break

    if not prompt:
        prompt = f"镜头{shot_index} 视频生成"

    previous_context = ""
    if shot_index > 1 and not custom_prompt:
        prev_index = shot_index - 1
        for prompts_dir in [project.project_dir / "06_提示词", project.project_dir / "05_分镜脚本"]:
            if not prompts_dir.exists():
                continue
            prompt_files = sorted(prompts_dir.glob("提示词_*.md"))
            if not prompt_files:
                prompt_files = sorted(prompts_dir.glob("分镜提示词*.md"))
            if not prompt_files:
                prompt_files = sorted(prompts_dir.glob("*.md"))
            for f in prompt_files:
                content = f.read_text(encoding="utf-8")
                prev_marker = f"### 镜头{prev_index}"
                prev_idx = content.find(prev_marker)
                if prev_idx >= 0:
                    next_marker_idx = content.find("### 镜头", prev_idx + len(prev_marker))
                    prev_section = content[prev_idx:next_marker_idx] if next_marker_idx >= 0 else content[prev_idx:prev_idx+600]
                    lines = []
                    for line in prev_section.split("\n"):
                        s = line.strip()
                        if s.startswith("出场：") or s.startswith("场景：") or s.startswith("【整体"):
                            continue
                        if s and not s.startswith("###") and not s.startswith("# "):
                            lines.append(s)
                    body = " ".join(lines)[:200].strip()
                    if body:
                        previous_context = body
                    break
            if previous_context:
                break
        if previous_context:
            prompt = f"承接上一镜头：{previous_context}\n\n{prompt}"

    same_scene_context = ""
    if shot_index > 1 and not custom_prompt and scene_name:
        prev_scene = ""
        prev_index = shot_index - 1
        for prompts_dir in [project.project_dir / "06_提示词", project.project_dir / "05_分镜脚本"]:
            if not prompts_dir.exists():
                continue
            for f in sorted(prompts_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                prev_marker = f"### 镜头{prev_index}"
                prev_idx = content.find(prev_marker)
                if prev_idx >= 0:
                    next_marker_idx = content.find("### 镜头", prev_idx + len(prev_marker))
                    prev_section = content[prev_idx:next_marker_idx] if next_marker_idx >= 0 else content[prev_idx:prev_idx+600]
                    scene_match = re.search(r'场景[：:]\s*(.+)', prev_section)
                    if scene_match:
                        prev_scene = scene_match.group(1).strip()
                    break
            if prev_scene:
                break
        if prev_scene and prev_scene == scene_name:
            same_scene_context = f"与前一镜头处于同一场景「{scene_name}」，保持完全相同的色调、光影风格和环境氛围。"

    if same_scene_context:
        prompt += f"\n\n{same_scene_context}"

    same_char_context = ""
    if shot_index > 1 and not custom_prompt:
        prev_chars = set()
        prev_index = shot_index - 1
        for prompts_dir in [project.project_dir / "06_提示词", project.project_dir / "05_分镜脚本"]:
            if not prompts_dir.exists():
                continue
            for f in sorted(prompts_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                prev_marker = f"### 镜头{prev_index}"
                prev_idx = content.find(prev_marker)
                if prev_idx >= 0:
                    next_marker_idx = content.find("### 镜头", prev_idx + len(prev_marker))
                    prev_section = content[prev_idx:next_marker_idx] if next_marker_idx >= 0 else content[prev_idx:prev_idx+600]
                    char_match = re.search(r'出场角色[：:]\s*(.+)', prev_section)
                    if char_match:
                        prev_chars = {c.strip() for c in char_match.group(1).split('、') if c.strip()}
                    break
            if prev_chars:
                break
        cur_chars = set(data.get("character_names", []))
        overlap = prev_chars & cur_chars if cur_chars else set()
        if overlap:
            names = "、".join(sorted(overlap))
            same_char_context = f"角色{names}与前一镜头一致，保持完全相同的服装、发型和面部特征。角色动作须自然衔接前一镜头的姿态。"

    if same_char_context:
        prompt += f"\n\n{same_char_context}"

    ref_images = []
    char_images = {}
    asset_dir = PROJECTS_DIR / project_name / "07_生成素材"

    chars_dir = asset_dir / "角色"
    if chars_dir.exists():
        for char_dir in sorted(chars_dir.iterdir()):
            if not char_dir.is_dir():
                continue
            for vdir in sorted(char_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                if not vdir.is_dir() or not vdir.name.startswith("v"):
                    continue
                confirmed = (vdir / "_confirmed").exists()
                if confirmed or vdir == list(sorted(char_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True))[0]:
                    pngs = sorted(vdir.glob("*.png"))
                    char_images[char_dir.name] = [str(p) for p in pngs[:2]]
                    break

    scenes_dir = asset_dir / "场景"
    scene_images = []
    if scenes_dir.exists():
        if scene_name:
            scene_dir = scenes_dir / scene_name
            if scene_dir.exists() and scene_dir.is_dir():
                for vdir in sorted(scene_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                    if not vdir.is_dir() or not vdir.name.startswith("v"):
                        continue
                    confirmed = (vdir / "_confirmed").exists()
                    if confirmed or vdir == list(sorted(scene_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True))[0]:
                        pngs = sorted(vdir.glob("*.png"))
                        scene_images = [str(p) for p in pngs[:2]]
                        break
        else:
            for scene_dir in sorted(scenes_dir.iterdir()):
                if not scene_dir.is_dir():
                    continue
                for vdir in sorted(scene_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                    if not vdir.is_dir() or not vdir.name.startswith("v"):
                        continue
                    confirmed = (vdir / "_confirmed").exists()
                    if confirmed or vdir == list(sorted(scene_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True))[0]:
                        pngs = sorted(vdir.glob("*.png"))
                        scene_images.extend(str(p) for p in pngs[:2])
                        break

    shot_char_names = data.get("character_names", [])
    if shot_char_names:
        for cn in shot_char_names:
            if cn in char_images:
                ref_images.extend(char_images[cn])
    for cn, imgs in char_images.items():
        if cn not in shot_char_names:
            ref_images.extend(imgs)
    ref_images.extend(scene_images)
    ref_images = ref_images[:5]

    last_frame_path = ""
    if shot_index > 1:
        video_base = project.project_dir / "07_生成素材" / "视频"
        if video_base.exists():
            prev_frame_pattern = f"镜头{shot_index - 1:03d}_尾帧.png"
            found_frames = list(video_base.rglob(prev_frame_pattern))
            if found_frames:
                found_frames.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                last_frame_path = str(found_frames[0])

    try:
        if ref_images:
            task_id = backend.image_to_video(
                ref_images[0], prompt, resolution, duration, generate_audio,
                model=data.get("model", ""),
                negative_prompt=data.get("negative_prompt", ""),
                seed=seed, camera_fixed=camera_fixed,
                last_frame_path=last_frame_path,
            )
        else:
            task_id = backend.text_to_video(
                prompt, resolution, duration, generate_audio,
                model=data.get("model", ""),
                negative_prompt=data.get("negative_prompt", ""),
                seed=seed, camera_fixed=camera_fixed,
            )

        result = backend.wait_for_result(task_id, timeout=600)
        video_url = result["video_url"]

        shot_num = f"镜头{shot_index:03d}"
        video_dir = project.project_dir / "07_生成素材" / "视频" / episode / scene_label / shot_num
        existing_versions = [d for d in video_dir.parent.glob("v*")] if video_dir.parent.exists() else []
        version = f"v{len(existing_versions) + 1}"
        video_dir = video_dir.parent / version
        video_dir.mkdir(parents=True, exist_ok=True)
        save_path = video_dir / f"镜头{shot_index:03d}.mp4"
        resp = requests.get(video_url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if result.get("last_frame_url"):
            last_frame_resp = requests.get(result["last_frame_url"], timeout=120)
            last_frame_resp.raise_for_status()
            last_frame_path_save = video_dir / f"镜头{shot_index:03d}_尾帧.png"
            last_frame_path_save.write_bytes(last_frame_resp.content)

        try:
            meta_dir = GENERATED_DIR / "_meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            video_filename = os.path.basename(save_path)
            meta = {
                "filename": video_filename,
                "mode": "project",
                "project_name": project_name,
                "prompt": prompt,
                "model": data.get("model", ""),
                "resolution": resolution,
                "duration": 5,
                "negative_prompt": data.get("negative_prompt", ""),
                "timestamp": datetime.now().isoformat(),
            }
            meta_path = meta_dir / f"{video_filename}.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

        return {"shot_index": shot_index, "video_url": video_url, "local_path": str(save_path)}
    except Exception as e:
        return {"shot_index": shot_index, "error": str(e)}


@router.post("/projects/{project_name}/video/bgm/upload")
async def upload_project_bgm(project_name: str, file: UploadFile = File(...)):
    from pathlib import Path as Pt
    bgm_dir = PROJECTS_DIR / project_name / "07_生成素材" / "bgm"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Pt(file.filename).name
    dest = bgm_dir / safe_name
    dest.write_bytes(await file.read())
    return {"filename": str(dest), "url": f"/api/gen-files/projects/{project_name}/bgm/{safe_name}"}


@router.post("/projects/{project_name}/video/shots/concat")
async def concat_project_shots(project_name: str, data: dict):
    from tools.video_concat import VideoConcat
    shot_indices = data.get("shot_indices", [])
    if not shot_indices:
        raise HTTPException(status_code=400, detail="请指定要拼接的镜头编号")

    video_dir = PROJECTS_DIR / project_name / "07_生成素材" / "视频"
    if not video_dir.exists():
        raise HTTPException(status_code=404, detail="未找到视频目录")

    video_paths = []
    for idx in shot_indices:
        pattern = f"镜头{idx:03d}.mp4"
        found = list(video_dir.rglob(pattern))
        if found:
            video_paths.append(str(found[0]))

    if not video_paths:
        raise HTTPException(status_code=404, detail="未找到任何视频文件")

    if not VideoConcat.is_ffmpeg_available():
        raise HTTPException(status_code=400, detail="未安装 ffmpeg，请先安装")

    title_text = data.get("title_text", "")
    title_duration = float(data.get("title_duration", 2))
    transition_duration = float(data.get("transition_duration", 0))
    subtitle_enabled = data.get("subtitle_enabled", False)
    bgm_path = data.get("bgm_path", "")
    bgm_volume = float(data.get("bgm_volume", 0.3))

    subtitle_srt_path = ""
    if subtitle_enabled:
        srt_path = video_dir / "_subtitles.srt"
        shot_data = []
        for i, idx in enumerate(shot_indices):
            dialogue = ""
            prompts_dir = PROJECTS_DIR / project_name / "05_分镜脚本"
            if prompts_dir.exists():
                for md_file in sorted(prompts_dir.rglob("*.md")):
                    content = md_file.read_text(encoding="utf-8")
                    markers = [f"镜头{idx}", f"### 镜头{idx}"]
                    for m in markers:
                        pos = content.find(m)
                        if pos >= 0:
                            section = content[pos:pos+600]
                            dialogue_match = __import__("re").search(r'【台词】\s*(.+?)(?:\n|$)', section)
                            if not dialogue_match:
                                dialogue_match = __import__("re").search(r'"(.*?)"', section)
                            if dialogue_match:
                                dialogue = dialogue_match.group(1).strip()
                            break
                    if dialogue:
                        break
            shot_data.append({"dialogue_raw": dialogue})
        subtitle_srt_path = VideoConcat.generate_subtitle_srt(video_paths, shot_data, str(srt_path))

    output_dir = video_dir / "成片"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"完整视频_{shot_indices[0]}-{shot_indices[-1]}.mp4"
    result_path = VideoConcat.concat(
        video_paths, str(output_path),
        title_text=title_text,
        title_duration=title_duration,
        transition_duration=transition_duration,
        subtitle_srt_path=subtitle_srt_path,
        bgm_path=bgm_path,
        bgm_volume=bgm_volume,
    )

    total_duration = 0.0
    for vp in video_paths:
        try:
            total_duration += VideoConcat.get_duration(vp)
        except:
            pass

    return {
        "output": str(result_path),
        "shot_count": len(video_paths),
        "total_duration": round(total_duration, 1),
        "filename": output_path.name,
        "title_applied": bool(title_text),
        "transition_applied": transition_duration > 0,
        "subtitle_applied": bool(subtitle_srt_path),
        "bgm_applied": bool(bgm_path),
    }


@router.post("/projects/{project_name}/video/concat")
async def concat_project_videos(project_name: str):
    """Concatenate all generated shot videos into a final video"""
    from tools.video_concat import VideoConcat
    import shutil
    project = ProjectManager(project_name)
    video_base = project.project_dir / "07_生成素材" / "视频"
    output_dir = video_base / "成片"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "全片.mp4"

    video_files = sorted(video_base.rglob("镜头*.mp4"))
    if not video_files:
        raise HTTPException(status_code=404, detail="无视频片段")

    if len(video_files) == 1:
        shutil.copy2(str(video_files[0]), str(output_path))
    else:
        VideoConcat.concat([str(f) for f in video_files], str(output_path))

    return {"output": str(output_path), "count": len(video_files)}


@router.get("/projects/{project_name}/video/download")
def download_project_video(project_name: str):
    """Download the concatenated final video"""
    from fastapi.responses import FileResponse
    project = ProjectManager(project_name)
    output_path = project.project_dir / "07_生成素材" / "视频" / "成片" / "全片.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="成片尚未生成")
    return FileResponse(str(output_path), media_type="video/mp4", filename=f"{project_name}_成片.mp4")


@router.post("/image-gen/upscale")
async def upscale_image(data: dict):
    """基于 Pillow 的图片放大，指定缩放倍数"""
    url = data.get("url", "")
    scale_factor = int(data.get("scale", 2))
    if scale_factor < 1 or scale_factor > 4:
        scale_factor = 2

    import tempfile
    if url.startswith("data:"):
        import base64
        img_data = base64.b64decode(url.split(",", 1)[1])
        img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        Path(img_path).write_bytes(img_data)
    elif url.startswith("http"):
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        Path(img_path).write_bytes(resp.content)
    else:
        img_path = url

    try:
        img = Image.open(img_path)
        w, h = img.size
        new_w, new_h = w * scale_factor, h * scale_factor
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        filename = f"upscale_{uuid.uuid4().hex[:8]}.png"
        save_path = GENERATED_DIR / filename
        img_resized.save(str(save_path))
        result_url = f"/api/gen-files/{filename}"
        return {"url": result_url, "local": str(save_path), "size": f"{new_w}x{new_h}"}
    finally:
        if os.path.exists(img_path) and not img_path.startswith(str(GENERATED_DIR)):
            os.unlink(img_path)


@router.get("/assets/list")
def list_assets(project_name: str = Query(...), asset_type: str = Query("角色")):
    """列出指定类型的资产（角色/场景/道具）"""
    from core.asset_manager import AssetManager
    mgr = AssetManager(PROJECTS_DIR / project_name)
    return {"assets": mgr.list_assets(asset_type)}


@router.post("/assets/confirm-version")
def confirm_asset_version(
    project_name: str = Query(...),
    asset_type: str = Query(...),
    asset_name: str = Query(...),
    version: int = Query(...)
):
    """确认资产版本"""
    from core.asset_manager import AssetManager
    mgr = AssetManager(PROJECTS_DIR / project_name)
    mgr.confirm_version(asset_type, asset_name, version)
    return {"status": "ok", "confirmed_version": version}


@router.post("/assets/modify")
def modify_asset_endpoint(
    project_name: str = Query(...),
    asset_type: str = Query(...),
    asset_name: str = Query(...),
    variant: str = Query("基础形象"),
    prompt: str = Query(...),
    negative_prompt: str = Query(""),
    strength: float = Query(0.7, ge=0.0, le=1.0),
    model: str = Query(""),
    save_as: str = Query("variant"),
    new_asset_name: str = Query("")
):
    """图生图：基于参考图修改资产
    Args:
        save_as: "variant" (存为版本) 或 "new_asset" (存为新资产)
        new_asset_name: save_as=new_asset 时必填
    """
    from core.asset_manager import AssetManager
    from core.image_pipeline import ImagePipeline
    
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if asset_type not in ["角色", "场景", "道具"]:
        raise HTTPException(status_code=400, detail="asset_type 必须是 角色/场景/道具")
    
    if save_as not in ["variant", "new_asset"]:
        raise HTTPException(status_code=400, detail="save_as 必须是 variant 或 new_asset")
    
    if save_as == "new_asset" and not new_asset_name:
        raise HTTPException(status_code=400, detail="save_as=new_asset 时必须提供 new_asset_name")
    
    pipeline = ImagePipeline(project_dir)
    result = pipeline.modify_asset(
        asset_type=asset_type,
        asset_name=asset_name,
        prompt=prompt,
        variant=variant,
        negative_prompt=negative_prompt,
        strength=strength,
        model=model,
        save_as=save_as,
        new_asset_name=new_asset_name
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    # 返回带访问URL
    from pathlib import Path
    rel_path = Path(result["path"]).relative_to(project_dir)
    result["url"] = f"/api/projects/{project_name}/assets/{asset_type}/{rel_path.name}"
    result["model_info"] = {
        "max_ref_images": 1,
        "supports_img2img": True
    }
    return result
