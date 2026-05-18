# 素材面板组件 - 设计文档

## 概述

创建可复用的 `AssetGallery` 和 `ProjectAssetPicker` 组件，统一管理项目中的所有角色/场景生成图片，替换视频生成页面中现有的引用素材卡片。

## 组件架构

```
src/components/
├── AssetGallery.tsx            ← 通用素材浏览器(纯展示)
├── ProjectAssetPicker.tsx      ← 素材选择器(含添加图片到参考)
├── __tests__/
    ├── AssetGallery.test.tsx
    └── ProjectAssetPicker.test.tsx
```

## AssetGallery 组件

纯展示组件，显示指定项目的所有角色/场景图片（含版本切换）。

### Props

```tsx
interface AssetGalleryProps {
  projectName: string
  projectImages: EntityImagesMap
  loading?: boolean
  onPreview?: (url: string) => void
  onConfirmVersion?: (type: string, name: string, version: string) => void
  onDeleteVersion?: (type: string, name: string, version: string) => void
}
```

### 布局

```
┌──────────────────────────────────────────┐
│  👤 角色                                  │
│  ┌──────┐ ┌──────┐                      │
│  │ 林深  │ │ 天眼  │                     │
│  │ [img] │ │ [img]│                     │
│  │ v1 v2 │ │ v1   │                     │
│  └──────┘ └──────┘                      │
│                                          │
│  🌆 场景                                  │
│  ┌─────────┐ ┌──────────┐               │
│  │ 第10场   │ │ 第14场    │               │
│  │ [img]   │ │ [img]    │               │
│  │ v1      │ │ v1 v2 v3 │               │
│  └─────────┘ └──────────┘               │
└──────────────────────────────────────────┘
```

- 每个实体一个卡片，显示名称 + 缩略图（第一张） + 版本号按钮
- 点击版本号展开该版本的全部图片
- 点击图片触发 onPreview

## ProjectAssetPicker 组件

选择器组件，用于视频生成页面替换现有的引用素材卡片。

### Props

```tsx
interface ProjectAssetPickerProps {
  projectName: string
  assets: VisualAssetsData
  selectedEntity: string | null
  onSelectEntity: (name: string | null) => void
  onAddAsset: (url: string) => void
}
```

### 行为

- 选择项目后显示角色/场景列表
- 每个实体点击可查看其图片
- 点击图片调用 onAddAsset 添加到参考列表
- 显示已选图片数量

## 接入替换

| 目标 | 操作 |
|------|------|
| `VideoGenPage.tsx` 中的引用素材卡片（第 200-250 行） | 替换为 `ProjectAssetPicker` |
| `VideoGenPage.tsx` 中的已确认素材卡片（第 252-298 行） | 替换为 `AssetGallery`（过滤已确认） |

## 测试

- AssetGallery: 渲染角色/场景卡片、版本切换、图片预览
- ProjectAssetPicker: 选择实体、添加图片

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `src/components/AssetGallery.tsx` | 新建 |
| `src/components/ProjectAssetPicker.tsx` | 新建 |
| `src/components/__tests__/AssetGallery.test.tsx` | 新建 |
| `src/components/__tests__/ProjectAssetPicker.test.tsx` | 新建 |
| `src/pages/VideoGenPage.tsx` | 修改 — 替换引用素材卡片 |
