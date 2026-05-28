# 🎬 Story Forge — 多智能体故事创作系统

**输入一个故事想法 → 产出完整剧本 + 角色设定图 + 分镜脚本 + AI 视频提示词 → 一键导出 Word**

---

## ✨ 功能亮点

- 🤖 **六 Agent 协作流水线**：大纲 → 剧情 → 剧本 → 视觉提取 → 分镜 → 生图提示词，全流程自动串联
- 📡 **WebSocket 实时流**：token 逐字推前端，非 HTTP 轮询，生成进度实时可见
- 🎛️ **人机协同审核**：每个阶段 AI 生成后进入审核面板——确认、修改或重新生成，质量可控
- 🎨 **AI 生图系统**：自由模式 + 项目模式（自动提取角色/场景），同角色跨模型保持一致
- 🎥 **多后端视频生成**：Kling / Runway / Pika / Luma / Seedance 五家集成，自动路由
- 📄 **Word 导出**：纯 Python 正则渲染，零第三方依赖，支持汇总 / 分集 / 单文件三种模式
- ⭐ **星图全景项目浏览器**：Three.js 3D 宇宙背景，可视化浏览所有创作项目

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────┐
│          React 19 + TypeScript       │  ← 前端
│   Three.js 星图 · Tailwind CSS       │
├─────────────────────────────────────┤
│            WebSocket (ws://)         │  ← 实时通信
├─────────────────────────────────────┤
│        Python FastAPI                │  ← 后端
│   异步编排 · 审核循环 · 分块生成      │
├─────────────────────────────────────┤
│  六个 AI Agent · Prompt 模板         │  ← Agent 层
├─────────────────────────────────────┤
│  DeepSeek · OpenAI · Kling · Runway  │  ← AI 后端
│  Pika · Luma · Seedance · Seedream   │
└─────────────────────────────────────┘
```

---

## 🚀 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt    # Python 后端
npm install                        # 前端（需要 Node.js 18+）
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API Key：

```env
LLM_BACKEND=deepseek
DEEPSEEK_API_KEY=sk-xxxxx
OPENAI_API_KEY=sk-xxxxx        # 可选
CLAUDE_API_KEY=sk-xxxxx        # 可选
AGGREGATED_API_KEY=sk-xxxxx    # 聚合平台（生图/视频）
```

### 3. 启动

```bash
# Windows：双击 run_web.py
python run_web.py

# macOS / Linux
python run_web.py
```

浏览器打开 `http://localhost:8000`。

---

## 🧭 Agent 流水线

```
任务指令 → 故事大纲 → 完整剧情 → 完整剧本 → 视觉提取 → 分镜设计 → 生图/视频提示词
```

每个阶段三步：**AI 生成 → 审核 → 保存**。通过后才进入下一阶段。

---

## 📁 项目结构

```
├── agents/            # AI Agent 定义
├── core/              # 核心模块（风格配置、项目管理、工作流）
├── server/            # FastAPI + WebSocket 后端
│   └── routes/        # API 路由
├── tools/             # 图像/视频 AI 后端接入
├── src/               # React 前端
│   └── pages/         # 页面组件
├── prompts/           # Agent prompt 模板
├── projects/          # 用户项目数据
├── run_web.py         # 一键启动脚本
└── .env.example       # 环境变量模板
```

---

## 🔌 支持的 AI 后端

| 类型 | 后端 | 识别规则 |
|------|------|---------|
| LLM 文本 | DeepSeek / OpenAI / Claude | `.env` 配置 |
| 图像生成 | OpenAI Compatible / Seedream | 模型名识别 |
| 视频生成 | Kling / Runway / Pika / Luma / Seedance | 自动路由 |

---

## 🙋‍♂️ 关于本项目

独立开发，一个月交付。我借助 AI 编程助手完成代码实现，自身负责产品方向决策、架构设计、Prompt 工程和全流程测试验收。

---

## 📄 License

MIT — 欢迎学习、引用、提 PR。
