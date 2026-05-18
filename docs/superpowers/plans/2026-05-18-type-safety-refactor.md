# 类型安全重构 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为前端代码添加精确的类型定义，消除 `any` 类型

**Architecture:** 新建 `src/lib/types.ts` 集中管理共享类型，`api.ts` 导入精确类型作为返回值，页面组件替换 `any` 为具体类型

**Tech Stack:** TypeScript, React 18

---

### Task 1: 创建共享类型文件 types.ts

**Files:**
- Create: `src/lib/types.ts`

- [ ] **Step 1: 写测试 — 类型是纯 TS 定义，只需验证导入不报错**

创建 `src/lib/__tests__/types.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import type {
  ProjectInfo, PhaseInfo, VisualAsset, VisualAssetsData,
  EntityImage, EntityImagesMap, FreeImageResult,
  ProjectImageGenResult, FreeVideoResult, GenerationHistory, Template
} from '../types'

describe('types', () => {
  it('ProjectInfo can be constructed', () => {
    const p: ProjectInfo = { name: 'test', phases: [{ name: '大纲', done: false }] }
    expect(p.name).toBe('test')
  })
  it('EntityImagesMap can hold character images', () => {
    const m: EntityImagesMap = {
      characters: { '林深': [{ name: '林深', url: '/img.png' }] },
      scenes: {}
    }
    expect(m.characters['林深'][0].name).toBe('林深')
  })
  it('FreeImageResult can hold images', () => {
    const r: FreeImageResult = { images: [{ url: 'http://x.com/a.png', local: 'a.png' }] }
    expect(r.images.length).toBe(1)
  })
  it('FreeVideoResult can hold error', () => {
    const r: FreeVideoResult = { error: 'timeout' }
    expect(r.error).toBe('timeout')
  })
  it('GenerationHistory can hold history items', () => {
    const h: GenerationHistory = { images_free: [], images_project: [], videos: [{ name: 'v', url: '/v.mp4' }] }
    expect(h.videos.length).toBe(1)
  })
})
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `npm test -- src/lib/__tests__/types.test.tsx`
Expected: FAIL — 找不到 `../types` 模块

- [ ] **Step 3: 创建 types.ts**

创建 `src/lib/types.ts`:
```ts
// ===== 项目 =====

export interface PhaseInfo {
  name: string
  done: boolean
}

export interface ProjectInfo {
  name: string
  genre?: string
  updated_at?: string
  created_at?: string
  phases?: PhaseInfo[]
  total_phases?: number
  style_type?: string
  status?: string
  [key: string]: unknown
}

// ===== 素材 =====

export interface VisualAsset {
  name: string
  file: string
  from_generated?: boolean
}

export interface VisualAssetsData {
  characters: VisualAsset[]
  scenes: VisualAsset[]
}

export interface EntityImage {
  name: string
  url: string
}

export interface EntityImagesMap {
  characters: Record<string, EntityImage[]>
  scenes: Record<string, EntityImage[]>
}

// ===== 生成结果 =====

export interface FreeImageResult {
  images: { url: string; local: string }[]
}

export interface ProjectImageGenResult {
  images: { url: string; local: string }[]
  project_images: { folder: string; images: { url: string; local: string }[] }[]
  versions?: Record<string, number>
}

export interface FreeVideoResult {
  video_url?: string
  local?: string
  error?: string
  task_id?: string
}

export interface GenerationHistory {
  images_free: { name: string; url: string }[]
  images_project: { name: string; url: string }[]
  videos: { name: string; url: string }[]
}

export interface Template {
  name: string
  genre?: string
  [key: string]: unknown
}
```

- [ ] **Step 4: 运行测试，验证通过**

Run: `npm test -- src/lib/__tests__/types.test.tsx`
Expected: PASS

---

### Task 2: 更新 api.ts 使用精确返回类型

**Files:**
- Modify: `src/lib/api.ts`

- [ ] **Step 1: 从 types.ts 导入类型**

在 `src/lib/api.ts` 文件顶部添加：
```ts
import type { ProjectInfo, VisualAssetsData, EntityImagesMap, FreeImageResult, ProjectImageGenResult, FreeVideoResult, GenerationHistory, Template } from './types'
```

- [ ] **Step 2: 替换函数返回值类型**

找到每个函数并替换返回值：

```ts
// 原: export async function fetchProjects(): Promise<any[]> {
// 改:
export async function fetchProjects(): Promise<ProjectInfo[]> {

// 原: export async function fetchProject(name: string): Promise<any> {
// 改:
export async function fetchProject(name: string): Promise<ProjectInfo> {

// 原: export async function fetchVisualAssets(name: string): Promise<{ characters: ...; scenes: ... }>
// 改:
export async function fetchVisualAssets(name: string): Promise<{ characters: { name: string; file: string }[]; scenes: { name: string; file: string }[] }> {

// 原: export async function fetchProjectVisualAssets(...): Promise<{ characters: Record<...>; scenes: Record<...> }>
// 改:
export async function fetchProjectVisualAssets(projectName: string): Promise<EntityImagesMap> {

// 原: export async function freeImageGen(...): Promise<{ images: ... }>
// 改:
export async function freeImageGen(prompt: string, negativePrompt: string = '', size: string = '1024x1024', n: number = 1, model: string = ''): Promise<FreeImageResult> {

// 原: export async function projectImageGen(...): Promise<{ images: ...; project_images: ...; versions?: ... }>
// 改:
export async function projectImageGen(params: {
  project_name: string; prompt: string; negative_prompt?: string; size?: string; n?: number; model?: string; character_names?: string[]; scene_names?: string[]; reference_url?: string; reference_urls?: string[]; version?: string
}): Promise<ProjectImageGenResult> {

// 原: export async function freeVideoGen(...): Promise<{ video_url?: string; ... }>
// 改:
export async function freeVideoGen(prompt: string, files?: File[], model?: string, resolution?: string, duration?: number, generate_audio?: boolean): Promise<FreeVideoResult> {

// 原: export async function fetchGenerationHistory(): Promise<any>
// 改:
export async function fetchGenerationHistory(): Promise<GenerationHistory> {

// 原: export async function fetchTemplates(): Promise<any[]>
// 改:
export async function fetchTemplates(): Promise<Template[]> {

// 原: export async function fetchProjectImages(...): Promise<{ characters: ...; scenes: ... }>
// 改:
export async function fetchProjectImages(projectName: string): Promise<EntityImagesMap> {

// 原: export async function fetchConfirmedImages(...): Promise<{ characters: ...; scenes: ... }>
// 改:
export async function fetchConfirmedImages(projectName: string): Promise<EntityImagesMap> {
```

注意：保留 `StyleConfig`, `CreateProjectPayload`, `AggConfig`, `ProviderConfig`, `SettingsData` 在 api.ts 中（或者也移到 types.ts）。为了最小化改动，先不移除现有接口，只添加导入和类型替换。

- [ ] **Step 3: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 3: 替换 VideoGenPage.tsx 中的 any

**Files:**
- Modify: `src/pages/VideoGenPage.tsx`

- [ ] **Step 1: 导入类型**

在现有 import 后添加：
```ts
import type { ProjectInfo, EntityImage, EntityImagesMap, GenerationHistory } from '../lib/types'
```

- [ ] **Step 2: 替换 state 类型**

找到以下 state 声明，替换类型：
```ts
// 原: const [refProjects, setRefProjects] = useState<any[]>([])
// 改:
const [refProjects, setRefProjects] = useState<ProjectInfo[]>([])

// 原: const [refProjectImages, setRefProjectImages] = useState<{ characters: Record<...>; scenes: Record<...> }>({ characters: {}, scenes: {} })
// 改:
const [refProjectImages, setRefProjectImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })

// 原: const [historyVideos, setHistoryVideos] = useState<{ name: string; url: string }[]>([])
// 改:
const [historyVideos, setHistoryVideos] = useState<GenerationHistory['videos']>([])

// 原: const [projectImages, setProjectImages] = useState<{ characters: Record<...>; scenes: Record<...> }>({ characters: {}, scenes: {} })
// 改:
const [projectImages, setProjectImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })

// 原: const [confirmedImages, setConfirmedImages] = useState<{ characters: Record<...>; scenes: Record<...> }>({ characters: {}, scenes: {} })
// 改:
const [confirmedImages, setConfirmedImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })

// 原: const [projects, setProjects] = useState<any[]>([])
// 改:
const [projects, setProjects] = useState<ProjectInfo[]>([])
```

- [ ] **Step 3: 替换模板中的 any**

找到渲染部分的 `(p: any)` 和 `(imgs as any[])`：
```tsx
// 原: {refProjects.map((p: any) => ...
// 改: {refProjects.map((p: ProjectInfo) => ...

// 原: {(imgs as any[]).map((img, i) => ...
// 改: {(imgs as EntityImage[]).map((img, i) => ...
```

- [ ] **Step 4: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 4: 替换 HomePage.tsx 中的 any

**Files:**
- Modify: `src/pages/HomePage.tsx`

- [ ] **Step 1: 导入类型**

```ts
import type { ProjectInfo, Template } from '../lib/types'
```

- [ ] **Step 2: 替换 state 类型**

```ts
// 原: const [projects, setProjects] = useState<any[]>([])
// 改:
const [projects, setProjects] = useState<ProjectInfo[]>([])

// 原: const [templates, setTemplates] = useState<any[]>([])
// 改:
const [templates, setTemplates] = useState<Template[]>([])
```

- [ ] **Step 3: 替换模板中的 any**

```tsx
// 原: {(p: any) => ...
// 改: {(p: ProjectInfo) => ...

// 原: {(t: any) => ...
// 改: {(t: Template) => ...
```

- [ ] **Step 4: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 5: 替换 ImageGenPage.tsx 中的 any

**Files:**
- Modify: `src/pages/ImageGenPage.tsx`

- [ ] **Step 1: 导入类型**

```ts
import type { ProjectInfo, EntityImagesMap, GenerationHistory } from '../lib/types'
```

- [ ] **Step 2: 替换 state 类型**

搜索 ImageGenPage.tsx 中的 `useState<any[]>` 和 `useState<any>`，替换为精确类型。

```ts
// 原: const [projects, setProjects] = useState<any[]>([])
// 改:
const [projects, setProjects] = useState<ProjectInfo[]>([])

// 原: const [projectImages, setProjectImages] = useState<any>({ characters: {}, scenes: {} })
// 改:
const [projectImages, setProjectImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })

// 原: const [confirmedImages, setConfirmedImages] = useState<any>({ characters: {}, scenes: {} })
// 改:
const [confirmedImages, setConfirmedImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })

// 原: const [historyData, setHistoryData] = useState<any>({ images_free: [], images_project: [], videos: [] })
// 改:
const [historyData, setHistoryData] = useState<GenerationHistory>({ images_free: [], images_project: [], videos: [] })
```

- [ ] **Step 3: 替换模板中的 any**

In JSX, replace `(p: any)` with `(p: ProjectInfo)`, `(imgs: any)` with explicit types.

- [ ] **Step 4: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 6: 全量验证

- [ ] **Step 1: 运行全部测试**

Run: `npm test`
Expected: 全部通过

- [ ] **Step 2: 最终构建**

Run: `npm run build`
Expected: 构建成功，无 TS 错误
