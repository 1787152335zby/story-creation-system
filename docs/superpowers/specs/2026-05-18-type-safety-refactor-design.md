# 类型安全重构 - 设计文档

## 概述

为前端代码添加精确的类型定义，消除 `any` 类型，提高代码可维护性和开发效率。

## 范围

仅涉及前端 `src/` 目录。不涉及 Python 后端。

## 策略

- 不开启 `tsconfig.json` 的 `strict: true`（改动量过大，会引入数百个新错误）
- 改为启用 `noImplicitAny`，配合显式类型定义
- 新建 `src/lib/types.ts` 集中管理共享类型
- 逐步替换页面中的 `any`

## 新增类型定义

见 `src/lib/types.ts`，包含：

### 项目相关
- `ProjectInfo` — 项目概要信息
- `PhaseInfo` — 创作阶段状态

### 素材相关
- `VisualAsset` — 单个素材文件
- `VisualAssetsData` — API 返回的素材列表
- `EntityImage` — 带 URL 的实体图片
- `EntityImagesMap` — 按实体分组的图片映射

### 生成结果
- `FreeImageResult` — 自由生图结果
- `ProjectImageGenResult` — 项目生图结果
- `FreeVideoResult` — 自由视频生成结果
- `GenerationHistory` — 生成历史
- `Template` — 模板信息

### 设置相关（已在 api.ts 中定义，移到 types.ts）
- `StyleConfig`
- `CreateProjectPayload`
- `SettingsData`
- `AggConfig`
- `ProviderConfig`

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/lib/types.ts` | 新建 | 集中定义所有共享类型 |
| `src/lib/api.ts` | 修改 | 导入类型，函数返回精确类型 |
| `src/pages/VideoGenPage.tsx` | 修改 | 替换 any → 精确类型 |
| `src/pages/HomePage.tsx` | 修改 | 替换 any → 精确类型 |
| `src/pages/ImageGenPage.tsx` | 修改 | 替换 any → 精确类型 |
| `tsconfig.json` | 修改 | 启用 `noImplicitAny` |
