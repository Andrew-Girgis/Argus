# Argus Brand Kit — Design Spec

## Overview

Build a visual brand kit for Argus, a property intelligence platform. Two deliverables:

1. **`brandkit.html`** — Self-contained interactive brand kit page with live-rendered color swatches, typography samples, component mockups, sticky nav, and dark/light mode toggle.
2. **`brandkit.md`** — Referenceable design token and guideline document for the frontend team.

## Brand Identity

- **Positioning**: Precision property intelligence. Built for analysts, investors, and curious homeowners.
- **Tone**: Authoritative, data-driven, trustworthy. Clean and professional. "Bloomberg meets Zillow."
- **Visual Philosophy**: Dark neumorphic soft UI with tactile embossed depth. Data-forward intelligence layer — monospace for data values, confidence scores, coordinates. Card-based layouts, photography-forward, clear information hierarchy.
- **Inspiration**: Zillow's card-heavy, address-search-centered UI adapted with neumorphic depth system inspired by Abhinai Adhikaram's Soft UI design system, remixed for dark mode.

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

## HTML Page Structure

Single self-contained HTML file with:
- **Sticky sidebar nav**: Colors, Typography, Components, Spacing sections
- **Dark/light mode toggle**: Top right, persists preference
- **Google Fonts**: Space Grotesk, Inter, JetBrains Mono (CDN)
- **Lucide Icons**: CDN
- **No other external dependencies**
- **Embedded Argus SVG logo** (from `assets/argus-logo.svg`)

## File Locations

- `brandkit.html` — project root
- `brandkit.md` — project root (frontend reference)
