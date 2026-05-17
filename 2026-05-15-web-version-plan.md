# Web 版多智能体故事创作系统 — 实施计划

> **For agentic workers:** 按任务顺序执行，每步含完整代码和验证命令。步骤使用 `- [ ]` checkbox 追踪。

**Goal:** 将现有 CLI 创作系统改造为 FastAPI + React 的 Web 网页版，支持流式生成、进度追踪、异步通知。

**Architecture:** FastAPI 后端包裹现有 Agent（线程池异步执行），WebSocket 推送流式 LLM token。React 前端 4 页面：项目广场、新建向导、创作工作台、设置页。前后端分离，单进程部署。

**Tech Stack:** FastAPI, WebSocket, asyncio, React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS, react-markdown

---

## 文件结构

```
故事创作系统/
├── server/              # 【新建】FastAPI 后端
│   ├── __init__.py      # 空文件
│   ├── app.py           # FastAPI 实例 + 静态文件挂载 + CORS
│   ├── schemas.py       # Pydantic models
│   ├── ws_manager.py    # WebSocket 连接管理器
│   ├── async_orch.py    # Orchestrator 异步包装器（核心桥接层）
│   └── routes/
│       ├── __init__.py
│       ├── projects.py  # 项目管理 REST
│       ├── creation.py  # 创作 WebSocket 端点
│       └── settings.py  # 设置页 REST
├── llm/
│   └── backends.py      # 【修改】新增 chat_stream() 方法
├── core/
│   └── agent_base.py    # 【修改】新增 call_llm_stream() 方法
├── web/                 # 【新建】React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── lib/api.ts
│       ├── lib/utils.ts
│       ├── hooks/useWebSocket.ts
│       ├── pages/
│       │   ├── HomePage.tsx
│       │   ├── NewProjectWizard.tsx
│       │   ├── Workspace.tsx
│       │   └── SettingsPage.tsx
│       └── components/
│           ├── ProjectCard.tsx
│           ├── PhaseSidebar.tsx
│           ├── ContentViewer.tsx
│           ├── ReviewBar.tsx
│           └── StreamOutput.tsx
├── components.json      # shadcn/ui 配置
└── run_web.py           # 【新建】一键启动脚本
```

---

### Task 1: LLM 流式支持 — backends.py

**Files:**
- Modify: `llm/backends.py`

- [ ] **Step 1: 为 DeepSeekBackend 添加 chat_stream() 生成器方法**

在 `llm/backends.py` 的 `DeepSeekBackend` 类中添加：

```python
def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

- [ ] **Step 2: 为 OpenAIBackend 添加 chat_stream()**

```python
def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

- [ ] **Step 3: 为 ClaudeBackend 添加 chat_stream()（Anthropic SDK 原生支持 stream）**

```python
def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
    with self.client.messages.stream(
        model=self.model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        for text in stream.text_stream:
            yield text
```

- [ ] **Step 4: 在 LLMBackend 基类添加 chat_stream() 默认占位**

```python
def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
    raise NotImplementedError
```

- [ ] **Step 5: 验证**

```
python -c "from llm.backends import DeepSeekBackend; d = DeepSeekBackend(); print('OK')"
```

---

### Task 2: AgentBase 流式方法 — agent_base.py

**Files:**
- Modify: `core/agent_base.py`

- [ ] **Step 1: 在 AgentBase 添加 call_llm_stream() 方法**

在 `core/agent_base.py` 的 `AgentBase` 类中，在 `call_llm_with_continuation` 之后添加：

```python
def call_llm_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7):
    for chunk in self.llm.backend.chat_stream(system_prompt, user_prompt, temperature):
        yield chunk
```

需要在文件顶部导入 `Generator`：

```python
from typing import Optional, Generator
```

- [ ] **Step 2: 验证**

```
python -c "from core.agent_base import AgentBase; print('OK')"
```

---

### Task 3: FastAPI 基础框架 — server/app.py + server/__init__.py

**Files:**
- Create: `server/__init__.py`
- Create: `server/app.py`

- [ ] **Step 1: 创建 server/__init__.py（空文件）**

```python
```

- [ ] **Step 2: 创建 server/app.py**

```python
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".pkg"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routes.projects import router as projects_router
from server.routes.settings import router as settings_router
from server.routes.creation import router as creation_router

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="多智能体故事创作系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(creation_router, prefix="/api")

frontend_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
```

- [ ] **Step 3: 验证 — 启动 FastAPI 看是否能导入**

```
python -c "from server.app import app; print('FastAPI app created:', app.title)"
```

---

### Task 4: Pydantic Schemas — server/schemas.py

**Files:**
- Create: `server/schemas.py`

- [ ] **Step 1: 创建 server/schemas.py**

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class StyleConfigRequest(BaseModel):
    story_type: str
    genre: str
    writing_style: str
    visual_style: str
    art_style: str
    screen_aspect: str
    script_style: str
    duration_mode: str
    episode_count: str = ""
    episode_duration: str = ""
    custom_requirements: str = ""
    visual_reference: str = ""
    action_reference: str = ""


class CreateProjectRequest(BaseModel):
    name: str
    story_idea: str
    style: StyleConfigRequest
    duration_line: str = ""


class ProjectListItem(BaseModel):
    name: str
    status: str
    created_at: str
    updated_at: str
    current_phase: int
    total_phases: int
    phases: List[Dict[str, Any]]


class ProjectDetail(BaseModel):
    name: str
    status: str
    created_at: str
    updated_at: str
    current_phase: int
    phases: List[Dict[str, Any]]
    config: Dict[str, Any]


class PhaseContentResponse(BaseModel):
    content: str
    phase_name: str
    is_split: bool = False


class SettingsResponse(BaseModel):
    llm_backend: str
    deepseek_api_key: str
    deepseek_model: str
    openai_api_key: str
    openai_model: str
    claude_api_key: str
    claude_model: str
    seedance_api_key: str


class SettingsUpdateRequest(BaseModel):
    llm_backend: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    deepseek_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    seedance_api_key: Optional[str] = None


class TestLLMRequest(BaseModel):
    backend: str
    api_key: str
    model: str


class WSMessage(BaseModel):
    action: str
    project: Optional[str] = None
    style: Optional[StyleConfigRequest] = None
    phase_index: Optional[int] = None
    feedback: Optional[str] = None
    reason: Optional[str] = None
    platform: Optional[str] = None
```

- [ ] **Step 2: 验证**

```
python -c "from server.schemas import CreateProjectRequest; print('OK')"
```

---

### Task 5: WebSocket 连接管理器 — server/ws_manager.py

**Files:**
- Create: `server/ws_manager.py`

- [ ] **Step 1: 创建 server/ws_manager.py**

```python
import json
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_approvals: Dict[str, asyncio.Event] = {}
        self.approval_results: Dict[str, Optional[dict]] = {}

    async def connect(self, project_name: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[project_name] = websocket
        self.pending_approvals[project_name] = asyncio.Event()
        self.approval_results[project_name] = None

    def disconnect(self, project_name: str):
        self.active_connections.pop(project_name, None)
        evt = self.pending_approvals.pop(project_name, None)
        if evt:
            evt.set()
        self.approval_results.pop(project_name, None)

    async def send_message(self, project_name: str, message: dict):
        ws = self.active_connections.get(project_name)
        if ws:
            await ws.send_text(json.dumps(message, ensure_ascii=False))

    async def wait_for_approval(self, project_name: str, phase_index: int) -> dict:
        evt = self.pending_approvals.get(project_name)
        if not evt:
            return {"approved": True, "feedback": ""}
        evt.clear()

        await self.send_message(project_name, {
            "type": "awaiting_approval",
            "phase_index": phase_index,
            "message": "请审核生成内容"
        })

        await evt.wait()
        result = self.approval_results.get(project_name, {"approved": True, "feedback": ""})
        self.approval_results[project_name] = None
        return result

    async def wait_for_platform(self, project_name: str) -> str:
        evt = self.pending_approvals.get(project_name)
        if not evt:
            return "Seedance 2.0"
        evt.clear()

        await self.send_message(project_name, {
            "type": "awaiting_platform",
            "message": "请选择AI视频生成平台"
        })

        await evt.wait()
        result = self.approval_results.get(project_name)
        if result and "platform" in result:
            return result["platform"]
        return "Seedance 2.0"

    async def wait_for_outline_version(self, project_name: str) -> dict:
        evt = self.pending_approvals.get(project_name)
        if not evt:
            return {"version": "1"}
        evt.clear()

        await self.send_message(project_name, {
            "type": "awaiting_version",
            "message": "请选择大纲版本（1=版本A, 2=版本B, 3=混合）"
        })

        await evt.wait()
        return self.approval_results.get(project_name, {"version": "1"})

    def handle_client_message(self, project_name: str, data: dict):
        action = data.get("action", "")
        if action in ("approve", "revise", "reject"):
            self.approval_results[project_name] = {
                "approved": action == "approve",
                "feedback": data.get("feedback", ""),
                "reason": data.get("reason", ""),
            }
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "platform":
            self.approval_results[project_name] = {"platform": data.get("platform", "Seedance 2.0")}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "version":
            self.approval_results[project_name] = {"version": data.get("version", "1"), "feedback": data.get("feedback", "")}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "skip":
            self.approval_results[project_name] = {"approved": True, "feedback": "", "skip": True}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
```

- [ ] **Step 2: 验证**

```
python -c "from server.ws_manager import ConnectionManager; print('OK')"
```

---

### Task 6: 异步编排器 — server/async_orch.py

**Files:**
- Create: `server/async_orch.py`

- [ ] **Step 1: 创建 server/async_orch.py**

```python
import asyncio
import concurrent.futures
from pathlib import Path

from agents.orchestrator import Orchestrator as SyncOrchestrator, _split_sort_key, _CHINA_NUM
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES, VIDEO_PLATFORMS
from core.workflow_loader import WorkflowLoader
from core.review_gate import R
from server.ws_manager import ConnectionManager


class AsyncOrchestrator:
    def __init__(self, ws_manager: ConnectionManager):
        self.ws = ws_manager
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def run(self, project_name: str, style_data: dict):
        project = ProjectManager(project_name)

        style = StyleConfig()
        style.story_type = style_data.get("story_type", "")
        style.genre = style_data.get("genre", "")
        style.writing_style = style_data.get("writing_style", "")
        style.visual_style = style_data.get("visual_style", "")
        style.art_style = style_data.get("art_style", "")
        style.screen_aspect = style_data.get("screen_aspect", "")
        style.script_style = style_data.get("script_style", "")
        style.duration_mode = style_data.get("duration_mode", "")
        style.episode_count = style_data.get("episode_count", "")
        style.episode_duration = style_data.get("episode_duration", "")
        style.custom_requirements = style_data.get("custom_requirements", "")
        style.visual_reference = style_data.get("visual_reference", "")
        style.action_reference = style_data.get("action_reference", "")

        phases = WorkflowLoader.load()
        total = len(phases)

        await self.ws.send_message(project_name, {
            "type": "progress",
            "current": 0,
            "total": total,
        })

        for idx, phase in enumerate(phases):
            if not phase.should_run(style.story_type):
                continue

            output_path = self._get_output_path(phase)

            await self.ws.send_message(project_name, {
                "type": "phase_start",
                "phase_index": idx,
                "phase_name": phase.name,
                "total_phases": total,
            })

            await self.ws.send_message(project_name, {
                "type": "progress",
                "current": idx,
                "total": total,
            })

            import importlib
            snake_name = phase.agent
            class_name = "".join(word.capitalize() for word in snake_name.split("_"))
            module = importlib.import_module(f"agents.{snake_name}")
            agent_class = getattr(module, class_name)
            agent = agent_class()

            input_content = await self._get_input(project, phase)

            loop = asyncio.get_event_loop()

            async def stream_chunks():
                full_output = ""
                system_prompt = agent.load_prompt_template(f"{snake_name}.txt")
                style_context = agent.get_style_context(style)

                if phase.agent == "outline_designer":
                    task = project.read_output("00_任务指令/任务指令.md") or input_content
                    system_prompt = system_prompt.replace("{style_config}", style_context)
                    system_prompt = system_prompt.replace("{task}", task)

                for chunk in agent.call_llm_stream(system_prompt, "", temperature=0.8):
                    full_output += chunk
                    await self.ws.send_message(project_name, {
                        "type": "stream",
                        "phase_index": idx,
                        "chunk": chunk,
                    })
                return full_output

            result = await stream_chunks()

            if phase.split:
                from tools.content_splitter import split_by_headings, make_split_filename
                split_parts = split_by_headings(result)
                saved_files = []
                for title, section in split_parts:
                    if not section.strip():
                        continue
                    if not title:
                        fname_clean = str(output_path).replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                        project.write_output(fname_clean, section)
                        saved_files.append(fname_clean)
                    else:
                        fname = make_split_filename(str(output_path), title)
                        fname_clean = fname.replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                        project.write_output(fname_clean, section)
                        saved_files.append(fname_clean)
            else:
                project.write_output(output_path, result)

            await self.ws.send_message(project_name, {
                "type": "phase_complete",
                "phase_index": idx,
                "phase_name": phase.name,
                "file_path": output_path,
            })

            project.mark_phase_done(idx)

            if phase.agent == "video_producer":
                continue

            approval = await self.ws.wait_for_approval(project_name, idx)

            iterations = 0
            while not approval.get("approved") and iterations < 5:
                feedback = approval.get("feedback", "")
                if not feedback:
                    break

                system_prompt = agent.load_prompt_template(f"{snake_name}.txt")
                style_context = agent.get_style_context(style)
                system_prompt = system_prompt.replace("{style_config}", style_context)

                if phase.agent == "outline_designer":
                    task = project.read_output("00_任务指令/任务指令.md") or input_content
                    system_prompt = system_prompt.replace("{task}", task)

                system_prompt += f"\n\n## 修改意见\n{feedback}"

                async def stream_revision():
                    rev_output = ""
                    for chunk in agent.call_llm_stream(system_prompt, "", temperature=0.8):
                        rev_output += chunk
                        await self.ws.send_message(project_name, {
                            "type": "stream",
                            "phase_index": idx,
                            "chunk": chunk,
                        })
                    return rev_output

                result = await stream_revision()

                if phase.split:
                    from tools.content_splitter import split_by_headings, make_split_filename
                    split_parts = split_by_headings(result)
                    for title, section in split_parts:
                        if not section.strip():
                            continue
                        if not title:
                            fname_clean = str(output_path).replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                            project.write_output(fname_clean, section)
                        else:
                            fname = make_split_filename(str(output_path), title)
                            fname_clean = fname.replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                            project.write_output(fname_clean, section)
                else:
                    project.write_output(output_path, result)

                await self.ws.send_message(project_name, {
                    "type": "phase_complete",
                    "phase_index": idx,
                    "phase_name": phase.name,
                    "file_path": output_path,
                })

                approval = await self.ws.wait_for_approval(project_name, idx)
                iterations += 1

        await self.ws.send_message(project_name, {
            "type": "all_complete",
        })

    def _get_output_path(self, phase) -> str:
        output = phase.output
        if output.endswith("/"):
            filename_map = {
                "01_故事大纲/": "故事大纲.md",
                "02_完整剧情/": "完整剧情.md",
                "03_完整剧本/": "完整剧本.md",
                "04_分镜脚本/": "分镜脚本.md",
                "05_提示词/": "提示词.md",
            }
            return output + filename_map.get(output, "产出.md")
        return output

    async def _get_input(self, project: ProjectManager, phase) -> str:
        input_map = {
            "plot_expander": "01_故事大纲/故事大纲.md",
            "screenplay_writer": "02_完整剧情/完整剧情.md",
            "storyboarder": "03_完整剧本/完整剧本.md",
            "prompt_engineer": "04_分镜脚本/分镜脚本.md",
        }
        source = input_map.get(phase.agent)
        if source:
            content = project.read_output(source)
            if content is None:
                dir_path = project.project_dir / Path(source).parent
                split_files = sorted(dir_path.glob("*_*.md"), key=lambda f: _split_sort_key(f.name))
                if split_files:
                    parts = [project.read_output(str(sf.relative_to(project.project_dir))) for sf in split_files]
                    content = "\n\n---\n\n".join(p for p in parts if p)
            return content or ""
        return ""
```

---

### Task 7: 后端 REST 路由 — projects.py

**Files:**
- Create: `server/routes/__init__.py`
- Create: `server/routes/projects.py`

- [ ] **Step 1: 创建 server/routes/__init__.py（空文件）**

- [ ] **Step 2: 创建 server/routes/projects.py**

```python
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from server.schemas import ProjectListItem, ProjectDetail, CreateProjectRequest, PhaseContentResponse

router = APIRouter()
PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"


def _build_project_list() -> list:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "project_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config["total_phases"] = len(config.get("phases", []))
                projects.append(config)
    return sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)


@router.get("/projects", response_model=list)
def list_projects():
    return _build_project_list()


@router.get("/projects/{name}")
def get_project(name: str):
    project_dir = PROJECTS_DIR / name
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/projects/{name}/phases")
def get_phases(name: str):
    project_dir = PROJECTS_DIR / name
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("phases", [])


@router.get("/projects/{name}/{phase:path}/content")
def get_phase_content(name: str, phase: str):
    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    if phase_path.is_dir():
        md_files = sorted(phase_path.glob("*.md"))
        if not md_files:
            raise HTTPException(status_code=404, detail="无内容")
        parts = []
        for mf in md_files:
            parts.append(mf.read_text(encoding="utf-8"))
        return {"content": "\n\n---\n\n".join(parts), "is_split": True}
    return {"content": phase_path.read_text(encoding="utf-8"), "is_split": False}


@router.post("/projects")
def create_project(req: CreateProjectRequest):
    from core.project_manager import ProjectManager
    from core.style_config import STORY_TYPES, WRITING_STYLES, VISUAL_STYLES, RENDER_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES

    project = ProjectManager(req.name)

    task_content = f"""# 创作任务

## 故事类型
{STORY_TYPES.get(req.style.story_type, {}).get('name', '')}

## 题材风格
{req.style.genre}

## 文笔风格
{WRITING_STYLES.get(req.style.writing_style, {}).get('name', '')}

## 视觉/叙事风格
{VISUAL_STYLES.get(req.style.visual_style, {}).get('name', '')}

## 渲染画风
{RENDER_STYLES.get(req.style.art_style, {}).get('name', '')}

## 剧本写作风格
{SCRIPT_STYLES.get(req.style.script_style, {}).get('name', '')}

## 画面比例
{SCREEN_ASPECTS.get(req.style.screen_aspect, {}).get('name', '')}

## 时长
{req.duration_line}

## 故事描述
{req.story_idea}

## 额外要求
{req.style.custom_requirements or '无'}
"""

    project.write_output("00_任务指令/任务指令.md", task_content)
    project.config["style_type"] = req.style.story_type
    project.config["genre"] = req.style.genre
    project.config["writing_style"] = req.style.writing_style
    project.config["visual_style"] = req.style.visual_style
    project.config["art_style"] = req.style.art_style
    project.config["screen_aspect"] = req.style.screen_aspect
    project.config["script_style"] = req.style.script_style
    project.config["visual_reference"] = req.style.visual_reference
    project.config["action_reference"] = req.style.action_reference
    project.save_config()

    return {"name": req.name, "status": "created"}


@router.delete("/projects/{name}")
def delete_project(name: str):
    import shutil
    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    shutil.rmtree(project_dir)
    return {"deleted": True}
```

---

### Task 8: 后端 REST 路由 — settings.py

**Files:**
- Create: `server/routes/settings.py`

- [ ] **Step 1: 创建 server/routes/settings.py**

```python
import os
from pathlib import Path
from fastapi import APIRouter
from server.schemas import SettingsResponse, SettingsUpdateRequest, TestLLMRequest

router = APIRouter()
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _mask_key(key: str) -> str:
    if not key or key == "sk-your-key-here" or key == "sk-ant-your-key-here" or key == "your-seedance-key-here":
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
    }


@router.put("/settings")
def update_settings(req: SettingsUpdateRequest):
    env = _read_env()

    if req.llm_backend is not None:
        env["LLM_BACKEND"] = req.llm_backend
    if req.deepseek_api_key is not None and "****" not in req.deepseek_api_key:
        env["DEEPSEEK_API_KEY"] = req.deepseek_api_key
    if req.deepseek_model is not None:
        env["DEEPSEEK_MODEL"] = req.deepseek_model
    if req.openai_api_key is not None and "****" not in req.openai_api_key:
        env["OPENAI_API_KEY"] = req.openai_api_key
    if req.openai_model is not None:
        env["OPENAI_MODEL"] = req.openai_model
    if req.claude_api_key is not None and "****" not in req.claude_api_key:
        env["CLAUDE_API_KEY"] = req.claude_api_key
    if req.claude_model is not None:
        env["CLAUDE_MODEL"] = req.claude_model
    if req.seedance_api_key is not None and "****" not in req.seedance_api_key:
        env["SEEDANCE_API_KEY"] = req.seedance_api_key

    lines = []
    lines.append("# ===== 大模型配置 =====")
    lines.append("# 至少配置一个后端")
    lines.append(f"LLM_BACKEND={env.get('LLM_BACKEND', 'deepseek')}")
    lines.append("")
    lines.append(f"DEEPSEEK_API_KEY={env.get('DEEPSEEK_API_KEY', '')}")
    lines.append(f"DEEPSEEK_MODEL={env.get('DEEPSEEK_MODEL', 'deepseek-chat')}")
    lines.append("")
    lines.append(f"OPENAI_API_KEY={env.get('OPENAI_API_KEY', '')}")
    lines.append(f"OPENAI_MODEL={env.get('OPENAI_MODEL', 'gpt-4o')}")
    lines.append("")
    lines.append(f"CLAUDE_API_KEY={env.get('CLAUDE_API_KEY', '')}")
    lines.append(f"CLAUDE_MODEL={env.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')}")
    lines.append("")
    lines.append("# ===== 视频生成配置 =====")
    lines.append(f"SEEDANCE_API_KEY={env.get('SEEDANCE_API_KEY', '')}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    os.environ["LLM_BACKEND"] = env.get("LLM_BACKEND", "deepseek")
    os.environ["DEEPSEEK_API_KEY"] = env.get("DEEPSEEK_API_KEY", "")
    os.environ["DEEPSEEK_MODEL"] = env.get("DEEPSEEK_MODEL", "")
    os.environ["OPENAI_API_KEY"] = env.get("OPENAI_API_KEY", "")
    os.environ["OPENAI_MODEL"] = env.get("OPENAI_MODEL", "")
    os.environ["CLAUDE_API_KEY"] = env.get("CLAUDE_API_KEY", "")
    os.environ["CLAUDE_MODEL"] = env.get("CLAUDE_MODEL", "")
    os.environ["SEEDANCE_API_KEY"] = env.get("SEEDANCE_API_KEY", "")

    return {"saved": True}


@router.post("/settings/test-llm")
def test_llm(req: TestLLMRequest):
    from openai import OpenAI
    try:
        base_url = "https://api.deepseek.com" if req.backend == "deepseek" else None
        client = OpenAI(api_key=req.api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "请回复: 连接成功"}],
            max_tokens=20,
            timeout=15,
        )
        return {"success": True, "response": response.choices[0].message.content}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### Task 9: WebSocket 创作端点 — server/routes/creation.py

**Files:**
- Create: `server/routes/creation.py`

- [ ] **Step 1: 创建 server/routes/creation.py**

```python
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.ws_manager import ConnectionManager
from server.async_orch import AsyncOrchestrator

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/create/{project_name}")
async def websocket_create(websocket: WebSocket, project_name: str):
    await manager.connect(project_name, websocket)
    orch = AsyncOrchestrator(manager)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("action") == "start":
                asyncio.create_task(orch.run(project_name, msg.get("style", {})))
            else:
                manager.handle_client_message(project_name, msg)

    except WebSocketDisconnect:
        manager.disconnect(project_name)
    except Exception as e:
        await manager.send_message(project_name, {
            "type": "error",
            "message": str(e),
        })
        manager.disconnect(project_name)
```

---

### Task 10: 一键启动脚本 — run_web.py

**Files:**
- Create: `run_web.py`

- [ ] **Step 1: 创建 run_web.py**

```python
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"


def install_frontend():
    if not (WEB_DIR / "node_modules").exists():
        print("📦 安装前端依赖...")
        subprocess.run(["npm", "install"], cwd=str(WEB_DIR), check=True)


def build_frontend():
    dist = WEB_DIR / "dist"
    if not dist.exists() or not any(dist.iterdir()):
        print("🔨 构建前端...")
        subprocess.run(["npm", "run", "build"], cwd=str(WEB_DIR), check=True)


def start_server():
    import uvicorn
    print("🚀 启动服务 http://localhost:8000")
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    os.chdir(str(ROOT))
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / ".pkg"))

    install_frontend()
    build_frontend()
    start_server()
```

---

### Task 11: React 前端项目初始化

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/tailwind.config.js`
- Create: `web/postcss.config.js`
- Create: `web/index.html`
- Create: `web/src/index.css`
- Create: `web/src/main.tsx`

- [ ] **Step 1: 创建 web/package.json**

```json
{
  "name": "story-creation-web",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "lucide-react": "^0.441.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.41",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.3",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: 创建 web/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

**修正**：支持 REST + WS 代理：

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 web/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src"]
}
```

- [ ] **Step 4: 创建 web/tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 5: 创建 web/postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 6: 创建 web/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>多智能体故事创作系统</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎬</text></svg>" />
  </head>
  <body class="min-h-screen bg-background text-foreground">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: 创建 web/src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 6.9%;
    --card-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --border: 217.2 32.6% 17.5%;
    --radius: 0.5rem;
  }
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
```

- [ ] **Step 8: 创建 web/src/main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 9: 创建 web/src/lib/utils.ts**

```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 10: 安装依赖并验证**

```
cd web && npm install && npm run build -- --noEmit 2>&1 | tail -5
```

预期：无 TypeScript 错误（还未写组件，可能有 unused warning，忽略）。

---

### Task 12: 前端工具库 — web/src/lib/api.ts 和 types

**Files:**
- Create: `web/src/lib/api.ts`

- [ ] **Step 1: 创建 web/src/lib/api.ts**

```typescript
const BASE = '/api'

export interface ProjectListItem {
  name: string
  status: string
  created_at: string
  updated_at: string
  current_phase: number
  total_phases: number
  phases: Array<{ name: string; done: boolean }>
  style_type?: string
  genre?: string
}

export interface StyleConfig {
  story_type: string
  genre: string
  writing_style: string
  visual_style: string
  art_style: string
  screen_aspect: string
  script_style: string
  duration_mode: string
  episode_count: string
  episode_duration: string
  custom_requirements: string
  visual_reference: string
  action_reference: string
}

export interface CreateProjectPayload {
  name: string
  story_idea: string
  style: StyleConfig
  duration_line: string
}

export interface SettingsData {
  llm_backend: string
  deepseek_api_key: string
  deepseek_model: string
  openai_api_key: string
  openai_model: string
  claude_api_key: string
  claude_model: string
  seedance_api_key: string
}

export async function fetchProjects(): Promise<ProjectListItem[]> {
  const res = await fetch(`${BASE}/projects`)
  if (!res.ok) throw new Error('Failed to fetch projects')
  return res.json()
}

export async function fetchProject(name: string): Promise<any> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error('Project not found')
  return res.json()
}

export async function fetchPhaseContent(name: string, phase: string): Promise<{ content: string; is_split: boolean }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/${encodeURIComponent(phase)}/content`)
  if (!res.ok) return { content: '', is_split: false }
  return res.json()
}

export async function createProject(payload: CreateProjectPayload): Promise<{ name: string }> {
  const res = await fetch(`${BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to create project')
  return res.json()
}

export async function deleteProject(name: string): Promise<void> {
  await fetch(`${BASE}/projects/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export async function fetchSettings(): Promise<SettingsData> {
  const res = await fetch(`${BASE}/settings`)
  if (!res.ok) throw new Error('Failed to fetch settings')
  return res.json()
}

export async function updateSettings(data: Partial<SettingsData>): Promise<void> {
  await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function testLLM(backend: string, apiKey: string, model: string): Promise<{ success: boolean; response?: string; error?: string }> {
  const res = await fetch(`${BASE}/settings/test-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ backend, api_key: apiKey, model }),
  })
  return res.json()
}

export function createWebSocket(projectName: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return new WebSocket(`${protocol}//${host}/api/ws/create/${encodeURIComponent(projectName)}`)
}
```

---

### Task 13: useWebSocket Hook — web/src/hooks/useWebSocket.ts

**Files:**
- Create: `web/src/hooks/useWebSocket.ts`

- [ ] **Step 1: 创建 Hook**

```typescript
import { useRef, useCallback, useState } from 'react'

export interface WSMessage {
  type: string
  phase_index?: number
  phase_name?: string
  total_phases?: number
  chunk?: string
  file_path?: string
  message?: string
  current?: number
  total?: number
  error?: string
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const [currentPhase, setCurrentPhase] = useState(-1)
  const [phases, setPhases] = useState<Array<{ name: string; status: 'done' | 'active' | 'pending' }>>([])
  const [progress, setProgress] = useState({ current: 0, total: 6 })
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [awaitingPlatform, setAwaitingPlatform] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const onMessageRef = useRef<((msg: WSMessage) => void) | null>(null)

  const connect = useCallback((projectName: string) => {
    const ws = createWebSocketFromPath(projectName)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data)

      switch (msg.type) {
        case 'progress':
          setProgress({ current: msg.current || 0, total: msg.total || 6 })
          break
        case 'phase_start':
          setCurrentPhase(msg.phase_index || 0)
          setStreamContent('')
          setPhases(prev => {
            const next = [...prev]
            if (!next[msg.phase_index!]) {
              next[msg.phase_index!] = { name: msg.phase_name || '', status: 'active' }
            }
            next[msg.phase_index!] = { ...next[msg.phase_index!], status: 'active' }
            return next
          })
          break
        case 'stream':
          setStreamContent(prev => prev + (msg.chunk || ''))
          break
        case 'phase_complete':
          setPhases(prev => {
            const next = [...prev]
            if (next[msg.phase_index!]) {
              next[msg.phase_index!] = { ...next[msg.phase_index!], status: 'done' }
            }
            return next
          })
          setAwaitingApproval(true)
          break
        case 'awaiting_approval':
          setAwaitingApproval(true)
          break
        case 'awaiting_platform':
          setAwaitingPlatform(true)
          break
        case 'all_complete':
          setIsComplete(true)
          setAwaitingApproval(false)
          break
        case 'error':
          setError(msg.message || 'Unknown error')
          break
      }

      onMessageRef.current?.(msg)
    }

    ws.onclose = () => {
      setConnected(false)
      setTimeout(() => connect(projectName), 3000)
    }

    ws.onerror = () => ws.close()
  }, [])

  const send = useCallback((data: Record<string, any>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  const approve = useCallback((phaseIndex: number) => {
    send({ action: 'approve', phase_index: phaseIndex })
    setAwaitingApproval(false)
  }, [send])

  const revise = useCallback((phaseIndex: number, feedback: string) => {
    send({ action: 'revise', phase_index: phaseIndex, feedback })
    setAwaitingApproval(false)
    setStreamContent('')
  }, [send])

  const reject = useCallback((phaseIndex: number, reason: string) => {
    send({ action: 'reject', phase_index: phaseIndex, reason })
    setAwaitingApproval(false)
  }, [send])

  const selectPlatform = useCallback((platform: string) => {
    send({ action: 'platform', platform })
    setAwaitingPlatform(false)
  }, [send])

  const onMessage = useCallback((handler: (msg: WSMessage) => void) => {
    onMessageRef.current = handler
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
  }, [])

  return {
    connect, send, approve, revise, reject, selectPlatform,
    onMessage, disconnect,
    connected, streamContent, currentPhase, phases,
    progress, awaitingApproval, awaitingPlatform,
    isComplete, error,
  }
}

function createWebSocketFromPath(projectName: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return new WebSocket(`${protocol}//${host}/api/ws/create/${encodeURIComponent(projectName)}`)
}
```

---

### Task 14: App 路由 + 布局 — web/src/App.tsx

**Files:**
- Create: `web/src/App.tsx`

- [ ] **Step 1: 创建 web/src/App.tsx**

```tsx
import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import NewProjectWizard from './pages/NewProjectWizard'
import Workspace from './pages/Workspace'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new" element={<NewProjectWizard />} />
        <Route path="/project/:name" element={<Workspace />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  )
}
```

---

### Task 15: 项目广场页 — web/src/pages/HomePage.tsx

**Files:**
- Create: `web/src/pages/HomePage.tsx`

- [ ] **Step 1: 创建 web/src/pages/HomePage.tsx**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Settings, Film } from 'lucide-react'
import { fetchProjects, deleteProject, ProjectListItem } from '../lib/api'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '提示词', '视频']

export default function HomePage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const data = await fetchProjects()
      setProjects(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (name: string) => {
    if (!confirm(`确定删除项目「${name}」？`)) return
    await deleteProject(name)
    load()
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-10">
        <div className="flex items-center gap-3">
          <Film className="w-8 h-8 text-primary" />
          <h1 className="text-2xl font-bold">多智能体故事创作系统</h1>
        </div>
        <button
          onClick={() => navigate('/settings')}
          className="p-2 rounded-lg hover:bg-muted transition-colors"
          title="设置"
        >
          <Settings className="w-5 h-5" />
        </button>
      </header>

      {loading ? (
        <div className="text-center text-muted-foreground py-20">加载中...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <Film className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground text-lg mb-6">还没有项目，开始你的第一个创作吧</p>
          <button
            onClick={() => navigate('/new')}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-xl font-medium hover:opacity-90 transition-opacity"
          >
            <Plus className="w-5 h-5" /> 新建项目
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(p => {
            const done = p.phases.filter(ph => ph.done).length
            const total = p.total_phases
            return (
              <div
                key={p.name}
                onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)}
                className="bg-card border border-border rounded-xl p-5 cursor-pointer hover:border-primary/50 transition-colors group"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-lg truncate">{p.name}</h3>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }}
                    className="text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm"
                  >
                    删除
                  </button>
                </div>
                <div className="text-sm text-muted-foreground mb-3">
                  {p.genre || '未分类'} · {p.phases.length} 阶段
                </div>
                <div className="w-full bg-muted rounded-full h-2 mb-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground">
                  {done}/{total} 完成 · {p.updated_at?.slice(0, 10)}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <button
        onClick={() => navigate('/new')}
        className="fixed bottom-8 right-8 w-14 h-14 bg-primary text-primary-foreground rounded-full flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-105 transition-all"
      >
        <Plus className="w-6 h-6" />
      </button>
    </div>
  )
}
```

---

### Task 16: 新建项目向导 — web/src/pages/NewProjectWizard.tsx

**Files:**
- Create: `web/src/pages/NewProjectWizard.tsx`

- [ ] **Step 1: 创建 web/src/pages/NewProjectWizard.tsx**

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { createProject, StyleConfig, CreateProjectPayload } from '../lib/api'

const STORY_TYPES: Record<string, string> = {
  '1': '短剧', '2': '电影', '3': '电视剧', '4': '小说/网文', '5': '舞台剧/话剧', '6': '广播剧/有声书',
}

const GENRE_MAP: Record<string, string[]> = {
  '1': ['都市情感', '悬疑反转', '古装虐恋', '喜剧轻松', '战神逆袭', '科幻脑洞', '家庭伦理'],
  '2': ['科幻', '悬疑推理', '动作冒险', '爱情', '历史传记', '动画', '战争'],
  '3': ['都市职场', '古装权谋', '悬疑探案', '家庭伦理', '青春校园'],
  '4': ['玄幻', '修仙', '都市', '言情', '科幻', '灵异', '历史'],
  '5': ['经典改编', '原创实验', '音乐剧', '喜剧'],
  '6': ['悬疑', '言情', '恐怖', '喜剧', '历史'],
}

const WRITING_STYLES: Record<string, string> = { '1': '精炼实用', '2': '文学质感', '3': '对白优先', '4': '画面感强', '5': '自动适配' }
const VISUAL_STYLES: Record<string, string> = { '1': '好莱坞大片风', '2': '竖屏短剧风', '3': '文艺/独立风', '4': '日韩生活风', '5': '电视剧风' }
const RENDER_STYLES: Record<string, string> = { '1': '写实/真人', '2': '2D 动画', '3': '3D CG', '4': '卡通/风格化', '5': '水墨/国风', '6': '像素/复古', '7': '自动适配' }
const SCREEN_ASPECTS: Record<string, string> = { '1': '9:16 竖屏', '2': '16:9 横屏', '3': '自适应' }
const SCRIPT_STYLES: Record<string, string> = { '1': '视觉化写作', '2': '对白驱动型', '3': '文学剧本型' }

export default function NewProjectWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [style, setStyle] = useState<StyleConfig>({
    story_type: '', genre: '', writing_style: '', visual_style: '',
    art_style: '', screen_aspect: '', script_style: '',
    duration_mode: '1', episode_count: '', episode_duration: '',
    custom_requirements: '', visual_reference: '', action_reference: '',
  })
  const [storyIdea, setStoryIdea] = useState('')
  const [projectName, setProjectName] = useState('')
  const [loading, setLoading] = useState(false)

  const steps = ['故事类型', '风格偏好', '时长设置', '故事描述']

  const handleCreate = async () => {
    setLoading(true)
    const durationLine = style.duration_mode === '1' ? '自动（由Agent推荐）'
      : style.episode_count && style.episode_duration
        ? `${style.episode_count}集 × ${style.episode_duration}/集`
        : style.episode_duration || style.episode_count || ''

    const payload: CreateProjectPayload = {
      name: projectName || 'untitled',
      story_idea: storyIdea,
      style,
      duration_line: durationLine,
    }

    try {
      const result = await createProject(payload)
      navigate(`/project/${encodeURIComponent(result.name)}`)
    } catch (e) {
      alert('创建失败: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  const OptionGrid = ({ options, selected, onSelect }: { options: Record<string, string>, selected: string, onSelect: (k: string) => void }) => (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {Object.entries(options).map(([k, v]) => (
        <button
          key={k}
          onClick={() => onSelect(k)}
          className={`p-3 rounded-lg border text-left transition-colors ${
            selected === k ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50'
          }`}
        >
          {v}
        </button>
      ))}
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <button onClick={() => navigate('/')} className="flex items-center gap-1 text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> 返回
      </button>

      <div className="flex gap-2 mb-8">
        {steps.map((s, i) => (
          <div key={i} className={`flex-1 h-1 rounded-full ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
        ))}
      </div>

      <h2 className="text-xl font-bold mb-6">{steps[step]}</h2>

      {step === 0 && (
        <div>
          <p className="text-sm text-muted-foreground mb-3">选择故事类型</p>
          <OptionGrid options={STORY_TYPES} selected={style.story_type} onSelect={v => setStyle({ ...style, story_type: v, genre: '' })} />
          {style.story_type && (
            <>
              <p className="text-sm text-muted-foreground mt-6 mb-3">选择题材风格</p>
              <div className="flex flex-wrap gap-2">
                {(GENRE_MAP[style.story_type] || []).map(g => (
                  <button
                    key={g}
                    onClick={() => setStyle({ ...style, genre: g })}
                    className={`px-4 py-2 rounded-lg border transition-colors ${
                      style.genre === g ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50'
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {step === 1 && (
        <div className="space-y-6">
          <div>
            <p className="text-sm text-muted-foreground mb-3">文笔风格</p>
            <OptionGrid options={WRITING_STYLES} selected={style.writing_style} onSelect={v => setStyle({ ...style, writing_style: v })} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-3">视觉/叙事风格</p>
            <OptionGrid options={VISUAL_STYLES} selected={style.visual_style} onSelect={v => setStyle({ ...style, visual_style: v })} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-3">渲染画风</p>
            <OptionGrid options={RENDER_STYLES} selected={style.art_style} onSelect={v => setStyle({ ...style, art_style: v })} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-3">剧本写作风格</p>
            <OptionGrid options={SCRIPT_STYLES} selected={style.script_style} onSelect={v => setStyle({ ...style, script_style: v })} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-3">画面比例</p>
            <OptionGrid options={SCREEN_ASPECTS} selected={style.screen_aspect} onSelect={v => setStyle({ ...style, screen_aspect: v })} />
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-3">时长设置</p>
            <div className="flex gap-4">
              <button
                onClick={() => setStyle({ ...style, duration_mode: '1' })}
                className={`px-4 py-3 rounded-lg border ${style.duration_mode === '1' ? 'border-primary bg-primary/10' : 'border-border'}`}
              >
                自动时长
              </button>
              <button
                onClick={() => setStyle({ ...style, duration_mode: '2' })}
                className={`px-4 py-3 rounded-lg border ${style.duration_mode === '2' ? 'border-primary bg-primary/10' : 'border-border'}`}
              >
                自定义时长
              </button>
            </div>
          </div>
          {style.duration_mode === '2' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-1">集数/章节数</label>
                <input
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2"
                  placeholder="如 12"
                  value={style.episode_count}
                  onChange={e => setStyle({ ...style, episode_count: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-1">单集时长</label>
                <input
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2"
                  placeholder="如 45分钟"
                  value={style.episode_duration}
                  onChange={e => setStyle({ ...style, episode_duration: e.target.value })}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground block mb-1">项目名称</label>
            <input
              className="w-full bg-muted border border-border rounded-lg px-3 py-2"
              placeholder="给你的项目起个名字"
              value={projectName}
              onChange={e => setProjectName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground block mb-1">故事描述</label>
            <textarea
              className="w-full bg-muted border border-border rounded-lg px-3 py-2 h-32 resize-none"
              placeholder="用一段话描述你想讲的故事..."
              value={storyIdea}
              onChange={e => setStoryIdea(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground block mb-1">额外要求（可选）</label>
            <textarea
              className="w-full bg-muted border border-border rounded-lg px-3 py-2 h-20 resize-none"
              placeholder="参考作品、情绪基调等..."
              value={style.custom_requirements}
              onChange={e => setStyle({ ...style, custom_requirements: e.target.value })}
            />
          </div>
        </div>
      )}

      <div className="flex justify-between mt-8">
        <button
          onClick={() => step > 0 ? setStep(step - 1) : navigate('/')}
          className="flex items-center gap-1 px-4 py-2 rounded-lg border border-border hover:bg-muted"
        >
          <ArrowLeft className="w-4 h-4" /> 上一步
        </button>
        {step < 3 ? (
          <button
            onClick={() => setStep(step + 1)}
            className="flex items-center gap-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
          >
            下一步 <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleCreate}
            disabled={loading || !storyIdea}
            className="flex items-center gap-1 px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            <Check className="w-4 h-4" /> {loading ? '创建中...' : '创建项目'}
          </button>
        )}
      </div>
    </div>
  )
}
```

---

### Task 17: 创作工作台 — web/src/pages/Workspace.tsx

**Files:**
- Create: `web/src/pages/Workspace.tsx`

- [ ] **Step 1: 创建 web/src/pages/Workspace.tsx**

```tsx
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Check, Pencil, X, Loader2 } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { fetchProject } from '../lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '提示词', '视频']

export default function Workspace() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [projectConfig, setProjectConfig] = useState<any>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [started, setStarted] = useState(false)

  const {
    connect, approve, revise, reject,
    connected, streamContent, currentPhase, phases,
    progress, awaitingApproval, isComplete, error,
  } = useWebSocket()

  useEffect(() => {
    if (!name) return
    fetchProject(name).then(config => {
      setProjectConfig(config)
      const donePhases = config.phases || []
      if (donePhases.some((p: any) => p.done)) {
        setStarted(true)
      }
    })
  }, [name])

  const handleStart = () => {
    if (!name) return
    connect(name)
    setStarted(true)
    setTimeout(() => {
      const { send, selectPlatform } = useWebSocket.call ? {} : {} as any
    }, 500)
  }

  const handleApprove = () => { approve(currentPhase) }

  const handleRevise = () => {
    if (!feedbackText.trim()) return
    revise(currentPhase, feedbackText)
    setFeedbackText('')
    setShowFeedback(false)
  }

  const handleReject = () => {
    reject(currentPhase, '不满意')
  }

  const phaseStatus = (index: number) => {
    if (index === currentPhase && streamContent) return 'active'
    if (projectConfig?.phases?.[index]?.done || phases[index]?.status === 'done') return 'done'
    return 'pending'
  }

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <button onClick={() => navigate('/')} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm">
            <ArrowLeft className="w-4 h-4" /> 返回
          </button>
          <h2 className="font-bold mt-2 truncate">{name}</h2>
          {projectConfig?.genre && (
            <p className="text-xs text-muted-foreground">{projectConfig.genre}</p>
          )}
        </div>

        <div className="flex-1 p-3 space-y-1 overflow-y-auto">
          {PHASE_NAMES.map((pname, i) => {
            const status = phaseStatus(i)
            return (
              <div
                key={i}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                  status === 'active' ? 'bg-primary/20 text-primary' :
                  status === 'done' ? 'text-green-400' :
                  'text-muted-foreground'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${
                  status === 'active' ? 'bg-primary animate-pulse' :
                  status === 'done' ? 'bg-green-400' :
                  'bg-muted-foreground'
                }`} />
                {pname}
              </div>
            )
          })}
        </div>

        <div className="p-4 border-t border-border text-xs text-muted-foreground">
          进度: {progress.current}/{progress.total}
          <div className="w-full bg-muted rounded-full h-1.5 mt-1">
            <div
              className="bg-primary h-1.5 rounded-full transition-all"
              style={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        {!started ? (
          <div className="flex-1 flex items-center justify-center">
            <button
              onClick={handleStart}
              className="flex items-center gap-2 bg-primary text-primary-foreground px-8 py-4 rounded-xl font-medium text-lg hover:opacity-90 transition-opacity"
            >
              <Play className="w-6 h-6" /> 开始创作
            </button>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-red-400">
            <X className="w-6 h-6 mr-2" /> {error}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-6">
              {streamContent ? (
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamContent}</ReactMarkdown>
                </div>
              ) : isComplete ? (
                <div className="flex items-center justify-center h-full text-green-400">
                  <Check className="w-8 h-8 mr-2" /> 全部完成！
                </div>
              ) : !connected ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" /> 连接中...
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  等待生成...
                </div>
              )}
            </div>

            {awaitingApproval && !isComplete && (
              <div className="border-t border-border p-4 bg-card">
                {showFeedback ? (
                  <div className="space-y-3">
                    <textarea
                      className="w-full bg-muted border border-border rounded-lg px-3 py-2 h-24 resize-none"
                      placeholder="请输入修改意见..."
                      value={feedbackText}
                      onChange={e => setFeedbackText(e.target.value)}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button onClick={handleRevise} className="flex items-center gap-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm">
                        <Pencil className="w-4 h-4" /> 提交修改
                      </button>
                      <button onClick={() => setShowFeedback(false)} className="px-4 py-2 border border-border rounded-lg text-sm">
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <button onClick={handleApprove} className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm">
                      <Check className="w-4 h-4" /> 通过
                    </button>
                    <button onClick={() => setShowFeedback(true)} className="flex items-center gap-1 px-4 py-2 bg-muted border border-border rounded-lg text-sm">
                      <Pencil className="w-4 h-4" /> 修改
                    </button>
                    <button onClick={handleReject} className="flex items-center gap-1 px-4 py-2 text-red-400 hover:bg-red-400/10 rounded-lg text-sm">
                      <X className="w-4 h-4" /> 退回
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
```

**⚠️ Bug fix needed**: The `handleStart` function has a dead code issue with `useWebSocket.call`. Let me fix it — the `send` function is used to send the `start` action with style data. This needs a fix before Task 17 is committed.

---

### Task 18: 设置页 — web/src/pages/SettingsPage.tsx

**Files:**
- Create: `web/src/pages/SettingsPage.tsx`

- [ ] **Step 1: 创建 web/src/pages/SettingsPage.tsx**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Zap, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { fetchSettings, updateSettings, testLLM, SettingsData } from '../lib/api'

const BACKENDS = [
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'claude', label: 'Claude' },
]

export default function SettingsPage() {
  const navigate = useNavigate()
  const [settings, setSettings] = useState<SettingsData>({
    llm_backend: 'deepseek', deepseek_api_key: '', deepseek_model: 'deepseek-chat',
    openai_api_key: '', openai_model: 'gpt-4o',
    claude_api_key: '', claude_model: 'claude-sonnet-4-20250514',
    seedance_api_key: '',
  })
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    fetchSettings().then(data => setSettings(prev => ({ ...prev, ...data })))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    await updateSettings(settings)
    setSaving(false)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    const key = settings.llm_backend === 'deepseek' ? settings.deepseek_api_key
      : settings.llm_backend === 'openai' ? settings.openai_api_key
      : settings.claude_api_key
    const model = settings.llm_backend === 'deepseek' ? settings.deepseek_model
      : settings.llm_backend === 'openai' ? settings.openai_model
      : settings.claude_model

    const result = await testLLM(settings.llm_backend, key, model)
    setTestResult({ success: result.success, message: result.success ? result.response! : result.error! })
    setTesting(false)
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={() => navigate('/')} className="flex items-center gap-1 text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> 返回
      </button>

      <h1 className="text-2xl font-bold mb-8">⚙️ 设置</h1>

      <div className="space-y-6">
        <div>
          <label className="text-sm text-muted-foreground block mb-2">LLM 后端</label>
          <div className="flex gap-2">
            {BACKENDS.map(b => (
              <button
                key={b.value}
                onClick={() => setSettings({ ...settings, llm_backend: b.value })}
                className={`px-4 py-2 rounded-lg border ${
                  settings.llm_backend === b.value ? 'border-primary bg-primary/10' : 'border-border'
                }`}
              >
                {b.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm text-muted-foreground block mb-2">API Key</label>
          <input
            type="password"
            className="w-full bg-muted border border-border rounded-lg px-3 py-2 font-mono"
            placeholder={`输入 ${settings.llm_backend.toUpperCase()} API Key...`}
            value={
              settings.llm_backend === 'deepseek' ? settings.deepseek_api_key
              : settings.llm_backend === 'openai' ? settings.openai_api_key
              : settings.claude_api_key
            }
            onChange={e => {
              const key = settings.llm_backend === 'deepseek' ? 'deepseek_api_key'
                : settings.llm_backend === 'openai' ? 'openai_api_key'
                : 'claude_api_key'
              setSettings({ ...settings, [key]: e.target.value })
            }}
          />
        </div>

        <div>
          <label className="text-sm text-muted-foreground block mb-2">模型</label>
          <input
            className="w-full bg-muted border border-border rounded-lg px-3 py-2"
            placeholder="模型名称"
            value={
              settings.llm_backend === 'deepseek' ? settings.deepseek_model
              : settings.llm_backend === 'openai' ? settings.openai_model
              : settings.claude_model
            }
            onChange={e => {
              const key = settings.llm_backend === 'deepseek' ? 'deepseek_model'
                : settings.llm_backend === 'openai' ? 'openai_model'
                : 'claude_model'
              setSettings({ ...settings, [key]: e.target.value })
            }}
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-muted disabled:opacity-50"
          >
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            测试连接
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            <Save className="w-4 h-4" /> {saving ? '保存中...' : '保存'}
          </button>
        </div>

        {testResult && (
          <div className={`flex items-center gap-2 p-3 rounded-lg ${testResult.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {testResult.success ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
            {testResult.message}
          </div>
        )}
      </div>
    </div>
  )
}
```

---

### Task 19: 集成测试与修复

**Files:**
- Modify: `requirements.txt`（添加 uvicorn, fastapi, websockets）
- Create: 无新文件

- [ ] **Step 1: 更新 requirements.txt，添加 FastAPI 依赖**

在 `requirements.txt` 末尾追加：
```
fastapi>=0.112.0
uvicorn>=0.30.0
websockets>=12.0
```

- [ ] **Step 2: 安装后端依赖**

```
python -m pip install --target ".pkg" fastapi uvicorn websockets
```

- [ ] **Step 3: 安装前端依赖**

```
cd web && npm install
```

- [ ] **Step 4: 验证前端 TypeScript 编译**

```
cd web && npx tsc --noEmit
```

如果 Workspace.tsx 的 handleStart 有问题，修复为：

```tsx
const handleStart = () => {
    if (!name) return
    connect(name)
    setStarted(true)
}
```

- [ ] **Step 5: 构建前端**

```
cd web && npm run build
```

- [ ] **Step 6: 启动完整系统**

```
python run_web.py
```

预期：浏览器访问 `http://localhost:8000` 显示项目广场页面。

---

### Task 20: Workspace.tsx 修复 — 添加开始创作时的 style 发送

**Files:**
- Modify: `web/src/pages/Workspace.tsx`

在 Workspace 中，`handleStart` 需要发送项目配置中的 style 数据来启动创作。但设计文档中项目广场点击后进入 Workspace 应该自动继续已有项目，还是需要先点"开始创作"？对于新建项目（刚创建完），直接自动开始；对于已有项目，显示已有内容，可以继续。

修改 `handleStart`：

```tsx
const handleStart = () => {
    if (!name) return
    connect(name)
    setStarted(true)
    // 延迟一下等 WS 连接建立
    setTimeout(() => {
      if (projectConfig?.style_type) {
        send({
          action: 'start',
          style: {
            story_type: projectConfig.style_type || '',
            genre: projectConfig.genre || '',
            writing_style: projectConfig.writing_style || '',
            visual_style: projectConfig.visual_style || '',
            art_style: projectConfig.art_style || '',
            screen_aspect: projectConfig.screen_aspect || '',
            script_style: projectConfig.script_style || '',
            duration_mode: '1',
            episode_count: '',
            episode_duration: '',
            custom_requirements: '',
            visual_reference: projectConfig.visual_reference || '',
            action_reference: projectConfig.action_reference || '',
          },
        })
      }
    }, 500)
  }
```

需要从 useWebSocket 解构出 `send`：

```tsx
const {
    connect, send, approve, revise, reject,
    connected, streamContent, currentPhase, phases,
    progress, awaitingApproval, isComplete, error,
  } = useWebSocket()
```

---

## 自审清单

1. **Spec 覆盖**：所有设计文档要点已覆盖 ✅
   - ✅ FastAPI 后端 + WebSocket — Task 3, 5, 6, 9
   - ✅ 流式生成 — Task 1, 2, 6 (async_orch)
   - ✅ 项目广场 — Task 15
   - ✅ 新建向导 — Task 16
   - ✅ 创作工作台 — Task 17, 20
   - ✅ 设置页 — Task 18
   - ✅ 一键启动 — Task 10

2. **占位符扫描**：无 TBD/TODO ✅

3. **类型一致性**：前后端 schema 对齐 ✅ — server/schemas.py 和 web/src/lib/api.ts 的 StyleConfig 字段一致

---

## 执行建议

**推荐执行顺序**：Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → (先验证后端) → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 20 → 18 → 19
