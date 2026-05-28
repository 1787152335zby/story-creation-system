# NewProjectWizard & Workspace Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish NewProjectWizard and Workspace pages to match premium visual quality of ImageGen/VideoGen pages.

**Architecture:** Apply existing `premium-*` CSS classes and add targeted CSS animations to both pages. No new dependencies, no logic changes. Two pages tackled independently.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, custom CSS in index.css

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/pages/NewProjectWizard.tsx` | Modify | Apply premium classes, step transition, navigation buttons, option buttons |
| `src/pages/Workspace.tsx` | Modify | Main content area premium-panel, bottom bar, celebration page, control buttons |
| `src/components/PhaseTimeline.tsx` | Modify | Apply premium-subpanel, done/active/pending visual states |
| `src/index.css` | Modify (if needed) | Add any missing premium animations |

---

### Task 1: NewProjectWizard — Main Card Container

**Files:**
- Modify: `src/pages/NewProjectWizard.tsx:194-201`
- Add: CSS to index.css if needed

- [ ] **Step 1: Replace card container inline styles with premium-panel**

Current inline styles at line 194-201:
```tsx
<div className="rounded-2xl overflow-hidden animate-fade-in-up delay-100">
  <div className="px-6 py-6" key={step}
    style={{
      background: 'rgba(255,255,255,0.12)',
      backdropFilter: 'blur(24px)',
      border: '1px solid rgba(255,255,255,0.22)',
    }}>
```

Replace with:
```tsx
<div className="animate-fade-in-up delay-100">
  <div className="premium-panel px-8 py-8" key={step}>
```

- [ ] **Step 2: Verify card has premium-panel styling**

The card should now have:
- Gradient glass background (160deg, rgba(255,255,255,0.12) → rgba(255,255,255,0.06) → rgba(255,255,255,0.09))
- Top purple gradient accent line (50% width, centered)
- Inner top highlight layer
- Brighter border on state changes

- [ ] **Step 3: Update h2 inside the card**

Current (line 202-205):
```tsx
<h2 className="text-sm font-semibold text-white/80 mb-6 flex items-center gap-2">
  <Wand2 className="w-4 h-4 text-white/40" />
  {steps[step]}
</h2>
```

Replace with:
```tsx
<div className="premium-header">
  <h2 className="text-sm font-semibold flex items-center gap-2">
    <Wand2 className="w-4 h-4" style={{ color: 'rgba(167, 139, 250, 0.6)' }} />
    {steps[step]}
  </h2>
</div>
```

---

### Task 2: NewProjectWizard — Step Indicator Glow Enhancement

**Files:**
- Modify: `src/pages/NewProjectWizard.tsx:168-192`

- [ ] **Step 1: Replace step indicators with glow-enhanced version**

Current (lines 168-192):
```tsx
<div className="flex items-center justify-center gap-2 mb-10">
  {steps.map((s, i) => (
    <div key={i} className="flex items-center gap-2">
      <div className="flex items-center gap-2">
        <div style={{
          width: 28, height: 28, borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: i <= step ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
          border: `1px solid ${i <= step ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)'}`,
          transition: 'all 0.3s',
        }}>
          {i < step ? (
            <Check className="w-3.5 h-3.5 text-white/60" />
          ) : (
            <span style={{ fontSize: 11, fontWeight: 600, color: i <= step ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.45)' }}>{i + 1}</span>
          )}
        </div>
        <span className="hidden sm:inline text-[11px]" style={{ color: i <= step ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.35)', fontWeight: i <= step ? 500 : 400 }}>{s}</span>
      </div>
      {i < steps.length - 1 && (
        <div style={{ width: 20, height: 1, background: i < step ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.1)' }} />
      )}
    </div>
  ))}
</div>
```

Replace with:
```tsx
<div className="flex items-center justify-center gap-2 mb-10">
  {steps.map((s, i) => (
    <div key={i} className="flex items-center gap-2">
      <div className="flex items-center gap-2">
        <div style={{
          width: 30, height: 30, borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: i <= step ? 'rgba(255,255,255,0.10)' : 'rgba(255,255,255,0.03)',
          border: `1px solid ${i === step ? 'rgba(167,139,250,0.5)' : i < step ? 'rgba(74,222,128,0.3)' : 'rgba(255,255,255,0.05)'}`,
          boxShadow: i === step ? '0 0 16px rgba(167,139,250,0.2), inset 0 0 8px rgba(167,139,250,0.08)' : 'none',
          transition: 'all 0.4s ease',
        }}>
          {i < step ? (
            <Check className="w-3.5 h-3.5" style={{ color: 'rgba(74,222,128,0.85)' }} />
          ) : (
            <span style={{ fontSize: 11, fontWeight: 700, color: i <= step ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.35)' }}>{i + 1}</span>
          )}
        </div>
        <span className="hidden sm:inline text-[11px]" style={{
          color: i === step ? 'rgba(167, 139, 250, 0.8)' : i < step ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.25)',
          fontWeight: i === step ? 600 : 400
        }}>{s}</span>
      </div>
      {i < steps.length - 1 && (
        <div style={{
          width: 24, height: 1.5, borderRadius: 1,
          background: i < step
            ? 'linear-gradient(90deg, rgba(74,222,128,0.3), rgba(255,255,255,0.1))'
            : 'rgba(255,255,255,0.08)'
        }} />
      )}
    </div>
  ))}
</div>
```

---

### Task 3: NewProjectWizard — Option Buttons Contrast

**Files:**
- Modify: `src/pages/NewProjectWizard.tsx` (all `tagStyle` usages and inline button styles)

- [ ] **Step 1: Update tagStyle function**

Current (line 142-146):
```tsx
const tagStyle = (active: boolean) => ({
  border: active ? '1px solid rgba(255,255,255,0.15)' : '1px solid rgba(255,255,255,0.06)',
  background: active ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)',
  color: active ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.45)',
})
```

Replace with:
```tsx
const tagStyle = (active: boolean) => ({
  border: active ? '1px solid rgba(167,139,250,0.4)' : '1px solid rgba(255,255,255,0.06)',
  background: active ? 'rgba(167,139,250,0.15)' : 'rgba(255,255,255,0.03)',
  color: active ? 'rgba(220,210,255,0.95)' : 'rgba(255,255,255,0.50)',
  boxShadow: active ? '0 0 12px rgba(167,139,250,0.08)' : 'none',
})
```

- [ ] **Step 2: Update story type buttons (lines 241-255)**

Replace the inline style objects for story type buttons. The `selected` pattern changes from:
```tsx
style={{
  background: style.story_type === k ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.07)',
  border: `1px solid ${style.story_type === k ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.16)'}`,
  color: style.story_type === k ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.60)',
}}
```

To:
```tsx
style={{
  background: style.story_type === k ? 'rgba(167,139,250,0.15)' : 'rgba(255,255,255,0.04)',
  border: `1px solid ${style.story_type === k ? 'rgba(167,139,250,0.4)' : 'rgba(255,255,255,0.06)'}`,
  color: style.story_type === k ? 'rgba(230,220,255,0.95)' : 'rgba(255,255,255,0.55)',
  boxShadow: style.story_type === k ? '0 0 16px rgba(167,139,250,0.10)' : 'none',
}}
```

- [ ] **Step 3: Update genre/mood tag buttons (lines 262-289, 361-390)**

Replace ALL `selectedGenres.includes(g)` / `selectedMoods.includes(m)` inline style blocks to use the new purple active scheme (same pattern as step 2: `rgba(167,139,250,0.15)` active background, `rgba(167,139,250,0.4)` active border, bright text).

For unselected:
```tsx
{ border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.50)' }
```

For selected:
```tsx
{ border: '1px solid rgba(167,139,250,0.4)', background: 'rgba(167,139,250,0.15)', color: 'rgba(220,210,255,0.95)', boxShadow: '0 0 12px rgba(167,139,250,0.08)' }
```

- [ ] **Step 4: Update style preference buttons (lines 303-357)**

Same pattern — replace ALL `active` inline styles in step 1 (writing_style, visual_style, art_style, etc.) with the new purple active scheme.

---

### Task 4: NewProjectWizard — Form Inputs + Navigation Buttons

**Files:**
- Modify: `src/pages/NewProjectWizard.tsx`

- [ ] **Step 1: Replace all text inputs with premium-input**

Find all `<input>` with inline style `background: 'rgba(255,255,255,0.08)'` and add `premium-input` class. Also add `premium-select` to the model `<select>`.

For each input (appears at lines 349, 435, 437, 442, 455, 468, 475, 488), change:
```tsx
className="w-full ... outline-none"
style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
```
To:
```tsx
className="w-full premium-input rounded-xl px-4 py-2.5 text-xs"
```

- [ ] **Step 2: Update navigation buttons**

"上一步" button (lines 500-503):
```tsx
// Replace from:
<button ... className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-[11px] transition-all"
  style={{ border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.05)' }}>
  <ArrowLeft className="w-3.5 h-3.5" /> 上一步
</button>

// To:
<button ... className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] transition-all hover:opacity-80"
  style={{ color: 'rgba(255,255,255,0.45)' }}>
  <ArrowLeft className="w-3.5 h-3.5" /> 上一步
</button>
```

"下一步" button (lines 506-514):
```tsx
// Replace from:
<button ... className="flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-[11px] font-medium transition-all"
  style={{ background: '#fff', color: '#000' }}>
  下一步 <ArrowRight className="w-3.5 h-3.5" />
</button>

// To:
<button ... className="flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-[11px] font-medium transition-all hover:gap-3"
  style={{ background: 'linear-gradient(135deg, #fff, rgba(255,255,255,0.85))', color: '#000' }}>
  下一步 <ArrowRight className="w-3.5 h-3.5" />
</button>
```

"开始创作" button (lines 516-520):
```tsx
// Replace from:
<button ... className="flex items-center gap-1.5 px-8 py-2.5 rounded-xl text-[11px] font-medium transition-all disabled:opacity-40"
  style={{ background: '#fff', color: '#000' }}>
  <Sparkles className="w-3.5 h-3.5" /> {loading ? '创建中...' : '开始创作'}
</button>

// To:
<button ... className="flex items-center gap-1.5 px-8 py-3 rounded-xl text-[11px] font-medium transition-all disabled:opacity-40 hover:scale-[1.02]"
  style={{ background: 'linear-gradient(135deg, #fff, rgba(255,255,255,0.85))', color: '#000', boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}>
  <Sparkles className="w-3.5 h-3.5" /> {loading ? '创建中...' : '开始创作'}
</button>
```

---

### Task 5: NewProjectWizard — Step Transition Animation

**Files:**
- Modify: `src/pages/NewProjectWizard.tsx`

- [ ] **Step 1: Add step transition effect**

Wrap the card content in a container that fades + slides on step change. Replace the key-based re-render approach with a CSS transition.

Find the `<div key={step}>` wrapping the card content (currently the `key={step}` on the inner div at line 195). Change it to:

```tsx
<div className="transition-all duration-400"
  style={{
    animation: 'fade-slide-in 0.4s cubic-bezier(0.22, 0.61, 0.36, 1) forwards'
  }}
  key={step}>
```

- [ ] **Step 2: Add the CSS keyframe if not already present**

In `src/index.css`, add:
```css
@keyframes fade-slide-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

---

### Task 6: PhaseTimeline — premium-subpanel + Visual States

**Files:**
- Modify: `src/components/PhaseTimeline.tsx`

- [ ] **Step 1: Read the current component structure**

Read `src/components/PhaseTimeline.tsx` to understand current className assignments before modifying.

- [ ] **Step 2: Apply premium-subpanel to the sidebar container**

Find the outermost div of PhaseTimeline and change its className to include `premium-subpanel`.

- [ ] **Step 3: Add visual state differentiation for phase items**

Find each phase item render loop. For each phase item, add conditional styling:
- **Done:** `borderLeft: '2px solid rgba(74,222,128,0.4)'` + green dot
- **Active (currentPhase):** `borderLeft: '2px solid rgba(167,139,250,0.6)'` + pulse animation on dot
- **Selected (for viewing):** `background: 'rgba(167,139,250,0.10)'`
- **Pending:** dim text, no border accent

---

### Task 7: Workspace — Main Content Area premium-panel

**Files:**
- Modify: `src/pages/Workspace.tsx`

- [ ] **Step 1: Replace main content area background**

Find the `<main>` element (line 467):
```tsx
<main className="flex-1 flex flex-col overflow-hidden relative z-10" style={{ background: 'rgba(255,255,255,0.02)' }}>
```

Replace with:
```tsx
<main className="flex-1 flex flex-col overflow-hidden relative z-10 premium-panel" style={{ borderRadius: 0, borderLeft: '1px solid rgba(255,255,255,0.06)' }}>
```

Note: `borderRadius: 0` because the panel needs to fill edge-to-edge vertically. The top accent line and inner glow from premium-panel will give the workspace a premium feel.

- [ ] **Step 2: Adjust internal padding for content area**

Ensure the content area (where stream/view content renders) has proper padding:
```tsx
<div className="max-w-3xl mx-auto p-10">
```

---

### Task 8: Workspace — Bottom Control Bar

**Files:**
- Modify: `src/pages/Workspace.tsx`

- [ ] **Step 1: Update bottom control bar styling**

Find all bottom bars with this pattern:
```tsx
style={{ borderTop: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' }}
```

Replace each occurrence with the `premium-panel` style (flat bottom bar version). Add a CSS class or shared inline pattern:

```tsx
className="p-5 animate-fade-in-up"
style={{
  borderTop: '1px solid rgba(139,92,246,0.15)',
  background: 'rgba(255,255,255,0.06)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
}}
```

There are approximately 6 bars (approval, version, proceed, episode, paused, confirmed phase) — lines 609, 651, 689, 715, 792, 807. Update ALL of them to use the same consistent style.

- [ ] **Step 2: Update approve/revise/edit buttons**

Replace buttons using `border-border` or `bg-muted` or `hover:bg-muted` with new premium style:

**Approve button (通过):**
```tsx
<button ... className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
  style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
```

**Revise button (修改):**
```tsx
<button ... className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
  style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
  onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
  onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
```

**Edit button (编辑):**
```tsx
<button ... className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
  style={{ color: 'rgba(255,255,255,0.5)' }}
  onMouseOver={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
  onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)' }}>
```

**Continue button (继续):**
```tsx
<button ... className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
  style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
```

---

### Task 9: Workspace — Celebration Page Polish

**Files:**
- Modify: `src/pages/Workspace.tsx`
- Modify: `src/index.css`

- [ ] **Step 1: Add celebration animation CSS**

In `src/index.css`, add:
```css
/* Celebration page */
@keyframes celebrate-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

@keyframes celebrate-fade-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes star-drift {
  0% { opacity: 0; transform: translateY(0) scale(0.5); }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-60px) scale(1.2); }
}
```

- [ ] **Step 2: Update the celebration page section (lines 468-513)**

Wrap the celebration content in `animate-fade-in-up` and style the elements:

Main icon container:
```tsx
<div style={{ animation: 'celebrate-float 3s ease-in-out infinite' }}>
```

Title:
```tsx
<h2 className="text-xl font-bold mb-1" style={{
  background: 'linear-gradient(135deg, rgba(74,222,128,0.95), rgba(52,211,153,0.85))',
  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
}}>完成所有任务！</h2>
```

Entire section:
```tsx
<div className="flex-1 flex items-center justify-center" style={{ animation: 'celebrate-fade-in 0.6s ease forwards' }}>
```

---

### Task 10: Build and Verify

**Files:**
- Run: `npm run build`

- [ ] **Step 1: Run build**

```bash
npm run build
```

Expected: No errors, all transforms pass.

- [ ] **Step 2: Start dev server and spot-check**

Start `npm run dev` and manually verify:
1. NewProjectWizard card has premium-panel styling with top accent line
2. Step indicators have glow effects for active/completed
3. Option buttons have strong selected/unselected contrast (purple scheme)
4. Inputs have premium-input styling
5. Navigation buttons updated
6. Step transition animation plays
7. Workspace main area has premium-panel border/glow
8. PhaseTimeline sidebar has premium-subpanel styling with state colors
9. Bottom control bars have consistent glass style
10. Buttons (approve/revise/edit/continue) use new styles
11. Celebration page has entrance animation and visual polish

---
