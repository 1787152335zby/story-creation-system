# 分层自由搭配主题系统 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 5 套预设纯色主题重构为色系/背景/纹理/光效 4 层独立叠加的主题系统

**Architecture:** 4 层通过 CSS class 叠加到 `<html>` 元素实现。色系使用 CSS 变量驱动所有组件颜色；背景/纹理/光效通过 `body::before` 等伪元素实现，互不干扰。组件层提供抽屉面板 UI，各维度独立 useState 管理状态，持久化到 localStorage。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, CSS Custom Properties, Vitest + @testing-library/react

---

### Task 1: 初始化 TDD 测试环境

**Files:**
- Modify: `package.json` — 添加 vitest 和相关依赖
- Create: `vitest.config.ts`
- Create: `src/test-setup.ts`

- [ ] **Step 1: 安装 vitest + 测试库**

Run:
```bash
cd "e:\AI\Trae CN\book\story-creation-system"
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Expected: 依赖安装成功，输出 "added N packages"

- [ ] **Step 2: 创建 vitest 配置**

Create: `vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: 创建测试 setup 文件**

Create: `src/test-setup.ts`:
```ts
import '@testing-library/jest-dom'
```

- [ ] **Step 4: 添加 test script 到 package.json**

Edit `package.json` scripts section — 在 `"preview"` 行后添加:
```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 5: 验证环境可运行**

Run: `npm test -- --version`
Expected: 输出 vitest 版本号

---

### Task 2: 实现 6 套色系 CSS 变量（替换旧 5 套主题）

**Files:**
- Modify: `src/index.css` (lines 5-114)
- Test: 手动前端验证 (CSS 变量视觉测试)

- [ ] **Step 1: 写入验证测试组件**

暂时跳过单元测试，CSS 变量视觉效果无法用 jsdom 测试。实际验证通过浏览器查看。

- [ ] **Step 2: 替换 `:root` 为色系层叠规则**

在 `src/index.css` 中，替换 `:root` + 5个 `.theme-*` 规则块 (lines 5-114) 为 6 套新色系:

```css
/* ===== 色系：控制全局 CSS 变量 ===== */
/* 使用 html.palette-xxx 确保特异性高于 :root */

/* 默认色系：星云紫 */
html:not([class*="palette-"]),
html.palette-nebula {
  --background: 270 20% 8%;
  --foreground: 260 25% 95%;
  --card: 270 20% 10%;
  --card-foreground: 260 25% 95%;
  --primary: 270 80% 65%;
  --primary-foreground: 0 0% 100%;
  --muted: 270 15% 13%;
  --muted-foreground: 260 15% 60%;
  --border: 270 15% 18%;
  --radius: 0.75rem;
  --accent: 230 70% 55%;
  --accent-foreground: 0 0% 100%;
  --warning: 35 92% 55%;
  --success: 150 60% 50%;
  --danger: 0 80% 60%;
}

/* 极光蓝 */
html.palette-aurora {
  --background: 210 20% 8%;
  --foreground: 210 35% 95%;
  --card: 210 20% 10%;
  --card-foreground: 210 35% 95%;
  --primary: 195 90% 58%;
  --primary-foreground: 0 0% 100%;
  --muted: 210 15% 13%;
  --muted-foreground: 210 20% 60%;
  --border: 210 18% 18%;
  --accent: 180 80% 50%;
  --accent-foreground: 0 0% 100%;
  --warning: 35 92% 55%;
  --success: 150 60% 50%;
  --danger: 0 80% 60%;
}

/* 琥珀橙 */
html.palette-amber {
  --background: 25 15% 8%;
  --foreground: 30 30% 95%;
  --card: 25 15% 10%;
  --card-foreground: 30 30% 95%;
  --primary: 30 95% 60%;
  --primary-foreground: 0 0% 100%;
  --muted: 25 12% 13%;
  --muted-foreground: 25 18% 60%;
  --border: 25 15% 18%;
  --accent: 350 80% 55%;
  --accent-foreground: 0 0% 100%;
  --warning: 35 92% 55%;
  --success: 150 60% 50%;
  --danger: 0 80% 60%;
}

/* 翡翠绿 */
html.palette-jade {
  --background: 155 15% 8%;
  --foreground: 150 25% 94%;
  --card: 155 15% 10%;
  --card-foreground: 150 25% 94%;
  --primary: 155 75% 45%;
  --primary-foreground: 0 0% 100%;
  --muted: 155 12% 13%;
  --muted-foreground: 150 15% 58%;
  --border: 155 15% 17%;
  --accent: 120 60% 50%;
  --accent-foreground: 0 0% 0%;
  --warning: 35 92% 55%;
  --success: 150 60% 50%;
  --danger: 0 80% 60%;
}

/* 玫瑰红 */
html.palette-rose {
  --background: 340 15% 8%;
  --foreground: 340 25% 94%;
  --card: 340 15% 10%;
  --card-foreground: 340 25% 94%;
  --primary: 340 80% 60%;
  --primary-foreground: 0 0% 100%;
  --muted: 340 12% 13%;
  --muted-foreground: 340 15% 58%;
  --border: 340 15% 17%;
  --accent: 290 65% 55%;
  --accent-foreground: 0 0% 100%;
  --warning: 35 92% 55%;
  --success: 150 60% 50%;
  --danger: 0 80% 60%;
}

/* 月光白（浅色主题） */
html.palette-moonlight {
  --background: 45 10% 96%;
  --foreground: 250 15% 18%;
  --card: 0 0% 100%;
  --card-foreground: 250 15% 18%;
  --primary: 250 70% 55%;
  --primary-foreground: 0 0% 100%;
  --muted: 45 12% 90%;
  --muted-foreground: 250 10% 50%;
  --border: 45 12% 85%;
  --radius: 0.75rem;
  --accent: 170 70% 40%;
  --accent-foreground: 0 0% 100%;
  --warning: 35 92% 55%;
  --success: 150 60% 45%;
  --danger: 0 80% 55%;
}
```

- [ ] **Step 3: 添加背景层 CSS 类**

在色系定义之后（index.css 原 old 行 114 之后），添加背景类:

```css
/* ===== 第二层：背景效果 ===== */
html.bg-solid body::before { display: none; }

html.bg-subtle body::before {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background: linear-gradient(135deg, transparent 40%, hsl(var(--foreground) / 0.02) 100%);
}

html.bg-aurora-grad body::before {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(ellipse 80% 55% at 25% 20%, hsl(var(--primary) / 0.07) 0%, transparent 60%),
    radial-gradient(ellipse 60% 70% at 75% 80%, hsl(var(--accent) / 0.05) 0%, transparent 60%);
}

html.bg-aurora-grad.theme-animated body::before {
  animation: bg-drift 15s ease-in-out infinite alternate;
}

html.bg-dusk body::before {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    linear-gradient(135deg, hsl(var(--primary) / 0.04) 0%, transparent 50%),
    radial-gradient(ellipse 70% 50% at 80% 90%, hsl(var(--warning) / 0.04) 0%, transparent 60%);
}

html.bg-dusk.theme-animated body::before {
  animation: bg-drift 12s ease-in-out infinite alternate;
}

html.bg-deep body::before {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    linear-gradient(180deg, hsl(var(--primary) / 0.05) 0%, transparent 50%),
    radial-gradient(ellipse 60% 50% at 50% 60%, hsl(var(--accent) / 0.03) 0%, transparent 70%);
}

html.bg-deep.theme-animated body::before {
  animation: bg-drift 18s ease-in-out infinite alternate;
}

html.bg-nebula-grad body::before {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(ellipse 70% 50% at 15% 30%, hsl(var(--primary) / 0.08) 0%, transparent 50%),
    radial-gradient(ellipse 60% 50% at 85% 40%, hsl(var(--accent) / 0.06) 0%, transparent 50%),
    radial-gradient(ellipse 50% 40% at 50% 80%, hsl(var(--warning) / 0.03) 0%, transparent 50%);
}

html.bg-nebula-grad.theme-animated body::before {
  animation: bg-drift 20s ease-in-out infinite alternate;
}

@keyframes bg-drift {
  0% { background-position: 0% 0%; }
  100% { background-position: 100% 100%; }
}
```

- [ ] **Step 4: 添加纹理层 CSS 类**

```css
/* ===== 第三层：纹理效果 ===== */
html.texture-none #theme-texture-layer { display: none; }

html.texture-noise #theme-texture-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 256px 256px;
}

html.texture-grid #theme-texture-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  opacity: 0.04;
  background-image:
    linear-gradient(to right, hsl(var(--foreground)) 1px, transparent 1px),
    linear-gradient(to bottom, hsl(var(--foreground)) 1px, transparent 1px);
  background-size: 40px 40px;
}

html.texture-dots #theme-texture-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  opacity: 0.05;
  background-image: radial-gradient(circle, hsl(var(--foreground)) 1px, transparent 1px);
  background-size: 30px 30px;
}

html.texture-ripple #theme-texture-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  opacity: 0.03;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 20px, hsl(var(--primary) / 0.3) 20px, hsl(var(--primary) / 0.3) 21px),
    repeating-linear-gradient(90deg, transparent, transparent 40px, hsl(var(--accent) / 0.2) 40px, hsl(var(--accent) / 0.2) 41px);
}
```

- [ ] **Step 5: 添加光效层 CSS 类**

```css
/* ===== 第四层：氛围光效 ===== */
html.ambient-none #theme-ambient-layer { display: none; }

html.ambient-top-glow #theme-ambient-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background: radial-gradient(ellipse 60% 25% at 50% 0%, hsl(var(--primary) / 0.08) 0%, transparent 60%);
}

html.ambient-edge-glow #theme-ambient-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  box-shadow: inset 0 0 60px 0 hsl(var(--primary) / 0.04);
}

html.ambient-corner #theme-ambient-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background: radial-gradient(ellipse 50% 40% at 85% 90%, hsl(var(--accent) / 0.06) 0%, transparent 60%);
}

html.ambient-orbit #theme-ambient-layer {
  display: block; position: fixed; inset: -50%; z-index: -1; pointer-events: none;
  background: conic-gradient(from 0deg, transparent 60%, hsl(var(--primary) / 0.04) 70%, transparent 80%);
  animation: orbit-rotate 20s linear infinite;
}

@keyframes orbit-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

html.ambient-stardust #theme-ambient-layer {
  display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  overflow: hidden;
}
html.ambient-stardust #theme-ambient-layer::before,
html.ambient-stardust #theme-ambient-layer::after {
  content: ''; position: absolute; width: 3px; height: 3px;
  background: hsl(var(--primary) / 0.3); border-radius: 50%;
  animation: stardust-float 8s ease-in-out infinite alternate;
}
html.ambient-stardust #theme-ambient-layer::before { top: 30%; left: 20%; animation-delay: 0s; }
html.ambient-stardust #theme-ambient-layer::after { top: 60%; right: 25%; width: 2px; height: 2px; animation-delay: 3s; }

@keyframes stardust-float {
  0% { transform: translate(0, 0) scale(1); opacity: 0.3; }
  100% { transform: translate(30px, -20px) scale(1.2); opacity: 0.8; }
}
```

- [ ] **Step 6: 删除旧的 `.theme-*` CSS 块并添加纹理/光效 DOM 容器**

在 `index.html` 的 `<body>` 末尾（`<div id="root">` 之后），添加:
```html
<div id="theme-texture-layer"></div>
<div id="theme-ambient-layer"></div>
```

- [ ] **Step 7: 验证 CSS 构建无报错**

Run: `npm run build`
Expected: 构建成功，无 CSS 错误

---

### Task 3: 编写 ThemeSwitcher 组件测试（TDD：RED）

**Files:**
- Create: `src/components/__tests__/ThemeSwitcher.test.tsx`

- [ ] **Step 1: 编写第一个测试**

Create: `src/components/__tests__/ThemeSwitcher.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ThemeSwitcher from '../ThemeSwitcher'

describe('ThemeSwitcher', () => {
  it('renders the trigger button', () => {
    render(<ThemeSwitcher />)
    expect(screen.getByTitle('定制主题')).toBeInTheDocument()
  })

  it('opens the drawer panel when button is clicked', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('主题定制')).toBeInTheDocument()
  })

  it('shows all 6 palette options when panel is open', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('星云紫')).toBeInTheDocument()
    expect(screen.getByText('极光蓝')).toBeInTheDocument()
    expect(screen.getByText('琥珀橙')).toBeInTheDocument()
    expect(screen.getByText('翡翠绿')).toBeInTheDocument()
    expect(screen.getByText('玫瑰红')).toBeInTheDocument()
    expect(screen.getByText('月光白')).toBeInTheDocument()
  })

  it('shows background mode section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('纯色')).toBeInTheDocument()
    expect(screen.getByText('极光')).toBeInTheDocument()
  })

  it('shows texture section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('噪点')).toBeInTheDocument()
    expect(screen.getByText('网格')).toBeInTheDocument()
  })

  it('shows ambient light section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('顶光')).toBeInTheDocument()
    expect(screen.getByText('星尘')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `npm test -- src/components/__tests__/ThemeSwitcher.test.tsx`
Expected: 失败，提示找不到组件或功能

---

### Task 4: 实现 ThemeSwitcher 组件（TDD：GREEN）

**Files:**
- Rewrite: `src/components/ThemeSwitcher.tsx`

- [ ] **Step 1: 编写数据常量和类型定义**

重写 `src/components/ThemeSwitcher.tsx` 第一部分 — 常量和类型:
```tsx
import { useEffect, useState, useCallback } from 'react'
import { Palette, X, Sparkles } from 'lucide-react'

interface PaletteOption {
  id: string
  label: string
  color: string
}

interface LayerOption {
  id: string
  label: string
}

const PALETTES: PaletteOption[] = [
  { id: 'nebula', label: '星云紫', color: 'hsl(270, 80%, 65%)' },
  { id: 'aurora', label: '极光蓝', color: 'hsl(195, 90%, 58%)' },
  { id: 'amber', label: '琥珀橙', color: 'hsl(30, 95%, 60%)' },
  { id: 'jade', label: '翡翠绿', color: 'hsl(155, 75%, 45%)' },
  { id: 'rose', label: '玫瑰红', color: 'hsl(340, 80%, 60%)' },
  { id: 'moonlight', label: '月光白', color: 'hsl(250, 70%, 55%)' },
]

const BACKGROUNDS: LayerOption[] = [
  { id: 'solid', label: '纯色' },
  { id: 'subtle', label: '微渐变' },
  { id: 'aurora-grad', label: '极光' },
  { id: 'dusk', label: '黄昏' },
  { id: 'deep', label: '深海' },
  { id: 'nebula-grad', label: '星云' },
]

const TEXTURES: LayerOption[] = [
  { id: 'none', label: '无' },
  { id: 'noise', label: '噪点' },
  { id: 'grid', label: '网格' },
  { id: 'dots', label: '点阵' },
  { id: 'ripple', label: '波纹' },
]

const AMBIENTS: LayerOption[] = [
  { id: 'none', label: '无' },
  { id: 'top-glow', label: '顶光' },
  { id: 'edge-glow', label: '边缘' },
  { id: 'corner', label: '角落' },
  { id: 'orbit', label: '环绕' },
  { id: 'stardust', label: '星尘' },
]

const STORAGE_KEYS = {
  palette: 'theme_palette',
  background: 'theme_background',
  texture: 'theme_texture',
  ambient: 'theme_ambient',
  animated: 'theme_animated',
  presets: 'theme_presets',
} as const

interface Preset {
  name: string
  palette: string
  background: string
  texture: string
  ambient: string
  animated: boolean
}
```

- [ ] **Step 2: 实现 localStorage 读写逻辑**

```tsx
function loadLayer<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v !== null ? JSON.parse(v) : fallback
  } catch { return fallback }
}

function saveLayer(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

function loadPresets(): Preset[] {
  try {
    const v = localStorage.getItem(STORAGE_KEYS.presets)
    return v ? JSON.parse(v) : []
  } catch { return [] }
}
```

- [ ] **Step 3: 实现主题应用逻辑**

```tsx
function applyTheme(palette: string, background: string, texture: string, ambient: string, animated: boolean) {
  const html = document.documentElement
  // 清除所有主题相关 class
  html.className = html.className
    .split(' ').filter(c => !c.startsWith('palette-') && !c.startsWith('bg-') && !c.startsWith('texture-') && !c.startsWith('ambient-') && c !== 'theme-animated')
    .join(' ')

  const classes: string[] = []
  if (palette !== 'nebula') classes.push(`palette-${palette}`)
  if (background !== 'solid') {
    classes.push(`bg-${background}`)
  }
  if (texture !== 'none') classes.push(`texture-${texture}`)
  if (ambient !== 'none') classes.push(`ambient-${ambient}`)
  if (animated) classes.push('theme-animated')

  if (classes.length > 0) {
    html.className = (html.className + ' ' + classes.join(' ')).trim()
  }
}
```

- [ ] **Step 4: 实现组件主体 + 抽屉面板 UI**

```tsx
export default function ThemeSwitcher() {
  const [open, setOpen] = useState(false)
  const [palette, setPaletteState] = useState(() => loadLayer(STORAGE_KEYS.palette, 'nebula'))
  const [background, setBackgroundState] = useState(() => loadLayer(STORAGE_KEYS.background, 'solid'))
  const [texture, setTextureState] = useState(() => loadLayer(STORAGE_KEYS.texture, 'none'))
  const [ambient, setAmbientState] = useState(() => loadLayer(STORAGE_KEYS.ambient, 'none'))
  const [animated, setAnimatedState] = useState(() => loadLayer(STORAGE_KEYS.animated, false))

  const setPalette = useCallback((v: string) => { setPaletteState(v); saveLayer(STORAGE_KEYS.palette, v) }, [])
  const setBackground = useCallback((v: string) => { setBackgroundState(v); saveLayer(STORAGE_KEYS.background, v) }, [])
  const setTexture = useCallback((v: string) => { setTextureState(v); saveLayer(STORAGE_KEYS.texture, v) }, [])
  const setAmbient = useCallback((v: string) => { setAmbientState(v); saveLayer(STORAGE_KEYS.ambient, v) }, [])
  const setAnimated = useCallback((v: boolean) => { setAnimatedState(v); saveLayer(STORAGE_KEYS.animated, v) }, [])

  useEffect(() => {
    applyTheme(palette, background, texture, ambient, animated)
  }, [palette, background, texture, ambient, animated])

  // 保存预设
  const savePreset = useCallback(() => {
    const name = prompt('输入预设名称：')
    if (!name?.trim()) return
    const presets = loadPresets()
    presets.push({ name: name.trim(), palette, background, texture, ambient, animated })
    localStorage.setItem(STORAGE_KEYS.presets, JSON.stringify(presets))
  }, [palette, background, texture, ambient, animated])

  // 加载预设
  const loadPresetAction = useCallback((preset: Preset) => {
    setPalette(preset.palette)
    setBackground(preset.background)
    setTexture(preset.texture)
    setAmbient(preset.ambient)
    setAnimated(preset.animated)
  }, [setPalette, setBackground, setTexture, setAmbient, setAnimated])

  // 删除预设
  const deletePreset = useCallback((index: number) => {
    const presets = loadPresets()
    presets.splice(index, 1)
    localStorage.setItem(STORAGE_KEYS.presets, JSON.stringify(presets))
    // force re-render
    setPaletteState(p => p)
  }, [])

  return (
    <>
      {/* 触发器按钮 */}
      <button onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-11 h-11 rounded-xl glass-card flex items-center justify-center hover:bg-muted/80 transition-all shadow-lg"
        title="定制主题">
        <Palette className="w-[18px] h-[18px] text-muted-foreground" />
      </button>

      {/* 遮罩层 */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setOpen(false)} />
      )}

      {/* 抽屉面板 */}
      <div className={`fixed top-0 right-0 z-50 h-full w-80 glass-card border-l border-border transform transition-transform duration-300 ease-out ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            主题定制
          </h2>
          <button onClick={() => setOpen(false)} className="p-1 rounded-lg hover:bg-muted transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="p-4 space-y-5 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 60px)' }}>
          {/* 色系 */}
          <LayerSection title="色系" icon="🌈">
            <div className="flex gap-2">
              {PALETTES.map(p => (
                <button key={p.id} onClick={() => setPalette(p.id)}
                  className={`w-9 h-9 rounded-full border-2 transition-all ${palette === p.id ? 'border-foreground scale-110' : 'border-transparent hover:scale-105'}`}
                  style={{ background: p.color }}
                  title={p.label} />
              ))}
            </div>
          </LayerSection>

          {/* 背景 */}
          <LayerSection title="背景" icon="🖼">
            <LayerButtons options={BACKGROUNDS} value={background} onChange={setBackground} />
          </LayerSection>

          {/* 纹理 */}
          <LayerSection title="纹理" icon="✨">
            <LayerButtons options={TEXTURES} value={texture} onChange={setTexture} />
          </LayerSection>

          {/* 光效 */}
          <LayerSection title="光效" icon="💡">
            <LayerButtons options={AMBIENTS} value={ambient} onChange={setAmbient} />
          </LayerSection>

          {/* 控制项 */}
          <div className="pt-2 space-y-3 border-t border-border">
            <label className="flex items-center justify-between text-xs text-muted-foreground cursor-pointer">
              <span>🔄 动态背景动画</span>
              <button onClick={() => setAnimated(!animated)}
                className={`w-9 h-5 rounded-full transition-colors relative ${animated ? 'bg-primary' : 'bg-muted'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${animated ? 'translate-x-4' : 'translate-x-0.5'}`} />
              </button>
            </label>

            <button onClick={savePreset}
              className="w-full text-xs text-muted-foreground hover:text-foreground py-2 px-3 rounded-lg hover:bg-muted transition-all text-left">
              📂 保存为预设...
            </button>

            {/* 预设列表 */}
            <PresetList onLoad={loadPresetAction} onDelete={deletePreset} />
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 5: 实现子组件**

在同一个文件末尾添加:

```tsx
function LayerSection({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs text-muted-foreground font-medium mb-2">{icon} {title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {children}
      </div>
    </div>
  )
}

function LayerButtons({ options, value, onChange }: { options: LayerOption[]; value: string; onChange: (id: string) => void }) {
  return (
    <>
      {options.map(o => (
        <button key={o.id} onClick={() => onChange(o.id)}
          className={`px-2.5 py-1.5 rounded-lg text-xs transition-all ${
            value === o.id
              ? 'bg-primary/15 text-primary font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}>
          {o.label}
        </button>
      ))}
    </>
  )
}

function PresetList({ onLoad, onDelete }: { onLoad: (p: Preset) => void; onDelete: (i: number) => void }) {
  const presets = loadPresets()
  if (presets.length === 0) return null

  return (
    <div className="space-y-1">
      {presets.map((p, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-muted group">
          <button onClick={() => onLoad(p)}
            className="flex-1 text-xs text-left text-muted-foreground hover:text-foreground truncate">
            📁 {p.name}
          </button>
          <button onClick={() => onDelete(i)}
            className="opacity-0 group-hover:opacity-100 text-[10px] text-danger hover:text-danger/80 transition-all">
            删除
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: 更新 App.tsx 入口（如需要）**

Read `src/App.tsx` to verify ThemeSwitcher is still imported. No changes needed unless import broke.

- [ ] **Step 7: 运行测试，验证通过**

Run: `npm test -- src/components/__tests__/ThemeSwitcher.test.tsx`
Expected: 全部测试通过 (PASS)

---

### Task 5: 添加旧主题兼容性逻辑

**Files:**
- Modify: `src/components/ThemeSwitcher.tsx` — 初始化时读取旧 `app_theme` key

- [ ] **Step 1: 编写兼容性测试**

添加测试到 `src/components/__tests__/ThemeSwitcher.test.tsx`:
```tsx
it('migrates old localStorage app_theme key', () => {
  localStorage.setItem('app_theme', 'aurora')
  // unmount and re-mount to trigger new read
  const { unmount } = render(<ThemeSwitcher />)
  unmount()
  // Now the old key should be migrated
  expect(localStorage.getItem(STORAGE_KEYS.palette)).toBe('aurora')
  // cleanup
  localStorage.removeItem('app_theme')
})
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `npm test -- src/components/__tests__/ThemeSwitcher.test.tsx`
Expected: FAIL — 兼容性逻辑尚未实现

- [ ] **Step 3: 添加兼容代码**

在 `loadLayer` 函数之前，添加:
```tsx
function migrateOldTheme() {
  const oldTheme = localStorage.getItem('app_theme')
  if (oldTheme && !localStorage.getItem(STORAGE_KEYS.palette)) {
    const oldMap: Record<string, string> = {
      default: 'nebula',
      aurora: 'aurora',
      blaze: 'amber',
      jade: 'jade',
      light: 'moonlight',
    }
    const newPalette = oldMap[oldTheme] || 'nebula'
    localStorage.setItem(STORAGE_KEYS.palette, newPalette)
    localStorage.removeItem('app_theme')
  }
}
```

在组件内部初始化 state 之前调用:
```tsx
migrateOldTheme()
```

- [ ] **Step 4: 运行测试，验证通过**

Run: `npm test -- src/components/__tests__/ThemeSwitcher.test.tsx`
Expected: PASS

---

### Task 6: 全量测试与构建验证

- [ ] **Step 1: 运行全部测试**

Run: `npm test`
Expected: 所有测试通过，无警告

- [ ] **Step 2: 构建验证**

Run: `npm run build`
Expected: 构建成功，无 TS/CSS 错误

- [ ] **Step 3: 功能验证**

重启 Web 服务后手动验证:
1. 点击右下角调色板按钮，抽屉面板正常滑出
2. 切换色系（点击色块），页面颜色立即变化
3. 切换背景模式，页面背景渐变效果变化
4. 切换纹理，叠加微妙质感
5. 切换光效，添加氛围光晕
6. 开关"动态动画"，渐变背景开始/停止流动
7. 刷新页面，所有设置保持
8. 保存预设，刷新后预设列表仍在
9. 加载预设，所有 4 层一起切换
10. 关闭面板重新打开，设置保持
