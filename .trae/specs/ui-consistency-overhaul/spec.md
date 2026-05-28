# UI 一致性翻新 Spec

## Why

当前 UI 设计基础扎实（玻璃拟态、渐变按钮、6 套主题色、入场动画），但在落地执行层面存在累积性债务：

1. **背景与主题割裂** — SceneBackground 硬编码蓝色系，切换琥珀橙/翡翠绿等色系时背景不跟随
2. **弹窗 3 份重复实现** — 首页/生图页/历史页各写了一个确认弹窗，视觉和行为不一致
3. **项目模式表单过长** — 8 个区块垂直堆叠，用户需滚 3-4 屏完成操作
4. **字号体系过散** — 8px~24px 共 10 级，8px/9px 基本不可读
5. **硬编码颜色多处** — 工具卡片图标色、按钮色绕过 CSS 变量
6. **确认弹窗 backdrop 不统一** — 有的带 blur 有的没有

本次翻新聚焦 **P0 + P1**，不动整体布局结构，只修一致性问题。

## What Changes

### P0 — 必须修复

1. **SceneBackground 接入主题系统**：将 5 个场景背景的硬编码色值改为通过 CSS 变量或当前 `theme_scene` state 传入主题色，背景随色系切换变化
2. **统一 ConfirmModal 组件**：新建 `ConfirmModal` 共享组件，替换 HomePage / ProjectImageGenForm / HistoryPage 三处独立实现
3. **ProjectImageGenForm 改用折叠面板**：角色、场景面板收拢为 `CollapsibleSection` 组件，减少默认展开高度

### P1 — 强烈建议

4. **收窄字号体系**：移除 `text-[8px]` 和 `text-[9px]`，将 8px/9px 的引用统一提升到 `text-[10px]`；定义字号层级 Token
5. **硬编码颜色迁移**：首页工具卡片图标色、首页 Header 图标色、视频页按钮色改为 `hsl(var(--primary) / x)` 等 CSS 变量引用
6. **统一 backdrop-blur**：所有 `bg-black/50` 改用于确认弹窗的 backdrop，统一为 `bg-black/50 backdrop-blur-sm`

## Impact

- Affected specs: 首页、生图页、历史页、视频页、场景背景
- Affected code:
  - `src/components/SceneBackground.tsx` — 背景色与主题联动
  - `src/components/ConfirmModal.tsx` — **新建**共享组件
  - `src/pages/HomePage.tsx` — 引用 ConfirmModal、硬编码颜色迁移、字号调整
  - `src/components/ProjectImageGenForm.tsx` — 折叠面板、引用 ConfirmModal
  - `src/pages/HistoryPage.tsx` — 引用 ConfirmModal、字号调整
  - `src/pages/VideoGenPage.tsx` — 硬编码颜色迁移
  - `src/components/FreeImageGenForm.tsx` — 字号调整
  - `src/pages/ImageGenPage.tsx` — 字号调整
  - `src/pages/NewProjectWizard.tsx` — 字号调整
  - `src/pages/Workspace.tsx` — 字号调整

## ADDED Requirements

### Requirement: 主题感知背景

The system SHALL make SceneBackground respond to theme color changes.

#### Scenario: 切换色系
- **WHEN** 用户在 ThemeSwitcher 中从"星云紫"切换到"琥珀橙"
- **THEN** 背景的主色调从蓝紫色系变为琥珀色系
- **AND** 渐变粒子颜色跟随 `--primary` 变化

#### Scenario: 粒子颜色复用
- **WHEN** SceneBackground 渲染粒子
- **THEN** 粒子的颜色从 `getComputedStyle(document.documentElement).getPropertyValue('--primary')` 读取

### Requirement: 统一确认弹窗

The system SHALL use a single `ConfirmModal` component for all deletion confirmations.

#### Scenario: 删除确认
- **WHEN** 用户点击删除按钮
- **THEN** 使用 `<ConfirmModal>` 组件显示确认弹窗
- **AND** 弹窗包含图标区域、标题、描述、取消/确认按钮
- **AND** backdrop 统一使用 `bg-black/50 backdrop-blur-sm`

### Requirement: 折叠面板

The system SHALL use collapsible sections in ProjectImageGenForm to reduce vertical space.

#### Scenario: 角色/场景面板
- **WHEN** 项目模式表单加载
- **THEN** 角色和场景面板以折叠状态显示
- **AND** 点击头部展开/收拢

## MODIFIED Requirements

### Requirement: SceneBackground（原）

背景色值从硬编码迁移到通过 CSS 变量读取，每次主题切换时重新计算粒子颜色。

### Requirement: ProjectImageGenForm 布局（原）

角色树和场景树区域改为 `CollapsibleSection`，每个 section 包含 `useState<boolean>` 控制展开/收拢。

## REMOVED Requirements

### Requirement: 三处独立删除弹窗

**Reason**：同一功能三份实现，维护成本高且体验不一致
**Migration**：统一由 `ConfirmModal` 组件替代
