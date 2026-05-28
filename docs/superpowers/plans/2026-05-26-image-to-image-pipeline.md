# 图生图（Image-to-Image）管线实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps uses checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有文生图管线基础上增加图生图能力，支持基于参考图修改资产，可存为变体或新资产

**Architecture:** 4个核心组件改造：SeedreamBackend (图生图API封装) → ImagePipeline (编排) → AssetManager (存储) → gen.py (API端点)

**Tech Stack:** Python, FastAPI, Seedream API

---

## 文件结构

| 文件 | 改动类型 | 职责 |
|------|----------|------|
| `tools/image_api_seedream.py` | 修改 | 新增 `image_to_image()` 方法封装图生图API |
| `core/asset_manager.py` | 修改 | 新增 `save_as_variant()` 和 `save_as_new_asset()` 方法 |
| `core/image_pipeline.py` | 修改 | 新增 `modify_image()` 和 `modify_asset()` 编排方法 |
| `server/routes/gen.py` | 修改 | 新增 `/assets/modify` API端点 |

---

## Task 1: SeedreamBackend 新增图生图方法

**Files:**
- Modify: `tools/image_api_seedream.py`

- [ ] **Step 1: 在 SeedreamBackend 类中新增 image_to_image 方法**

在现有 `text_to_image` 方法后新增：

```python
    def image_to_image(
        self,
        image_base64: str,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        if not self.api_key or self.api_key == "your-seedance-key-here":
            raise HTTPException(status_code=400, detail="生图 API Key 未配置，请在设置页配置 SEEDANCE_API_KEY")
        
        # 清理 base64 前缀（如果有）
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "seedream-v1",
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        response = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=f"图生图 API 返回异常 (HTTP {response.status_code})：API Key 可能无效或没有权限，请在设置页检查 SEEDANCE_API_KEY"
            )
        if response.status_code == 400:
            detail = data.get("error", {}).get("message", str(data))
            if "not have permission" in detail or "auth" in detail.lower() or "unauthorized" in detail.lower():
                raise HTTPException(status_code=400, detail="SEEDANCE_API_KEY 无效或没有权限，请检查设置页中的 API Key")
            raise HTTPException(status_code=400, detail=f"图生图请求失败: {detail}")
        response.raise_for_status()
        return [img["url"] for img in data.get("data", [])]
```

---

## Task 2: AssetManager 新增保存方法

**Files:**
- Modify: `core/asset_manager.py`

- [ ] **Step 1: 新增 save_as_variant 方法**

在 AssetManager 类中新增：

```python
    def save_as_variant(self, asset_type: str, asset_name: str,
                        image_data: bytes, variant: str = "基础形象",
                        meta: dict = None) -> tuple[Path, int]:
        """保存为现有资产的新版本变体
        Returns: (保存路径, 版本号)
        """
        asset_dir = self._asset_dir(asset_type, asset_name)
        if not asset_dir.exists():
            raise FileNotFoundError(f"资产不存在: {asset_type}/{asset_name}")
        
        # 查找现有版本目录
        existing_versions = []
        for d in asset_dir.iterdir():
            if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit():
                existing_versions.append(int(d.name[1:]))
        
        next_version = max(existing_versions) + 1 if existing_versions else 2
        version_dir = asset_dir / f"v{next_version}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = version_dir / f"{variant}.png"
        target_path.write_bytes(image_data)
        
        if meta:
            meta_path = version_dir / f"{variant}.png.meta"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return target_path, next_version
```

- [ ] **Step 2: 新增 save_as_new_asset 方法**

```python
    def save_as_new_asset(self, asset_type: str, asset_name: str,
                          image_data: bytes, variant: str = "基础形象",
                          meta: dict = None) -> Path:
        """保存为全新独立资产
        Returns: 保存路径
        """
        asset_dir = self._asset_dir(asset_type, asset_name)
        if asset_dir.exists():
            raise FileExistsError(f"资产已存在: {asset_type}/{asset_name}")
        
        asset_dir.mkdir(parents=True, exist_ok=True)
        target_path = asset_dir / f"{variant}.png"
        target_path.write_bytes(image_data)
        
        if meta:
            meta_path = asset_dir / f"{variant}.png.meta"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return target_path
```

---

## Task 3: ImagePipeline 新增图改图编排方法

**Files:**
- Modify: `core/image_pipeline.py`

- [ ] **Step 1: 新增导入和辅助方法**

在文件顶部导入区域添加：
```python
import base64
```

- [ ] **Step 2: 新增 modify_image 方法**

在 ImagePipeline 类中新增：

```python
    def modify_image(self, image_data: bytes, prompt: str,
                     negative_prompt: str = "", strength: float = 0.7,
                     model: str = "") -> Optional[bytes]:
        """基于参考图和提示词修改图片
        Returns: 生成的图片字节
        """
        from tools.image_api_seedream import SeedreamBackend
        
        # 转换为 base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        backend = SeedreamBackend()
        try:
            urls = backend.image_to_image(
                image_base64=image_base64,
                prompt=prompt,
                negative_prompt=negative_prompt,
                strength=strength,
                model=model
            )
            if urls:
                resp = requests.get(urls[0], timeout=120)
                resp.raise_for_status()
                return resp.content
            return None
        except Exception as e:
            import logging
            logging.error(f"图生图失败: {e}")
            return None
```

- [ ] **Step 3: 新增 modify_asset 方法**

```python
    def modify_asset(self, asset_type: str, asset_name: str, prompt: str,
                     variant: str = "基础形象", negative_prompt: str = "",
                     strength: float = 0.7, model: str = "",
                     save_as: str = "variant", new_asset_name: str = "") -> dict:
        """修改指定资产
        Args:
            save_as: "variant" | "new_asset"
        Returns: {"status": "ok", "path": "...", "version": ...}
        """
        # Step 1: 读取参考图
        asset_dir = self.asset_mgr._asset_dir(asset_type, asset_name)
        ref_path = asset_dir / f"{variant}.png"
        
        if not ref_path.exists():
            # 尝试查找 _confirmed 指向的版本
            confirmed_file = asset_dir / "_confirmed"
            if confirmed_file.exists():
                confirmed_ver = confirmed_file.read_text(encoding="utf-8").strip()
                if confirmed_ver.startswith("v") and confirmed_ver[1:].isdigit():
                    ref_path = asset_dir / confirmed_ver / f"{variant}.png"
        
        if not ref_path.exists():
            return {"status": "error", "reason": "参考图不存在"}
        
        ref_image = ref_path.read_bytes()
        
        # Step 2: 图改图生成
        new_image = self.modify_image(
            image_data=ref_image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            model=model
        )
        
        if new_image is None:
            return {"status": "error", "reason": "图生图API调用失败"}
        
        # Step 3: 保存
        meta = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "strength": strength,
            "model": model,
            "source_asset": f"{asset_type}/{asset_name}/{variant}",
            "timestamp": datetime.now().isoformat()
        }
        
        if save_as == "variant":
            try:
                saved_path, version = self.asset_mgr.save_as_variant(
                    asset_type, asset_name, new_image, variant, meta
                )
                return {
                    "status": "ok",
                    "path": str(saved_path),
                    "version": version,
                    "asset_type": asset_type,
                    "asset_name": asset_name
                }
            except Exception as e:
                return {"status": "error", "reason": f"保存变体失败: {e}"}
        else:
            if not new_asset_name:
                return {"status": "error", "reason": "new_asset_name 不能为空"}
            try:
                saved_path = self.asset_mgr.save_as_new_asset(
                    asset_type, new_asset_name, new_image, variant, meta
                )
                return {
                    "status": "ok",
                    "path": str(saved_path),
                    "version": 1,
                    "asset_type": asset_type,
                    "asset_name": new_asset_name
                }
            except FileExistsError:
                return {"status": "error", "reason": "新资产名已存在"}
            except Exception as e:
                return {"status": "error", "reason": f"保存新资产失败: {e}"}
```

---

## Task 4: gen.py 新增图改图 API 端点

**Files:**
- Modify: `server/routes/gen.py`

- [ ] **Step 1: 在文件末尾新增 API 端点**

在现有 `/assets/confirm-version` 端点后新增：

```python
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
    return result
```

---

## 自审查检查

**1. Spec 覆盖**
- ✅ SeedreamBackend.image_to_image: Task 1
- ✅ AssetManager.save_as_variant/save_as_new_asset: Task 2
- ✅ ImagePipeline.modify_image/modify_asset: Task 3
- ✅ /assets/modify API: Task 4

**2. 无占位符**
- ✅ 所有代码完整，无 TBD/TODO
- ✅ 所有路径和文件名明确

**3. 类型一致**
- ✅ 方法签名与设计一致
- ✅ 参数命名一致
