# 素材面板组件 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 AssetGallery 和 ProjectAssetPicker 组件，统一管理项目素材，替换 VideoGenPage 中的现有卡片

**Architecture:** 两个独立组件 AssetGallery（纯展示）和 ProjectAssetPicker（含添加到参考），通过 props 接收数据和回调

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vitest + @testing-library/react

---

### Task 1: 编写 AssetGallery 测试 (TDD RED)

**Files:**
- Create: `src/components/__tests__/AssetGallery.test.tsx`

- [ ] **Step 1: 编写测试**

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AssetGallery from '../AssetGallery'

const mockImages = {
  characters: {
    '林深': [{ name: '林深', url: '/api/gen-files/char_1.png' }],
  },
  scenes: {
    '第10场': [
      { name: '第10场', url: '/api/gen-files/scene_1.png' },
      { name: '第10场', url: '/api/gen-files/scene_2.png' },
    ],
  },
}

describe('AssetGallery', () => {
  it('renders entity names', () => {
    render(<AssetGallery projectName="test" projectImages={mockImages} />)
    expect(screen.getByText('林深')).toBeInTheDocument()
    expect(screen.getByText('第10场')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<AssetGallery projectName="test" projectImages={{ characters: {}, scenes: {} }} loading={true} />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows empty state when no assets', () => {
    render(<AssetGallery projectName="test" projectImages={{ characters: {}, scenes: {} }} />)
    expect(screen.getByText('暂无素材')).toBeInTheDocument()
  })

  it('renders version badges for entities with versions', () => {
    const imagesWithVersions = {
      characters: {
        '林深': { images: [{ name: '林深', url: '/img.png' }], versions: { '1': { confirmed: false, images: [{ name: '1', url: '/img.png' }] } } },
      },
      scenes: {},
    }
    render(<AssetGallery projectName="test" projectImages={imagesWithVersions as any} />)
    // Should show version button
    expect(screen.getByText(/v1/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `npm test -- src/components/__tests__/AssetGallery.test.tsx`
Expected: FAIL — 找不到模块

---

### Task 2: 实现 AssetGallery 组件 (TDD GREEN)

**Files:**
- Create: `src/components/AssetGallery.tsx`

- [ ] **Step 1: 实现组件**

```tsx
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import type { EntityImagesMap } from '../lib/types'

interface AssetGalleryProps {
  projectName: string
  projectImages: EntityImagesMap
  loading?: boolean
  onPreview?: (url: string) => void
  onConfirmVersion?: (type: string, name: string, version: string) => void
  onDeleteVersion?: (type: string, name: string, version: string) => void
}

export default function AssetGallery({
  projectName,
  projectImages,
  loading,
  onPreview,
  onConfirmVersion,
  onDeleteVersion,
}: AssetGalleryProps) {
  const [expandedVersions, setExpandedVersions] = useState<Record<string, boolean>>({})

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">加载中...</span>
      </div>
    )
  }

  const charNames = Object.keys(projectImages.characters)
  const sceneNames = Object.keys(projectImages.scenes)

  if (charNames.length === 0 && sceneNames.length === 0) {
    return (
      <div className="glass-card rounded-xl p-6 text-center">
        <p className="text-sm text-muted-foreground">暂无素材</p>
      </div>
    )
  }

  const renderEntityCard = (name: string, data: any, type: string) => {
    const imgs = data.images || []
    const versions = data.versions || {}
    const versionKeys = Object.keys(versions).sort()
    const key = `${type}-${name}`
    const expanded = expandedVersions[key]

    return (
      <div key={name} className="bg-muted/40 rounded-xl p-3 border border-border/30">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium truncate flex-1">{name}</span>
          {imgs.length > 0 && <span className="text-green-400 text-[9px]" title="已确认">✓</span>}
        </div>
        {imgs.length > 0 && (
          <div className="flex gap-1.5 mb-2">
            {imgs.slice(0, 3).map((img: any, i: number) => (
              <img key={i} src={img.url} alt={name}
                className="w-12 h-12 rounded-lg object-cover border border-border/40 cursor-pointer hover:ring-2 hover:ring-primary/50"
                onClick={() => onPreview?.(img.url)} />
            ))}
          </div>
        )}
        {versionKeys.length > 0 && (
          <div className="space-y-1">
            <button onClick={() => setExpandedVersions(prev => ({ ...prev, [key]: !prev[key] }))}
              className="text-[9px] text-muted-foreground hover:text-primary flex items-center gap-1 px-1 py-0.5 rounded">
              {expanded ? '▼' : '▶'} {versionKeys.length} 个版本
            </button>
            {expanded && versionKeys.map(vk => {
              const v = versions[vk]
              return (
                <div key={vk} className="pl-2 border-l-2 border-border/40">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[9px] text-muted-foreground">v{vk} {v.confirmed && <span className="text-green-400">✓</span>}</span>
                    {onDeleteVersion && (
                      <button onClick={() => onDeleteVersion(type, name, vk)}
                        className="text-[8px] text-red-400 hover:text-red-300 px-1 rounded hover:bg-red-500/10">删除</button>
                    )}
                  </div>
                  <div className="flex gap-1 overflow-x-auto">
                    {v.images.map((img: any, j: number) => (
                      <img key={j} src={img.url} alt=""
                        className="w-9 h-9 rounded object-cover border border-border/40 cursor-pointer hover:border-primary/50 flex-shrink-0"
                        onClick={() => onPreview?.(img.url)} title={img.name} />
                    ))}
                  </div>
                  {!v.confirmed && onConfirmVersion && (
                    <button onClick={() => onConfirmVersion(type, name, vk)}
                      className="mt-1 w-full text-[8px] py-0.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors">确认此版</button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {charNames.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground font-medium mb-2">👤 角色</p>
          <div className="grid grid-cols-2 gap-2">
            {charNames.map(n => renderEntityCard(n, projectImages.characters[n], 'characters'))}
          </div>
        </div>
      )}
      {sceneNames.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground font-medium mb-2">🌆 场景</p>
          <div className="grid grid-cols-2 gap-2">
            {sceneNames.map(n => renderEntityCard(n, projectImages.scenes[n], 'scenes'))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 运行测试验证通过**

Run: `npm test -- src/components/__tests__/AssetGallery.test.tsx`
Expected: PASS

---

### Task 3: 编写 ProjectAssetPicker 测试 (TDD RED)

**Files:**
- Create: `src/components/__tests__/ProjectAssetPicker.test.tsx`

- [ ] **Step 1: 编写测试**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ProjectAssetPicker from '../ProjectAssetPicker'

const mockAssets = {
  characters: [
    { name: '林深', file: 'char_1.png' },
    { name: '天眼', file: 'char_2.png' },
  ],
  scenes: [
    { name: '第10场-虚拟城市', file: 'scene_1.png' },
    { name: '第14场-对话', file: 'scene_2.png' },
  ],
}

const mockEntityImages = {
  characters: {
    '林深': [{ name: '林深', url: '/img.png' }],
  },
  scenes: {},
}

describe('ProjectAssetPicker', () => {
  it('renders project name and entity count', () => {
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={mockEntityImages}
      selectedEntity={null}
      onSelectEntity={vi.fn()}
      onAddAsset={vi.fn()}
    />)
    expect(screen.getByText('测试2')).toBeInTheDocument()
    expect(screen.getByText('2 个角色')).toBeInTheDocument()
    expect(screen.getByText('2 个场景')).toBeInTheDocument()
  })

  it('calls onAddAsset when clicking an image', () => {
    const onAdd = vi.fn()
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={mockEntityImages}
      selectedEntity="林深"
      onSelectEntity={vi.fn()}
      onAddAsset={onAdd}
    />)
    const img = screen.getByRole('img')
    fireEvent.click(img)
    expect(onAdd).toHaveBeenCalledWith('/img.png')
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `npm test -- src/components/__tests__/ProjectAssetPicker.test.tsx`
Expected: FAIL

---

### Task 4: 实现 ProjectAssetPicker 组件 (TDD GREEN)

**Files:**
- Create: `src/components/ProjectAssetPicker.tsx`

- [ ] **Step 1: 实现组件**

```tsx
import { useState } from 'react'
import type { VisualAsset, EntityImagesMap } from '../lib/types'

interface ProjectAssetPickerProps {
  projectName: string
  assets: { characters: VisualAsset[]; scenes: VisualAsset[] }
  entityImages: EntityImagesMap
  selectedEntity: string | null
  onSelectEntity: (name: string | null) => void
  onAddAsset: (url: string) => void
}

export default function ProjectAssetPicker({
  projectName,
  assets,
  entityImages,
  selectedEntity,
  onSelectEntity,
  onAddAsset,
}: ProjectAssetPickerProps) {
  const [view, setView] = useState<'characters' | 'scenes'>('characters')

  const chars = assets.characters || []
  const scns = assets.scenes || []

  const currentImages = selectedEntity
    ? (view === 'characters'
        ? (entityImages.characters[selectedEntity] || [])
        : (entityImages.scenes[selectedEntity] || []))
    : []

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="text-xs font-medium text-muted-foreground mb-3">📂 {projectName} 素材库</h3>

      <div className="flex gap-2 mb-3">
        <button onClick={() => setView('characters')}
          className={`text-[10px] px-2.5 py-1 rounded-lg transition-all ${view === 'characters' ? 'bg-primary/15 text-primary font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
          👤 角色 ({chars.length})
        </button>
        <button onClick={() => setView('scenes')}
          className={`text-[10px] px-2.5 py-1 rounded-lg transition-all ${view === 'scenes' ? 'bg-primary/15 text-primary font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
          🌆 场景 ({scns.length})
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {(view === 'characters' ? chars : scns).map(item => (
          <button key={item.name} onClick={() => onSelectEntity(selectedEntity === item.name ? null : item.name)}
            className={`text-[10px] px-2 py-1 rounded-lg transition-all ${
              selectedEntity === item.name
                ? 'bg-primary/20 text-primary font-medium ring-1 ring-primary/40'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted'
            }`}>
            {item.name}
          </button>
        ))}
      </div>

      {selectedEntity && currentImages.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {currentImages.map((img, i) => (
            <img key={i} src={img.url} alt={img.name}
              className="w-16 h-16 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
              onClick={() => onAddAsset(img.url)} title={`点击添加到参考: ${img.name}`} />
          ))}
        </div>
      )}
      {selectedEntity && currentImages.length === 0 && (
        <p className="text-[10px] text-muted-foreground">该实体暂无生成图片</p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 运行测试验证通过**

Run: `npm test -- src/components/__tests__/ProjectAssetPicker.test.tsx`
Expected: PASS

---

### Task 5: 替换 VideoGenPage 中的引用素材卡片

**Files:**
- Modify: `src/pages/VideoGenPage.tsx`

- [ ] **Step 1: 读取当前 VideoGenPage.tsx，找到引用素材卡片代码**

替换 lines 200-250（引用项目素材卡片 + 已确认素材卡片）为：
```tsx
              {/* Project reference gallery */}
              <ProjectAssetPicker
                projectName={selectedRefProject || ''}
                assets={{ characters: refProjectImages.characters, scenes: refProjectImages.scenes }}
                entityImages={{ characters: refProjectImages.characters, scenes: refProjectImages.scenes }}
                selectedEntity={selectedRefEntity}
                onSelectEntity={setSelectedRefEntity}
                onAddAsset={(url) => {
                  fetch(url).then(r => r.blob()).then(blob => {
                    const file = new File([blob], 'ref.png', { type: 'image/png' })
                    const reader = new FileReader()
                    reader.onload = (ev) => setFreeFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
                    reader.readAsDataURL(blob)
                  })
                }}
              />
```

需要添加新的 state: `const [selectedRefEntity, setSelectedRefEntity] = useState<string | null>(null)`

- [ ] **Step 2: 验证构建**

Run: `npm run build`
Expected: 构建成功

---

### Task 6: 全量验证

- [ ] **Step 1: 运行全部测试**

Run: `npm test`
Expected: 全部通过

- [ ] **Step 2: 最终构建**

Run: `npm run build`
Expected: 构建成功
