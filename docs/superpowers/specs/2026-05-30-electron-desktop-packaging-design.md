# 织镜 — Electron 桌面打包设计

## 目标

将现有 Web 应用（React + Vite + FastAPI）打包为 Windows 桌面软件，用户双击 exe 即可使用，无需安装 Python/Node.js。

## 架构概览

```
┌─────────────────────────────────────┐
│       织镜.exe（Electron 壳）         │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  React 前端（100% 不动现有代码）│  │
│  │  宇宙首页 / 工作台 / 生图/视频  │  │
│  └────────────┬──────────────────┘  │
│               │ HTTP + WebSocket     │
│  ┌────────────▼──────────────────┐  │
│  │ Python FastAPI（PyInstaller）  │  │
│  │ localhost:随机端口             │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

启动流程：
1. 用户双击 `织镜.exe`
2. Electron 主进程随机选一个未被占用的端口
3. 主进程启动内嵌的 `backend.exe`（PyInstaller 打包的 FastAPI）
4. 轮询等待后端就绪后，Electron 窗口加载 `http://localhost:{port}`
5. 窗口关闭时 Electron 自动杀掉 Python 子进程

## 文件部署

### 安装目录（只读，不可改）

```
C:\Program Files\织镜\
├── 织镜.exe          # Electron 入口
├── backend.exe       # PyInstaller 打包的 Python 后端
├── _internal/        # Python 运行时（自动生成）
└── uninstall.exe     # NSIS 卸载程序
```

### 用户数据目录（全部可编辑）

```
%APPDATA%\织镜\
├── .env              # 用户 API Key
├── config/
│   └── image_presets.json
├── prompts/          # Agent prompt 模板（用户可编辑）
│   ├── outline_designer.txt
│   ├── plot_expander.txt
│   ├── screenplay_writer.txt
│   ├── storyboarder.txt
│   ├── video_producer.txt
│   ├── visual_extractor.txt
│   ├── image_artist.txt
│   ├── outline_direction_card.txt
│   ├── outline_full.txt
│   └── prompt_engineer.txt
├── projects/         # 用户创作项目
├── memory/sessions/  # 会话记忆
├── orchestor_router.txt
└── generated/        # 生成的图片/视频
```

初始化逻辑：每次后端启动时检查 AppData 下各目录/文件是否存在，不存在则从内置模板复制。用户删除后重启自动恢复默认。

## 打包工具链

| 环节 | 工具 | 说明 |
|------|------|------|
| Python 打包 | PyInstaller | `server/app.py` + 所有 py 依赖 → `backend.exe` |
| 前端构建 | Vite | 现有流程，`npm run build` → `dist/` |
| Electron 打包 | electron-builder + NSIS | 整合 dist + backend.exe + 资源文件 |

最终产物：`release/织镜-Setup-1.0.0.exe`（NSIS 安装向导）

## 新增文件清单

| 文件 | 用途 | 预估行数 |
|------|------|----------|
| `electron/main.js` | Electron 主进程：端口选择、启后端、开窗口、杀子进程 | ~80 |
| `electron/preload.js` | 预加载脚本 | ~15 |
| `electron-builder.yml` | 打包配置：图标、NSIS、文件列表 | ~40 |
| `assets/icon.ico` | 软件图标（需用户提供或生成） | - |
| `pyinstaller.spec` | PyInstaller 配置 | ~30 |

## 现有文件改动

| 文件 | 改动 | 影响 |
|------|------|------|
| `package.json` | 加 `main`、`scripts.package`、electron 依赖 | 3处 |
| `server/app.py` | 加启动时复制默认文件到 AppData | ~25行 |
| `vite.config.ts` | 加 `base: './'` 兼容 Electron file:// | 1行 |
| `.gitignore` | 加 `release/` `dist-electron/` | 2行 |

## 不碰的部分

- 所有 `agents/`、`core/`、`tools/`、`llm/` Python 代码
- 所有 `src/` 前端代码
- 所有 `prompts/` 模板文件
- `requirements.txt`
- `run_web.py`、`setup_env.py`、`main.py`（保留，CLI 模式仍可用）

## 后期 macOS 扩展

- PyInstaller 同配置可出 macOS 可执行文件
- electron-builder 改 `target: [dmg]` 即可出 macOS 安装包
- `electron/main.js` 中启后端的命令需要区分平台，改动 <10 行
