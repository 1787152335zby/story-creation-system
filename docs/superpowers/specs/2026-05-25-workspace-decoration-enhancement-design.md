# Workspace Decoration Enhancement

## Goal

Add 3 decorative layers to the Workspace `premium-panel` main content area so it matches the visual richness of CosmicHomePage's h-cards.

## Changes

### CSS: Add `.premium-panel-rich` class

A new CSS class for the Workspace main panel. On hover it reveals three decorative effects found on homepage cards:

1. **Conic gradient border** — subtle rotating purple glow on the panel edges (opacity 0 → 0.4 on hover)
2. **Sweep shimmer** — diagonal light sweep across the panel (left → right on hover)  
3. **Bottom glow** — soft purple gradient rising from the bottom edge

### Implementation

- Modify `src/index.css` to add `.premium-panel-rich`
- Modify `src/pages/Workspace.tsx` to add `premium-panel-rich` class alongside existing `premium-panel`

No logic changes, no new dependencies.
