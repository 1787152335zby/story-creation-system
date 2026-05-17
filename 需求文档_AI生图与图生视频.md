# 需求文档：AI 生图 + 图生视频

## 一、需求背景

当前系统已完成从**故事大纲 → 提示词**的文本生成流水线。下一步是用 AI 生成视觉内容：

- 根据剧本和分镜生成角色定妆照、场景概念图
- 用生成的图片作为参考，图生视频，保证角色/场景一致性
- 最终产出完整的短片

## 二、整体架构

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  现有流水线  │     │  新增模块     │     │  新增模块     │
│  (1-5阶段)   │ ──→ │  角色/场景提取 │ ──→ │  生图 Agent  │
│  大纲→提示词  │     │  从剧本/分镜   │     │  角色图+场景图 │
└─────────────┘     │  提取描述      │     └──────┬───────┘
                    └──────────────┘            │
                                               ▼
                    ┌──────────────┐     ┌──────────────┐
                    │  视频拼接     │ ←── │  图生视频      │
                    │  ffmpeg拼接   │     │  Seedance等   │
                    └──────────────┘     └──────────────┘
```

## 三、具体要求（分步实现）

---

### 阶段一：角色/场景信息提取

**目标：** 从已有的剧本和分镜脚本中自动提取角色和场景的外貌/环境描述。

#### 新建模块

**文件：** `core/visual_bible.py`

```python
class VisualBible:
    """视觉圣经 — 管理角色/场景的视觉参考信息"""

    def extract_from_script(self, script_content: str) -> dict:
        """从剧本中提取所有角色外貌描述和场景环境描述"""
        # 用 LLM 解析剧本，输出结构化数据
        pass

    def extract_from_storyboard(self, storyboard_content: str) -> dict:
        """从分镜中提取每个场景的光影、色调、构图信息"""
        pass

    def to_prompt_context(self) -> str:
        """把视觉参考信息格式化成文字，供后续生图使用"""
        pass
```

#### 输出数据结构

```json
{
  "characters": [
    {
      "name": "陈锋",
      "appearance": "35岁，国字脸，左眉一道疤，寸头，常穿棕色皮夹克",
      "age": "35",
      "gender": "男",
      "clothing": "棕色皮夹克，黑色工装裤",
      "key_features": ["左眉疤", "寸头", "国字脸"]
    },
    {
      "name": "林雪",
      "appearance": "28岁，长发，鹅蛋脸，常穿白色衬衫",
      "age": "28",
      "gender": "女",
      "clothing": "白色衬衫，深色长裤",
      "key_features": ["长发", "鹅蛋脸"]
    }
  ],
  "scenes": [
    {
      "name": "天台审讯",
      "environment": "老旧居民楼天台，锈蚀铁皮屋顶，黄昏光线",
      "lighting": "冷色调，主光从右侧45°打来",
      "color_tone": "青灰色调",
      "props": ["铁皮屋顶", "生锈水管"]
    }
  ]
}
```

#### 涉及文件

| 文件 | 操作 |
|:-----|:------|
| `core/visual_bible.py` | **新建** |
| `core/__init__.py` | 添加导入 |

---

### 阶段二：生图 Agent

**目标：** 用角色/场景描述生成图片，支持文生图和图生图。

#### 新增 Agent

**文件：** `agents/image_artist.py`

```python
class ImageArtist(AgentBase):
    def run_stream(self, project, style, input_content):
        bible = VisualBible()
        
        # 1. 从剧本提取角色/场景信息
        script = project.read_output("03_完整剧本/完整剧本.md")
        info = bible.extract_from_script(script)
        
        # 2. 逐角色生成定妆照
        for character in info["characters"]:
            prompt = self._build_character_prompt(character, style)
            image_url = self._call_image_api(prompt)
            self._save_image(project, f"角色/{character['name']}.png", image_url)
            yield f"✅ 角色 {character['name']} 定妆照已生成\n"
        
        # 3. 逐场景生成概念图
        for scene in info["scenes"]:
            prompt = self._build_scene_prompt(scene, style)
            image_url = self._call_image_api(prompt)
            self._save_image(project, f"场景/{scene['name']}.png", image_url)
            yield f"✅ 场景 {scene['name']} 概念图已生成\n"
```

#### 图片 API 调用

**文件：** `tools/image_api.py`（**新建**）

```python
class ImageAPI:
    @staticmethod
    def generate(prompt: str, api_key: str = None) -> str:
        """调用文生图 API，返回图片 URL"""
        # 选择后端：Seedream / DALL-E / Stable Diffusion
        backend = os.getenv("IMAGE_BACKEND", "seedream")
        
        if backend == "seedream":
            return ImageAPI._call_seedream(prompt, api_key)
        elif backend == "dalle":
            return ImageAPI._call_dalle(prompt, api_key)
        # ...
    
    @staticmethod
    def _call_seedream(prompt: str, api_key: str) -> str:
        url = "https://api.volcengine.com/ark/v1/images/generations"
        # 调用火山引擎 Seedream API
        # 返回图片 URL
    
    @staticmethod
    def download(url: str, save_path: str):
        """下载图片到本地"""
```

**注意：** Seedream 和 Seedance 共用火山引擎生态，API Key 可从设置页读取。

#### 输出结构

```
06_视觉素材/
├── 角色/
│   ├── 陈锋.png
│   └── 林雪.png
├── 场景/
│   ├── 天台审讯.png
│   └── 废弃仓库.png
└── 视觉圣经.json
```

#### 涉及文件

| 文件 | 操作 |
|:-----|:------|
| `agents/image_artist.py` | **新建** |
| `tools/image_api.py` | **新建** |
| `core/visual_bible.py` | 前面已建 |
| `workflow.yaml` | 新增阶段（在提示词之后） |
| `prompts/image_artist.txt` | **新建**（生图 prompt 模板） |
| `server/async_orch.py` | 新增 `image_artist` 到 `AGENT_TO_CONFIG` |

---

### 阶段三：图生视频 Agent

**目标：** 用角色图 + 场景图 + 提示词生成视频片段。

#### 改造已有 Agent

**文件：** `agents/video_producer.py`（重写）

```python
class VideoProducer(AgentBase):
    def run_stream(self, project, style, input_content):
        # 1. 读取提示词（上一阶段输出）
        prompts = project.read_output("05_提示词/提示词.md")
        
        # 2. 读取角色/场景图路径
        visual_dir = project.project_dir / "06_视觉素材"
        
        # 3. 对每幕/每场景生成视频
        for segment in self._parse_segments(prompts):
            # 图生视频：角色图 + 场景图 + 动作提示词
            image_url = self._get_matching_image(segment, visual_dir)
            prompt = self._build_video_prompt(segment)
            
            task_id = self._submit_video_task(image_url, prompt)
            result = self._poll_until_done(task_id)
            
            self._save_video(project, segment["name"], result["video_url"])
            yield f"✅ 视频片段 {segment['name']} 已生成\n"
        
        # 4. 拼接所有片段
        self._concat_videos(project)
        yield "✅ 全片拼接完成\n"
```

#### 图生视频 API

**文件：** `tools/video_api.py`（**改造** `tools/api_caller.py`）

```python
class VideoAPI:
    @staticmethod
    def submit_image_to_video(image_path: str, prompt: str) -> str:
        """提交图生视频任务，返回 task_id"""
        # Seedance 图生视频接口
        # POST /v1/video/generate with image_url + prompt
        pass
    
    @staticmethod
    def check_status(task_id: str) -> dict:
        """查询任务状态"""
        pass
    
    @staticmethod
    def download_video(url: str, save_path: str):
        """下载视频文件"""
        pass
```

#### 视频拼接

**文件：** `tools/video_concat.py`（**新建**）

```python
class VideoConcat:
    @staticmethod
    def concat(video_paths: list[str], output_path: str):
        """用 ffmpeg 拼接视频片段"""
        # ffmpeg -f concat -i filelist.txt -c copy output.mp4
        pass
```

**依赖：** 需要安装 ffmpeg（`pip install ffmpeg-python` 或系统安装）

#### 涉及文件

| 文件 | 操作 |
|:-----|:------|
| `agents/video_producer.py` | **重写**（目前是空骨架） |
| `tools/api_caller.py` | **扩展**，新增图生视频方法 |
| `tools/video_concat.py` | **新建** |
| `workflow.yaml` | 新增视频生成阶段 |
| `server/async_orch.py` | 新增 `video_producer` 到 `AGENT_TO_CONFIG` |

---

### 阶段四：前端展示

**目标：** 在 Workspace 中展示生成的图片和视频。

#### 后端 API

**文件：** `server/routes/projects.py`

```python
@router.get("/projects/{name}/images")
def list_images(name: str):
    """列出项目的角色/场景图"""
    # 扫描 06_视觉素材/ 目录

@router.get("/projects/{name}/videos")
def list_videos(name: str):
    """列出生成的视频片段"""
    # 扫描 07_视频/ 目录

@router.get("/projects/{name}/media/{path:path}")
def get_media(name: str, path: str):
    """返回图片/视频文件"""
    # 用 FileResponse 返回静态文件
```

#### 前端展示

**文件：** `src/pages/Workspace.tsx`

在侧边栏"05_提示词"之后新增"视觉素材"和"视频"两个阶段入口：

```
侧边栏新增：
  06_视觉素材 ─→ 展开显示所有角色/场景缩略图，点击查看大图
  07_视频     ─→ 播放列表，支持逐个预览和全片播放
```

#### 涉及文件

| 文件 | 操作 |
|:-----|:------|
| `server/routes/projects.py` | 新增媒体文件 API |
| `src/pages/Workspace.tsx` | 新增阶段展示 |
| `src/lib/api.ts` | 新增 API 调用 |
| `core/project_manager.py` | 初始化阶段列表新增 2 个阶段 |

---

## 四、workflow.yaml 最终形态

```yaml
phases:
  - name: 故事大纲
    agent: outline_designer
    split: false

  - name: 完整剧情
    agent: plot_expander
    split: true

  - name: 完整剧本
    agent: screenplay_writer
    split: true

  - name: 分镜设计
    agent: storyboarder
    split: true

  - name: 视频提示词
    agent: prompt_engineer
    split: true

  - name: 视觉素材          # 新增
    agent: image_artist
    split: false

  - name: 视频生成           # 新增
    agent: video_producer
    split: true
```

---

## 五、实现顺序建议

| 优先级 | 阶段 | 周期 | 原因 |
|:-------|:-----|:------|:------|
| P0 | 阶段一：提取角色/场景信息 | 1-2 天 | 所有后续步骤的基础 |
| P0 | 阶段二：生图 Agent | 2-3 天 | 独立可验证，成本低 |
| P1 | 阶段四前端：图片展示 | 1 天 | 看到图片才能验证质量 |
| P1 | 阶段三：图生视频 Agent | 3-5 天 | 核心功能，但依赖前面 |
| P2 | 阶段四前端：视频播放 | 1-2 天 | 展示层 |
| P2 | 视频拼接 | 1 天 | 锦上添花 |

---

## 六、验收标准

1. 运行完整流水线 → `06_视觉素材/` 下生成角色图 + 场景图
2. 图片质量可用（角色外貌与剧本描述一致）
3. 运行视频阶段 → `07_视频/` 下生成视频片段
4. 视频中角色长相与定妆照一致
5. 前端可查看图片缩略图、播放视频
6. 全片拼接后流畅无跳帧

---

## 七、注意事项

- **图片 API Key**：Seedream 和 Seedance 共用火山引擎生态，设置页已有 `SEEDANCE_API_KEY` 字段，可复用或新增 `IMAGE_API_KEY`
- **图片存储**：图片文件建议存本地文件系统，`projects/项目名/06_视觉素材/` 下
- **视频存储**：视频文件较大，建议保留原始 URL（存一份），本地存缩略图
- **异步等待**：图生视频任务可能等 1-5 分钟，后端需非阻塞轮询
- **成本控制**：生图单张约 0.002 元，生视频单段约 0.1-0.5 元，建议加成本预估提示
- **ffmpeg**：视频拼接依赖 ffmpeg，需确保环境已安装或通过 Python 包安装
- **前端展示**：图片用 `<img>` 标签即可，视频用 `<video>` 标签
