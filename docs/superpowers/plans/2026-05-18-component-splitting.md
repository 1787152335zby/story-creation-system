# 超大组件拆分 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 3 个超大页面组件拆分为可维护的子组件，不改变功能行为

**Architecture:** 提取逻辑边界清晰的子组件到 `src/components/` 目录，原页面通过 props 传递状态和方法，保持所有功能不变

**Tech Stack:** React 18, TypeScript, Tailwind CSS

---

### Task 1: 拆分 ImageGenPage → FreeImageGenForm + ProjectImageGenForm

**Files:**
- Create: `src/components/FreeImageGenForm.tsx`
- Create: `src/components/ProjectImageGenForm.tsx`
- Modify: `src/pages/ImageGenPage.tsx`

- [ ] **Step 1: 读取并分析 ImageGenPage.tsx 完整内容**

读取 `src/pages/ImageGenPage.tsx` 全部内容，理解：
- 自由模式（`mode === 'free'`）的 UI 和逻辑范围（lines 150-200 左右）
- 项目模式（`mode === 'project'`）的 UI 和逻辑范围（剩下的）
- 两个模式共享的 state、effects、handlers
- `handleGen` 函数是核心起发逻辑

- [ ] **Step 2: 创建 FreeImageGenForm.tsx**

新建组件，接收 props：
```tsx
interface FreeImageGenFormProps {
  freePrompt: string
  freeNegative: string
  freeSize: string
  freeCount: number
  freeGenerating: boolean
  freeError: string
  freeResults: { url: string; local: string }[]
  resolutions: string[]
  ratioGroups: Record<string, string[]>
  selectedRatio: string
  freeModel: string
  historyFree: { name: string; url: string }[]
  showAllFree: boolean
  onPromptChange: (v: string) => void
  onNegativeChange: (v: string) => void
  onSizeChange: (v: string) => void
  onCountChange: (v: number) => void
  onRatioChange: (v: string) => void
  onModelChange: (v: string) => void
  onGenerate: () => void
  onToggleShowAll: () => void
  freeFileInputRef: React.RefObject<HTMLInputElement>
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveFile: (index: number) => void
  freeFiles: { file: File; preview: string }[]
}
```

将原 ImageGenPage.tsx 中 `mode === 'free'` 分支的全部 JSX（原约 150 行）和相关的内联逻辑移入该组件。

- [ ] **Step 3: 创建 ProjectImageGenForm.tsx**

新建组件，接收 props：
```tsx
interface ProjectImageGenFormProps {
  projects: ProjectInfo[]
  selectedProject: string
  characters: any[]
  scenes: any[]
  selectedCharNames: string[]
  selectedSceneNames: string[]
  projectPrompt: string
  projectNegative: string
  projectSize: string
  projectCount: number
  projectGenerating: boolean
  projectError: string
  useCharTemplate: boolean
  useSceneTemplate: boolean
  generatedImages: EntityImagesMap
  projectResults: { url: string; local: string }[]
  historyProject: { name: string; url: string }[]
  expanedVersions: Record<string, boolean>
  showAllProject: boolean
  previewSrc: string | null
  resolutions: string[]
  ratioGroups: Record<string, string[]>
  selectedRatio: string
  projectModel: string
  onProjectChange: (v: string) => void
  onCharToggle: (name: string) => void
  onSceneToggle: (name: string) => void
  onPromptChange: (v: string) => void
  onNegativeChange: (v: string) => void
  onSizeChange: (v: string) => void
  onCountChange: (v: number) => void
  onRatioChange: (v: string) => void
  onModelChange: (v: string) => void
  onCharTemplateChange: (v: boolean) => void
  onSceneTemplateChange: (v: boolean) => void
  onGenerate: () => void
  onToggleShowAll: () => void
  onClearGenerated: (folder: string) => void
  onDeleteFile: (path: string) => void
  onConfirmVersion: (type: string, name: string, version: string) => void
  onPreview: (src: string) => void
  onToggleVersion: (key: string) => void
}
```

将原 ImageGenPage.tsx 中 `mode === 'project'` 分支的全部 JSX（原约 300 行）和相关的内联逻辑移入该组件。

- [ ] **Step 4: 精简 ImageGenPage.tsx**

删除全部 JSX 渲染内容，改为：
```tsx
return (
  <div className="min-h-screen relative overflow-hidden">
    ...header and mode tabs...
    {mode === 'free' ? (
      <FreeImageGenForm ...props... />
    ) : (
      <ProjectImageGenForm ...props... />
    )}
    ...ImagePreview modal...
  </div>
)
```

保留所有 state、effects、handlers。

- [ ] **Step 5: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 2: 拆分 SettingsPage → ProviderCard + AggConfigSection

**Files:**
- Create: `src/components/ProviderCard.tsx`
- Create: `src/components/AggConfigSection.tsx`
- Modify: `src/pages/SettingsPage.tsx`

- [ ] **Step 1: 读取 SettingsPage.tsx 全部内容**

- [ ] **Step 2: 创建 ProviderCard.tsx**

提取单个 Provider 的展示/编辑卡片（含 Key 显示/隐藏、模型选择、测试连接）。

- [ ] **Step 3: 创建 AggConfigSection.tsx**

提取聚合配置管理（新增/编辑/删除配置、设置活跃）。

- [ ] **Step 4: 精简 SettingsPage.tsx**

保留标签页切换逻辑和 GROUPS/KEY_LINKS 常量，渲染委托给子组件。

- [ ] **Step 5: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 3: 全量验证

- [ ] **Step 1: 运行全部测试**

Run: `npm test`
Expected: 全部通过

- [ ] **Step 2: 最终构建**

Run: `npm run build`
Expected: 构建成功
