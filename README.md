# AI 故事创作系统

AI 驱动的故事创作流水线：从故事大纲 → 完整剧情 → 完整剧本 → 分镜脚本 → 视频提示词，全自动生成。

## 项目结构

```
├── agents/              # AI Agent 定义（每个阶段一个 Agent）
│   ├── outline_designer.py   # 故事大纲
│   ├── plot_expander.py      # 完整剧情
│   ├── screenplay_writer.py  # 完整剧本
│   ├── storyboarder.py       # 分镜脚本
│   └── prompt_engineer.py    # 视频提示词
├── core/                # 核心模块
│   ├── style_config.py       # 风格配置
│   ├── project_manager.py    # 项目管理
│   └── workflow_loader.py    # 工作流加载
├── server/              # Web 后端（FastAPI + WebSocket）
│   ├── app.py                # FastAPI 入口
│   ├── async_orch.py         # 异步编排器
│   ├── ws_manager.py         # WebSocket 管理
│   └── routes/               # API 路由
├── src/                 # Web 前端（React + Vite + TypeScript）
│   ├── pages/
│   │   ├── HomePage.tsx           # 首页
│   │   ├── NewProjectWizard.tsx   # 创建项目向导
│   │   └── Workspace.tsx          # 工作区
│   └── lib/api.ts
├── llm/                 # LLM 客户端
│   └── backends.py            # OpenAI / Claude / DeepSeek
├── prompts/             # AI Agent 的 prompt 模板
├── projects/            # 项目数据（自动生成）
├── workflow.yaml        # 工作流配置（增删阶段只需改此文件）
├── requirements.txt     # Python 依赖
├── package.json         # 前端依赖
└── .env                 # 环境变量
```

## 快速启动

### 1. 安装依赖

```bash
# Python 后端
pip install -r requirements.txt

# 前端（需要 Node.js 18+）
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API Key（至少配一个 LLM 后端）：

```env
# LLM 后端选择: openai / claude / deepseek
LLM_BACKEND=deepseek

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_MODEL=deepseek-chat

# OpenAI（可选）
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4o

# Claude（可选）
CLAUDE_API_KEY=sk-xxxxx
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### 3. 启动

开两个终端：

```bash
# 终端 1：启动后端（端口 8000）
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000

# 终端 2：启动前端（端口 5173）
npx vite --host 0.0.0.0 --port 5173
```

浏览器打开 `http://localhost:5173` 即可使用。

### 一键启动（Windows）

双击 `启动系统.bat` 会自动启动后端和前端。

## 工作流配置

`workflow.yaml` 定义了流水线的阶段和执行条件，直接修改即可增删阶段，无需改代码。

```yaml
phases:
  - name: 故事大纲
    agent: outline_designer
    condition: true              # 总是执行
    split: false                 # 不分幕

  - name: 完整剧情
    agent: plot_expander
    condition: true
    split: true                  # 分幕输出

  - name: 完整剧本
    agent: screenplay_writer
    condition: true
    split: true

  - name: 分镜设计
    agent: storyboarder
    condition: "story_type in ['1', '2', '3']"  # 仅短剧/电影/电视剧
    split: true

  - name: 视频提示词
    agent: prompt_engineer
    condition: "story_type in ['1', '2', '3']"
    split: true
```

## 项目状态

项目数据存储在 `projects/<项目名>/` 目录下：

```
projects/我的项目/
├── project_config.json   # 配置 + 阶段状态
├── 00_任务指令/           # 指令
├── 01_故事大纲/           # 故事大纲输出
├── 02_完整剧情/           # 完整剧情（含分幕）
├── 03_完整剧本/           # 完整剧本（含分幕）
├── 04_分镜脚本/           # 分镜脚本（含分幕）
└── 05_提示词/             # 视频提示词（含分幕）
```

## API 概览

| 路径 | 方法 | 用途 |
|:-----|:-----|:------|
| `/api/projects` | GET | 项目列表 |
| `/api/projects/{name}` | GET | 项目详情 |
| `/api/projects/{name}/{phase}/content` | GET | 阶段内容 |
| `/api/projects` | POST | 创建项目 |
| `/api/projects/random-idea` | POST | 随机生成故事创意 |
| `/api/projects/{name}/delete` | DELETE | 删除项目 |
| `/api/ws/create/{name}` | WebSocket | 实时生成（流式输出 + 审批/版本选择） |
