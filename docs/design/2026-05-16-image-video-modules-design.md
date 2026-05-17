# 设计文档：AI 生图 + 图生视频 模块化架构

## 一、架构总览

### 三大模块

```
┌─────────────────────────────────────────────────────────┐
│                    故事创作系统                           │
├─────────────────┬─────────────────┬─────────────────────┤
│   模块一         │   模块二         │   模块三             │
│   文本生成模块    │   图像生成模块    │   视频生成模块       │
│                 │                 │                     │
│   ✅ 已完整实现   │   🆕 待实现     │   🆕 待实现          │
│                 │                 │                     │
│  大纲→剧情→剧本   │  文生图         │  图生视频（多图参考）  │
│  →分镜→提示词     │  图生图（上传）   │  首尾帧生视频        │
│                 │                 │  文生视频            │
│  输出:           │  单线程(选角色)  │  单线程(选片段)       │
│  01~05_*        │  流水线(全批量)  │  流水线(全片拼接)     │
└─────────────────┴─────────────────┴─────────────────────┘
         ⬇                         ⬇
   可被模块二/三读取          可被模块三读取
```

### 两种运行模式

每个模块均支持两种模式：

| 模式 | 模块一（已实现） | 模块二（新增） | 模块三（新增） |
|:--|:--|:--|:--|
| **流水线模式** | 用户填想法→全自动5阶段 | 自动遍历全部角色/场景→批量生图 | 自动遍历全部分镜→逐段生视频→拼接 |
| **单线程模式** | —（未来可加） | 用户从角色/场景清单中选1个→只生成该角色的定妆照 | 用户选择某1个或几个片段→只生成选中的视频 |

### 项目输出目录结构（完整版）

```
projects/项目名/
├── 00_任务指令/          ← 模块一
├── 01_故事大纲/          ← 模块一
├── 02_完整剧情/          ← 模块一 (split)
├── 03_完整剧本/          ← 模块一 (split)
├── 04_分镜脚本/          ← 模块一 (split)
├── 05_提示词/            ← 模块一 (split)
├── 06_角色场景/          ← 模块一提取 + 模块二/三读
│   ├── 角色/
│   │   ├── 陈锋.json
│   │   ├── 陈锋_参考图/   ← 用户可放参考图
│   │   └── 林雪.json
│   ├── 场景/
│   │   ├── 深海基地.json
│   │   └── 档案室.json
│   └── 提取报告.md
├── 07_视觉素材/          ← 模块二 输出
│   ├── 角色/
│   │   ├── 陈锋.png
│   │   └── 林雪.png
│   └── 场景/
│       ├── 深海基地.png
│       └── 档案室.png
└── 08_视频/              ← 模块三 输出
    ├── 片段/
    │   ├── 片段_001.mp4
    │   ├── 片段_002.mp4
    │   └── ...
    └── 成片.mp4
```

---

## 二、模块一：新增角色/场景提取

在现有文本流水线末尾新增一个"提取"步骤，作为模块一的最后阶段。

### 核心：VisualBible

**文件：** `core/visual_bible.py`（新建）

```python
class VisualBibleExtractor:
    """从剧本/分镜中提取角色和场景的结构化描述"""
    
    @staticmethod
    def extract_all(project) -> dict:
        """
        读取项目中的剧本和分镜文件，
        调用 LLM 提取角色外貌/服装/性格 + 场景环境/光照/色调
        返回结构化数据并写入 06_角色场景/
        """
    
    @staticmethod
    def save_character(project, name: str, data: dict):
        """保存单个角色 JSON"""
    
    @staticmethod
    def save_scene(project, name: str, data: dict):
        """保存单个场景 JSON"""
    
    @staticmethod
    def list_characters(project) -> list[dict]:
        """返回角色清单（供前端展示和单线程选择）"""
    
    @staticmethod
    def list_scenes(project) -> list[dict]:
        """返回场景清单（供前端展示和单线程选择）"""
```

### 触发时机

- **自动**：模块一流水线跑完"提示词"阶段后，自动触发提取
- **手动**：如果用户修改了剧本内容，可在 Workspace 中点击"重新提取"按钮

---

## 三、模块二：图像生成

### API 抽象层

**文件：** `tools/image_api.py`（新建）

```python
class ImageBackend(ABC):
    """图像生成后端抽象基类"""
    @abstractmethod
    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024") -> str:
        """文生图，返回图片URL"""
    @abstractmethod
    def image_to_image(self, image_path: str, prompt: str, strength: float = 0.8) -> str:
        """图生图，返回图片URL（首次未实现，预留）"""
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
```

**文件：** `tools/image_api_seedream.py`（新建）

```python
class SeedreamBackend(ImageBackend):
    """Seedream（火山引擎）实现"""
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY")  # 复用已有Key
        self.base_url = "https://api.volcengine.com/ark/v1/images/generations"
```

后续加 DALL-E / Midjourney 只需新建文件实现 `ImageBackend` 接口。

### ImageArtist Agent

**文件：** `agents/image_artist.py`（新建）

```python
class ImageArtist(AgentBase):
    """
    两种模式：
    - 流水线模式：run_stream() 遍历全部角色/场景
    - 单线程模式：generate_character(project, name) 只生成单个角色
    """

    def run_stream(self, project, style, input_content):
        """流水线模式：遍历全部"""
        bible = project.read_visual_bible()
        for char in bible["characters"]:
            yield from self._generate_character(project, char)
        for scene in bible["scenes"]:
            yield from self._generate_scene(project, scene)

    def generate_character(self, project, character_name: str):
        """单线程模式：只生成指定的角色"""
        char_data = VisualBibleExtractor.load_character(project, character_name)
        if not char_data:
            return "角色不存在"
        prompt = self._build_prompt(char_data)
        yield from self._call_and_save(project, f"07_视觉素材/角色/{character_name}.png", prompt)

    def generate_scene(self, project, scene_name: str):
        """单线程模式：只生成指定的场景"""
        # 同上
```

### Prompt 模板

**文件：** `prompts/image_artist.txt`

根据角色 JSON 数据，组装成 Seedream 可用的文生图提示词，包含：角色外貌描述、服装、姿态、光线、画幅比例等。

---

## 三-B：生图输出格式规范

### 3-B-1 角色定妆照 — 四视图（AI 一次性绘制）

每生成一个角色，输出 **1 张图片**，由 AI 在一张图中直接绘出四个角度。

**AI Prompt 模板思路：**
```
"角色名" 的定妆照，纯白背景。画布分为4格2x2网格：
左上：脸部特写（胸部以上，正脸）
右上：全身正面
左下：全身侧面（90°侧身）
右下：全身背面
每格内人物居中，无文字遮挡。整体白色背景。
```

**规格要求：**
- 分辨率：1024×1024 或更高（AI 原生输出）
- 纯白背景（prompt 中强调 `white background, no text`）
- 文件名：`角色名_四视图.png`

**注意：** AI 自绘四视图的构图排布无法精确控制（AI 可能不画成标准的 2×2 网格），但只需一次调用、一张图，速度快。

### 3-B-2 场景概念图 — 四角度环绕

每生成一个场景，输出 **5 张图片**：4 张独立角度图 + 1 张合成总览。

#### 4 张独立角度图

| 编号 | 角度 | 描述 | 用途 |
|:----|:-----|:-----|:-----|
| 1 | 正视图 | 从场景正面看过去，看清空间入口方向 | 确定场景正立面 |
| 2 | 左45° | 从左侧45°看，展示深度和纵深感 | 理解空间纵深 |
| 3 | 右45° | 从右侧45°看，对称了解空间 | 了解空间两侧布局 |
| 4 | 鸟瞰图 | 从正上方俯瞰，看清房间布局/家具位置 | 理解空间平面关系 |

**规格要求：**
- 每张独立生成，全分辨率
- prompt 中保持场景内外观描述一致（颜色、材质、光线统一）
- 文件名：`场景名_正视图.png` / `场景名_左45度.png` / 等

#### 合成总览图（第5张）

2×2 网格合成，四角标注方向（"正面" / "左侧" / "右侧" / "俯视"）。

### 3-B-3 勾选按钮（前端交互）

在生图侧边栏或弹窗中，每个角色/场景下方显示格式勾选：

```
角色四视图：
  □ 输出四视图（含角色名标注）    ← 默认选中

场景概念图（可多选角度）：
  □ 正视图    □ 左侧45°
  □ 右侧45°   □ 鸟瞰图
  └─ □ 合成总览（含方向标注）    ← 默认选中
```

- **角色**：四视图只有"生成/不生成"一个开关（因为是一张图）
- **场景**：支持勾选单个角度或全部
- **流水线模式**：使用默认勾选
- **单线程模式**：用户可以取消某些角度的勾选

### 输出目录结构（补充）

```
07_视觉素材/
├── 角色/
│   ├── 陈锋_四视图.png       ← AI一次性绘制的四视图
│   └── 林雪_四视图.png
├── 场景/
│   ├── 深海基地_正视图.png
│   ├── 深海基地_左45度.png
│   ├── 深海基地_右45度.png
│   ├── 深海基地_鸟瞰图.png
│   └── 深海基地_全景总览.png  ← 合成图（含方向标注）
```

---

## 四、模块三：视频生成

### API 抽象层

**文件：** `tools/video_api.py`（新建）

```python
class VideoBackend(ABC):
    @abstractmethod
    def image_to_video(self, image_path: str, prompt: str) -> str:
        """图生视频，返回 task_id"""
    @abstractmethod
    def text_to_video(self, prompt: str) -> str:
        """文生视频，返回 task_id"""
    @abstractmethod
    def check_status(self, task_id: str) -> dict:
        """轮询任务状态"""
    @abstractmethod
    def wait_for_result(self, task_id: str, timeout: int = 300) -> str:
        """阻塞等待完成，返回视频URL"""
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
```

**文件：** `tools/video_api_seedance.py`（新建）

```python
class SeedanceBackend(VideoBackend):
    """Seedance（火山引擎）实现"""
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY")
```

首尾帧生视频、多图参考等能力在具体后端的 `image_to_video` 方法中根据参数调整。

### VideoProducer Agent

**文件：** `agents/video_producer.py`（重写，当前为空骨架）

```python
class VideoProducer(AgentBase):
    """
    两种模式：
    - 流水线模式：遍历全部分镜片段，逐段生视频 → 拼接
    - 单线程模式：只生成指定的 1 个或几个片段
    """

    def run_stream(self, project, style, input_content):
        """流水线模式：遍历全部提示词片段 → 生视频 → 拼接"""
        segments = self._parse_prompt_segments(project)
        for seg in segments:
            image = self._find_matching_image(project, seg)
            yield from self._generate_and_save(project, seg, image)
        self._concat_all(project)

    def generate_segment(self, project, segment_index: int):
        """单线程模式：只生成指定索引的片段"""
        # 只处理1个片段

    def generate_segments(self, project, indices: list[int]):
        """单线程模式：生成选中的多个片段"""
        # 只处理选中的片段
```

### 视频拼接

**文件：** `tools/video_concat.py`（新建）

```python
class VideoConcat:
    @staticmethod
    def concat(video_paths: list[str], output_path: str):
        """ffmpeg 拼接"""
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """检查环境是否安装了 ffmpeg"""
    
    @staticmethod
    def get_video_duration(path: str) -> float:
        """获取视频时长"""
```

---

## 五、workflow.yaml 调整

```yaml
phases:
  - name: 故事大纲
  - name: 完整剧情
  - name: 完整剧本
  - name: 分镜设计
  - name: 视频提示词
  # ↑ 现有5阶段
  - name: 视觉素材提取    # 新增，提取角色/场景信息
    agent: visual_extractor
    output: 06_角色场景/
    condition: true
    split: false
  - name: 视觉素材生成     # 新增，生图
    agent: image_artist
    output: 07_视觉素材/
    condition: true
    split: false
  - name: 视频生成        # 新增，生视频
    agent: video_producer
    output: 08_视频/
    condition: true
    split: true
```

---

## 六、前端 Workspace 新增

### 侧边栏新增阶段入口

```
06_📷 视觉素材     ← 可展开
  ├── 🧑 角色 (3)   ← 点击展开角色列表
  │   ├── 陈锋    ← 点击 → 单线程生成（或查看已有图片）
  │   ├── 林雪
  │   └── 批量生成全部角色 ← 流水线模式
  └── 🌆 场景 (5)
      ├── 深海基地
      ├── 档案室
      └── 批量生成全部场景

07_🎬 视频         ← 可展开
  ├── 片段列表     ← 勾选多个 / 全部
  ├── 片段_001     ← 点击 → 单线程生成
  ├── 片段_002
  ├── 片段_003
  ├── ───
  ├── 🔄 批量生成全部片段 ← 流水线模式
  └── ▶️ 拼接成片   ← 所有片段完成后启用
```

### 主区域

- **视觉素材**：网格展示缩略图，点击查看大图
- **视频**：视频播放器，支持预览单个片段和播放成片

### 新增 API

```typescript
// api.ts 新增
fetchCharacters(projectName)    // GET /api/projects/{name}/characters
fetchScenes(projectName)        // GET /api/projects/{name}/scenes
fetchVisualAssets(projectName)  // GET /api/projects/{name}/visual-assets
fetchVideoClips(projectName)    // GET /api/projects/{name}/video-clips
startImageGeneration()          // WS: {action: 'image_gen', mode: 'all'|'single', target: '陈锋'}
startVideoGeneration()          // WS: {action: 'video_gen', mode: 'all'|'single', indices: [1,3,5]}
```

---

## 七、实现顺序

| 优先级 | 内容 | 周期估计 |
|:-------|:-----|:---------|
| P0 | `core/visual_bible.py` — 角色/场景提取 | 1-2天 |
| P0 | `tools/image_api.py` + `agents/image_artist.py` + Seedream 接入 | 2-3天 |
| P1 | 前端 Workspace 侧边栏 — 视觉素材展示 + 单线程/流水线切换 | 1-2天 |
| P1 | `tools/video_api.py` + `agents/video_producer.py` + Seedance 接入 | 3-5天 |
| P2 | `tools/video_concat.py` — ffmpeg 拼接 | 1天 |
| P2 | 前端 Workspace — 视频展示 + 播放器 | 1-2天 |
| P3 | 多后端扩展（DALL-E / Midjourney / Kling / Runway） | 后续 |

---

## 八、注意事项

1. **异步等待**：Seedance 图生视频任务可能等 1-5 分钟，需非阻塞轮询
2. **成本控制**：生图单张约 0.002 元，生视频单段约 0.1-0.5 元
3. **ffmpeg**：视频拼接依赖，需检查环境是否安装，未安装时给出提示但不阻塞其他功能
4. **提取准确性**：角色/场景提取结果需展示给用户确认（`提取报告.md`），允许手动修正
5. **图片/视频存储**：文件存本地文件系统，图片保留原始 URL 作为备用
