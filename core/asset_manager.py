import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class AssetManager:
    """管理 07_生成素材 目录下的资产文件"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.assets_dir = self.project_dir / "07_生成素材"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def _asset_dir(self, asset_type: str, asset_name: str) -> Path:
        return self.assets_dir / asset_type / asset_name

    def save_generated_image(self, asset_type: str, asset_name: str,
                             image_data: bytes, variant: str = "基础形象",
                             meta: dict = None) -> Path:
        asset_dir = self._asset_dir(asset_type, asset_name)
        asset_dir.mkdir(parents=True, exist_ok=True)
        target_path = asset_dir / f"{variant}.png"
        target_path.write_bytes(image_data)
        if meta:
            meta_path = asset_dir / f"{variant}.png.meta"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return target_path

    def get_all_assets(self, asset_type: str) -> list[dict]:
        type_dir = self.assets_dir / asset_type
        if not type_dir.exists():
            return []
        result = []
        for asset_dir in sorted(type_dir.iterdir()):
            if not asset_dir.is_dir():
                continue
            variants = []
            for f in asset_dir.iterdir():
                if f.name.endswith(".png") and not f.name.startswith("_"):
                    variants.append({"name": f.stem, "path": str(f)})
            if variants:
                result.append({"name": asset_dir.name, "variants": variants})
        return result

    def save_as_variant(self, asset_type: str, asset_name: str,
                        image_data: bytes, variant: str = "基础形象",
                        meta: dict = None) -> Tuple[Path, int]:
        asset_dir = self._asset_dir(asset_type, asset_name)
        if not asset_dir.exists():
            raise FileNotFoundError(f"资产不存在: {asset_type}/{asset_name}")
        
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

    def save_as_new_asset(self, asset_type: str, asset_name: str,
                          image_data: bytes, variant: str = "基础形象",
                          meta: dict = None) -> Path:
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
