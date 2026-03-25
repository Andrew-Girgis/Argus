# Argus Brand Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two deliverables — a standalone `brandkit.html` visual reference page and a `brandkit.md` frontend implementation guide — codifying the Argus dark neumorphic design system.

**Architecture:** Two independent files at the project root. `brandkit.md` defines all design tokens mapped to the existing React/Tailwind/shadcn stack. `brandkit.html` is a self-contained visual showcase (not part of the React app) that renders every token and component mockup live.

**Tech Stack:** HTML/CSS/JS (brandkit.html), Markdown (brandkit.md), Google Fonts CDN, Lucide CDN icons

---

## File Structure

| File | Purpose |
|---|---|
| `brandkit.md` | Frontend implementation reference — CSS variables, Tailwind tokens, type scale, component patterns |
| `brandkit.html` | Self-contained visual brand kit page — color swatches, type samples, component mockups, dark/light toggle |

---

### Task 1: Write `brandkit.md` — Design Token Reference

**Files:**
- Create: `brandkit.md`

- [ ] **Step 1: Create `brandkit.md` with full token documentation**

Write the complete file with these sections:

```markdown
# Argus Brand Kit

> Precision property intelligence. Built for analysts, investors, and curious homeowners.
> Design system: Dark Neumorphic Soft UI — inspired by Abhinai Adhikaram's neumorphic system, remixed for dark mode intelligence UI.

---

## 1. Color System

### Dark Mode (Primary)

All values provided in both hex (for reference) and oklch (for `index.css` integration).

| Token | Hex | oklch | Tailwind Class | Role |
|---|---|---|---|---|
| `--background` | `#0F172A` | `oklch(0.155 0.044 264.1)` | `bg-background` | Page background, deepest layer |
| `--card` | `#1a2236` | `oklch(0.195 0.035 264.1)` | `bg-card` | Card faces, interactive elements |
| `--popover` | `#1a2236` | `oklch(0.195 0.035 264.1)` | `bg-popover` | Popover/dropdown surfaces |
| `--primary` | `#6366F1` | `oklch(0.541 0.222 264.1)` | `bg-primary` | CTAs, active states, key actions |
| `--primary-foreground` | `#FFFFFF` | `oklch(1 0 0)` | `text-primary-foreground` | Text on primary buttons |
| `--secondary` | `#1E293B` | `oklch(0.216 0.029 264.1)` | `bg-secondary` | Secondary surfaces |
| `--secondary-foreground` | `#C8D2E0` | `oklch(0.862 0.015 264.1)` | `text-secondary-foreground` | Text on secondary surfaces |
| `--muted` | `#1E293B` | `oklch(0.216 0.029 264.1)` | `bg-muted` | Muted backgrounds |
| `--muted-foreground` | `#7c8db5` | `oklch(0.623 0.06 264.1)` | `text-muted-foreground` | Tertiary text |
| `--accent` | `#A5B4FC` | `oklch(0.771 0.128 264.1)` | `bg-accent` | Data highlights, chip text, links |
| `--accent-foreground` | `#0F172A` | `oklch(0.155 0.044 264.1)` | `text-accent-foreground` | Text on accent backgrounds |
| `--destructive` | `#EF4444` | `oklch(0.577 0.245 27.3)` | `bg-destructive` | Errors, value decreases |
| `--border` | `rgba(99,102,241,0.15)` | `oklch(0.541 0.222 264.1 / 15%)` | `border-border` | Default borders |
| `--input` | `rgba(99,102,241,0.2)` | `oklch(0.541 0.222 264.1 / 20%)` | `border-input` | Input borders |
| `--ring` | `#6366F1` | `oklch(0.541 0.222 264.1)` | `ring-ring` | Focus rings |
| `--foreground` | `#FFFFFF` | `oklch(1 0 0)` | `text-foreground` | Primary text |

#### Neumorphic Surface Tokens (new — add to `@theme inline`)

| Token | Value | Purpose |
|---|---|---|
| `--surface-raised` | `#161d2f` | Neumorphic base surface (between background and card) |
| `--neu-shadow-dark` | `#0a0e1a` | Dark offset for neumorphic shadows |
| `--neu-shadow-light` | `#242e48` | Light offset for neumorphic shadows |
| `--accent-glow` | `rgba(99,102,241,0.4)` | Glow effects on active indicators |

#### Functional Colors

| Token | Hex | Use |
|---|---|---|
| `--success` | `#22C55E` | Positive signals, value increases |
| `--warning` | `#F59E0B` | Caution, moderate confidence |
| `--error` | `#EF4444` | Errors, value decreases |
| `--neutral` | `#64748B` | Disabled, tertiary info |

#### Chart Colors (remap existing shadcn chart tokens)

| Token | oklch | Hex | Use |
|---|---|---|---|
| `--chart-1` | `oklch(0.541 0.222 264.1)` | `#6366F1` | Primary data series (indigo) |
| `--chart-2` | `oklch(0.771 0.128 264.1)` | `#A5B4FC` | Secondary data series (light indigo) |
| `--chart-3` | `oklch(0.627 0.209 145.5)` | `#22C55E` | Tertiary / positive (green) |
| `--chart-4` | `oklch(0.702 0.164 79.5)` | `#F59E0B` | Quaternary / warning (amber) |
| `--chart-5` | `oklch(0.577 0.245 27.3)` | `#EF4444` | Quinary / negative (red) |

#### Map / Geo Accent Colors

| Category | Hex | Use |
|---|---|---|
| Isochrone 5min | `rgba(99,102,241,0.4)` | Innermost walk ring |
| Isochrone 10min | `rgba(99,102,241,0.25)` | Middle ring |
| Isochrone 15min | `rgba(99,102,241,0.15)` | Outermost ring |
| Transit POI | `#A5B4FC` | Bus, subway, rail markers |
| Parks POI | `#22C55E` | Green space markers |
| Schools POI | `#F59E0B` | Education markers |
| Hospitals POI | `#EF4444` | Healthcare markers |
| Retail POI | `#818CF8` | Shopping markers |
| Selected Parcel | `#6366F1` stroke, `rgba(99,102,241,0.1)` fill | Active property boundary |
| Overlay panels | `var(--card)` at 95% opacity | Map info panels |

### Light Mode (Secondary)

| Token | oklch |
|---|---|
| `--background` | `oklch(0.965 0.005 264.1)` |
| `--card` | `oklch(1 0 0)` |
| `--foreground` | `oklch(0.155 0.044 264.1)` |
| `--secondary` | `oklch(0.932 0.005 264.1)` |
| `--muted-foreground` | `oklch(0.488 0.03 264.1)` |
| `--neu-shadow-dark` | `#d1d5db` |
| `--neu-shadow-light` | `#ffffff` |
| `--surface-raised` | `#E8ECF1` |
| Accent colors | Unchanged from dark mode |

---

## 2. Typography

### Font Stack

| Role | Font | Fallback | CSS Variable | Install |
|---|---|---|---|---|
| Headlines | Space Grotesk | system-ui, sans-serif | `--font-heading` | `@fontsource-variable/space-grotesk` |
| UI / Body | Inter | system-ui, sans-serif | `--font-sans` | `@fontsource-variable/inter` |
| Data Values | JetBrains Mono | Fira Code, monospace | `--font-mono` | `@fontsource-variable/jetbrains-mono` |

#### index.css font imports (replace existing Geist import)

```css
@import "@fontsource-variable/space-grotesk";
@import "@fontsource-variable/inter";
@import "@fontsource-variable/jetbrains-mono";
```

#### @theme inline overrides

```css
@theme inline {
  --font-heading: "Space Grotesk Variable", system-ui, sans-serif;
  --font-sans: "Inter Variable", system-ui, sans-serif;
  --font-mono: "JetBrains Mono Variable", "Fira Code", monospace;
}
```

### Type Scale

| Level | Font | Size | Weight | Line Height | Letter Spacing | Tailwind Example |
|---|---|---|---|---|---|---|
| Hero | Space Grotesk | 48px (3rem) | 700 | 1.1 | -0.03em | `font-heading text-5xl font-bold leading-tight tracking-tighter` |
| H1 | Space Grotesk | 36px (2.25rem) | 700 | 1.15 | -0.02em | `font-heading text-4xl font-bold leading-tight tracking-tight` |
| H2 | Space Grotesk | 28px (1.75rem) | 600 | 1.2 | -0.015em | `font-heading text-3xl font-semibold leading-snug` |
| H3 | Space Grotesk | 22px (1.375rem) | 600 | 1.25 | -0.01em | `font-heading text-xl font-semibold` |
| Body Large | Inter | 18px (1.125rem) | 400 | 1.6 | 0 | `text-lg leading-relaxed` |
| Body | Inter | 15px (0.9375rem) | 400 | 1.6 | 0 | `text-[15px] leading-relaxed` |
| Caption | Inter | 13px (0.8125rem) | 500 | 1.4 | 0.01em | `text-sm font-medium tracking-wide` |
| Data Value | JetBrains Mono | 13px | 500 | 1.4 | 0.02em | `font-mono text-sm font-medium tracking-wider` |
| Label | Inter | 11px (0.6875rem) | 600 | 1.2 | 0.08em | `text-xs font-semibold uppercase tracking-widest` |

### UI-Specific Typography

| Element | Font | Size | Weight | Notes |
|---|---|---|---|---|
| Buttons | Inter | 14px | 600 | Sentence case |
| Navigation | Inter | 14px | 500 | Sentence case |
| Card titles | Space Grotesk | 18px | 600 | — |
| Form labels | Inter | 12px | 500 | Uppercase, 0.06em tracking |
| Data callouts | JetBrains Mono | 13–15px | 500 | Coordinates, confidence %, stat values |

---

## 3. Component Tokens

### Border Radius

| Token | Value | Tailwind |
|---|---|---|
| `--radius` | `0.625rem` (10px) | `rounded-lg` (base) |
| `--radius-sm` | `6px` | `rounded-sm` |
| `--radius-md` | `10px` | `rounded-md` |
| `--radius-lg` | `16px` | `rounded-lg` |
| `--radius-full` | `9999px` | `rounded-full` |

### Neumorphic Shadow Scale

Add these as CSS custom properties in `:root` / `.dark`:

| Token | Value | Use |
|---|---|---|
| `--neu-flat` | `6px 6px 14px var(--neu-shadow-dark), -6px -6px 14px var(--neu-shadow-light)` | Default card state |
| `--neu-pressed` | `inset 3px 3px 6px var(--neu-shadow-dark), inset -3px -3px 6px var(--neu-shadow-light)` | Inputs, active chips, pressed buttons |
| `--neu-elevated` | `10px 10px 20px var(--neu-shadow-dark), -10px -10px 20px var(--neu-shadow-light)` | Modals, elevated panels |
| `--neu-glow` | `0 0 8px var(--accent-glow)` | Active indicators, confidence dots |

#### Tailwind usage via arbitrary values

```html
<!-- Flat neumorphic card -->
<div class="shadow-[var(--neu-flat)]">...</div>

<!-- Pressed/inset input -->
<input class="shadow-[var(--neu-pressed)]" />

<!-- Elevated modal -->
<div class="shadow-[var(--neu-elevated)]">...</div>

<!-- Glowing indicator -->
<span class="shadow-[var(--neu-glow)]">...</span>
```

### Spacing Scale (4px base grid)

| Step | Value | Tailwind |
|---|---|---|
| 1 | 4px | `p-1` / `gap-1` |
| 2 | 8px | `p-2` / `gap-2` |
| 3 | 12px | `p-3` / `gap-3` |
| 4 | 16px | `p-4` / `gap-4` |
| 5 | 20px | `p-5` / `gap-5` |
| 6 | 24px | `p-6` / `gap-6` |
| 8 | 32px | `p-8` / `gap-8` |
| 10 | 40px | `p-10` / `gap-10` |
| 12 | 48px | `p-12` / `gap-12` |
| 16 | 64px | `p-16` / `gap-16` |
| 20 | 80px | `p-20` / `gap-20` |

### Icon Sizing

| Context | Size | Tailwind |
|---|---|---|
| Inline (with text) | 16px | `size-4` |
| UI elements | 20px | `size-5` |
| Feature highlights | 24px | `size-6` |
| Hero / empty states | 32px | `size-8` |

Icon library: **Lucide React** (`lucide-react`)

### Map Overlay Standards

| Element | Opacity | Notes |
|---|---|---|
| Isochrone fill | 15–40% | Graduated by ring distance |
| POI markers | 90% | Consistent across categories |
| Overlay panels | 95% | With `backdrop-blur-xl` (12px) |
| Map attribution | — | `text-muted-foreground text-[10px]` |

---

## 4. Component Patterns (React/shadcn)

### Property Card

```tsx
<Card className="bg-card shadow-[var(--neu-flat)] rounded-2xl overflow-hidden">
  <div className="aspect-[16/10] bg-muted rounded-t-2xl" />
  <CardContent className="p-5 space-y-3">
    <h3 className="font-heading text-2xl font-bold text-foreground">$847,000</h3>
    <p className="text-sm text-muted-foreground">123 Queen St W, Toronto, ON</p>
    <div className="flex gap-3 text-xs text-muted-foreground">
      <span>3 bed</span><span>&middot;</span>
      <span>2 bath</span><span>&middot;</span>
      <span>1,847 sqft</span>
    </div>
    <InsightChip label="Pool Detected" confidence={94} />
  </CardContent>
</Card>
```

### Search Bar

```tsx
<div className="bg-card shadow-[var(--neu-flat)] focus-within:shadow-[var(--neu-pressed)] rounded-xl px-4 py-3.5 flex items-center gap-3 transition-shadow">
  <Search className="size-5 text-primary" />
  <input
    className="bg-transparent text-foreground placeholder:text-muted-foreground text-sm font-sans outline-none flex-1"
    placeholder="Enter an address, city, or postal code"
  />
</div>
```

### Insight Chip

```tsx
<div className="inline-flex items-center gap-2 bg-card shadow-[var(--neu-pressed)] rounded-lg px-3 py-1.5">
  <span className="size-1.5 rounded-full bg-primary shadow-[var(--neu-glow)]" />
  <span className="font-mono text-xs font-medium text-accent tracking-wider">
    {label} · {confidence}%
  </span>
</div>
```

### Confidence Bar

```tsx
<div className="flex items-center gap-2.5">
  <div className="flex-1 h-1.5 bg-card shadow-[var(--neu-pressed)] rounded-full overflow-hidden">
    <div
      className="h-full bg-gradient-to-r from-primary to-accent rounded-full shadow-[var(--neu-glow)]"
      style={{ width: `${confidence}%` }}
    />
  </div>
  <span className="font-mono text-xs font-medium text-accent">{confidence}%</span>
</div>
```

---

## 5. index.css Integration Guide

Replace the contents of `frontend/src/index.css` with the Argus brand tokens. Key changes:

1. Replace `@import "@fontsource-variable/geist"` with the three font imports
2. Update `--font-heading` and `--font-sans` in `@theme inline`
3. Add `--font-mono` to `@theme inline`
4. Add neumorphic tokens (`--color-surface-raised`, `--neu-shadow-dark`, `--neu-shadow-light`, `--neu-flat`, `--neu-pressed`, `--neu-elevated`, `--neu-glow`, `--accent-glow`) to `@theme inline`
5. Remap all `:root` and `.dark` color values to the Argus palette in oklch
6. Update chart tokens to the brand palette
```

- [ ] **Step 2: Verify the file renders correctly in preview**

Open `brandkit.md` in VS Code preview or GitHub to confirm all tables render properly and no markdown syntax errors exist.

- [ ] **Step 3: Commit**

```bash
git add brandkit.md
git commit -m "feat: add Argus brand kit design token reference (brandkit.md)"
```

---

### Task 2: Build `brandkit.html` — Colors & Typography Sections

**Files:**
- Create: `brandkit.html`

- [ ] **Step 1: Create the HTML file with page shell, sidebar nav, dark/light toggle, and Colors section**

Create `brandkit.html` at the project root. This is a single self-contained HTML file. Include:

- Google Fonts CDN imports: Space Grotesk, Inter, JetBrains Mono
- Lucide CDN (unpkg)
- Embedded Argus SVG logo (copy from `assets/argus-logo.svg` and `assets/argus-logo-light.svg`)
- CSS custom properties matching the full token set from `brandkit.md`
- Sticky sidebar navigation with links: Colors, Typography, Components, Spacing
- Dark/light mode toggle button in the top-right header
- JavaScript for: dark/light toggle (adds/removes `.dark` class on `<html>`, swaps CSS variables), smooth scroll nav, active section highlighting on scroll

**Colors section** should render:
- Surface colors as large rectangular swatches showing `--background`, `--surface-raised`, `--card` side by side with their hex, oklch, and CSS variable name
- Accent colors: `--primary`, `--accent` as swatches with glow preview
- Functional colors: success, warning, error, neutral as a row of circles
- Text hierarchy: each level rendered as sample text on the background color
- Map/geo accents: colored dots with category labels (transit, parks, schools, hospitals, retail) plus an isochrone ring preview (three concentric circles at graduated opacity)

- [ ] **Step 2: Add the Typography section**

Append to the same file, after the Colors section:

- Full type scale rendered live: Hero → H1 → H2 → H3 → Body Large → Body → Caption → Data Value → Label, each showing "123 Queen Street West" or contextually appropriate sample text at the correct font, size, weight, line-height, and letter-spacing
- Font stack display: show each font family name rendered in itself
- UI-specific rules: a mini table showing Button, Nav, Card Title, Form Label, Data Callout styles each rendered live

- [ ] **Step 3: Verify in browser**

Open `brandkit.html` in a browser. Confirm:
- Sidebar nav links scroll to correct sections
- Dark/light toggle swaps all colors correctly
- All color swatches display with correct hex labels
- Typography renders at correct sizes with correct fonts
- Google Fonts load successfully

- [ ] **Step 4: Commit**

```bash
git add brandkit.html
git commit -m "feat: add brandkit.html with colors and typography sections"
```

---

### Task 3: Add Component Mockups Section to `brandkit.html`

**Files:**
- Modify: `brandkit.html`

- [ ] **Step 1: Add Property Card mockup**

Add a "Components" section after Typography. Build a Property Card component mockup:
- Neumorphic card (`--neu-flat` shadow) on `--surface-raised` background
- Image placeholder area (16:10 ratio, rounded top, dark gradient placeholder with a house icon from Lucide)
- Price: `$847,000` in Space Grotesk 24px/700
- Address: `123 Queen St W, Toronto, ON` in Inter 13px, `--text-tertiary` color (`--muted-foreground`)
- Stats row: `3 bed · 2 bath · 1,847 sqft` in Inter 12px, `--text-muted` color
- Two insight chips: "Pool Detected · 94%" and "Renovated Kitchen · 87%" using neumorphic inset style with glowing dots
- Confidence bar below chips (gradient fill from `--primary` to `--accent`)
- "View Intelligence" button with neumorphic flat shadow, indigo text, arrow icon

- [ ] **Step 2: Add Search Bar mockup**

Below the property card, add:
- Full-width search bar with neumorphic flat shadow
- Lucide `Search` icon in `--primary` color on the left
- Placeholder text: "Enter an address, city, or postal code"
- On focus (use `:focus-within`), shadow transitions to `--neu-pressed` (inset)
- Right side: a small neumorphic button with Lucide `MapPin` icon

- [ ] **Step 3: Add Stat/Insight Chip component showcase**

Below the search bar, add a row of chips in different states:
- Default chip: "Pool Detected · 94%" with glowing indigo dot
- Warning chip: "Roof Age · 22 yrs" with amber dot using `--warning` color
- Success chip: "Value Trend · +12%" with green dot using `--success` color
- Error chip: "Foundation Risk · High" with red dot using `--error` color
- Show each chip with its neumorphic pressed shadow and the corresponding functional color dot

- [ ] **Step 4: Add Map Panel mockup**

Below the chips, add a map panel mockup:
- Full-width container on `--surface-raised` background with `--neu-elevated` shadow
- Dark map placeholder area (dark gray/navy gradient to simulate a dark-themed map, no actual map tile needed)
- Three concentric isochrone rings centered in the map area: innermost at 40% opacity `--primary`, middle at 25%, outermost at 15%
- POI legend overlay panel in bottom-left: frosted glass style (`--card` at 95% opacity, `backdrop-filter: blur(12px)`), showing colored dots + labels for Transit, Parks, Schools, Hospitals, Retail
- A small info callout panel in top-right of the map: showing coordinates in JetBrains Mono (`43.6532°N, 79.3832°W`) and a confidence badge

- [ ] **Step 5: Verify all components in browser**

Open `brandkit.html`. Confirm:
- Property card renders with correct neumorphic shadows in both dark and light mode
- Search bar focus state transitions shadow correctly
- All chip variants display correct functional colors
- Map panel shows isochrone rings and legend
- All components use the correct fonts and colors from the token system

- [ ] **Step 6: Commit**

```bash
git add brandkit.html
git commit -m "feat: add component mockups to brandkit.html (card, search, chips, map)"
```

---

### Task 4: Add Spacing & Tokens Section to `brandkit.html`

**Files:**
- Modify: `brandkit.html`

- [ ] **Step 1: Add Spacing section**

After Components, add a "Spacing" section:
- Visual spacing scale: render rectangles at each step (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80px) with the pixel value labeled, using `--primary` color at 20% opacity as fill
- Border radius showcase: five boxes showing `none`, `sm` (6px), `md` (10px), `lg` (16px), `full` (9999px) with labels
- Neumorphic shadow showcase: four cards showing `--neu-flat`, `--neu-pressed`, `--neu-elevated`, and `--neu-glow` states with labels
- Icon sizing guide: four Lucide icons (e.g., Home, MapPin, Search, Eye) rendered at 16px, 20px, 24px, 32px with size labels

- [ ] **Step 2: Verify spacing section**

Open in browser. Confirm spacing rectangles are proportional, shadows render correctly in both modes, and icons display at correct sizes.

- [ ] **Step 3: Final commit**

```bash
git add brandkit.html
git commit -m "feat: add spacing and token reference section to brandkit.html"
```

---

### Task 5: Final Review & Polish

**Files:**
- Modify: `brandkit.html`
- Modify: `brandkit.md`

- [ ] **Step 1: Cross-check brandkit.md tokens against brandkit.html**

Verify that every token defined in `brandkit.md` is visually represented in `brandkit.html`. Check:
- All color hex values match between files
- All typography sizes/weights match
- All shadow definitions match
- Neumorphic token names are consistent

- [ ] **Step 2: Test dark/light mode toggle end-to-end**

Toggle between dark and light mode in `brandkit.html`. Verify:
- All surface colors swap correctly
- Neumorphic shadows use the correct light-mode shadow colors
- Text hierarchy remains legible
- Component mockups look correct in both modes
- Logo swaps between dark and light variants

- [ ] **Step 3: Polish responsive behavior**

Verify the page is usable at common viewport widths (1440px, 1024px, 768px). The sidebar should collapse to a top nav or hamburger on mobile. Component mockups should stack vertically on narrow viewports.

- [ ] **Step 4: Final commit**

```bash
git add brandkit.html brandkit.md
git commit -m "feat: finalize Argus brand kit — polish and cross-check tokens"
```
