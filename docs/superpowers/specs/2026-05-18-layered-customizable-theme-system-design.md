# 分层自由搭配主题系统 - 设计文档

## 概述

将当前单一维度的主题切换（5 套预设纯色主题）重构为 **4 层独立叠加的主题系统**，允许用户自由搭配色系、背景、纹理和氛围光效，实现 1000+ 种组合。

## 四层架构

```
┌─────────────────────────────┐
│   🌈 色系 (Color Palette)    │  ← 控制所有 CSS 颜色变量（6 套）
├─────────────────────────────┤
│   🖼 背景 (Background)       │  ← 页面背景视觉效果（6 种模式）
├─────────────────────────────┤
│   ✨ 纹理 (Texture)          │  ← 微妙表面质感叠加（5 种）
├─────────────────────────────┤
│   💡 光效 (Ambient Light)    │  ← 边缘/角落氛围光晕（6 种）
└─────────────────────────────┘
```

## 第一层：色系 (Color Palette)

控制所有 CSS 自定义属性变量（--background, --foreground, --primary, --accent 等 10 个变量）。

### 6 套色系定义

| 色系 ID | 名称 | 背景底色 | 主色 | 点缀色 |
|---------|------|---------|------|--------|
| nebula | 星云紫 | hsl(270, 20%, 8%) | hsl(270, 80%, 65%) | 靛蓝-紫渐变 |
| aurora | 极光蓝 | hsl(210, 20%, 8%) | hsl(195, 90%, 58%) | 青-蓝渐变 |
| amber | 琥珀橙 | hsl(25, 15%, 8%) | hsl(30, 95%, 60%) | 橙-红渐变 |
| jade | 翡翠绿 | hsl(155, 15%, 8%) | hsl(155, 75%, 45%) | 绿-青渐变 |
| rose | 玫瑰红 | hsl(340, 15%, 8%) | hsl(340, 80%, 60%) | 粉-紫渐变 |
| moonlight | 月光白 | hsl(45, 10%, 96%) | hsl(250, 70%, 55%) | 紫-蓝渐变 |

每个色系包含 10 个 CSS 变量：
- --background, --foreground, --card, --card-foreground
- --primary, --primary-foreground, --accent, --accent-foreground
- --muted, --muted-foreground, --border, --warning, --success, --danger

### 兼容性

旧主题映射规则：
- `default` → `nebula`
- `aurora` → `aurora`
- `blaze` → `amber`
- `jade` → `jade`
- `light` → `moonlight`

## 第二层：背景 (Background)

通过 body 伪元素实现，在色系背景色之上叠加视觉效果。

| 模式 ID | 名称 | 实现方式 | 动态动画 |
|---------|------|---------|---------|
| solid | 纯色 | 无色差纯色背景 | 无 |
| subtle | 微渐变 | 左上到右下 5° 渐变，终点色 +5% 亮度 | 无 |
| aurora-grad | 极光渐变 | 两道 radial-gradient 光晕定位在 30%/70% 位置 | 可选，15s 循环 |
| dusk | 黄昏渐变 | 左下到右上暖色系 linear-gradient | 可选，12s 循环 |
| deep | 深海渐变 | 从上到下冷色系渐变 + 中部 radial-gradient | 可选，18s 循环 |
| nebula-grad | 星云渐变 | 3-4 个 radial-gradient 交汇 + 色彩交织 | 可选，20s 循环 |

### CSS 实现方案

```css
html.bg-aurora-grad body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(ellipse 80% 60% at 30% 20%, hsl(var(--primary) / 0.06) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 70% 80%, hsl(var(--accent) / 0.05) 0%, transparent 60%);
}
```

动态版本在 `background` 上应用 `background-position` 动画。

## 第三层：纹理 (Texture)

超低透明度（3%-5%）的表面纹理叠加。

| 模式 ID | 名称 | 实现方式 |
|---------|------|---------|
| none | 无 | - |
| noise | 噪点 | base64 PNG 噪点图，opacity 0.03 |
| grid | 网格 | repeating-linear-gradient 1px 线，间距 40px，opacity 0.04 |
| dots | 点阵 | radial-gradient 点阵，间距 30px，opacity 0.05 |
| ripple | 波纹 | 多层 linear-gradient 模拟水纹，opacity 0.03 |

所有纹理通过 `body::after` 或独立遮罩层实现，fixed 定位，pointer-events: none。

## 第四层：光效 (Ambient Light)

在页面边缘或角落添加柔和光晕。

| 模式 ID | 名称 | 实现方式 | 动画 |
|---------|------|---------|------|
| none | 无 | - | 无 |
| top-glow | 顶光 | radial-gradient 在顶部中央 | 无 |
| edge-glow | 边缘光 | box-shadow inset | 无 |
| corner | 角落光 | radial-gradient 在右下/左上 | 无 |
| orbit | 环绕光 | conic-gradient + rotate | 20s 旋转循环 |
| stardust | 粒子星尘 | 多 radial-gradient + float | 3 个光点独立浮动 |

## UI 交互设计

### 触发方式
右下角固定的圆形按钮（替换现有 Palette 按钮），点击后从右侧滑出抽屉面板。

### 面板布局

```
┌────────────────────────┐
│  🎨 主题定制        ✕  │
├────────────────────────┤
│                        │
│  🌈 色系               │
│  [●][○][○][○][○][○]   │  ← 6 色块横排
│                        │
│  🖼 背景               │
│  [纯色][微渐变][极光].. │  ← 标签按钮
│                        │
│  ✨ 纹理               │
│  [无][噪点][网格]...    │  ← 标签按钮
│                        │
│  💡 光效               │
│  [无][顶光][边缘]...    │  ← 标签按钮
│                        │
│  ── ── ── ── ──       │
│  🔄 动态背景动画  [开关] │
│  📂 保存为预设...       │
│                        │
└────────────────────────┘
```

### 交互细节
- 每个维度独立 useState，修改立即生效
- 面板本身使用毛玻璃效果（glass-card）
- 切换动画：渐变背景使用 CSS transition，约 300ms ease-out
- 纹理和光效切换无闪烁（opacity 过渡）
- 面板打开/关闭：slide-in/slide-out 动画

## 数据持久化

localStorage 键：
- `theme_palette` — 色系 ID
- `theme_background` — 背景模式 ID
- `theme_texture` — 纹理模式 ID
- `theme_ambient` — 光效模式 ID
- `theme_animated` — boolean，是否开启动态
- `theme_presets` — JSON 数组，保存的预设列表

### 预设格式
```json
{
  "name": "赛博之夜",
  "palette": "nebula",
  "background": "aurora-grad",
  "texture": "grid",
  "ambient": "orbit",
  "animated": true
}
```

## 兼容性

- 支持所有现代浏览器（Chrome/Firefox/Safari/Edge）
- 所有动画使用 CSS transform/opacity/background-position，GPU 加速
- 切换时无页面重排（reflow）
- 与现有组件完全兼容（所有颜色通过 CSS 变量驱动）
- 旧 localStorage 键 `app_theme` 读取兜底映射

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| src/index.css | 修改 | 替换现有 5 套主题为 6 套色系 CSS 变量 + 新增背景/纹理/光效类 |
| src/components/ThemeSwitcher.tsx | 重写 | 改为四层抽屉面板 |
| src/components/ThemeCustomizer.tsx | 新建 | 抽屉面板组件 |
| tailwind.config.js | 不改 | CSS 变量驱动，无需修改 |
