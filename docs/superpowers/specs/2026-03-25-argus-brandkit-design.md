# Argus Brand Kit — Design Spec

## Overview

Build a visual brand kit for Argus, a property intelligence platform. Two deliverables:

1. **`brandkit.html`** — Self-contained interactive brand kit page with live-rendered color swatches, typography samples, component mockups, sticky nav, and dark/light mode toggle.
2. **`brandkit.md`** — Referenceable design token and guideline document for the frontend team.

## Brand Identity

- **Name Origin**: Argus Panoptes — the all-seeing giant of Greek mythology with a hundred eyes. The visual identity subtly carries a sense of omniscience and total visibility. This manifests through: radial/lens-like motifs, concentric circle elements, and the eye-inspired logomark. The mythology is a whisper in the design, not a costume — abstract and precise, never literal or illustrative.
- **Positioning**: Precision property intelligence. Built for analysts, investors, and curious homeowners.
- **Tone**: Authoritative, data-driven, trustworthy. Clean and professional. "Bloomberg meets Zillow."
- **Visual Philosophy**: Dark neumorphic soft UI with tactile embossed depth. Data-forward intelligence layer — monospace for data values, confidence scores, coordinates. Card-based layouts, photography-forward, clear information hierarchy. The Argus Panoptes motif threads through the system as concentric rings (isochrones, confidence indicators, loading states), radial scan patterns (search animations, data processing), and the ever-present eye logomark — reinforcing omniscient property intelligence.
- **Inspiration**: Zillow's card-heavy, address-search-centered UI adapted with neumorphic depth system inspired by Abhinai Adhikaram's Soft UI design system, remixed for dark mode.

### Visual Motif: The All-Seeing Eye

The Argus Panoptes mythology informs these recurring design elements:

| Motif | Where It Appears | How It Manifests |
|---|---|---|
| **Concentric rings** | Isochrone map overlays, confidence indicators, loading spinners | Expanding rings from a center point — echoes the hundred eyes radiating outward |
| **Radial scan** | Search animation, data processing indicator | A sweeping radial line (like a radar) suggesting constant surveillance of data |
| **Lens/iris** | Logo, empty states, section dividers | The existing eye logomark; simplified iris shapes as decorative accents |
| **Dot grid / constellation** | Background textures, data visualization empty states | Scattered dots suggesting many eyes watching — subtle, never busy |
| **Glow pulse** | Active confidence indicators, live data badges | A slow breathing glow on key indicators — the system is alive and watching |

## Design Decisions (User-Validated)

1. **Color direction**: Deep Ink + Indigo — near-black ink primary (`#0F172A`) with indigo accent (`#6366F1`). Editorial, data-heavy, Bloomberg-esque.
2. **Typography**: Space Grotesk (headlines) + Inter (UI/body) + JetBrains Mono (data values). Geometric/fintech feel.
3. **Component style**: Dark Neumorphic — tactile embossed aesthetic on dark ink palette (`#161d2f` / `#1a2236`). Dual-shadow system with inset variants. Indigo glow accents.

## Color System

### Dark Mode (Primary)

| Token | Hex | Role |
|---|---|---|
| `--surface-base` | `#0F172A` | Page background, deepest layer |
| `--surface-raised` | `#161d2f` | Neumorphic base surface |
| `--surface-card` | `#1a2236` | Card faces, interactive elements |
| `--neu-shadow-dark` | `#0a0e1a` | Neumorphic dark offset shadow |
| `--neu-shadow-light` | `#242e48` | Neumorphic light offset shadow |
| `--accent-primary` | `#6366F1` | CTAs, active states, key actions |
| `--accent-light` | `#A5B4FC` | Data highlights, chip text, links |
| `--accent-glow` | `rgba(99,102,241,0.4)` | Glow effects on indicators |

### Functional Colors

| Token | Hex | Use |
|---|---|---|
| `--success` | `#22C55E` | Positive signals, value increases |
| `--warning` | `#F59E0B` | Caution, moderate confidence |
| `--error` | `#EF4444` | Errors, value decreases |
| `--neutral` | `#64748B` | Disabled, tertiary info |

### Text Hierarchy

| Token | Hex |
|---|---|
| `--text-primary` | `#FFFFFF` |
| `--text-secondary` | `#C8D2E0` |
| `--text-tertiary` | `#7c8db5` |
| `--text-muted` | `#5a6a8a` |
| `--text-disabled` | `#3a4560` |

### Map/Geo Accents

- Isochrone rings: `#6366F1` at 40%/25%/15% opacity (5/10/15 min)
- POI categories: `#A5B4FC` (transit), `#22C55E` (parks), `#F59E0B` (schools), `#EF4444` (hospitals), `#818CF8` (retail)
- Selected parcel: `#6366F1` stroke 2px, `rgba(99,102,241,0.1)` fill
- Map overlay panels: `--surface-card` at 95% opacity + backdrop-filter blur(12px)

### Light Mode (Secondary)

| Token | Light Value |
|---|---|
| `--surface-base` | `#F1F5F9` |
| `--surface-raised` | `#E8ECF1` |
| `--surface-card` | `#FFFFFF` |
| `--neu-shadow-dark` | `#d1d5db` |
| `--neu-shadow-light` | `#ffffff` |
| `--text-primary` | `#0F172A` |
| `--text-secondary` | `#334155` |
| `--text-tertiary` | `#64748B` |
| Accent colors | Unchanged |

## Typography System

### Font Stack

- **Primary (Headlines)**: `'Space Grotesk', system-ui, sans-serif`
- **Secondary (UI/Body)**: `'Inter', system-ui, sans-serif`
- **Monospace (Data)**: `'JetBrains Mono', 'Fira Code', monospace`

### Type Scale

| Level | Font | Size | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|---|
| Hero | Space Grotesk | 48px | 700 | 1.1 | -0.03em |
| H1 | Space Grotesk | 36px | 700 | 1.15 | -0.02em |
| H2 | Space Grotesk | 28px | 600 | 1.2 | -0.015em |
| H3 | Space Grotesk | 22px | 600 | 1.25 | -0.01em |
| Body Large | Inter | 18px | 400 | 1.6 | 0 |
| Body | Inter | 15px | 400 | 1.6 | 0 |
| Caption | Inter | 13px | 500 | 1.4 | 0.01em |
| Data Value | JetBrains Mono | 13px | 500 | 1.4 | 0.02em |
| Label | Inter | 11px | 600 | 1.2 | 0.08em (uppercase) |

### UI-Specific Rules

- **Buttons**: Inter 14px/600
- **Navigation**: Inter 14px/500
- **Card titles**: Space Grotesk 18px/600
- **Form labels**: Inter 12px/500 uppercase, 0.06em tracking
- **Data callouts**: JetBrains Mono 13-15px/500, used for coordinates, confidence %, prices in stat contexts

## Component Tokens

### Border Radius

| Token | Value |
|---|---|
| `--radius-none` | `0` |
| `--radius-sm` | `6px` |
| `--radius-md` | `10px` |
| `--radius-lg` | `16px` |
| `--radius-full` | `9999px` |

### Neumorphic Shadow Scale

| Token | Value |
|---|---|
| `--neu-flat` | `6px 6px 14px var(--neu-shadow-dark), -6px -6px 14px var(--neu-shadow-light)` |
| `--neu-pressed` | `inset 3px 3px 6px var(--neu-shadow-dark), inset -3px -3px 6px var(--neu-shadow-light)` |
| `--neu-elevated` | `10px 10px 20px var(--neu-shadow-dark), -10px -10px 20px var(--neu-shadow-light)` |
| `--neu-glow` | `0 0 8px var(--accent-glow)` |

### Spacing Scale (4px base)

`4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80`

### Icon Sizing

| Context | Size |
|---|---|
| Inline (with text) | 16px |
| UI elements | 20px |
| Feature highlights | 24px |
| Hero / empty states | 32px |
| Icon set | Lucide |

### Map Overlay Standards

- Isochrone fill: 15–40% opacity depending on ring
- POI markers: 90% opacity
- Overlay panels: `--surface-card` at 95% opacity, `backdrop-filter: blur(12px)`
- Map attribution: `--text-muted` 10px

## Component Mockups (HTML Deliverable)

### 1. Property Card

Neumorphic `--neu-flat` shadow on `--surface-card`. Contains:
- Image placeholder area (16:10 ratio, rounded top corners `--radius-lg`)
- Price in Space Grotesk 24px/700
- Address in Inter 13px `--text-tertiary`
- Stats row: bed/bath/sqft in Inter 12px `--text-muted`
- AI insight chips with confidence bars
- "View Intelligence" neumorphic button

### 2. Search Bar

Neumorphic `--neu-flat` on `--surface-card`. Contains:
- Search icon in `--accent-primary`
- Placeholder text in Inter 14px `--text-muted`
- Focus state: switches to `--neu-pressed` (inset shadow)

### 3. Stat/Insight Chip

Neumorphic `--neu-pressed` (inset). Contains:
- Glowing dot indicator (`--accent-primary` with `--neu-glow`)
- Label in JetBrains Mono 11px `--accent-light`
- Pattern: `[dot] Label · Confidence%`

### 4. Map Panel

Styled container on `--surface-raised`. Contains:
- Dark-themed map placeholder area
- Isochrone ring visualization (concentric indigo rings at varying opacity)
- POI category legend using the geo accent colors
- Overlay info panel with backdrop blur

## Tech Stack Alignment

The Argus frontend uses:
- **React 19 + TypeScript** with Vite
- **Tailwind CSS 4** with `@theme inline` and `@custom-variant dark`
- **shadcn/ui** (base-nova preset) with CSS variables in oklch
- **Lucide React** for icons
- **Mapbox GL** for mapping
- Dark mode via `.dark` class on `<html>`

### How tokens map to the existing system

The `brandkit.md` must express all design tokens as:
1. **CSS custom properties** compatible with the existing `index.css` `:root` / `.dark` pattern
2. **Tailwind utility classes** where applicable (e.g., `bg-card`, `text-muted-foreground`)
3. **New neumorphic tokens** (`--neu-shadow-dark`, `--neu-shadow-light`, `--neu-flat`, `--neu-pressed`, `--neu-elevated`, `--neu-glow`, `--surface-raised`) added to the `@theme inline` block
4. **Font overrides**: Replace `--font-sans` with Inter, add `--font-heading` as Space Grotesk, add `--font-mono` as JetBrains Mono

Existing shadcn variables (`--primary`, `--card`, `--accent`, `--destructive`, etc.) should be remapped to the Argus brand colors in oklch format.

## Deliverables

### 1. `brandkit.html` (project root)

Self-contained HTML reference page — **not** part of the React app. Uses Google Fonts CDN and Lucide CDN. Contains:
- Sticky sidebar nav: Colors, Typography, Components, Spacing
- Dark/light mode toggle (top right)
- Live-rendered color swatches, type samples, component mockups
- Embedded Argus SVG logo (from `assets/argus-logo.svg`)

### 2. `brandkit.md` (project root)

Frontend implementation reference. Defines:
- All CSS custom properties with oklch values for shadcn compatibility
- Tailwind `@theme inline` additions for neumorphic tokens
- Font stack configuration (`@fontsource` packages to install)
- Type scale as Tailwind utility patterns
- Component patterns as React/shadcn conventions (not raw HTML)
- Neumorphic shadow utilities as Tailwind custom classes
