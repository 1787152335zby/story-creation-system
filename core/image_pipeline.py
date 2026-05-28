import json
import time
import requests
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator
from core.asset_manager import AssetManager
from agents.prompt_factory import PromptBuilder


class ImagePipeline:
    """从资产数据到实际图片的编排管线"""

    def __init__(self, project_dir: Path):
        self.asset_mgr = AssetManager(project_dir)
        self.project_dir = project_dir

    def get_character_prompt(self, char_data: dict) -> str:
        return PromptBuilder.generate_character_prompt(char_data, mode="base")

    def get_scene_prompt(self, scene_data: dict) -> str:
        return PromptBuilder.generate_scene_prompt(scene_data)

    def get_prop_prompt(self, prop_data: dict) -> str:
        return PromptBuilder.generate_prop_prompt(prop_data)

    def generate_image(self, prompt: str) -> Optional[bytes]:
        from tools.image_api_seedream import SeedreamBackend
        backend = SeedreamBackend()
        try:
            urls = backend.text_to_image(prompt)
            if urls:
                resp = requests.get(urls[0], timeout=120)
                resp.raise_for_status()
                return resp.content
            return None
        except Exception:
            return None

    def generate_batch(self, assets: list[dict],
                       on_progress: callable = None) -> Generator[dict, None, None]:
        for asset in assets:
            atype = asset["type"]
            aname = asset["name"]
            adata = asset.get("data", {})

            if atype == "角色":
                prompt = self.get_character_prompt(adata)
            elif atype == "场景":
                prompt = self.get_scene_prompt(adata)
            elif atype == "道具":
                prompt = self.get_prop_prompt(adata)
            else:
                yield {"type": atype, "name": aname, "status": "skip", "reason": "未知类型"}
                continue

            if not prompt:
                yield {"type": atype, "name": aname, "status": "skip", "reason": "无提示词"}
                continue

            if on_progress:
                on_progress({"type": atype, "name": aname, "status": "generating"})

            image_data = self.generate_image(prompt)
            if image_data is None:
                yield {"type": atype, "name": aname, "status": "error", "reason": "API失败"}
                continue

            meta = {
                "prompt": prompt,
                "model": "seedream",
                "timestamp": datetime.now().isoformat(),
            }
            path = self.asset_mgr.save_generated_image(atype, aname, image_data, meta=meta)
            yield {"type": atype, "name": aname, "status": "ok", "path": path}

    def modify_image(self, images_data: list[bytes], prompt: str,
                     negative_prompt: str = "", strength: float = 0.7,
                     model: str = "") -> Optional[bytes]:
        from tools.image_api_seedream import SeedreamBackend
        
        images_base64 = [base64.b64encode(img).decode("utf-8") for img in images_data]
        
        backend = SeedreamBackend()
        try:
            urls = backend.image_to_image(
                images_base64=images_base64,
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

    def modify_asset(self, asset_type: str, asset_name: str, prompt: str,
                     variant: str = "基础形象", negative_prompt: str = "",
                     strength: float = 0.7, model: str = "",
                     save_as: str = "variant", new_asset_name: str = "") -> dict:
        asset_dir = self.asset_mgr._asset_dir(asset_type, asset_name)
        ref_path = asset_dir / f"{variant}.png"
        
        if not ref_path.exists():
            confirmed_file = asset_dir / "_confirmed"
            if confirmed_file.exists():
                confirmed_ver = confirmed_file.read_text(encoding="utf-8").strip()
                if confirmed_ver.startswith("v") and confirmed_ver[1:].isdigit():
                    ref_path = asset_dir / confirmed_ver / f"{variant}.png"
        
        if not ref_path.exists():
            return {"status": "error", "reason": "参考图不存在"}
        
        ref_image = ref_path.read_bytes()
        
        new_image = self.modify_image(
            images_data=[ref_image],
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            model=model
        )
        
        if new_image is None:
            return {"status": "error", "reason": "图生图API调用失败"}
        
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
