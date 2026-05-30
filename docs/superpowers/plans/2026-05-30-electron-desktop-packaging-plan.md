# 织镜 Electron 桌面打包 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 React + FastAPI Web 应用打包为 Windows NSIS 安装包，用户直接双击 exe 使用。

**Architecture:** Electron 主进程内嵌 PyInstaller 打包的 Python 后端，启动时自动从 AppData 初始化用户可编辑文件（prompts/、config/、.env），通过 electron-builder + NSIS 生成安装器。

**Tech Stack:** Electron 28、electron-builder、NSIS、PyInstaller

---

## 新增/改动文件总览

| 文件 | 操作 | 职责 |
|------|------|------|
| `electron/main.js` | 创建 | Electron 主进程：端口选择、启 backend.exe、开窗口、杀子进程 |
| `electron/preload.js` | 创建 | 预加载脚本 |
| `electron-builder.yml` | 创建 | electron-builder 打包配置 |
| `pyinstaller.spec` | 创建 | PyInstaller 打包配置 |
| `assets/icon.ico` | 创建 | 占位图标（1x1 像素黑色 ico） |
| `package.json` | 修改 | 加 main、scripts、electron 依赖 |
| `vite.config.ts` | 修改 | 加 `base: './'` |
| `server/app.py` | 修改 | 加 AppData 初始化 + 路径切换逻辑 |
| `.gitignore` | 修改 | 加 release/、dist-electron/ |
| `core/project_manager.py` | 修改 | 支持从环境变量读取 PROJECTS_DIR |
| `tsconfig.json` | 修改 | 排除 electron/ 目录 |

---

### Task 1: Electron 主进程

**Files:**
- Create: `electron/main.js`
- Create: `electron/preload.js`

- [ ] **Step 1: 创建 preload.js**

```js
const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
})
```

- [ ] **Step 2: 创建 main.js**

```js
const { app, BrowserWindow, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const net = require('net')

let mainWindow = null
let backendProcess = null

function getAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

function getBackendPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend.exe')
  }
  return path.join(__dirname, '..', 'dist-backend', 'backend.exe')
}

function getResourcesPath() {
  if (app.isPackaged) {
    return process.resourcesPath
  }
  return path.join(__dirname, '..')
}

function waitForBackend(url, maxRetries = 60) {
  return new Promise((resolve, reject) => {
    let retries = 0
    const check = () => {
      http.get(url + '/api/projects', (res) => {
        resolve()
      }).on('error', () => {
        retries++
        if (retries >= maxRetries) {
          reject(new Error('Backend failed to start'))
        } else {
          setTimeout(check, 500)
        }
      })
    }
    check()
  })
}

async function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: '织镜',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  })

  const url = `http://127.0.0.1:${port}`
  mainWindow.loadURL(url)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  try {
    const port = await getAvailablePort()
    const backendPath = getBackendPath()

    const appDataEnv = process.env.APPDATA || path.join(app.getPath('home'), 'AppData', 'Roaming')
    const dataDir = path.join(appDataEnv, '织镜')
    const resourcesPath = getResourcesPath()

    backendProcess = spawn(backendPath, [], {
      env: {
        ...process.env,
        STORYFORGE_PORT: String(port),
        STORYFORGE_DATA_DIR: dataDir,
        STORYFORGE_RESOURCES_DIR: resourcesPath,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    backendProcess.stdout.on('data', (data) => {
      console.log(`[backend] ${data}`)
    })
    backendProcess.stderr.on('data', (data) => {
      console.error(`[backend] ${data}`)
    })
    backendProcess.on('error', (err) => {
      dialog.showErrorBox('启动失败', `无法启动后端服务: ${err.message}`)
      app.quit()
    })

    await waitForBackend(`http://127.0.0.1:${port}`)
    await createWindow(port)
  } catch (err) {
    dialog.showErrorBox('启动失败', err.message)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
  app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
})
```

- [ ] **Step 3: 验证文件存在**

Run: `node -e "require('./electron/main.js')"` 会报错没有 electron 模块，正常——稍后装完依赖再测。

---

### Task 2: 更新前端构建配置

**Files:**
- Modify: `vite.config.ts`
- Modify: `tsconfig.json`

- [ ] **Step 1: 修改 vite.config.ts，加 `base: './'`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'

export default defineConfig({
  plugins: [react()],
  base: './',
  css: {
    postcss: {
      plugins: [tailwindcss(), autoprefixer()],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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

- [ ] **Step 2: 修改 tsconfig.json，排除 electron 目录**

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
    "types": [],
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src"],
  "exclude": ["electron", "dist-electron"]
}
```

---

### Task 3: 更新 package.json

**Files:**
- Modify: `package.json`

- [ ] **Step 1: 在 package.json 加 `main` 字段**

```json
{
  "name": "story-creation-web",
  "private": true,
  "version": "1.0.0",
  "description": "织镜 - 多智能体故事创作系统",
  "main": "electron/main.js",
  "type": "module",
```

- [ ] **Step 2: 加打包脚本**

在 `scripts` 中加：

```json
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "package": "npm run build && npm run pyinstaller && electron-builder --win",
    "pyinstaller": "pyinstaller pyinstaller.spec --distpath dist-backend --workpath build-backend --noconfirm",
    "electron:dev": "vite build && electron ."
  },
```

- [ ] **Step 3: 加 Electron 依赖**

在 `devDependencies` 中加：

```json
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
```

完整 package.json 变为：

```json
{
  "name": "story-creation-web",
  "private": true,
  "version": "1.0.0",
  "description": "织镜 - 多智能体故事创作系统",
  "main": "electron/main.js",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "package": "npm run build && npm run pyinstaller && electron-builder --win",
    "pyinstaller": "pyinstaller pyinstaller.spec --distpath dist-backend --workpath build-backend --noconfirm",
    "electron:dev": "vite build && electron ."
  },
  "dependencies": {
    "@types/three": "^0.184.1",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.441.0",
    "micromark-extension-gfm-table": "^2.1.1",
    "micromark-util-classify-character": "^2.0.1",
    "postcss-selector-parser": "^7.1.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.1.0",
    "react-router-dom": "^6.26.0",
    "remark-gfm": "^4.0.1",
    "tailwind-merge": "^2.5.2",
    "three": "^0.184.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/node": "^25.8.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "4.3.4",
    "autoprefixer": "^10.5.0",
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1",
    "jsdom": "^29.1.1",
    "postcss": "^8.4.41",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.3",
    "vite": "^5.4.21",
    "vitest": "^4.1.6"
  }
}
```

---

### Task 4: 创建 PyInstaller 配置

**Files:**
- Create: `pyinstaller.spec`

```python
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

a = Analysis(
    ['server/app.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('prompts/*.txt', 'prompts'),
        ('config/image_presets.json', 'config'),
        ('orchestrator_router.txt', '.'),
    ],
    hiddenimports=[
        'server.routes.projects',
        'server.routes.settings',
        'server.routes.creation',
        'server.routes.gen',
        'server.routes.prompt_gen',
        'server.ws_manager',
        'server.async_orch',
        'server.schemas',
        'core.project_manager',
        'core.style_config',
        'core.workflow_loader',
        'core.agent_factory',
        'core.content_validator',
        'core.continuity',
        'core.qc_gates',
        'core.chunk_strategy',
        'core.bible_updater',
        'core.summary_extractor',
        'core.visual_bible',
        'core.novel_bible',
        'core.image_pipeline',
        'core.orchestrator_base',
        'core.asset_manager',
        'core.cli',
        'core.back_to_menu',
        'agents.orchestrator',
        'agents.outline_designer',
        'agents.plot_expander',
        'agents.screenplay_writer',
        'agents.storyboarder',
        'agents.visual_extractor',
        'agents.prompt_factory',
        'agents.image_preparator',
        'agents.image_artist',
        'agents.image_demand_analyzer',
        'agents.video_producer',
        'tools.api_caller',
        'tools.constants',
        'tools.content_splitter',
        'tools.duration_validator',
        'tools.file_ops',
        'tools.image_api',
        'tools.image_api_openai_compat',
        'tools.image_api_seedream',
        'tools.image_composer',
        'tools.model_registry',
        'tools.video_api',
        'tools.video_api_kling',
        'tools.video_api_luma',
        'tools.video_api_pika',
        'tools.video_api_runway',
        'tools.video_api_seedance',
        'tools.video_concat',
        'llm.backends',
        'llm.client',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'websockets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'pandas', 'numpy', 'scipy',
        'PIL', 'Pillow', 'sqlalchemy', 'sqlite3',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

---

### Task 5: 添加 AppData 初始化 + 路径切换

**Files:**
- Modify: `server/app.py:1-6`（顶部导入区）
- Modify: `server/app.py:56-80`（StaticFiles 挂载之后，路由注册之前）

- [ ] **Step 1: 在 server/app.py 顶部导入区后添加 AppData 初始化函数**

当前 `server/app.py` 第 1-12 行保持不动，在第 12 行 `load_dotenv(ROOT / ".env")` 之后插入：

```python
import shutil

DATA_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(ROOT)))
RESOURCES_DIR = Path(os.environ.get("STORYFORGE_RESOURCES_DIR", str(ROOT)))
ELECTRON_PORT = os.environ.get("STORYFORGE_PORT", "")


def _init_user_data():
    """初始化用户数据目录：缺失的默认文件从 built-in 资源复制"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dirs_to_ensure = ["prompts", "config", "memory", "memory/sessions", "projects", "generated"]
    for d in dirs_to_ensure:
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)

    # 复制缺失的默认文件
    files_to_seed = {
        "prompts": [
            "outline_designer.txt", "plot_expander.txt", "screenplay_writer.txt",
            "storyboarder.txt", "video_producer.txt", "visual_extractor.txt",
            "image_artist.txt", "outline_direction_card.txt", "outline_full.txt",
            "prompt_engineer.txt",
        ],
        "config": ["image_presets.json"],
        ".": ["orchestrator_router.txt"],
    }

    for subdir, filenames in files_to_seed.items():
        for fname in filenames:
            dest = DATA_DIR / subdir / fname if subdir != "." else DATA_DIR / fname
            if not dest.exists():
                src = RESOURCES_DIR / subdir / fname if subdir != "." else RESOURCES_DIR / fname
                if src.exists():
                    shutil.copy2(src, dest)

    env_dest = DATA_DIR / ".env"
    if not env_dest.exists():
        env_src = RESOURCES_DIR / ".env.example"
        if env_src.exists():
            shutil.copy2(env_src, env_dest)

    # 重新加载 .env（可能从 AppData 加载）
    load_dotenv(DATA_DIR / ".env", override=True)


_init_user_data()
```

- [ ] **Step 2: 修改 generated 目录挂载路径**

把第 77-78 行：

```python
generated_dir = ROOT / "generated"
if generated_dir.exists():
    app.mount("/generated", StaticFiles(directory=str(generated_dir)), name="generated")
```

改为：

```python
generated_dir = DATA_DIR / "generated"
if generated_dir.exists():
    app.mount("/generated", StaticFiles(directory=str(generated_dir)), name="generated")
```

- [ ] **Step 3: 修改 uvicorn 启动端口支持 ELECTRON_PORT**

在 `run_web.py` 中不需要改（`run_web.py` 是开发模式用的），但需要确保 `server/app.py` 作为一个可被 uvicorn 直接 run 的模块使用时能接收到端口。`uvicorn.run("server.app:app", port=...)` 中的 port 参数控制监听端口，我们通过环境变量控制。

在 `electron/main.js` 中已经通过 `STORYFORGE_PORT` 环境变量传递端口，但这要求修改 `server/app.py` 末尾或创建 `__main__` 入口。

更好的方式：在 `server/app.py` 末尾添加 `__main__` 入口：

```python
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("STORYFORGE_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
```

- [ ] **Step 4: 同步修改 core/project_manager.py 的 BASE_DIR**

`core/project_manager.py` 第 8-9 行：

```python
import os
BASE_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(Path(__file__).resolve().parent.parent)))
PROJECTS_DIR = BASE_DIR / "projects"
```

需要把原来的：

```python
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
```

改为从环境变量读取：

```python
import os
BASE_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(Path(__file__).resolve().parent.parent)))
PROJECTS_DIR = BASE_DIR / "projects"
```

（第 1 行已有 `import os`，无需再加）

完整改动后 `core/project_manager.py` 第 1-9 行：

```python
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


BASE_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(Path(__file__).resolve().parent.parent)))
PROJECTS_DIR = BASE_DIR / "projects"
```

---

### Task 6: 创建 electron-builder 配置

**Files:**
- Create: `electron-builder.yml`

```yaml
appId: com.storyforge.app
productName: "织镜"
copyright: "Copyright © 2024"

directories:
  output: release
  buildResources: assets

files:
  - dist/**/*
  - electron/**/*
  - package.json

extraResources:
  - from: dist-backend/backend.exe
    to: backend.exe
  - from: prompts/
    to: prompts/
  - from: config/
    to: config/
  - from: orchestrator_router.txt
    to: orchestrator_router.txt
  - from: .env.example
    to: .env.example

win:
  target:
    - target: nsis
  icon: assets/icon.ico

nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  installerIcon: assets/icon.ico
  uninstallerIcon: assets/icon.ico
  installerHeaderIcon: assets/icon.ico
  createDesktopShortcut: true
  createStartMenuShortcut: true
  shortcutName: "织镜"
  installerLanguages:
    - zh_CN
    - en_US
  language: "2052"
  unicode: true
  installerSidebar: null
```

---

### Task 7: 创建占位图标

**Files:**
- Create: `assets/icon.ico`

用 Python 生成一个最小有效的 ico 文件（后续可替换为正式图标）：

Run: `python -c "import struct; f=open('assets/icon.ico','wb'); f.write(b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x0b\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'); f.close()"`

---

### Task 8: 更新 .gitignore

**Files:**
- Modify: `.gitignore`

在现有内容末尾追加：

```
release/
dist-backend/
dist-electron/
build-backend/
*.spec.bak
```

---

### Task 9: 安装依赖并验证

- [ ] **Step 1: 安装 npm 依赖**

Run: `npm install`

- [ ] **Step 2: 安装 PyInstaller**

Run: `pip install pyinstaller`

- [ ] **Step 3: 验证前端构建**

Run: `npm run build`
Expected: 成功，`dist/` 目录生成

- [ ] **Step 4: 验证 PyInstaller 打包（开发模式）**

Run: `npm run pyinstaller`
Expected: 成功，`dist-backend/backend.exe` 生成

- [ ] **Step 5: 验证 Electron 开发模式启动**

Run: `npm run electron:dev`
Expected: Electron 窗口弹出，显示织镜首页，后端正常工作

- [ ] **Step 6: 验证最终打包**

Run: `npm run package`
Expected: 成功，`release/织镜-Setup-1.0.0.exe` 生成

---

## 验证清单

打包完成后验证以下项目：

1. [ ] 双击 `织镜-Setup-1.0.0.exe` 弹出安装向导（中文）
2. [ ] 安装到 `C:\Program Files\织镜\`，桌面出现快捷方式
3. [ ] 双击桌面快捷方式启动，Electron 窗口显示织镜首页
4. [ ] 关闭窗口，后台 Python 进程被清理（任务管理器无残留）
5. [ ] `%APPDATA%\织镜\prompts\` 目录下有所有模板文件
6. [ ] `%APPDATA%\织镜\.env` 已从 `.env.example` 自动创建
7. [ ] 编辑 `%APPDATA%\织镜\prompts\outline_designer.txt`，重启后修改生效
8. [ ] 删除 `%APPDATA%\织镜\prompts\outline_designer.txt`，重启后自动恢复
9. [ ] 新建项目 → 大纲 → 剧情 → 剧本流程正常
10. [ ] 控制面板"添加或删除程序"中有"织镜"，可正常卸载
