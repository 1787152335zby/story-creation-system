from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from pathlib import Path
import os, json, uuid, time, requests, shutil

router = APIRouter()

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_UPLOAD_DIR = GENERATED_DIR / "_uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AGG_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "aggregated_configs.json"

# ===== 分辨率管理 =====
# 所有模型都支持的标准分辨率
IMAGE_RESOLUTIONS_BASE = [
    "512x512", "768x768",
    "1024x576", "1024x768", "1024x1024",
    "1280x720", "1280x1024",
    "1440x900",
    "1920x1080",
]

# 模型关键词 → 额外支持的分辨率（按匹配优先级从高到低）
# 引擎匹配：模型名称中包含该关键词即匹配
IMAGE_RESOLUTIONS_EXTRA: list[tuple[str, list[str]]] = [
    # GPT-Image 系列 — 最高 3072 (3K)
    ("gpt-image", [
        "2560x1440",
        "2560x1920",
        "3072x3072",
    ]),
    # Gemini 系列（通过 Banana2 / 自定义后端）— 最高 3840 (4K)
    ("gemini", [
        "2048x2048",
        "2560x1440",
        "3072x3072",
        "3840x2160",
        "3840x3840",
    ]),
    # Banana2 内部使用 Gemini 3 Pro
    ("banana", [
        "2048x2048",
        "2560x1440",
        "3072x3072",
        "3840x2160",
        "3840x3840",
    ]),
    # DALL-E 3 — 特殊比例
    ("dall-e", [
        "1792x1024",
        "1024x1792",
    ]),
    # Flux — 最高 2048 (2K)
    ("flux", [
        "1440x900",
        "2048x2048",
        "2048x1152",
    ]),
    # Midjourney — 最高 2048 (2K)
    ("midjourney", [
        "2048x2048",
        "2048x1152",
    ]),
    ("mj_", [
        "2048x2048",
        "2048x1152",
    ]),
    # Qwen-Image — 最高 2048 (2K)
    ("qwen-image", [
        "1440x900",
        "2048x2048",
        "2048x1152",
    ]),
    # Seedream — 标准
    ("seedream", []),
    # Wan — 标准
    ("wan", []),
]


def _get_image_resolutions(model: str) -> list[str]:
    """根据模型名称返回完整分辨率列表。"""
    extras: list[str] = []
    for keyword, extra_list in IMAGE_RESOLUTIONS_EXTRA:
        if keyword and keyword in model.lower():
            extras.extend(extra_list)
    seen = set(IMAGE_RESOLUTIONS_BASE)
    result = list(IMAGE_RESOLUTIONS_BASE)
    for r in extras:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result


VIDEO_RESOLUTIONS_BASE = [
    "1024x1024",
    "540x960",
]

VIDEO_RESOLUTIONS_EXTRA: list[tuple[str, list[str]]] = [
    # Veo 3.1 — 支持 4K
    ("veo", [
        "1920x1080",
        "3840x2160",
    ]),
    # Seedance 2.0 — 支持 1080P
    ("seedance-2", [
        "1280x720",
    ]),
    # Seedance 1.x — 标准
    ("seedance", []),
    # Sora — 标准
    ("sora", []),
]


def _get_video_resolutions(model: str) -> list[str]:
    extras: list[str] = []
    for keyword, extra_list in VIDEO_RESOLUTIONS_EXTRA:
        if keyword and keyword in model.lower():
            extras.extend(extra_list)
    seen = set(VIDEO_RESOLUTIONS_BASE)
    result = list(VIDEO_RESOLUTIONS_BASE)
    for r in extras:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result


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


class FreeImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""


class ProjectImageRequest(BaseModel):
    project_name: str
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""
    character_names: list[str] = []
    scene_names: list[str] = []


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
                                  api_key: str | None = None, base_url: str | None = None) -> str:
    api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 未配置")
    submit_url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/video/generate"

    if len(image_paths) == 1:
        with open(image_paths[0], "rb") as f:
            file_name = os.path.basename(image_paths[0])
            files = {"image": (file_name, f, "image/png")}
            data = {"prompt": prompt}
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.post(submit_url, headers=headers, data=data, files=files, timeout=60)
    elif len(image_paths) >= 2:
        files = {}
        for i, ip in enumerate(image_paths):
            fname = os.path.basename(ip)
            files[f"image{i}"] = (fname, open(ip, "rb"), "image/png")
        data = {"prompt": prompt}
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.post(submit_url, headers=headers, data=data, files=files, timeout=60)
        for k, v in files.items():
            v[1].close()
    else:
        raise HTTPException(status_code=400, detail="请上传至少一张参考图片")

    resp.raise_for_status()
    result = resp.json()
    return result.get("id", "")


def _poll_seedance(task_id: str, timeout: int = 300) -> str:
    api_key = os.getenv("SEEDANCE_API_KEY", "")
    query_url = f"https://api.volcengine.com/ark/v1/video/status/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(query_url, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "running")
        if status == "succeeded":
            return result.get("video_url", "")
        elif status == "failed":
            raise RuntimeError(f"视频生成失败: {result.get('error', '未知错误')}")
        time.sleep(10)
    raise TimeoutError("视频生成超时")


def _download_file(url: str, save_dir: Path, prefix: str = "") -> str:
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


@router.post("/image-gen/free")
def free_image_gen(req: FreeImageRequest):
    """自由文生图 — 优先使用激活的聚合平台，否则使用本地后端"""
    agg = _get_active_agg_config("image")

    try:
        if agg and agg.get("api_key"):
            from openai import OpenAI
            client = OpenAI(api_key=agg["api_key"], base_url=agg["base_url"])
            model = req.model or agg.get("model", "gpt-image-1")
            resp = client.images.generate(
                model=model,
                prompt=req.prompt,
                n=req.n,
                size=req.size,
            )
            urls = [img.url for img in resp.data]
        else:
            backend_name = os.getenv("IMAGE_BACKEND", "seedream")
            from tools.image_api import create_image_backend
            backend = create_image_backend(backend_name)
            urls = backend.text_to_image(req.prompt, req.negative_prompt, req.size, req.n, model=req.model)

        saved = []
        for url in urls:
            local_path = _download_file(url, GENERATED_DIR, "free_")
            saved.append({"url": url, "local": local_path})
        return {"images": saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)}")


@router.get("/image-gen/resolutions")
def list_image_resolutions(model: str = Query(default="")):
    """根据模型返回支持的分辨率及比例分组。不同模型支持不同级别。"""
    resolutions = _get_image_resolutions(model)
    return {"resolutions": resolutions, "groups": _group_by_ratio(resolutions)}


def _copy_to_project_folder(src_path: str, project_name: str, subfolder: str, prefix: str = "") -> str:
    """Copy generated image to generated/projects/{project_name}/{subfolder}/ and return the new path."""
    dest_dir = GENERATED_DIR / "projects" / project_name / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(src_path)[1] or ".png"
    file_name = f"{prefix}{uuid.uuid4().hex[:8]}{ext}"
    dest_path = dest_dir / file_name
    import shutil
    shutil.copy2(src_path, str(dest_path))
    return str(dest_path)


@router.post("/image-gen/project")
def project_image_gen(req: ProjectImageRequest):
    """项目模式生图 — 按角色/场景分文件夹保存"""
    agg = _get_active_agg_config("image")

    try:
        if agg and agg.get("api_key"):
            from openai import OpenAI
            client = OpenAI(api_key=agg["api_key"], base_url=agg["base_url"])
            model = req.model or agg.get("model", "gpt-image-1")
            resp = client.images.generate(
                model=model,
                prompt=req.prompt,
                n=req.n,
                size=req.size,
            )
            urls = [img.url for img in resp.data]
        else:
            backend_name = os.getenv("IMAGE_BACKEND", "seedream")
            from tools.image_api import create_image_backend
            backend = create_image_backend(backend_name)
            urls = backend.text_to_image(req.prompt, req.negative_prompt, req.size, req.n, model=req.model)

        saved = []
        project_images = []

        for url in urls:
            local_path = _download_file(url, GENERATED_DIR, "proj_")
            saved.append({"url": url, "local": local_path})

        # Copy to character folders
        for char_name in req.character_names:
            folder = f"characters/{char_name}"
            copies = []
            for img in saved:
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, "char_")
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})

        # Copy to scene folders
        for scene_name in req.scene_names:
            folder = f"scenes/{scene_name}"
            copies = []
            for img in saved:
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, "scene_")
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})

        return {"images": saved, "project_images": project_images}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)}")


@router.get("/image-gen/project-images/{project_name}")
def list_project_images(project_name: str):
    """列出项目按角色/场景归档的生成图"""
    base_dir = GENERATED_DIR / "projects" / project_name
    result = {"characters": {}, "scenes": {}}
    if not base_dir.exists():
        return result

    chars_dir = base_dir / "characters"
    if chars_dir.exists():
        for char_folder in sorted(chars_dir.iterdir()):
            if char_folder.is_dir():
                images = []
                for f in sorted(char_folder.glob("*")):
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        images.append({
                            "name": f.name,
                            "url": f"/api/gen-files/projects/{project_name}/characters/{char_folder.name}/{f.name}"
                        })
                if images:
                    result["characters"][char_folder.name] = images

    scenes_dir = base_dir / "scenes"
    if scenes_dir.exists():
        for scene_folder in sorted(scenes_dir.iterdir()):
            if scene_folder.is_dir():
                images = []
                for f in sorted(scene_folder.glob("*")):
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        images.append({
                            "name": f.name,
                            "url": f"/api/gen-files/projects/{project_name}/scenes/{scene_folder.name}/{f.name}"
                        })
                if images:
                    result["scenes"][scene_folder.name] = images

    return result


@router.get("/image-gen/backends")
def list_image_backends():
    import os
    backends = {
        "seedream": {"name": "Seedream", "models": ["seedream-v1"]},
    }
    return {"backends": backends}


@router.post("/video-gen/free")
async def free_video_gen(
    prompt: str = Form(...),
    files: list[UploadFile] = File(...),
):
    saved_paths = []
    for f in files:
        ext = f.filename.split(".")[-1] if "." in (f.filename or "") else "png"
        temp_path = TEMP_UPLOAD_DIR / f"upload_{uuid.uuid4().hex[:8]}.{ext}"
        content = await f.read()
        temp_path.write_bytes(content)
        saved_paths.append(str(temp_path))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="请上传至少一张参考图片")

    agg = _get_active_agg_config("video")
    agg_key = agg.get("api_key") if agg else None
    agg_base = agg.get("base_url") if agg else None

    try:
        task_id = _call_seedance_image_to_video(saved_paths, prompt, api_key=agg_key, base_url=agg_base)
        video_url = _poll_seedance(task_id, timeout=300)
        local_path = _download_file(video_url, GENERATED_DIR, "video_")

        for sp in saved_paths:
            try:
                os.remove(sp)
            except Exception:
                pass

        return {"video_url": video_url, "local": local_path, "task_id": task_id}
    except Exception as e:
        for sp in saved_paths:
            try:
                os.remove(sp)
            except Exception:
                pass
        return {"error": str(e), "task_id": task_id if "task_id" in dir() else ""}


@router.get("/video-gen/resolutions")
def list_video_resolutions(model: str = Query(default="")):
    resolutions = _get_video_resolutions(model)
    return {"resolutions": resolutions, "groups": _group_by_ratio(resolutions)}


@router.get("/gen-files/{filename}")
def get_generated_file(filename: str):
    file_path = GENERATED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    from fastapi.responses import FileResponse
    import mimetypes
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type)


@router.get("/gen-files/projects/{project_name}/{subpath:path}")
def get_project_generated_file(project_name: str, subpath: str):
    file_path = GENERATED_DIR / "projects" / project_name / subpath
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
    videos = []
    for f in sorted(GENERATED_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_dir() or f.name.startswith("_"):
            continue
        ext = f.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"):
            continue
        entry = {"name": f.name, "url": f"/api/gen-files/{f.name}"}
        if ext in (".mp4", ".webm", ".mov"):
            videos.append(entry)
        elif f.name.startswith("free_"):
            images_free.append(entry)
        elif f.name.startswith("proj_"):
            images_project.append(entry)
        else:
            images_free.append(entry)
    return {"images_free": images_free[:50], "images_project": images_project[:50], "videos": videos[:20]}
