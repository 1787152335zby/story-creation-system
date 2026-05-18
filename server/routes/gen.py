import re
import base64
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
import os, json, uuid, time, requests, shutil
from PIL import Image, ImageDraw, ImageFont

router = APIRouter()

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_UPLOAD_DIR = GENERATED_DIR / "_uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AGG_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "aggregated_configs.json"

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


class ProjectImageRequest(BaseModel):
    project_name: str
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""
    character_names: list[str] = []
    scene_names: list[str] = []
    reference_url: str = ""
    reference_urls: list[str] = []
    version: str = ""


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
                                  api_key: str | None = None, base_url: str | None = None) -> str:
    api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 未配置")
    submit_url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/video/generate"

    if len(image_paths) == 1:
        with open(image_paths[0], "rb") as f:
            file_name = os.path.basename(image_paths[0])
            files = {"image": (file_name, f, "image/png")}
            data = {"prompt": prompt, "resolution": resolution, "duration": str(duration), "generate_audio": str(generate_audio).lower()}
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.post(submit_url, headers=headers, data=data, files=files, timeout=60)
    elif len(image_paths) >= 2:
        files = {}
        for i, ip in enumerate(image_paths):
            fname = os.path.basename(ip)
            files[f"image{i}"] = (fname, open(ip, "rb"), "image/png")
        data = {"prompt": prompt, "resolution": resolution, "duration": str(duration), "generate_audio": str(generate_audio).lower()}
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


def _call_image_api(req, agg: dict | None) -> list[str]:
    """Generate images using the user's selected config. Returns list of image URLs."""
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
    if reference_url and not reference_urls:
        reference_urls = [reference_url]

    is_gemini = "gemini" in model.lower()

    if is_gemini:
        urls = []
        for i in range(n):
            if i > 0:
                time.sleep(3)
            per_prompt = prompt
            if n > 1:
                per_prompt = f"（第{i+1}/{n}张）{prompt}"
            try:
                content_parts = [{"type": "text", "text": per_prompt}]
                if negative:
                    content_parts.append({"type": "text", "text": f"避免：{negative}"})
                for ref_url in reference_urls:
                    try:
                        if ref_url.startswith("data:"):
                            img_data = base64.b64decode(ref_url.split(",", 1)[1])
                        elif ref_url.startswith("http"):
                            resp_ref = requests.get(ref_url, timeout=30)
                            img_data = resp_ref.content
                        else:
                            img_data = Path(ref_url).read_bytes()
                        b64 = base64.b64encode(img_data).decode()
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"}
                        })
                    except Exception:
                        pass

                resp = requests.post(
                    f"{base_url}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": content_parts}]},
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
                raise
        if not urls:
            raise HTTPException(status_code=500, detail="Gemini 模型返回了内容但没有解析到图片数据")
        return urls

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    extra = "保持和参考图相同的风格、色彩和光照。" if reference_url else ""
    full_prompt = f"{extra}{prompt}" if extra else prompt
    try:
        resp = client.images.generate(model=model, prompt=full_prompt, n=n, size=size)
        return [img.url for img in resp.data]
    except Exception as e:
        if "429" in str(e) or "RateLimit" in str(e):
            raise HTTPException(status_code=429, detail=f"API 请求频率限制（429），请等待 30 秒后重试")
        raise


@router.post("/image-gen/free")
def free_image_gen(req: FreeImageRequest):
    """自由文生图 — 按用户选择的 API/模型生成"""
    agg = _get_active_agg_config("image")
    try:
        urls = _call_image_api(req, agg)
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
    """项目模式生图 — 按角色/场景分版本文件夹保存"""
    agg = _get_active_agg_config("image")

    try:
        urls = _call_image_api(req, agg)
        saved = []
        project_images = []
        version_map = {}

        for url in urls:
            local_path = _download_file(url, GENERATED_DIR, "proj_")
            saved.append({"url": url, "local": local_path})

        for char_name in req.character_names:
            char_dir = GENERATED_DIR / "projects" / req.project_name / "characters" / char_name
            version = _next_version(char_dir)
            folder = f"characters/{char_name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                file_name = f"char_{uuid.uuid4().hex[:8]}{ext}"
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, file_name)
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})
            version_map[f"characters/{char_name}"] = version

        for scene_name in req.scene_names:
            scene_dir = GENERATED_DIR / "projects" / req.project_name / "scenes" / scene_name
            version = int(req.version) if req.version else _next_version(scene_dir)
            folder = f"scenes/{scene_name}/v{version}"
            copies = []
            for img in saved:
                ext = os.path.splitext(img["local"])[1] or ".png"
                file_name = f"scene_{uuid.uuid4().hex[:8]}{ext}"
                copy_path = _copy_to_project_folder(img["local"], req.project_name, folder, file_name)
                copies.append({"url": img["url"], "local": copy_path})
            project_images.append({"folder": folder, "images": copies})
            version_map[f"scenes/{scene_name}"] = version

        return {"images": saved, "project_images": project_images, "versions": version_map}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生图失败: {str(e)}")


def _copy_to_project_folder(src_path: str, project_name: str, subfolder: str, file_name: str) -> str:
    """Copy generated image to generated/projects/{project_name}/{subfolder}/ with the given file name."""
    dest_dir = GENERATED_DIR / "projects" / project_name / subfolder
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
        dest = GENERATED_DIR / "projects" / req.save_to / save_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        composite.save(str(dest))
        result["saved_to"] = f"/api/gen-files/projects/{req.save_to}/{save_name}"
    return result


def _list_entity_versions(base_dir: Path, project_name: str, entity_type: str) -> dict:
    """List confirmed images and version history for a project entity."""
    result = {}
    entities_dir = base_dir / entity_type
    if not entities_dir.exists():
        return result
    for folder in sorted(entities_dir.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name
        # Confirmed images: files directly in the folder
        confirmed = []
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                confirmed.append({
                    "name": f.name,
                    "url": f"/api/gen-files/projects/{project_name}/{entity_type}/{name}/{f.name}"
                })
        # Versioned images: v1/, v2/, etc.
        versions = {}
        for vdir in sorted(folder.iterdir(), key=lambda x: x.name):
            if vdir.is_dir() and vdir.name.startswith("v"):
                vnum = vdir.name[1:]
                confirmed_fn = folder / "_confirmed"
                is_confirmed = confirmed_fn.exists() and confirmed_fn.read_text().strip() == vdir.name
                images = _scan_images(vdir, project_name, entity_type, f"{name}/{vdir.name}")
                versions[vnum] = {"confirmed": is_confirmed, "images": images}
        if confirmed or versions:
            result[name] = {"images": confirmed, "versions": versions}
    return result


@router.get("/image-gen/project-images/{project_name}")
def list_project_images(project_name: str):
    """列出项目按角色/场景归档的生成图（带版本信息）"""
    base_dir = GENERATED_DIR / "projects" / project_name
    if not base_dir.exists():
        return {"characters": {}, "scenes": {}}
    return {
        "characters": _list_entity_versions(base_dir, project_name, "characters"),
        "scenes": _list_entity_versions(base_dir, project_name, "scenes"),
    }


@router.get("/image-gen/confirmed-images/{project_name}")
def list_confirmed_images(project_name: str):
    """只返回每个角色/场景已确认的图片（父文件夹中的文件）"""
    base_dir = GENERATED_DIR / "projects" / project_name
    if not base_dir.exists():
        return {"characters": {}, "scenes": {}}
    result = {"characters": {}, "scenes": {}}
    for entity_type in ("characters", "scenes"):
        entities_dir = base_dir / entity_type
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
                        "url": f"/api/gen-files/projects/{project_name}/{entity_type}/{name}/{f.name}"
                    })
            if images:
                result[entity_type][name] = images
    return result


@router.delete("/image-gen/delete")
def delete_generated_file(file_path: str = Query(...)):
    """Delete a generated image file. Accepts local path or API URL path."""
    full = Path(file_path)
    if not full.exists():
        clean = file_path.replace("/api/gen-files/", "").lstrip("/")
        full = GENERATED_DIR / clean
        if not full.exists():
            full = GENERATED_DIR / "projects" / clean
            if not full.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
    try:
        full.unlink()
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/image-gen/clear-folder")
def clear_project_folder(project_name: str = Query(...), subfolder: str = Query(...)):
    """Clear all images in a project subfolder (e.g. scenes/xxx or characters/xxx)."""
    target = GENERATED_DIR / "projects" / project_name / subfolder
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
    """Confirm a version as the active one for a character/scene."""
    src = GENERATED_DIR / "projects" / project_name / entity_type / entity_name / f"v{version}"
    dst = GENERATED_DIR / "projects" / project_name / entity_type / entity_name
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"版本 v{version} 不存在")
    for f in list(dst.iterdir()):
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.name != ".gitkeep":
            try: f.unlink()
            except: pass
    for f in src.iterdir():
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            import shutil
            shutil.copy2(str(f), str(dst / f.name))
    (dst / "_confirmed").write_text(f"v{version}")
    return {"confirmed": True, "version": version}


@router.post("/image-gen/delete-version")
def delete_version(project_name: str = Query(...), entity_type: str = Query(...), entity_name: str = Query(...), version: str = Query(...)):
    """Delete an entire version folder."""
    target = GENERATED_DIR / "projects" / project_name / entity_type / entity_name / f"v{version}"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"版本 v{version} 不存在")
    import shutil
    shutil.rmtree(str(target))
    # Remove confirmed marker if this was the confirmed version
    dst = GENERATED_DIR / "projects" / project_name / entity_type / entity_name
    confirmed_fn = dst / "_confirmed"
    if confirmed_fn.exists() and confirmed_fn.read_text().strip() == f"v{version}":
        try: confirmed_fn.unlink()
        except: pass
    return {"deleted": True, "version": version}


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
    files: list[UploadFile] = File(default=None),
    model: str = Form(default=""),
    resolution: str = Form(default="1280x720"),
    duration: int = Form(default=5),
    generate_audio: bool = Form(default=False),
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

    try:
        if not saved_paths:
            # 文生视频
            if agg_key and agg_base:
                task_id = _call_seedance_text_to_video(prompt, resolution, duration, generate_audio, api_key=agg_key, base_url=agg_base)
            else:
                task_id = _call_seedance_text_to_video(prompt, resolution, duration, generate_audio)
        else:
            task_id = _call_seedance_image_to_video(saved_paths, prompt, resolution, duration, generate_audio, api_key=agg_key, base_url=agg_base)

        video_url = _poll_seedance(task_id, timeout=300)
        local_path = _download_file(video_url, GENERATED_DIR, "video_")

        for sp in saved_paths:
            try: os.remove(sp)
            except: pass

        return {"video_url": video_url, "local": local_path, "task_id": task_id}
    except Exception as e:
        for sp in saved_paths:
            try: os.remove(sp)
            except: pass
        return {"error": str(e), "task_id": task_id if "task_id" in dir() else ""}


def _call_seedance_text_to_video(prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False,
                                 api_key: str | None = None, base_url: str | None = None) -> str:
    api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 未配置")
    url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/video/generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "doubao-seedance-2-0-260128",
        "prompt": prompt,
        "resolution": resolution,
        "duration": duration,
        "generate_audio": generate_audio,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get("id", "")


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
        elif f.name.startswith("free_") or f.name.startswith("gemini_"):
            images_free.append(entry)
        elif f.name.startswith("proj_") or f.name.startswith("stitch_"):
            images_project.append(entry)
    return {"images_free": images_free[:50], "images_project": images_project[:50], "videos": videos[:20]}


# =============================================================================
#  Project video shot generation API
# =============================================================================

from core.project_manager import ProjectManager


@router.post("/projects/{project_name}/video/shots/generate")
async def generate_project_shot(project_name: str, data: dict):
    """Generate a single video shot for a project"""
    shot_index = data.get("shot_index", 1)
    custom_prompt = data.get("custom_prompt", "")
    resolution = data.get("resolution", "1280x720")
    generate_audio = data.get("generate_audio", False)

    from tools.video_api import create_video_backend
    backend = create_video_backend("seedance")

    project = ProjectManager(project_name)

    prompt = custom_prompt
    if not prompt:
        prompts_dir = project.project_dir / "06_提示词"
        for f in sorted(prompts_dir.glob("分镜提示词*.md")):
            content = f.read_text(encoding="utf-8")
            markers = [f"镜头{shot_index}", f"### 镜头{shot_index}"]
            for m in markers:
                idx = content.find(m)
                if idx >= 0:
                    prompt = content[idx:idx+800]
                    break
            if prompt:
                break

    if not prompt:
        prompt = f"镜头{shot_index} 视频生成"

    # Collect reference images
    ref_images = []
    scene_dir = project.project_dir / "07_视觉素材" / "场景"
    char_dir = project.project_dir / "07_视觉素材" / "角色"
    if scene_dir.exists():
        for f in sorted(scene_dir.glob("*.png"))[:3]:
            ref_images.append(str(f))
    if char_dir.exists():
        for f in sorted(char_dir.glob("*.png"))[:2]:
            ref_images.append(str(f))

    try:
        if ref_images:
            task_id = backend.image_to_video(ref_images[0], prompt, resolution, 5, generate_audio)
        else:
            task_id = backend.text_to_video(prompt, resolution, 5, generate_audio)

        video_url = backend.wait_for_result(task_id, timeout=600)

        # Save video to project
        output_dir = project.project_dir / "08_视频" / "片段"
        output_dir.mkdir(parents=True, exist_ok=True)
        save_path = output_dir / f"镜头{shot_index:03d}.mp4"
        resp = requests.get(video_url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return {"shot_index": shot_index, "video_url": video_url, "local_path": str(save_path)}
    except Exception as e:
        return {"shot_index": shot_index, "error": str(e)}


@router.post("/projects/{project_name}/video/concat")
async def concat_project_videos(project_name: str):
    """Concatenate all generated shot videos into a final video"""
    from tools.video_concat import VideoConcat
    import shutil
    project = ProjectManager(project_name)
    clips_dir = project.project_dir / "08_视频" / "片段"
    output_path = project.project_dir / "08_视频" / "成片.mp4"

    if not clips_dir.exists():
        raise HTTPException(status_code=404, detail="无视频片段")

    video_files = sorted(clips_dir.glob("*.mp4"))
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
    output_path = project.project_dir / "08_视频" / "成片.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="成片尚未生成")
    return FileResponse(str(output_path), media_type="video/mp4", filename=f"{project_name}_成片.mp4")
