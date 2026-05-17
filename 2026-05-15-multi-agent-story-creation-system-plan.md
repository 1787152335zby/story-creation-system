# 多智能体故事创作系统 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一套多智能体协作系统，让用户以"超级个体"身份管理一群AI Agent，完成从创意到视频生成的完整故事创作流程。

**Architecture:** 采用轻量级自定义框架（非CrewAI），以顺序管道模式串联各Agent。Agent之间通过项目文件目录传递数据，LLM调用抽象为统一客户端，支持多后端切换。CLI交互式界面引导用户逐步完成创作。

**Tech Stack:** Python 3.11+, OpenAI API / Claude API, Playwright (浏览器自动化), PyAutoGUI (桌面操控), python-dotenv (配置管理)

---

## 文件结构

```
e:\trae\ai\jvben\
├── main.py                              # 一键启动入口
├── requirements.txt                     # 依赖清单
├── .env.example                         # 配置模板
├── .env                                 # 实际配置（不提交）
├── agents/                              # Agent 定义
│   ├── __init__.py
│   ├── orchestrator.py                  # 总指挥官
│   ├── outline_designer.py              # 大纲设计师
│   ├── plot_expander.py                 # 剧情展开师
│   ├── storyboarder.py                  # 分镜师
│   └── prompt_engineer.py               # 提示词工程师
├── core/                                # 核心框架
│   ├── __init__.py
│   ├── cli.py                           # CLI 交互界面（富文本输出）
│   ├── project_manager.py               # 项目管理器
│   ├── style_config.py                  # 风格配置
│   ├── agent_base.py                    # Agent 基类
│   ├── workflow_loader.py               # 工作流配置加载器
│   └── review_gate.py                   # 审核门禁
├── tools/                               # 工具系统层
│   ├── __init__.py
│   ├── file_ops.py                      # 文件操作
│   ├── browser.py                       # 浏览器操控（后续阶段）
│   └── api_caller.py                    # API 调用封装
├── llm/                                 # 大模型接入
│   ├── __init__.py
│   ├── client.py                        # LLM 客户端（抽象层）
│   └── backends.py                      # 各后端实现（OpenAI/Claude）
├── prompts/                             # 提示词模板（文本文件，方便修改）
│   ├── outline_designer.txt
│   ├── plot_expander.txt
│   ├── storyboarder.txt
│   ├── prompt_engineer.txt
│   └── orchestrator_router.txt
├── projects/                            # 创作项目存放（自动创建）
├── workflow.yaml                        # 工作流配置（可插拔Agent流水线）
└── docs/superpowers/plans/              # 计划文档存放

---

## Phase 1：基础框架搭建

### Task 1.1：创建项目骨架和依赖配置

**Files:**
- Create: `e:\trae\ai\jvben\requirements.txt`
- Create: `e:\trae\ai\jvben\.env.example`
- Create: `e:\trae\ai\jvben\core\__init__.py`
- Create: `e:\trae\ai\jvben\agents\__init__.py`
- Create: `e:\trae\ai\jvben\tools\__init__.py`
- Create: `e:\trae\ai\jvben\llm\__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
# 核心依赖
openai>=1.0.0
anthropic>=0.30.0
python-dotenv>=1.0.0
pyyaml>=6.0

# 工具依赖
playwright>=1.40.0
pyautogui>=0.9.54

# 开发辅助
rich>=13.0.0          # 终端富文本输出
```

- [ ] **Step 2: 创建 .env.example**

```
# ===== 大模型配置 =====
# 至少配置一个后端
LLM_BACKEND=openai          # 可选: openai, claude, custom
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
CLAUDE_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-20250514

# ===== 视频生成配置 =====
SEEDANCE_API_KEY=your-seedance-key-here
```

- [ ] **Step 3: 创建 \_\_init\_\_.py 文件**

所有 `__init__.py` 文件只需一行：

```python
# __init__.py - 留空即可
```

---

### Task 1.2：LLM 客户端抽象层

**Files:**
- Create: `e:\trae\ai\jvben\llm\client.py`
- Create: `e:\trae\ai\jvben\llm\backends.py`

- [ ] **Step 1: 创建 backends.py — LLM 后端实现**

```python
import os
from typing import Optional


class LLMBackend:
    """LLM 后端基类"""
    def __init__(self, model: str):
        self.model = model

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        raise NotImplementedError


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o"):
        super().__init__(model)
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content


class ClaudeBackend(LLMBackend):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=8192,
        )
        return response.content[0].text
```

- [ ] **Step 2: 创建 client.py — LLM 客户端统一入口**

```python
import os
from typing import Optional
from .backends import OpenAIBackend, ClaudeBackend, LLMBackend


class LLMClient:
    """LLM 客户端统一入口，支持多后端切换"""

    def __init__(self):
        backend_name = os.getenv("LLM_BACKEND", "openai").lower()
        self.backend: LLMBackend = self._create_backend(backend_name)

    def _create_backend(self, name: str) -> LLMBackend:
        backends = {
            "openai": OpenAIBackend,
            "claude": ClaudeBackend,
        }
        backend_class = backends.get(name)
        if not backend_class:
            available = ", ".join(backends.keys())
            raise ValueError(f"未知后端: {name}，可选: {available}")
        return backend_class()

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        return self.backend.chat(system_prompt, user_prompt, temperature)
```

---

### Task 1.3：核心框架 — CLI 交互界面

**Files:**
- Create: `e:\trae\ai\jvben\core\cli.py`

- [ ] **Step 1: 创建 CLI 交互模块**

```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from typing import List, Tuple


console = Console()


def print_banner():
    """显示启动横幅"""
    banner = """
╔══════════════════════════════════════════╗
║     🎬 多智能体故事创作系统 v1.0         ║
║     输入 /start 开始新的创作             ║
║     输入 /list 查看已有项目              ║
║     输入 /continue 继续未完成的项目       ║
║     输入 /help 查看帮助                  ║
║     输入 /exit 退出系统                  ║
╚══════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold cyan"))


def show_menu() -> str:
    """显示主菜单，返回用户输入的命令"""
    return Prompt.ask("> ").strip().lower()


def select_option(title: str, options: List[Tuple[str, str]], allow_custom: bool = False) -> str:
    """
    通用选项选择器
    - title: 显示标题
    - options: [(编号, 描述), ...]
    - allow_custom: 是否允许自定义输入
    返回选中的编号或自定义文本
    """
    console.print(f"\n[bold yellow]{title}[/bold yellow]")
    for opt_id, desc in options:
        console.print(f"  {opt_id}) {desc}")

    if allow_custom:
        console.print(f"  {len(options)+1}) ✏️ 自定义")

    while True:
        choice = Prompt.ask("请输入编号").strip()
        if allow_custom and choice == str(len(options) + 1):
            return Prompt.ask("请输入自定义内容").strip()
        for opt_id, desc in options:
            if choice == opt_id:
                return choice
        console.print("[red]无效选择，请重新输入[/red]")


def multi_select(title: str, options: List[Tuple[str, str]]) -> List[str]:
    """
    多选器
    返回选中的编号列表
    """
    console.print(f"\n[bold yellow]{title}[/bold yellow]（可多选，用逗号分隔）")
    for opt_id, desc in options:
        console.print(f"  {opt_id}) {desc}")

    while True:
        choices = Prompt.ask("请输入编号（如 1,3,5）").strip()
        selected = [c.strip() for c in choices.split(",")]
        valid_ids = {opt_id for opt_id, _ in options}
        if all(s in valid_ids for s in selected):
            return selected
        console.print("[red]包含无效选择，请重新输入[/red]")


def get_text_input(prompt_text: str) -> str:
    """获取多行文本输入"""
    console.print(f"\n[bold yellow]{prompt_text}[/bold yellow]")
    console.print("[dim]（输入 /done 结束）[/dim]")
    lines = []
    while True:
        line = input()
        if line.strip() == "/done":
            break
        lines.append(line)
    return "\n".join(lines)


def show_progress(stage_name: str, progress: float):
    """显示进度信息"""
    bar_length = 30
    filled = int(bar_length * progress)
    bar = "━" * filled + "─" * (bar_length - filled)
    console.print(f"\n[cyan]{stage_name}[/cyan]")
    console.print(f"  {bar} {int(progress * 100)}%")


def notify_complete(stage_name: str, file_path: str):
    """通知用户某个阶段已完成"""
    console.print(f"\n[bold green]✅ {stage_name}已完成！[/bold green]")
    console.print(f"   请在 [cyan]{file_path}[/cyan] 中查看")
    console.print("   输入 [bold]/approve[/bold] 通过，或输入修改意见")


def wait_for_approval() -> Tuple[bool, str]:
    """
    等待用户审核
    返回: (是否通过, 修改意见)
    """
    feedback = Prompt.ask("[yellow]请审核[/yellow]").strip()
    if feedback.lower() == "/approve":
        return True, ""
    elif feedback.lower() == "/reject":
        reason = Prompt.ask("[red]请说明退回原因[/red]").strip()
        return False, reason
    else:
        return False, feedback
```

---

### Task 1.4：核心框架 — 项目管理器

**Files:**
- Create: `e:\trae\ai\jvben\core\project_manager.py`

- [ ] **Step 1: 创建项目管理器**

```python
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "projects"


def get_projects_list() -> List[Dict]:
    """获取所有项目列表"""
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "project_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                projects.append(config)
    return projects


class ProjectManager:
    """管理单个创作项目的目录、文件生命周期"""

    def __init__(self, name: str):
        self.name = self._sanitize_name(name)
        self.project_dir = PROJECTS_DIR / self.name
        self.config_file = self.project_dir / "project_config.json"
        self.config = self._load_or_create_config()

    def _sanitize_name(self, name: str) -> str:
        # 移除非法文件名字符
        invalid_chars = r'<>:"/\|?*'
        for c in invalid_chars:
            name = name.replace(c, "")
        return name.strip() or "untitled"

    def _load_or_create_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "name": self.name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "initialized",
            "current_phase": 0,
            "phases": [
                {"name": "story_outline", "done": False},
                {"name": "full_plot", "done": False},
                {"name": "storyboard", "done": False},
                {"name": "prompts", "done": False},
                {"name": "video", "done": False},
            ],
        }

    def save_config(self):
        self.config["updated_at"] = datetime.now().isoformat()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def mark_phase_done(self, phase_index: int):
        if 0 <= phase_index < len(self.config["phases"]):
            self.config["phases"][phase_index]["done"] = True
            self.config["current_phase"] = phase_index + 1
            self.save_config()

    def get_phase_path(self, phase_index: int) -> Optional[Path]:
        """获取某个阶段的产出文件路径"""
        phase_names = ["01_故事大纲.md", "02_完整剧情.md", "03_分镜脚本", "04_提示词", "05_视频"]
        if phase_index < len(phase_names):
            return self.project_dir / phase_names[phase_index]
        return None

    def write_output(self, filename: str, content: str) -> Path:
        """将内容写入项目文件"""
        file_path = self.project_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def read_output(self, filename: str) -> Optional[str]:
        """读取项目文件内容"""
        file_path = self.project_dir / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
```

---

### Task 1.5：工作流配置

**Files:**
- Create: `e:\trae\ai\jvben\workflow.yaml`

- [ ] **Step 1: 创建 workflow.yaml**

```yaml
# 工作流配置 - 定义Agent的执行顺序和条件
# 修改此文件可调整流水线，无需改动代码

phases:
  - name: 故事大纲
    agent: outline_designer
    output: 01_故事大纲.md
    condition: true
    auto_skip: false

  - name: 完整剧情
    agent: plot_expander
    output: 02_完整剧情.md
    condition: true
    auto_skip: false

  - name: 分镜设计
    agent: storyboarder
    output: 03_分镜脚本.md
    condition: "story_type in ['1', '2', '3']"
    auto_skip: false

  - name: 视频提示词
    agent: prompt_engineer
    output: 04_提示词.md
    condition: "story_type in ['1', '2', '3']"
    auto_skip: false

  - name: 视频生成
    agent: video_producer
    output: 05_视频/
    condition: "story_type in ['1', '2', '3']"
    auto_skip: true
```
说明：condition 中的 `'1', '2', '3'` 对应 STORY_TYPES 中的短剧/电影/电视剧。

### Task 1.6：核心框架 — 工作流加载器

**Files:**
- Create: `e:\trae\ai\jvben\core\workflow_loader.py`

- [ ] **Step 1: 创建工作流加载器**

```python
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from .style_config import STORY_TYPES


class WorkflowPhase:
    """工作流阶段定义"""
    def __init__(self, data: Dict):
        self.name: str = data["name"]
        self.agent: str = data["agent"]
        self.output: str = data["output"]
        self.condition: str = data.get("condition", "true")
        self.auto_skip: bool = data.get("auto_skip", False)

    def should_run(self, story_type_id: str) -> bool:
        """根据故事类型判断此阶段是否应该执行"""
        if self.condition == "true":
            return True
        # 解析条件表达式：story_type in ['1', '2', '3']
        if "story_type in" in self.condition:
            import ast
            allowed = ast.literal_eval(self.condition.split("[")[1].split("]")[0])
            return story_type_id in allowed
        return True


class WorkflowLoader:
    """加载和管理工作流配置"""

    @staticmethod
    def load(path: Optional[Path] = None) -> List[WorkflowPhase]:
        if path is None:
            path = Path(__file__).resolve().parent.parent / "workflow.yaml"
        if not path.exists():
            raise FileNotFoundError(f"工作流配置不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return [WorkflowPhase(p) for p in data["phases"]]
```

### Task 1.7：核心框架 — 风格配置管理器

**Files:**
- Create: `e:\trae\ai\jvben\core\style_config.py`

- [ ] **Step 1: 创建风格配置管理器**

```python
from typing import Dict, Optional


# 故事类型定义
STORY_TYPES = {
    "1": {"name": "短剧", "desc": "竖屏，每集1-3分钟，适合AI视频生成"},
    "2": {"name": "电影", "desc": "90-150分钟，完整三幕结构"},
    "3": {"name": "电视剧", "desc": "每集45分钟，多集/多季"},
    "4": {"name": "小说/网文", "desc": "纯文字，按章节"},
    "5": {"name": "舞台剧/话剧", "desc": "幕场结构"},
    "6": {"name": "广播剧/有声书", "desc": "声音驱动，无画面"},
}

# 题材风格（按故事类型分组）
GENRES = {
    "1": ["都市情感", "悬疑反转", "古装虐恋", "喜剧轻松", "战神逆袭", "科幻脑洞", "家庭伦理"],
    "2": ["科幻", "悬疑推理", "动作冒险", "爱情", "历史传记", "动画", "战争"],
    "3": ["都市职场", "古装权谋", "悬疑探案", "家庭伦理", "青春校园"],
    "4": ["玄幻", "修仙", "都市", "言情", "科幻", "灵异", "历史"],
    "5": ["经典改编", "原创实验", "音乐剧", "喜剧"],
    "6": ["悬疑", "言情", "恐怖", "喜剧", "历史"],
}

# 文笔风格
WRITING_STYLES = {
    "1": {"name": "精炼实用", "desc": "干净利落，适合短剧/快节奏"},
    "2": {"name": "文学质感", "desc": "细腻生动，适合小说/文艺片"},
    "3": {"name": "对白优先", "desc": "对话驱动，适合舞台剧/广播剧"},
    "4": {"name": "画面感强", "desc": "视觉化描写，适合电影"},
    "5": {"name": "自动适配", "desc": "根据故事类型自动选择最优风格"},
}

# 视觉/叙事风格
VISUAL_STYLES = {
    "1": {"name": "好莱坞大片风", "desc": "三幕结构、视觉冲击、电影感镜头语言"},
    "2": {"name": "竖屏短剧风", "desc": "快节奏、强反转、情绪密集"},
    "3": {"name": "文艺/独立风", "desc": "慢节奏、长镜头、情绪留白"},
    "4": {"name": "日韩生活风", "desc": "细腻日常、温暖治愈、轻节奏"},
    "5": {"name": "电视剧风", "desc": "多线叙事、人物群像"},
}

# 画面比例
SCREEN_ASPECTS = {
    "1": {"name": "9:16 竖屏", "desc": "强调人物近景/纵深"},
    "2": {"name": "16:9 横屏", "desc": "强调横向调度"},
    "3": {"name": "自适应", "desc": "让Agent根据故事类型自动选择"},
}

# 剧本写作风格
SCRIPT_STYLES = {
    "1": {"name": "视觉化写作", "desc": "动作描写先行，对白精炼，show dont tell"},
    "2": {"name": "对白驱动型", "desc": "大量对白驱动剧情，轻描写重对话"},
    "3": {"name": "文学剧本型", "desc": "细腻动作/心理描写+对白，文体接近文学"},
}


class StyleConfig:
    """风格配置，在大纲阶段选定后沿流水线传递"""

    def __init__(self):
        self.story_type: str = ""
        self.genre: str = ""
        self.writing_style: str = ""
        self.visual_style: str = ""
        self.screen_aspect: str = ""
        self.script_style: str = ""
        self.mood: str = ""
        self.custom_requirements: str = ""

    def to_dict(self) -> Dict:
        return {
            "story_type": self.story_type,
            "genre": self.genre,
            "writing_style": self.writing_style,
            "visual_style": self.visual_style,
            "screen_aspect": self.screen_aspect,
            "script_style": self.script_style,
            "mood": self.mood,
            "custom_requirements": self.custom_requirements,
        }

    def to_yaml_string(self) -> str:
        lines = [
            "# 风格配置文件（自动生成）",
            f"story_type: {self.story_type}",
            f"genre: {self.genre}",
            f"writing_style: {self.writing_style}",
            f"visual_style: {self.visual_style}",
            f"screen_aspect: {self.screen_aspect}",
            f"script_style: {self.script_style}",
            f"mood: {self.mood}",
        ]
        return "\n".join(lines)

    @classmethod
    def from_mapping(cls, data: Dict) -> "StyleConfig":
        config = cls()
        config.story_type = STORY_TYPES.get(data.get("story_type", ""), {}).get("name", "")
        config.genre = data.get("genre", "")
        config.writing_style = WRITING_STYLES.get(data.get("writing_style", ""), {}).get("name", "")
        config.visual_style = VISUAL_STYLES.get(data.get("visual_style", ""), {}).get("name", "")
        config.screen_aspect = SCREEN_ASPECTS.get(data.get("screen_aspect", ""), {}).get("name", "")
        config.script_style = SCRIPT_STYLES.get(data.get("script_style", ""), {}).get("name", "")
        config.mood = data.get("mood", "")
        config.custom_requirements = data.get("custom_requirements", "")
        return config
```

---

### Task 1.8：核心框架 — Agent 基类

**Files:**
- Create: `e:\trae\ai\jvben\core\agent_base.py`

- [ ] **Step 1: 创建 Agent 基类**

```python
from typing import Optional
from pathlib import Path
from .style_config import StyleConfig
from .project_manager import ProjectManager
from llm.client import LLMClient


class AgentBase:
    """所有Agent的基类"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def load_prompt_template(self, prompt_file: str) -> str:
        """从 prompts/ 目录加载提示词模板"""
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / prompt_file
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        return self.llm.chat(system_prompt, user_prompt, temperature)

    def get_style_context(self, style: StyleConfig) -> str:
        """生成风格上下文描述，注入到提示词中"""
        return style.to_yaml_string()

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        """子类实现具体逻辑"""
        raise NotImplementedError
```

---

### Task 1.9：主入口文件

**Files:**
- Create: `e:\trae\ai\jvben\main.py`

- [ ] **Step 1: 创建主入口文件**

```python
#!/usr/bin/env python3
"""
多智能体故事创作系统 - 一键启动入口
"""

import sys
import os
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from core.cli import console, print_banner, show_menu, notify_complete, wait_for_approval
from core.project_manager import ProjectManager, get_projects_list
from core.style_config import STORY_TYPES, GENRES, WRITING_STYLES, VISUAL_STYLES, StyleConfig
from core.cli import select_option, multi_select, get_text_input, show_progress
from agents.orchestrator import Orchestrator


def cmd_start():
    """开始一个新的创作项目"""
    console.print("\n[bold]开始新的创作旅程！[/bold]\n")

    # 第1步：选择故事类型
    story_type_id = select_option(
        "📋 请选择故事类型：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in STORY_TYPES.items()]
    )

    # 第2步：选择题材风格
    genre_options = GENRES.get(story_type_id, ["其他"])
    genre_choices = [(str(i+1), g) for i, g in enumerate(genre_options)]
    genre_id = select_option(
        "🎨 请选择题材风格：",
        genre_choices,
        allow_custom=True
    )

    # 第3步：选择文笔风格
    writing_id = select_option(
        "📖 请选择文笔风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in WRITING_STYLES.items()]
    )

    # 第4步：选择视觉/叙事风格
    visual_id = select_option(
        "🎬 请选择视觉/叙事风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in VISUAL_STYLES.items()]
    )

    # 第5步：选择画面比例
    from core.style_config import SCREEN_ASPECTS
    screen_id = select_option(
        "📏 请选择画面比例：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in SCREEN_ASPECTS.items()]
    )

    # 第6步：选择剧本写作风格
    from core.style_config import SCRIPT_STYLES
    script_id = select_option(
        "🎭 请选择剧本写作风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in SCRIPT_STYLES.items()]
    )

    # 第7步：收集创意描述
    console.print("\n[bold yellow]📝 请描述你想讲的故事（一句话或一段话）：[/bold yellow]")
    story_idea = input().strip()

    # 第8步：额外要求
    console.print("\n[bold yellow]📋 还有其他要求吗？（如参考作品、情绪基调、篇幅等，没有则输入 /skip）[/bold yellow]")
    extra_req = input().strip()

    # 构建风格配置
    style = StyleConfig()
    style.story_type = story_type_id
    style.genre = genre_id if not genre_id.isdigit() else genre_options[int(genre_id)-1]
    style.writing_style = writing_id
    style.visual_style = visual_id
    style.screen_aspect = screen_id
    style.script_style = script_id
    style.mood = ""
    style.custom_requirements = extra_req if extra_req != "/skip" else ""

    # 创建项目
    project_name = input("\n[bold yellow]给这个项目起个名字：[/bold yellow]").strip()
    if not project_name:
        project_name = "untitled"
    project = ProjectManager(project_name)

    # 保存任务指令
    task_content = f"""# 创作任务

## 故事类型
{STORY_TYPES[story_type_id]['name']}

## 题材风格
{style.genre}

## 文笔风格
{WRITING_STYLES[writing_id]['name']}

## 视觉/叙事风格
{VISUAL_STYLES[visual_id]['name']}

## 画面比例
{SCREEN_ASPECTS[screen_id]['name']}

## 剧本写作风格
{SCRIPT_STYLES[script_id]['name']}

## 故事描述
{story_idea}

## 额外要求
{style.custom_requirements if style.custom_requirements else "无"}
"""
    project.write_output("00_任务指令.md", task_content)
    project.save_config()

    console.print(f"\n[bold green]✅ 项目「{project_name}」已创建！[/bold green]")

    # 启动总指挥官
    orchestrator = Orchestrator()
    orchestrator.run(project, style)


def cmd_list():
    """查看已有项目"""
    projects = get_projects_list()
    if not projects:
        console.print("[yellow]暂无项目[/yellow]")
        return

    console.print("\n[bold]已有项目：[/bold]")
    for i, p in enumerate(projects, 1):
        phases_done = sum(1 for ph in p["phases"] if ph["done"])
        total_phases = len(p["phases"])
        console.print(f"  {i}. {p['name']} - [{phases_done}/{total_phases}] {p['status']}")
        console.print(f"     创建时间: {p['created_at']}")


def cmd_help():
    """显示帮助"""
    help_text = """
[bold]可用命令：[/bold]
  /start    开始新的创作
  /list     查看已有项目
  /continue 继续未完成的项目
  /help     显示本帮助
  /exit     退出系统

[bold]创作流程：[/bold]
  1. 选择故事类型 → 2. 选择风格 → 3. 描述创意
  4. 大纲设计师生成大纲 → 5. 你审核
  6. 剧情展开师展开剧情 → 7. 你审核
  8. 分镜师设计分镜 → 9. 你审核
  10. 提示词工程师写提示词 → 11. 你审核
  12. 视频生成（可选）
    """
    console.print(help_text)


def main():
    """主循环"""
    print_banner()

    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("CLAUDE_API_KEY"):
        console.print("[red]⚠️ 未检测到 API Key！[/red]")
        console.print("请复制 [cyan].env.example[/cyan] 为 [cyan].env[/cyan]，填入你的 API Key 后重试")
        return

    while True:
        cmd = show_menu()

        if cmd == "/start":
            cmd_start()
        elif cmd == "/list":
            cmd_list()
        elif cmd == "/help":
            cmd_help()
        elif cmd == "/exit":
            console.print("[cyan]再见！[/cyan]")
            break
        else:
            console.print("[red]未知命令，输入 /help 查看帮助[/red]")


if __name__ == "__main__":
    main()
```

---

### Task 1.10：总指挥官 Agent（工作流驱动版）

**Files:**
- Create: `e:\trae\ai\jvben\agents\orchestrator.py`

- [ ] **Step 1: 创建总指挥官**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES
from core.workflow_loader import WorkflowLoader
from core.cli import console, notify_complete, wait_for_approval, show_progress


class Orchestrator(AgentBase):
    """
    总指挥官（Orchestrator）
    职责：读取工作流配置 → 按顺序执行Agent → 协调审核
    扩展：修改 workflow.yaml 即可调整流水线，无需改代码
    """

    def run(self, project: ProjectManager, style: StyleConfig):
        console.print(f"\n[bold cyan]🧠 总指挥官启动[/bold cyan]")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        console.print(f"项目: {project.name} | 类型: {story_type_name}")

        # 加载工作流配置
        phases = WorkflowLoader.load()
        total = len(phases)

        for idx, phase in enumerate(phases):
            # 判断此阶段是否应该执行
            if not phase.should_run(style.story_type):
                console.print(f"[dim]⏭️ 跳过 [{phase.name}]（当前故事类型不适用）[/dim]")
                continue

            show_progress(f"阶段{idx+1}/{total}：{phase.name}", idx / total)

            if phase.agent == "outline_designer":
                self._run_agent_phase(
                    project, style, "outline_designer",
                    phase, idx, input_source=None
                )
            elif phase.agent == "plot_expander":
                self._run_agent_phase(
                    project, style, "plot_expander",
                    phase, idx, input_source="01_故事大纲.md"
                )
            elif phase.agent == "storyboarder":
                self._run_agent_phase(
                    project, style, "storyboarder",
                    phase, idx, input_source="02_完整剧情.md"
                )
            elif phase.agent == "prompt_engineer":
                from core.cli import select_option
                platform_id = select_option(
                    "🎯 请选择AI视频生成平台：",
                    [
                        ("1", "Seedance 2.0（推荐 - 人物表情自然）"),
                        ("2", "可灵 Kling（短剧常用，国风效果好）"),
                        ("3", "Runway Gen-3（电影感画面）"),
                        ("4", "Sora（物理模拟强）"),
                    ]
                )
                platform_map = {"1": "Seedance 2.0", "2": "可灵 Kling", "3": "Runway Gen-3", "4": "Sora"}
                selected_platform = platform_map[platform_id]
                console.print(f"[green]选定平台：{selected_platform}[/green]")
                self._run_agent_phase(
                    project, style, "prompt_engineer",
                    phase, idx, input_source="03_分镜脚本.md",
                    extra_kwargs={"platform": selected_platform}
                )

            project.mark_phase_done(idx)

        console.print("\n[bold green]🎉 所有阶段已完成！[/bold green]")

    def _run_agent_phase(
        self,
        project: ProjectManager,
        style: StyleConfig,
        agent_name: str,
        phase,
        phase_index: int,
        input_source: str = None,
        extra_kwargs: dict = None,
    ):
        """通用阶段执行器"""
        import importlib
        module = importlib.import_module(f"agents.{agent_name}")
        agent_class = getattr(module, agent_name.capitalize())
        agent = agent_class(self.llm)

        input_content = ""
        if input_source:
            content = project.read_output(input_source)
            if content is None:
                console.print(f"[red]错误：找不到 {input_source}[/red]")
                return
            input_content = content

        console.print(f"\n[cyan]{phase.name} 正在创作...[/cyan]")
        kwargs = {"project": project, "style": style, "input_content": input_content}
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        result = agent.run(**kwargs)

        # 写入
        path = project.write_output(phase.output, result)
        notify_complete(phase.name, str(path))

        # 审核循环
        if not phase.auto_skip:
            approved, feedback = wait_for_approval()
            iterations = 0
            while not approved and iterations < 5:
                if feedback:
                    feedback_kwargs = dict(kwargs)
                    feedback_kwargs["input_content"] = input_content + "\n\n## 修改意见\n" + feedback
                    result = agent.run(**feedback_kwargs)
                    path = project.write_output(phase.output, result)
                    notify_complete(f"{phase.name}（已修改）", str(path))
                    approved, feedback = wait_for_approval()
                    iterations += 1
                else:
                    approved = True
---

## Phase 2：大纲设计师 Agent

### Task 2.1：创建大纲设计师提示词模板

**Files:**
- Create: `e:\trae\ai\jvben\prompts\outline_designer.txt`

- [ ] **Step 1: 创建提示词模板**

```text
你是一位专业的故事大纲设计师。你的任务是根据用户的创意，生成一个完整、结构清晰的故事大纲。

## 你的工作原则
1. 结构完整：包含故事定位、人物设定、世界观、故事结构、关键情节点
2. 人物立体：每个角色都要有动机、弧光，不能脸谱化
3. 逻辑自洽：故事的内在逻辑必须通顺，不能有硬伤
4. 适配类型：根据不同类型适配不同的结构模板

## 当前项目的风格配置
{style_config}

## 输出格式
请严格按照以下Markdown格式输出：

# 《故事标题》- {story_type}大纲
> 风格标签：{writing_style} + {visual_style}

## 一、故事定位
- 类型：{story_type}
- 风格：{genre}
- 情绪基调：{mood}
- 一句话梗概：（30字以内）

## 二、人物设定
（主角、关键配角、反派/阻力的详细设定）

## 三、世界/背景设定
（时代时空、核心设定）

## 四、故事结构
（根据类型适配结构模板）

## 五、关键情节点
（钩子、转折、高潮、结局）
```

- [ ] **Step 2: 创建大纲设计师 Agent**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES, WRITING_STYLES, VISUAL_STYLES


class OutlineDesigner(AgentBase):
    """大纲设计师Agent"""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        template = self.load_prompt_template("outline_designer.txt")

        # 获取项目中的任务指令
        task = project.read_output("00_任务指令.md") or input_content

        # 构建风格上下文
        style_context = self.get_style_context(style)

        # 获取风格名称
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未指定")
        genre_name = style.genre if style.genre else "未指定"

        # 填充模板
        system_prompt = template.format(
            style_config=style_context,
            story_type=story_type_name,
            writing_style=writing_style_name,
            visual_style=visual_style_name,
            genre=genre_name,
            mood=style.mood if style.mood else "未指定",
        )

        # 用户输入 = 创意描述 + 修改意见（如果有）
        user_prompt = f"## 用户创意\n{task}\n"
        if input_content and "修改意见" in input_content:
            user_prompt += f"\n## 修改意见\n{input_content}\n"

        return self.call_llm(system_prompt, user_prompt, temperature=0.8)
```

---

## Phase 3：剧情展开师 Agent

### Task 3.1：创建剧情展开师提示词模板

**Files:**
- Create: `e:\trae\ai\jvben\prompts\plot_expander.txt`

- [ ] **Step 1: 创建提示词模板**

```text
你是一位专业的剧本创作大师。你的核心能力是：把故事大纲中的
骨架和人物，转化为有血有肉、画面感强、人物鲜活的完整剧本。

【核心原则】
1. 整体连贯流畅——集与集之间、场与场之间要有自然的衔接和过渡
2. 避免长对话导致混乱——对白超过5句时，中间必须插入动作/反应描写
3. 人物刻画细致——每个角色说话方式、用词习惯、肢体语言都要与众不同
4. 情绪要看得见——不要"她很伤心"，而要"她眼眶泛红，喉结滚了一下"

【人物刻画方式】
采用混合式：动作描写为主 + 关键情绪括号标注
- 动作描写让读者"看到"角色的状态
- 括号标注让AI/演员准确理解情绪

【写作风格适配】
当前剧本写作风格为 "{script_style}"：
- 视觉化写作：动作描写先行，对白精炼，"show don't tell"
- 对白驱动型：对白主导剧情，动作描写简洁
- 文学剧本型：细腻动作/心理描写 + 对白，文体接近文学

【画面比例适配】
当前画面比例为 "{screen_aspect}"：
- 9:16竖屏：偏人物近景、纵深描写、上半身动作
- 16:9横屏：偏环境关系、左右调度、全身动作

【文笔风格适配】
当前文笔风格为 "{writing_style}"，贯穿始终。

当前风格配置：
{style_config}

## 故事大纲
{outline}

## 输出格式要求
根据故事类型适配格式：

短剧格式：
# 第X集
> 写作风格：{script_style} | 画面比例：{screen_aspect}

### 场景X：地点 · 时间
**时长：约XX秒**

【画面】场景视觉描述

角色名（状态描述）动作描写

          （情绪标注）
"对白"

---

电影格式：
# 第X幕：标题

### 场景X：地点 · 内外景 · 时间

【画面】场景视觉描述
...

小说格式：
# 第X章
（小说体叙述）
```

- [ ] **Step 2: 创建剧情展开师 Agent**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES, WRITING_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES


class PlotExpander(AgentBase):
    """剧情展开师Agent"""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        template = self.load_prompt_template("plot_expander.txt")

        outline = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            outline = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        style_context = self.get_style_context(style)

        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")

        system_prompt = template.format(
            style_config=style_context,
            outline=outline,
            feedback=feedback,
            writing_style=writing_style_name,
            script_style=script_style_name,
            screen_aspect=screen_aspect_name,
        )

        return self.call_llm(system_prompt, "", temperature=0.8)
```

---

## Phase 4：分镜师 + 提示词工程师

### Task 4.1：创建分镜师提示词模板

**Files:**
- Create: `e:\trae\ai\jvben\prompts\storyboarder.txt`

- [ ] **Step 1: 创建提示词模板**

```text
你是一位专业的影视分镜师。你的核心能力是：把剧本中的文字描述，
转化为精确的镜头语言，让AI视频模型能准确理解每个镜头怎么拍。

【核心原则】
1. 每个镜头必须包含完整信息：景别、运镜、视角、焦点、机位、构图、光影、情绪
2. 保持人物/场景/服装在镜头间的一致性，不能出现跳跃
3. 相邻镜头遵循景别递进法则（不跳级），除非刻意制造冲击
4. 对话场景遵循180度轴线法则，保证人物视线方向一致
5. 每个镜头标注明确的「衔接」指向下一个镜头

【场景连续性机制 - 必须执行以下步骤】
步骤1 - 读取场景参考库：
   找到当前场景的场景参考文件，
   读取其中的「固定地标链」和「机位-描述映射表」
步骤2 - 继承状态链：
   上一个镜头的「状态→」就是当前镜头的初始状态
步骤3 - 标注机位代号：
   每个镜头标注机位代号（A/B/C/D/E位），
   不同镜头可以切换机位，
   但切换时必须保证地标链中的空间关系不变
步骤4 - 记录结束状态：
   每个镜头记录「状态→」供下个镜头继承
步骤5 - 判断版本升级：
   如果发生结构性破坏（坍塌/爆炸/火灾），
   标记为场景版本升级，重置状态链

【固定地标链规则】
每个镜头的画面描述中必须重复场景的固定地标信息

【输出格式】
每集输出一个md文件，每个镜头包含表格格式。
标注状态链和场景版本号。

当前视觉风格：{visual_style}
当前画面比例：{screen_aspect}
当前风格配置：
{style_config}
```

- [ ] **Step 2: 创建分镜师 Agent** (agents/storyboarder.py)

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, SCREEN_ASPECTS


class Storyboarder(AgentBase):
    """分镜师Agent"""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        template = self.load_prompt_template("storyboarder.txt")

        full_plot = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            full_plot = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未指定")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
        style_context = self.get_style_context(style)

        system_prompt = template.format(
            visual_style=visual_style_name,
            screen_aspect=screen_aspect_name,
            style_config=style_context,
            full_plot=full_plot,
            feedback=feedback,
        )

        return self.call_llm(system_prompt, "", temperature=0.7)
```

### Task 4.2：创建提示词工程师提示词模板

**Files:**
- Create: `e:\trae\ai\jvben\prompts\prompt_engineer.txt`

- [ ] **Step 1: 创建提示词模板**

```text
你是一位专业的AI视频提示词工程师。你的核心能力是：把分镜脚本
转化为精确的AI视频模型提示词，让每个镜头都能稳定生成。

【核心工作流程】
对于每个镜头，你必须按以下顺序组装提示词：

步骤1 - 建立人物追踪链
  扫描本集所有镜头，确定每个角色在每场戏的
  服装、发型、妆容，形成人物状态变更表。
  同一场戏内人物外观不得变化。

步骤2 - 加载场景参考
  根据分镜中的场景名称和版本号，找到场景参考文件
  提取「固定地标链」信息

步骤3 - 确定机位描述
  根据分镜中的机位代号（A/B/C/D/E），
  从场景参考的「机位-描述映射表」中找到对应描述

步骤4 - 继承状态链
  读取上一个镜头的结束状态，作为当前镜头的初始状态

步骤5 - 读取人物状态
  根据人物追踪链，确定当前角色在本镜头的服装/发型/妆容

步骤6 - 组合最终提示词
  按照六大模块顺序拼接：
  [固定地标链] + [当前状态] + [人物描述] + [机位描述] + [动作/表情] + [画质关键词]

步骤7 - 适配目标平台
  根据目标平台调整语言风格和长度

步骤8 - 记录结束状态
  根据当前镜头的动作，推断并记录：
  - 场景状态变化（供下个镜头继承）
  - 人物状态变化（如有服装/妆容变化）

【固定地标链规则（关键！）】
每条提示词必须包含场景的完整固定地标链，格式固定：
"场景名，左侧：XXX，中央：XXX，右侧：XXX，后方：XXX"
绝对不能省略！

【人物一致性规则】
1. 同一场戏内，同一角色的服装/发型/妆容必须完全一致
2. 换装必须在分镜中明确标注，否则视为不变
3. 人物描述格式固定：角色名（服装，发型，妆容）
4. 每个镜头提示词必须包含人物描述

【平台适配】
当前视觉风格：{visual_style}
当前风格配置：
{style_config}

## 分镜脚本
{storyboard}

## 修改意见（如有）
{feedback}

## 输出格式
### 镜头XXX - {platform}提示词
（适配目标平台的提示词，包含固定地标链+人物描述+状态链）

### 镜头XXX - 状态→
记录本镜头的结束状态，供下个镜头继承
```

- [ ] **Step 2: 创建提示词工程师 Agent** (agents/prompt_engineer.py)

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES


class PromptEngineer(AgentBase):
    """提示词工程师Agent"""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str, platform: str = "Seedance 2.0") -> str:
        template = self.load_prompt_template("prompt_engineer.txt")

        storyboard = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            storyboard = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未指定")
        style_context = self.get_style_context(style)

        system_prompt = template.format(
            visual_style=visual_style_name,
            style_config=style_context,
            storyboard=storyboard,
            feedback=feedback,
            platform=platform,
        )

        return self.call_llm(system_prompt, "", temperature=0.7)
```

---

## Phase 5：工具系统层（扩展能力）

### Task 5.1：文件操作工具

**Files:**
- Create: `e:\trae\ai\jvben\tools\file_ops.py`

- [ ] **Step 1: 创建文件操作工具**

```python
import shutil
from pathlib import Path
from typing import List, Optional


def create_directory(path: Path) -> Path:
    """创建目录（如果不存在）"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file(src: Path, dst: Path):
    """复制文件"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """列出目录中的文件"""
    if not directory.exists():
        return []
    return list(directory.glob(pattern))


def read_file(file_path: Path) -> Optional[str]:
    """读取文件内容"""
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def write_file(file_path: Path, content: str):
    """写入文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def backup_file(file_path: Path) -> Optional[Path]:
    """备份文件（添加 .bak 后缀）"""
    if file_path.exists():
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup)
        return backup
    return None
```

### Task 5.2：浏览器操控工具（预留）

**Files:**
- Create: `e:\trae\ai\jvben\tools\browser.py`

- [ ] **Step 1: 创建浏览器操控模块（骨架）**

```python
"""
浏览器操控模块
用于自动操作AI视频生成网站（如Seedance Web版）
当前为骨架实现，后续阶段完善
"""


class BrowserController:
    """浏览器控制器"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None

    async def start(self):
        """启动浏览器"""
        # from playwright.async_api import async_playwright
        # async with async_playwright() as p:
        #     self.browser = await p.chromium.launch(headless=self.headless)
        #     self.page = await self.browser.new_page()
        raise NotImplementedError("浏览器操控模块将在后续阶段实现")

    async def navigate(self, url: str):
        """导航到URL"""
        raise NotImplementedError

    async def upload_file(self, file_path: str, selector: str):
        """上传文件到指定选择器"""
        raise NotImplementedError

    async def screenshot(self, file_path: str):
        """截图"""
        raise NotImplementedError

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
```

### Task 5.3：API 调用工具

**Files:**
- Create: `e:\trae\ai\jvben\tools\api_caller.py`

- [ ] **Step 1: 创建API调用工具**

```python
import os
import requests
from typing import Optional, Dict


class APICaller:
    """统一的API调用封装"""

    @staticmethod
    def call_seedance(prompt: str, api_key: Optional[str] = None) -> Dict:
        """
        调用 Seedance API 生成视频
        实际实现需要根据Seedance官方API文档调整
        """
        key = api_key or os.getenv("SEEDANCE_API_KEY")
        if not key:
            raise ValueError("缺少 Seedance API Key")

        # 占位：实际API端点需要查阅Seedance官方文档
        url = "https://api.seedance.com/v1/video/generate"
        headers = {"Authorization": f"Bearer {key}"}
        payload = {
            "prompt": prompt,
            "model": "seedance-2.0",
            "duration": 5,
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def check_seedance_status(task_id: str, api_key: Optional[str] = None) -> Dict:
        """查询Seedance任务状态"""
        key = api_key or os.getenv("SEEDANCE_API_KEY")
        url = f"https://api.seedance.com/v1/video/status/{task_id}"
        headers = {"Authorization": f"Bearer {key}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
```

---

## Phase 6：审核门禁完善

### Task 6.1：审核门禁独立模块

**Files:**
- Create (modify): `e:\trae\ai\jvben\core\review_gate.py`

- [ ] **Step 1: 创建独立的审核门禁模块**

```python
from typing import Tuple, Callable
from .cli import notify_complete, wait_for_approval, console


def review_loop(
    stage_name: str,
    file_path: str,
    generate_fn: Callable[[str], str],
    write_fn: Callable[[str], None],
    max_iterations: int = 5,
) -> bool:
    """
    通用审核循环
    - stage_name: 阶段名称（如"故事大纲"）
    - file_path: 产出文件路径（用于显示）
    - generate_fn: 生成函数，接收修改意见，返回新内容
    - write_fn: 写入函数，接收内容并保存
    - max_iterations: 最大修改轮次
    返回是否最终通过
    """
    for iteration in range(max_iterations):
        notify_complete(stage_name, file_path)
        approved, feedback = wait_for_approval()

        if approved:
            console.print(f"[green]✅ {stage_name}已通过审核！[/green]")
            return True

        if not feedback:
            console.print("[yellow]跳过修改，进入下一阶段[/yellow]")
            return True

        console.print(f"[cyan]🔄 第{iteration+1}轮修改中...[/cyan]")
        new_content = generate_fn(feedback)
        write_fn(new_content)

    console.print(f"[red]⚠️ 已达到最大修改次数({max_iterations})，强制进入下一阶段[/red]")
    return True
```

---

## 安装与运行说明

### 首次运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器（后续浏览器操控需要）
playwright install chromium

# 3. 配置 API Key
# 复制 .env.example 为 .env，填入你的 API Key

# 4. 启动系统
python main.py
```

### 移植到另一台电脑

```bash
# 1. 将整个项目文件夹复制到新电脑
# 2. 在新电脑上安装 Python 3.11+
# 3. 运行：
pip install -r requirements.txt
python main.py
```
