# Web 版多智能体故事创作系统 — 设计文档

> 2026-05-15 | 将现有 CLI 版"多智能体故事创作系统 v1.0"改造为 Web 网页版

## 一、背景与目标

### 背景
现有一个基于 Python CLI (Rich 终端 UI) 的多智能体故事创作系统，支持 6 种故事类型、6 阶段自动创作流水线（大纲→剧情→剧本→分镜→提示词→视频）。用户通过命令行交互使用，产出为 Markdown 文件。

### 目标
在不修改现有 Agent 核心逻辑的前提下，新增 Web 前端界面，实现：
- 浏览器中完成所有创作操作
- 流式展示 AI 生成过程
- 进度条反馈阶段状态
- 离开页面后异步通知完成
- 图形化配置 LLM API Key

---

## 二、技术选型

### 后端
| 项目 | 选择 | 原因 |
|------|------|------|
| Web 框架 | **FastAPI** | 原生支持 WebSocket/SSE，适合流式场景；Python 生态兼容现有代码 |
| 异步运行 | **asyncio + FastAPI** | 现有 Agent 调用 LLM 是同步阻塞的，需要在后台线程池执行，通过 WebSocket 推送结果 |
| 存储 | **文件系统 + JSON** | 继续复用现有 ProjectManager，不引入数据库 |

### 前端
| 项目 | 选择 | 原因 |
|------|------|------|
| 框架 | **React 18 + TypeScript** | 生态成熟，shadcn/ui 组件丰富 |
| UI 组件库 | **shadcn/ui** | 基于 Tailwind + Radix，现代美观，项目内已有该 skill 支持 |
| 路由 | **React Router v6** | 标准方案 |
| Markdown 渲染 | **react-markdown + remark-gfm** | 渲染 Agent 产出的 Markdown |
| 流式接入 | **WebSocket API** | 浏览器原生支持，实时推送 |

### 部署
- **开发**：Vite 开发服务器 (前端) + FastAPI uvicorn (后端)
- **生产**：FastAPI 同时 serve 前端静态文件（构建产物），单进程部署

---

## 三、项目结构

```
创作系统/
└── 故事创作系统/
    ├── agents/              # 【不动】现有 Agent 代码
    ├── core/                # 【不动】项目管理、风格配置等
    ├── llm/                 # 【不动】LLM 客户端
    ├── tools/               # 【不动】工具模块
    ├── prompts/             # 【不动】提示词模板
    ├── projects/            # 【不动】用户项目数据
    ├── .pkg/                # 【已有】本地依赖包
    ├── .env                 # 【已有】LLM 配置
    ├── server/              # 【新增】FastAPI 后端
    │   ├── __init__.py
    │   ├── app.py           # FastAPI 实例，挂载路由
    │   ├── routes/
    │   │   ├── projects.py  # 项目管理 REST API
    │   │   ├── creation.py  # 创作流程 REST + WebSocket
    │   │   └── settings.py  # 设置页 REST API
    │   ├── ws_manager.py    # WebSocket 连接管理
    │   ├── async_orch.py    # Orchestrator 异步包装器
    │   └── schemas.py       # Pydantic 数据模型
    ├── web/                 # 【新增】React 前端
    │   ├── package.json
    │   ├── vite.config.ts
    │   ├── index.html
    │   ├── src/
    │   │   ├── main.tsx
    │   │   ├── App.tsx
    │   │   ├── pages/
    │   │   │   ├── HomePage.tsx       # 项目广场
    │   │   │   ├── NewProjectWizard.tsx # 新建向导
    │   │   │   ├── Workspace.tsx      # 创作工作台
    │   │   │   └── SettingsPage.tsx   # 设置页
    │   │   ├── components/
    │   │   │   ├── ProjectCard.tsx
    │   │   │   ├── PhaseSidebar.tsx
    │   │   │   ├── ContentViewer.tsx
    │   │   │   ├── ReviewBar.tsx
    │   │   │   ├── StreamOutput.tsx
    │   │   │   └── ProgressIndicator.tsx
    │   │   ├── hooks/
    │   │   │   ├── useWebSocket.ts
    │   │   │   └── useNotification.ts
    │   │   ├── lib/
    │   │   │   └── api.ts
    │   │   └── types/
    │   │       └── index.ts
    │   └── public/
    └── run_web.py            # 启动脚本（一件启动前后端）
```

---

## 四、后端 API 设计

### 4.1 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 获取所有项目列表 |
| GET | `/api/projects/{name}` | 获取项目详情（配置+阶段状态） |
| GET | `/api/projects/{name}/{phase}/content` | 获取某阶段产出内容 |
| POST | `/api/projects` | 创建新项目 |
| DELETE | `/api/projects/{name}` | 删除项目 |
| GET | `/api/settings` | 获取当前配置（脱敏） |
| PUT | `/api/settings` | 更新配置（写入 .env） |
| POST | `/api/settings/test-llm` | 测试 LLM 连接 |

### 4.2 WebSocket 端点

| 端点 | 说明 |
|------|------|
| `ws://host/api/ws/create/{project_name}` | 创作流程 WebSocket |

**消息协议（JSON）：**

```
客户端 → 服务端:
  { "action": "start", "project": "...", "style": {...} }
  { "action": "approve", "phase_index": 0 }
  { "action": "revise", "phase_index": 0, "feedback": "修改意见..." }
  { "action": "reject", "phase_index": 0, "reason": "..." }
  { "action": "skip", "phase_index": 3 }

服务端 → 客户端:
  { "type": "phase_start", "phase_index": 0, "phase_name": "故事大纲" }
  { "type": "stream", "phase_index": 0, "chunk": "## 故事大纲\n..." }
  { "type": "phase_complete", "phase_index": 0, "file_path": "01_故事大纲/故事大纲.md" }
  { "type": "progress", "current": 2, "total": 6 }
  { "type": "error", "message": "..." }
  { "type": "all_complete" }
  { "type": "notification", "phase_index": 0, "message": "大纲已生成，请审核" }
```

### 4.3 流式生成实现

1. DeepSeek API 本身支持 `stream: true`，后端透传 SSE chunk
2. 后端通过 `llm/backends.py` 的 DeepSeekBackend 调用时开启流式
3. 每个 chunk 通过 WebSocket 推送到前端
4. 前端实时追加渲染 Markdown

---

## 五、前端页面设计

### 5.1 项目广场（HomePage）
- 顶部：Logo + "多智能体故事创作系统" + 设置入口 ⚙️
- 中部：项目卡片网格
  - 每张卡片显示：项目名、故事类型、进度条（x/6）、最近修改时间
  - 点击进入创作工作台
- 右下角：FAB "+" 新建按钮

### 5.2 新建项目向导（NewProjectWizard）
- 4 个步骤，顶部 Steps 指示器
- 每步选完后 "下一步" → 最后一步 "创建项目" → 跳转至创作工作台

### 5.3 创作工作台（Workspace）
- **左侧 sidebar**：6 个阶段节点，显示完成/进行中/待开始状态
- **右侧主区域**：
  - 生成中：流式文本区（等宽 Markdown 渲染）+ 底部脉冲进度条
  - 生成完成：Markdown 预览 + 底部审核栏
- **审核栏**：✅ 通过 | ✏️ 修改（弹出输入框）| ↩️ 退回
- **离线通知**：如果生成过程中离开页面，再次回来时从项目状态判断是否完成，并提示

### 5.4 设置页（SettingsPage）
- LLM 后端下拉选择（DeepSeek / OpenAI / Claude）
- API Key 输入框（密码遮罩）
- 模型输入框
- "测试连接" 按钮
- 视频平台 API Key
- 保存按钮

---

## 六、数据流

```
用户点击"开始创作"
  → 前端 WS.send({ action: "start", project: "...", style: {...} })
  → 后端启动 Orchestrator（后台线程池）
  → 遍历 6 个 phase：
      → WS.send({ type: "phase_start" })
      → Agent.run() 流式调用 LLM
      → 每个 chunk: WS.send({ type: "stream", chunk: "..." })
      → 完成后: WS.send({ type: "phase_complete" })
      → 等待用户审核（WS 接收 approve/revise/reject）
      → 如果 approve → 继续下一阶段
      → 如果 revise → 用修改意见重新调用 Agent
      → 如果 reject → 退回上一阶段
  → 全部完成: WS.send({ type: "all_complete" })
```

---

## 七、兼容性说明

| 现有模块 | 改动 |
|----------|------|
| `agents/*` | **不改**，只通过 async_orch.py 在线程池中调用 |
| `core/project_manager.py` | **不加锁的读写**（单用户不存在并发问题） |
| `core/style_config.py` | **不改** |
| `llm/client.py` + `backends.py` | 新增 `chat_stream()` 方法支持流式返回 |
| `core/cli.py` | **不在 Web 版使用**，保留给 CLI |
| `workflow.yaml` | **不改** |
| `projects/` 目录 | **不改**，Web 和 CLI 共用同一套项目数据 |

---

## 八、启动方式

```bash
# 一件安装+启动
cd 故事创作系统
python run_web.py
# 自动: 安装前端依赖 → 构建前端 → 启动 FastAPI → 浏览器打开 http://localhost:8000
```

---

## 九、技术要点与风险

| 要点 | 说明 |
|------|------|
| 流式 LLM | DeepSeek API 支持 SSE stream，后端需改造 `backends.py` 让 chat 方法支持 yield chunk |
| WebSocket 保活 | 前端实现心跳 ping/pong，断线自动重连 |
| 长文本分幕 | 剧本和分镜阶段产出长文本，`content_splitter.py` 已有分幕逻辑，前端按幕展示 |
| 无用户系统 | 单用户模式，无需认证；所有 API 无鉴权 |

---

## 十、补充建议

1. **暗色模式**：创作类工具建议默认暗色主题，护眼且更有"创作感"。shadcn/ui 原生支持 dark mode。
2. **Markdown 导出**：每个阶段的 Markdown 内容支持一键复制或下载为 .md 文件。
3. **版本 B 选择**：现有系统大纲阶段生成 A/B 两版，Web 版可用分栏对比展示，选择后自动清理。
