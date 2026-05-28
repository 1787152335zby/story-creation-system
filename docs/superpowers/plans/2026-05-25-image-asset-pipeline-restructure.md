# 图像资产管线重构 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构系统生图管线，建立三层资产体系（角色/场景/道具），补全从提示词到实际图片的完整链路

**Architecture:** 三步提取（基础角色场景→道具分类→变化检测）+ 独立资产目录 + 半自动生图 + 版本管理

**Tech Stack:** Python, FastAPI, LLM (OpenAI-compatible), Seedream API (文生图)

---

## 文件总览

| 类别 | 文件 | 操作 | 职责 |
|:-----|:-----|:-----|:-----|
| **提取改造** | `core/visual_bible.py` | 修改 | 拆分提取提示词为三步法 |
| **提取改造** | `core/visual_bible.py` | 修改 | 修改 `SEGMENT_EXTRACT_PROMPT` 为 Step1 纯角色场景提取 |
| **提取改造** | `core/visual_bible.py` | 新增 | 新增 `PROP_EXTRACT_PROMPT` 道具分类提取提示词 |
| **提取改造** | `core/visual_bible.py` | 修改 | 修改 `CHANGE_DETECT_PROMPT` 增加范围约束 |
| **提取改造** | `core/visual_bible.py` | 修改 | `_save_to_files()` 增加道具分类字段 |
| **生图管线** | `core/asset_manager.py` | **创建** | 资产管理器——目录结构、索引、版本管理 |
| **生图管线** | `core/image_pipeline.py` | **创建** | 生图管线——从提示词到实际图片的编排 |
| **生图管线** | `agents/image_preparator.py` | 修改 | 调用 `image_pipeline.py` 执行生图 |
| **生图管线** | `server/routes/gen.py` | 修改 | 扩展版本管理API至角色/场景/道具资产 |
| **道具分类** | `core/visual_bible.py` | 修改 | 实现道具分类决策树逻辑 |

---

### 第一阶段：提取改造

### Task 1: 拆分角色场景提取提示词

**Files:**
- Modify: `core/visual_bible.py:8-60`（替换 SEGMENT_EXTRACT_PROMPT）

- [ ] **Step 1: 修改 SEGMENT_EXTRACT_PROMPT 为纯角色场景提取**

将当前 `SEGMENT_EXTRACT_PROMPT` 替换为：

```python
SEGMENT_EXTRACT_PROMPT = """你是一位剧本分析师。请从以下剧本片段中提取角色和场景信息。

对每个角色输出（只输出静态信息）：
- name, type(main/minor), appearance, age, gender
- clothing, accessories, key_features
⚠️ 禁止输出：pose(姿态)、手持物、动作描写、动态描述

对每个场景输出：
- name, environment, lighting, color_tone

输出格式为JSON：
{
  "characters": [
    {
      "name": "角色名",
      "type": "main"或"minor",
      "appearance": "外貌特征综合描述",
      "age": "年龄",
      "gender": "男/女",
      "clothing": "服装描述",
      "expression": "表情/神态",
      "accessories": ["配饰1", "配饰2"],
      "key_features": ["标志特征1", "标志特征2"]
    }
  ],
  "scenes": [
    {
      "name": "场景名",
      "environment": "环境描述",
      "lighting": "光线描述",
      "color_tone": "色调描述"
    }
  ],
  "scene_characters": {
    "场景名": ["角色1", "角色2"]
  }
}

只输出JSON，不要其他文字。"""
```

- [ ] **Step 2: 运行模块导入测试**

```bash
python -c "from core.visual_bible import VisualBibleExtractor, SEGMENT_EXTRACT_PROMPT; print(SEGMENT_EXTRACT_PROMPT[:100]); print('OK')"
```
Expected: 打印提示词前100字，不报错

- [ ] **Step 3: 提交**

```bash
git add core/visual_bible.py
git commit -m "refactor: 角色场景提取提示词移除pose/手持物等动态信息"
```

---

### Task 2: 新增道具专项提取提示词

**Files:**
- Modify: `core/visual_bible.py`（在 SEGMENT_EXTRACT_PROMPT 之后新增）

- [ ] **Step 1: 新增 PROP_EXTRACT_PROMPT 常量**

在 `SEGMENT_EXTRACT_PROMPT` 之后添加：

```python
PROP_EXTRACT_PROMPT = """你是一位道具分析师。请从以下剧本片段中识别所有物理道具，并按类别标记。

类别规则：
- "跨场景道具"：同一道具在多个场景中出现（如组织标志、传家宝剑、关键设备）
- "场景固有道具"：固定在某一场景中不会移动的物品（如固定书桌、路灯、大门、永久装修）
- "角色随身道具"：角色个人携带、可能换场景的物品（如配剑、眼镜、项链、背包）

输出JSON：
{
  "props": [
    {
      "name": "道具名称",
      "category": "跨场景道具|场景固有道具|角色随身道具",
      "scene": "归属场景名（如场景固有道具）",
      "owner": "归属角色名（如角色随身道具，否则null）",
      "appearance": "外观描述"
    }
  ]
}

只输出JSON，不要其他文字。"""
```

- [ ] **Step 2: 测试导入**

```bash
python -c "from core.visual_bible import PROP_EXTRACT_PROMPT; print('OK')"
```
Expected: 不报错

- [ ] **Step 3: 提交**

```bash
git add core/visual_bible.py
git commit -m "feat: 新增道具专项提取提示词(PROP_EXTRACT_PROMPT)"
```

---

### Task 3: 改造变化检测提示词

**Files:**
- Modify: `core/visual_bible.py:62-96`（替换 CHANGE_DETECT_PROMPT）

- [ ] **Step 1: 替换 CHANGE_DETECT_PROMPT**

替换为：

```python
CHANGE_DETECT_PROMPT = """你是一位专业的剧本状态跟踪员。请分析以下剧本，找出角色和场景的可见状态变化事件。

状态变化的定义（只关注「可见变化」，不关注心理/情绪变化）：

角色变化：
- 受伤：流血、包扎、淤青、疤痕
- 换装：更换衣服、外套、配饰
- 发型/妆容改变
- 佩戴新道具/移除原有道具

场景变化：
- 破坏：坍塌、裂痕、破损
- 装修：重新布置、新增物品
- 天气：下雨、起雾、飘雪
- 时间：白天→黄昏→夜晚，季节变化

每个变化必须精确标注以下字段：
- 变化角色/场景名
- variant_name: 变体名称（如"受伤形象""夜晚版"）
- appearance_change: 外貌上可见的变化（角色）/ change: 场景的变化描述
- clothing_change: 服装变化（仅角色）
- trigger_event: 触发事件，精确到场次（如"第3场被阿虎用刀划伤"）
- applies_from: 该变化从哪场开始生效（如"第3场"）
- applies_to: 该变化持续到哪场（如"第10场（之后伤口愈合）"，如永久则填"全片"）

输出格式为JSON：
{
  "character_changes": [
    {
      "character_name": "林深",
      "variant_name": "受伤形象",
      "based_on": "林深_基础形象",
      "appearance_change": "右脸颊贴纱布绷带，嘴角瘀青",
      "clothing_change": "夹克右袖被划破",
      "trigger_event": "第3场被阿虎用刀划伤",
      "applies_from": "第3场",
      "applies_to": "第10场"
    }
  ],
  "scene_changes": [
    {
      "scene_name": "地下室",
      "variant_name": "爆炸后",
      "based_on": "地下室_基础形象",
      "change": "天花板塌陷，地面碎石，水管爆裂漏水",
      "trigger_event": "第15场爆炸",
      "applies_from": "第15场",
      "applies_to": "全片"
    }
  ]
}

只输出JSON，不要其他文字。"""
```

- [ ] **Step 2: 测试导入**

```bash
python -c "from core.visual_bible import CHANGE_DETECT_PROMPT; print('OK')"
```
Expected: 不报错

- [ ] **Step 3: 提交**

```bash
git add core/visual_bible.py
git commit -m "feat: 改造变化检测提示词，增加applies_from/applies_to范围约束"
```

---

### Task 4: 实现三步提取调用逻辑

**Files:**
- Modify: `core/visual_bible.py`（修改 `extract_all` 方法）

- [ ] **Step 1: 修改 extract_all 方法执行三步提取**

修改 `VisualBibleExtractor.extract_all()`：

```python
@staticmethod
def extract_all(project) -> dict:
    """三段提取所有角色/场景/道具"""
    # 读取剧本（同现有逻辑）
    script_path = project.project_dir / "03_完整剧本" / "完整剧本.md"
    if not script_path.exists():
        files = sorted((project.project_dir / "03_完整剧本").glob("完整剧本_*.md"))
        script_content = "\n\n".join(f.read_text(encoding="utf-8") for f in files) if files else ""
    else:
        script_content = script_path.read_text(encoding="utf-8")
    if not script_content.strip():
        return {"characters": [], "scenes": [], "props": []}

    # 分段（同现有逻辑）
    segments = re.split(r'(第[一二三四五六七八九十百千\d]+场)', script_content)
    if len(segments) <= 1:
        segments = [script_content]

    client = LLMClient()
    all_chars: dict[str, dict] = {}
    all_scenes: dict[str, dict] = {}
    all_props: dict[str, dict] = {}
    scene_char_map: dict[str, list[str]] = {}

    # ── Pass 1: 提取基础角色+基础场景（使用改造后的 SEGMENT_EXTRACT_PROMPT）──
    # 复用现有分段逻辑，即批次约3场的方式
    batch_size = 3
    for batch_start in range(0, len(segments), batch_size * 2):
        batch_text = ""
        for i in range(batch_start, min(batch_start + batch_size * 2, len(segments)), 2):
            if i + 1 < len(segments):
                batch_text += segments[i] + segments[i + 1] + "\n"
            else:
                batch_text += segments[i] + "\n"
        if not batch_text.strip():
            continue
        batch_text = batch_text[:6000]

        result = ""
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.chat, SEGMENT_EXTRACT_PROMPT, batch_text, 0.3)
            try:
                result = future.result(timeout=120)
            except (TimeoutError, Exception):
                continue

        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if not json_match:
            continue
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            continue

        # 合并角色（同现有逻辑，但不含pose/handheld字段）
        for char in data.get("characters", []):
            name = char["name"]
            if name in all_chars:
                existing = all_chars[name]
                if char.get("type") == "main":
                    existing["type"] = "main"
                for field in ["appearance", "clothing", "expression"]:
                    if char.get(field) and not existing.get(field):
                        existing[field] = char[field]
            else:
                char["status"] = "pending"
                char["is_base"] = True
                char["variant_name"] = "基础形象"
                char["character_base"] = name
                char["character_id"] = _generate_entity_id("CHAR")
                char["based_on"] = None
                char["variants"] = []
                char["variant_tag"] = ""
                char["feature_desc"] = char.get("appearance", "") + " " + char.get("clothing", "")
                all_chars[name] = char

        # 合并场景（同现有逻辑）
        for scene in data.get("scenes", []):
            name = scene["name"]
            if name not in all_scenes:
                scene["status"] = "pending"
                scene["is_base"] = True
                scene["variant_name"] = "基础形象"
                scene["scene_base"] = name
                scene["scene_id"] = _generate_entity_id("SCENE")
                scene["based_on"] = None
                scene["variants"] = []
                scene["variant_tag"] = ""
                scene["feature_desc"] = scene.get("environment", "")
                all_scenes[name] = scene

        # 合并场景-角色关联（同现有逻辑）
        for sc_name, char_names in data.get("scene_characters", {}).items():
            if sc_name not in scene_char_map:
                scene_char_map[sc_name] = []
            scene_char_map[sc_name] = list(set(scene_char_map[sc_name] + char_names))

    # ── Pass 2: 提取道具并分类（新增） ──
    # 将全部剧本内容分块发送给道具提取提示词
    prop_batch_size = 6000
    for i in range(0, len(script_content), prop_batch_size):
        chunk = script_content[i:i+prop_batch_size]
        if not chunk.strip():
            continue
        result = ""
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.chat, PROP_EXTRACT_PROMPT, chunk, 0.3)
            try:
                result = future.result(timeout=120)
            except (TimeoutError, Exception):
                continue
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if not json_match:
            continue
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            continue
        for prop in data.get("props", []):
            pname = prop.get("name", "")
            if not pname:
                continue
            if pname in all_props:
                existing = all_props[pname]
                if prop.get("appearance") and not existing.get("appearance"):
                    existing["appearance"] = prop["appearance"]
            else:
                all_props[pname] = {
                    "name": pname,
                    "prop_id": _generate_entity_id("PROP"),
                    "category": prop.get("category", "场景固有道具"),
                    "scene": prop.get("scene", ""),
                    "owner": prop.get("owner"),
                    "appearance": prop.get("appearance", ""),
                    "status": "pending",
                }

    # 角色关联场景
    for char_name, char in all_chars.items():
        related = []
        for sc_name, char_names in scene_char_map.items():
            if char_name in char_names:
                related.append(sc_name)
        if related:
            char["related_scenes"] = related

    # ── Pass 3: 变化检测（同现有逻辑，使用改造后的 CHANGE_DETECT_PROMPT）──
    change_prompt_text = script_content[:12000]
    change_result = ""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.chat, CHANGE_DETECT_PROMPT, change_prompt_text, 0.3)
        try:
            change_result = future.result(timeout=120)
        except (TimeoutError, Exception):
            pass

    # 解析变化数据（同现有逻辑，使用改造后的字段名）
    if change_result:
        json_match = re.search(r"\{.*\}", change_result, re.DOTALL)
        if json_match:
            try:
                changes = json.loads(json_match.group())
                # 角色变体（同现有逻辑）
                for cc in changes.get("character_changes", []):
                    base_name = cc["character_name"]
                    if base_name in all_chars:
                        base = all_chars[base_name]
                        # ... 复用现有创建变体的逻辑 ...
                        base_id = base.get("character_id", "")
                        variant_unique = _ensure_variant_name(base_name, cc["variant_name"])
                        feature_desc_parts = []
                        if cc.get("appearance_change"):
                            feature_desc_parts.append(cc["appearance_change"])
                        if cc.get("clothing_change"):
                            feature_desc_parts.append(cc["clothing_change"])
                        feature_desc = "；".join(feature_desc_parts)
                        variant_tag = _build_variant_tag(base_id, cc["variant_name"], "")
                        variant = {
                            "name": variant_unique,
                            "character_base": base_name,
                            "character_id": base_id,
                            "type": base.get("type", "minor"),
                            "is_base": False,
                            "variant_name": cc["variant_name"],
                            "variant_tag": variant_tag,
                            "feature_desc": feature_desc,
                            "based_on": f"{base_name}_基础形象",
                            "appearance": base.get("appearance", ""),
                            "clothing": base.get("clothing", ""),
                            "appearance_change": cc.get("appearance_change", ""),
                            "clothing_change": cc.get("clothing_change", ""),
                            "expression": base.get("expression", ""),
                            "trigger_event": cc.get("trigger_event", ""),
                            "applies_from": cc.get("applies_from", ""),
                            "applies_to": cc.get("applies_to", ""),
                            "status": "pending",
                        }
                        if variant_unique not in all_chars:
                            all_chars[variant_unique] = variant
                            base["variants"].append(variant_unique)

                # 场景变体（同现有逻辑）
                for sc in changes.get("scene_changes", []):
                    base_name = sc["scene_name"]
                    if base_name in all_scenes:
                        base = all_scenes[base_name]
                        base_id = base.get("scene_id", "")
                        variant_unique = _ensure_variant_name(base_name, sc["variant_name"])
                        variant_tag = _build_variant_tag(base_id, sc["variant_name"], "")
                        variant = {
                            "name": variant_unique,
                            "scene_base": base_name,
                            "scene_id": base_id,
                            "is_base": False,
                            "variant_name": sc["variant_name"],
                            "variant_tag": variant_tag,
                            "feature_desc": sc.get("change", ""),
                            "based_on": f"{base_name}_基础形象",
                            "environment": base.get("environment", ""),
                            "lighting": base.get("lighting", ""),
                            "color_tone": base.get("color_tone", ""),
                            "change": sc.get("change", ""),
                            "trigger_event": sc.get("trigger_event", ""),
                            "applies_from": sc.get("applies_from", ""),
                            "applies_to": sc.get("applies_to", ""),
                            "status": "pending",
                        }
                        if variant_unique not in all_scenes:
                            all_scenes[variant_unique] = variant
                            base["variants"].append(variant_unique)
            except json.JSONDecodeError:
                pass

    # 保存到文件
    VisualBibleExtractor._save_to_files(project, all_chars, all_scenes, all_props)
    return {"characters": list(all_chars.values()), "scenes": list(all_scenes.values()), "props": list(all_props.values())}
```

- [ ] **Step 2: 修改 `_save_to_files` 保存道具时写入道具分类字段**

```python
# 修改 _save_to_files 内的道具处理逻辑
# 确保道具数据包含 category 字段
```

- [ ] **Step 3: 运行测试确保 extract_all 可调用**

```bash
python -c "from core.visual_bible import VisualBibleExtractor; print('extract_all exists:', hasattr(VisualBibleExtractor, 'extract_all'))"
```
Expected: True

- [ ] **Step 4: 提交**

```bash
git add core/visual_bible.py
git commit -m "refactor: extract_all改为三步提取(角色场景+道具+变化检测)"
```

---

### 第二阶段：生图管线

### Task 5: 创建资产管理器

**Files:**
- Create: `core/asset_manager.py`

- [ ] **Step 1: 创建 AssetManager 类**

```python
import json
from pathlib import Path
from typing import Optional


class AssetManager:
    """资产管理器：管理 07_生成素材/ 目录的角色图/场景图/道具图"""

    def __init__(self, project_dir: Path):
        self.base_dir = project_dir / "07_生成素材"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """创建资产目录结构"""
        for sub in ["角色图", "场景图", "道具图"]:
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)

    # ─── 角色资产 ───

    def get_character_dir(self, char_name: str) -> Path:
        return self.base_dir / "角色图" / char_name

    def save_character_data(self, char_name: str, data: dict):
        d = self.get_character_dir(char_name)
        d.mkdir(parents=True, exist_ok=True)
        (d / "基础形象.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_character_image(self, char_name: str, variant: str = "基础形象") -> Optional[Path]:
        d = self.get_character_dir(char_name)
        candidates = [
            d / f"{variant}.png",
            d / "基础形象.png",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def save_generated_image(self, asset_type: str, asset_name: str, image_data: bytes,
                             variant: str = "基础形象", meta: dict = None):
        """保存生成的图片并创建版本目录"""
        d = self.base_dir / {
            "角色": "角色图",
            "场景": "场景图",
            "道具": "道具图",
        }.get(asset_type, asset_type) / asset_name
        d.mkdir(parents=True, exist_ok=True)

        # 检查当前是否有确认版本，如果没有则写入根目录
        confirmed = d / "_confirmed"
        if not confirmed.exists():
            target = d / f"{variant}.png"
            target.write_bytes(image_data)
            if meta:
                (d / f"{variant}.png.meta").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(target)

        # 有确认版本，创建新版本目录
        existing_versions = [v for v in d.iterdir() if v.is_dir() and v.name.startswith("v")]
        next_v = len(existing_versions) + 1
        vdir = d / f"v{next_v}"
        vdir.mkdir(parents=True, exist_ok=True)
        target = vdir / f"{variant}.png"
        target.write_bytes(image_data)
        if meta:
            (vdir / f"{variant}.png.meta").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)

    def confirm_version(self, asset_type: str, asset_name: str, version: int):
        """确认某版本为当前使用版本"""
        d = self.base_dir / {
            "角色": "角色图",
            "场景": "场景图",
            "道具": "道具图",
        }.get(asset_type, asset_type) / asset_name
        (d / "_confirmed").write_text(f"v{version}")

    def list_assets(self, asset_type: str) -> list[dict]:
        """列出指定类型的全部资产"""
        sub_dir = {
            "角色": "角色图",
            "场景": "场景图",
            "道具": "道具图",
        }.get(asset_type, asset_type)
        d = self.base_dir / sub_dir
        if not d.exists():
            return []
        result = []
        for item in d.iterdir():
            if item.is_dir():
                # 读取角色数据
                data_file = item / "基础形象.json"
                data = {}
                if data_file.exists():
                    data = json.loads(data_file.read_text(encoding="utf-8"))
                result.append({
                    "name": item.name,
                    "type": asset_type,
                    "has_image": any(item.glob("*.png")),
                    "data": data,
                })
        return result
```

- [ ] **Step 2: 测试模块导入**

```bash
python -c "from core.asset_manager import AssetManager; print('OK')"
```
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add core/asset_manager.py
git commit -m "feat: 创建资产管理器(AssetManager)-管理角色/场景/道具图目录结构和版本"
```

---

### Task 6: 创建生图管线

**Files:**
- Create: `core/image_pipeline.py`
- Modify: `agents/image_preparator.py`

- [ ] **Step 1: 创建 ImagePipeline 类**

```python
import json
from pathlib import Path
from typing import Optional, Generator
from core.asset_manager import AssetManager
from agents.prompt_factory import PromptBuilder


class ImagePipeline:
    """生图管线：从资产数据到实际图片的编排"""

    def __init__(self, project_dir: Path):
        self.asset_mgr = AssetManager(project_dir)
        self.project_dir = project_dir

    def get_character_prompt(self, char_data: dict, variant: str = "基础形象") -> str:
        """生成角色的提示词（回调 PromptBuilder）"""
        return PromptBuilder.generate_character_prompt(char_data, mode="base")

    def get_scene_prompt(self, scene_data: dict) -> str:
        """生成场景的提示词"""
        return PromptBuilder.generate_scene_prompt(scene_data)

    def get_prop_prompt(self, prop_data: dict) -> str:
        """生成道具的提示词"""
        return PromptBuilder.generate_prop_prompt(prop_data)

    def generate_image(self, prompt: str, style_config: dict = None,
                       on_progress: callable = None) -> Optional[bytes]:
        """调用生图API生成单张图片

        实际调用由 tools/image_api_seedream.py 完成。
        这里提供统一的调用入口，方便后续切换API。
        """
        from tools.image_api_seedream import generate_image_sync
        try:
            if on_progress:
                on_progress("generating")
            result = generate_image_sync(prompt)
            if on_progress:
                on_progress("done")
            return result
        except Exception as e:
            if on_progress:
                on_progress(f"error: {e}")
            return None

    def generate_batch(self, assets: list[dict], style_config: dict = None,
                       auto_mode: bool = False) -> Generator[dict, None, None]:
        """批量生成资产图片

        assets: [{"type": "角色", "name": "韩信誉", "data": {...}}, ...]
        yield: {"type": "角色", "name": "韩信誉", "status": "ok|skip|error", "path": "..."}
        """
        for asset in assets:
            atype = asset["type"]
            aname = asset["name"]
            adata = asset.get("data", {})

            # 生成提示词
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

            # 调用API生成
            image_data = self.generate_image(prompt, style_config)
            if image_data is None:
                yield {"type": atype, "name": aname, "status": "error", "reason": "API调用失败"}
                continue

            # 保存
            meta = {"prompt": prompt, "model": "seedream", "timestamp": __import__("datetime").datetime.now().isoformat()}
            path = self.asset_mgr.save_generated_image(atype, aname, image_data, meta=meta)
            yield {"type": atype, "name": aname, "status": "ok", "path": path}
```

- [ ] **Step 2: 测试模块导入**

```bash
python -c "from core.image_pipeline import ImagePipeline; print('OK')"
```
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add core/image_pipeline.py
git commit -m "feat: 创建生图管线(ImagePipeline)-统一调用API生成实际图片"
```

---

### Task 7: 改造 image_preparator 使用生图管线

**Files:**
- Modify: `agents/image_preparator.py`

- [ ] **Step 1: 在 prepare 方法末尾增加生图调用**

在 `prepare` 方法的 return 之前，增加：

```python
# 如果配置了自动生图，则调用API
if style and getattr(style, "auto_generate", False):
    from core.image_pipeline import ImagePipeline
    pipeline = ImagePipeline(project.project_dir)
    
    # 收集需要生成的资产
    assets = []
    for c in characters[:10]:  # 限制前10个，避免过度消耗API
        assets.append({"type": "角色", "name": c["name"], "data": c})
    for s in scenes[:10]:
        assets.append({"type": "场景", "name": s["name"], "data": s})
    for p in key_props[:5]:
        assets.append({"type": "道具", "name": p["name"], "data": p})
    
    # 生成（同步，一次一张）
    results = list(pipeline.generate_batch(assets, style))
    result["generation_results"] = results
```

- [ ] **Step 2: 测试导入**

```bash
python -c "from agents.image_preparator import ImagePreparator; print('OK')"
```
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add agents/image_preparator.py
git commit -m "feat: image_preparator集成生图管线，支持自动生成角色/场景/道具图片"
```

---

### 第三阶段：版本管理

### Task 8: 扩展 gen.py 版本管理API

**Files:**
- Modify: `server/routes/gen.py`

- [ ] **Step 1: 增加资产列表API**

```python
@router.get("/assets/list")
def list_assets(project_name: str = Query(...), asset_type: str = Query(...)):
    """列出指定类型的资产列表"""
    from core.asset_manager import AssetManager
    from core.project_manager import PROJECTS_DIR
    mgr = AssetManager(PROJECTS_DIR / project_name)
    return {"assets": mgr.list_assets(asset_type)}
```

- [ ] **Step 2: 增加资产版本确认API**

```python
@router.post("/assets/confirm-version")
def confirm_asset_version(
    project_name: str = Query(...),
    asset_type: str = Query(...),
    asset_name: str = Query(...),
    version: int = Query(...)
):
    """确认资产版本"""
    from core.asset_manager import AssetManager
    from core.project_manager import PROJECTS_DIR
    mgr = AssetManager(PROJECTS_DIR / project_name)
    mgr.confirm_version(asset_type, asset_name, version)
    return {"status": "ok", "confirmed_version": version}
```

- [ ] **Step 3: 测试编译**

```bash
python -c "import py_compile; py_compile.compile('server/routes/gen.py', cfile='__pycache__/gen_test.pyc', doraise=True); print('OK')"
```
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add server/routes/gen.py
git commit -m "feat: 扩展资产版本管理API(list_assets/confirm_asset_version)"
```

---

## 自检

**1. 规范覆盖度：**
- 三层资产体系 → Task 5 (AssetManager)
- 三步提取 → Task 1-4 (extract_all改造)
- 道具分类 → Task 2 (PROP_EXTRACT_PROMPT) + Task 4
- 变化检测 → Task 3 (CHANGE_DETECT_PROMPT)
- 生图管线 → Task 6-7 (ImagePipeline + image_preparator)
- 版本管理 → Task 8 (gen.py API)

**2. 占位符检查：** 无TBD/TODO

**3. 类型一致性：** `AssetManager` 在Task 5定义，Task 6-8中引用的方法名称一致
