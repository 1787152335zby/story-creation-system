# Page Polish: NewProjectWizard & Workspace

## Overview

Polish the two core project-facing screens — the project creation wizard (`NewProjectWizard`) and the project workspace (`Workspace`) — to match the visual quality already delivered for ImageGen and VideoGen pages. The goal is to make both pages feel deliberate, premium, and layered.

## Design Direction

| Page              | Direction         | Mood                          |
| ----------------- | ----------------- | ----------------------------- |
| NewProjectWizard  | 沉浸式故事感      | 浪漫、引导、期待感             |
| Workspace         | 专业工作室        | 高效、清晰、可信赖              |

---

## 1. NewProjectWizard

### 1.1 Step Indicator (步骤条)

**Current:** Flat numbered circles with thin connector lines.

**Target:** Glowing gemstone dots with status-aware animations.

- **Completed step:** Checkmark icon, subtle glow ring, connector line fades from green to default
- **Active step:** Pulsing core (3s ease-in-out), soft purple glow ring
- **Future step:** Dim circle, low opacity label, thin connector
- Transition: when step changes, the indicator bar animates the active dot position
- Keep `sm:hidden` inline labels for mobile

### 1.2 Main Card Container

**Current:** `rgba(255,255,255,0.12)` background, `blur(24px)`, `1px solid rgba(255,255,255,0.22)` border.

**Target:** Upgrade to `premium-panel` class (already brightness-enhanced in previous session). The card sits inside a slightly larger container for breathing room.

- Apply `premium-panel` with increased padding (px-8 py-8)
- Top accent line (purple gradient) remains visible
- Internal high-light layer (top-to-bottom fade) provides the "depth" cue
- When step changes, the content region fades out → new step fades in with a subtle upward slide (translateY 8px)

### 1.3 Option Buttons (Story Type, Genre, Style)

**Current:** Flat button with subtle border change on select.

**Target:** Glass cards with strong selected/unselected contrast.

- **Unselected:** `background: rgba(255,255,255,0.04)`, `border: 1px solid rgba(255,255,255,0.06)`, `color: rgba(255,255,255,0.55)`
- **Selected:** `background: rgba(255,255,255,0.14)`, `border: 1px solid rgba(255,255,255,0.25)`, `color: rgba(255,255,255,0.95)`, plus a subtle inner top glow and a pulsing border glow animation at 2s interval
- **Genre/Mood tags (multi-select):** smaller chips, selected state includes a checkmark icon + tinted purple background, unselected is transparent with thin border

### 1.4 Form Inputs

**Current:** Inline style `rgba(255,255,255,0.08)` background.

**Target:** Apply `premium-input` / `premium-select` classes.

- Darker but still transparent background (`rgba(0,0,0,0.08)`)
- Focus ring in purple (`rgba(139, 92, 246, 0.35)`)
- Slightly brighter placeholder text

### 1.5 Navigation Buttons

**Current:** "上一步" as bordered button, "下一步/开始创作" as solid white button.

**Target:**
- **上一步:** Ghost link style — low opacity, hover reveals, no border
- **下一步 (step 0-3):** Gradient button (`#fff → rgba(255,255,255,0.9)`), slight arrow animation on hover (translateX 2px)
- **开始创作 (step 4):** Larger gradient button with sparkle icon, glow shadow, `transform: scale(1.02)` on hover

### 1.6 Step Transition Animation

- Content area uses `fade + slide` (opacity 0→1, translateY 8px→0, 0.4s cubic-bezier)
- Step indicator animates dot-to-dot

### 1.7 Template Section

- Template cards: use `premium-grid-item` style
- "从模板创建" divider line: use `premium-divider`

---

## 2. Workspace

### 2.1 Layout Structure

```
┌─────────────────────────────────────────────┐
│  Top Progress Bar (glass strip, gen only)   │
├──────────┬──────────────────────────────────┤
│ Timeline  │     Main Content Area            │
│ (220px)   │     premium-panel                │
│           │     ┌──────────────────────┐     │
│ ✅ Done   │     │                      │     │
│ ✦ Active │     │  Stream / View /     │     │
│ ◻ Pending│     │  Celebrations        │     │
│ ◻ Pending│     │                      │     │
│           │     └──────────────────────┘     │
├──────────┴──────────────────────────────────┤
│  Bottom Control Bar (glass, always visible) │
│  [Approve] [Revise] [Edit] [Continue]        │
└─────────────────────────────────────────────┘
```

### 2.2 Left Panel (PhaseTimeline)

**Current:** Semi-transparent background, minimal state differentiation.

**Target:**
- Apply `premium-subpanel` background to the sidebar
- **Done phases:** Green left-border accent (2px), subtle green dot, "Done" badge, clickable to view content
- **Active phase:** Purple pulsing left-border accent, glowing dot with pulse animation, bold label
- **Pending phases:** Dim text, thin grey dot, no border accent
- **Selected phase (for viewing):** Light purple background fill, brighter than hover
- Phase icons: slightly larger and more saturated
- Width: 220px (slightly wider than current for readability)

### 2.3 Main Content Area

**Current:** `background: rgba(255,255,255,0.02)` — nearly invisible.

**Target:** Apply `premium-panel` with full border, top accent line, and inner glow. This creates a clearly defined "workspace" region.

- The content area itself is a `premium-panel` that fills the remaining flex space
- Internal scroll maintains its own overflow
- Content types (streaming / historical view / celebration page) share the same container but have distinct inner layouts

### 2.4 Top Progress Bar

**Current:** Inline style with gradient fill.

**Target:** Glass bar with backdrop blur, visible border separation from content area.

- `background: rgba(255,255,255,0.06)`, `backdrop-filter: blur(12px)`
- Left side: phase icon + name + progress fraction
- Center: progress bar (gradient fill, animated)
- Right: connection status dot
- Only rendered during generation (`showStream`)

### 2.5 Bottom Control Bar

**Current:** Inline style with `borderTop + background`.

**Target:** Glass strip with premium-panel-like treatment.

- `background: rgba(255,255,255,0.06)`, `backdrop-filter: blur(12px)`
- Top separator: `1px solid rgba(255,255,255,0.08)` with purple accent line
- Left side: status text / context info
- Right side: action buttons grouped with consistent spacing
- **Approve (通过):** Green gradient button, check icon
- **Revise (修改):** Glass button, edit icon, opens textarea
- **Edit (编辑):** Ghost button, pencil icon
- **Continue (继续):** Gradient button (green), play icon

### 2.6 Streaming Content Display

**Current:** Plain text with markdown rendering.

**Target:** Keep the markdown rendering but wrap in a cleaner container.

- Content area padding: `p-8` → `p-10` for more breathing room
- Markdown typography: slightly larger line-height for readability
- Cursor blinking animation at end of stream
- "AI generating" indicator with elapsed time

### 2.7 Celebration Page ("完成所有任务！")

**Current:** Centered layout with icon, text, buttons.

**Target:**
- Large floating icon with slow float animation (`translateY -6px to 0`)
- Success text in bright green gradient
- Subtle particle/stars animation in the background (small floating dots)
- Action buttons: "返回首页" as premium gradient button, "去生图"/"去视频" as glass buttons
- Entire section fades in with a `scale(0.95 → 1) + opacity` entrance

### 2.8 Version Selection / Approval Flow

- Keep existing interaction flow, upgrade only visual containers
- "版本A/版本B/混合A+B" buttons: gradient buttons with hover effects
- Feedback textarea: `premium-input` style
- "混合" mode: same glass panel treatment

---

## 3. Shared Style Tokens

All new styles reuse the existing `premium-*` CSS class system (already defined in `index.css`). No new foundational tokens needed.

| Token | Purpose |
|-------|---------|
| `premium-panel` | Main card container |
| `premium-subpanel` | Inner card / sidebar panel |
| `premium-input` | Text inputs and textareas |
| `premium-select` | Select dropdowns |
| `premium-divider` | Section separators |
| `premium-label` | Section labels |
| `premium-btn-group` | Button cluster |
| `premium-grid-item` | Grid / template cards |
| `premium-upload` | File upload zones |
| `mode-toggle-btn` | Mode/binary selection |

---

## 4. Non-Goals

- Do not change the underlying logic, state management, or API calls
- Do not restructure component hierarchy
- Do not change PhaseTimeline component logic — only its CSS classes and visual presentation
- Do not add new npm dependencies

---

## 5. Success Criteria

- NewProjectWizard card has visible depth (top accent line, inner glow, border)
- Option buttons clearly distinguish selected vs unselected across all steps
- Step transition feels smooth and guided
- Workspace main content area has a clear "panel" boundary vs the background
- PhaseTimeline sidebar contrast improved: done/active/pending visually distinct
- Bottom control bar buttons are unified in a glass strip
- Celebration page has a sense of accomplishment (animation + visual polish)
- Build passes with no errors
