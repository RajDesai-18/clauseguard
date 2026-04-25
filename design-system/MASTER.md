# ClauseGuard Design System
_v1.3 — April 2026_

The single source of truth for visual, typographic, and interactive decisions.
When building a new page or component, consult this document first. Deviations
from this system require a discussed reason.

---

## Philosophy

**Dark editorial bond paper.** ClauseGuard reads like a well-designed
magazine printed on warm ivory stock. The aesthetic is refined minimalism
executed with precision, not maximalism. Every choice has a reason. The
product is a tool, not spectacle.

**Design principles**

- **The document is the metaphor.** Bond paper texture, margin rule, section
  numbers, editorial pull-quotes, masthead colophon. The product is visually
  adjacent to what it analyzes.
- **Monochrome except where it matters.** Risk colors (green/amber/coral)
  appear ONLY inside analyzed content. Marketing and structural UI is pure
  ink-on-paper.
- **Italics are precious.** Gambetta Italic appears sparingly — once in a
  headline, once in a pull-quote, never as body treatment. It carries weight
  because it's rare.
- **Motion responds to action.** Hover and press states animate. Elements do
  not animate on mount or scroll. No theater.
- **Explicit rhythm over viewport gymnastics.** No `min-h-screen` on content
  sections. Every section uses the same padding scale so rhythm is
  predictable and scales with breakpoints, not content size.

---

## Color

**Light mode (primary)**

| Token               | Value                   | Use                         |
|---------------------|-------------------------|-----------------------------|
| `--background`      | `oklch(0.965 0.006 85)` | Page surface (ivory paper)  |
| `--foreground`      | `oklch(0.18 0.006 50)`  | Ink                         |
| `--muted-foreground`| `oklch(0.45 0.006 50)`  | Secondary text, captions    |
| `--border`          | `foreground / 14%`      | Default divider             |
| `--paper`           | `oklch(0.965 0.006 85)` | Inset surfaces              |
| `--paper-rule`      | `foreground / 22%`      | Margin rule                 |

**Dark mode**

| Token               | Value                   | Use                         |
|---------------------|-------------------------|-----------------------------|
| `--background`      | `oklch(0.165 0.004 180)`| Page surface (dark paper)   |
| `--foreground`      | `oklch(0.93 0.008 85)`  | Ink                         |
| `--muted-foreground`| `oklch(0.68 0.008 85)`  | Secondary text              |

**Risk palette (analysis contexts only)**

| Risk   | Foreground              | Soft background              |
|--------|-------------------------|------------------------------|
| Low    | `oklch(0.48 0.09 155)`  | `oklch(0.93 0.025 155)`      |
| Medium | `oklch(0.6 0.13 72)`    | `oklch(0.94 0.035 72)`       |
| High   | `oklch(0.48 0.17 25)`   | `oklch(0.94 0.04 25)`        |

Risk colors NEVER appear on marketing pages, buttons, links, or structural UI.

---

## Typography

**Fonts**

| Role     | Family        | Source    | Usage                                   |
|----------|---------------|-----------|-----------------------------------------|
| Display  | Space Grotesk | Local     | Headlines, logo wordmark, button labels |
| Sans     | Outfit        | Local     | Body copy, long-form text               |
| Mono     | Azeret Mono   | Local     | Captions, nav items, section numbers    |
| Editorial| Gambetta      | Local     | Italic accent only, used sparingly      |

**Type scale**

Available as Tailwind utilities (`text-display-xl`, `text-heading-lg`, etc).
Fluid via `clamp(mobile, base + vw, desktop)`.

| Tier          | Mobile (375px) | Desktop (1440px) | Line-height | Tracking  | Usage                                  |
|---------------|----------------|------------------|-------------|-----------|----------------------------------------|
| `display-xl`  | 44px           | 96px             | 1.0         | -0.035em  | Hero H1 only                           |
| `display-lg`  | 30px           | 60px             | 1.05        | -0.028em  | Section H2s, Provenance pull-quote     |
| `display-md`  | 48px           | 88px             | 0.9         | -0.04em   | Stat numbers (e.g. "30%")              |
| `heading-lg`  | 22px           | 28px             | 1.1         | -0.02em   | Step titles in Process                 |
| `heading-md`  | 16px           | 17px             | 1.2         | -0.01em   | Annotation titles                      |
| `body-lg`     | 16px           | 18px             | 1.65        | 0         | Hero body, Provenance supporting prose |
| `body`        | 14px           | 15px             | 1.65        | 0         | Section body text                      |
| `body-sm`     | 13px           | 14px             | 1.55        | 0         | Card body, annotation body, footer     |
| `caption`     | 10px           | 11px             | 1.4         | 0.22em    | Mono captions, step labels, meta rail  |
| `micro`       | 10px           | 10px             | 1.4         | 0.16em    | Footer copyright                       |

**Typography rules**

- Display headings use `font-display` (Space Grotesk) with letter-spacing tight
- Body uses `font-sans` (Outfit) with no tracking
- Captions use `font-mono` (Azeret Mono), uppercase, wide tracking
- Italic accent uses `.font-editorial` (Gambetta italic 500) — max 2 usages per view
- Hero h1 breaks to 3 lines with muted middle line
- Section H2s use the editorial italic on ONE key word (never the whole heading)

---

## Spacing

**8px grid baseline.** All spacing values are multiples of 4 (half-step) or 8.

**Named internal spacing**

| Token           | Value  | Usage                                          |
|-----------------|--------|------------------------------------------------|
| `space-tight`   | 16px   | Caption → heading, heading → body gap          |
| `space-normal`  | 32px   | Body → content blocks, card internal gaps      |
| `space-loose`   | 64px   | Major content blocks within a section          |

**Section padding (UNIFIED across all content sections)**

Every content section uses the same vertical padding scale. This is the single
most important rule for maintaining consistent scroll rhythm.

```
py-32 md:py-40 lg:py-48 xl:py-56
```

| Breakpoint | Padding  |
|------------|----------|
| base       | 128px    |
| md (768+)  | 160px    |
| lg (1024+) | 192px    |
| xl (1280+) | 224px    |

There is NO `min-h-screen` on any section. Hero and Provenance previously
used it — that decision was reversed in v1.1 because it produced irregular
gaps on wide monitors. Explicit padding produces predictable rhythm.

**Horizontal layout**

- Content max-width: `1400px` (page wrapper in RootLayout)
- Section inner max-width: `1200px` (varies by section)
- Responsive left padding (margin-rule clearance):
  - Mobile: `px-6 pl-14`
  - Tablet: `md:px-10 md:pl-24`
  - Desktop: `xl:pl-28`
- Right padding always matches left

---

## Sections (landing page composition)

Four sections, each with a deliberately different layout gesture for
scrolling variety.

| Section          | Gesture                                                        |
|------------------|----------------------------------------------------------------|
| Hero (001)       | Left-aligned, 60% column, CTA + ghost link below               |
| Specimen (002)   | Right-aligned caption, asymmetric two-column (1.3:1), paper card |
| Process (003)    | Inline-left caption, full-width heading, 4-col grid with rule connectors |
| Provenance (004) | Left-stacked stat, right-stacked quote + body (5:7 split)      |

_Pricing was planned but removed. If re-adding, use the fifth gesture slot:
centered caption + heading with centered two-card grid._

---

## App chrome (authenticated surfaces)

Authenticated pages live in the `(app)` route group and use a different
chrome from the marketing site. Marketing is a magazine spread; the app
is a workshop bench. Same stock, same ink, different gestures.

**What stays from marketing**

- Bond paper texture (persistent, fixed layer)
- Color palette (ivory paper / charcoal ink, OKLCH tokens)
- Type families (Space Grotesk / Outfit / Azeret Mono / Gambetta)
- Type tokens (`text-body-sm`, `text-heading-md`, etc.)
- Motion curves and durations
- Hover/press interaction philosophy

**What changes for app chrome**

- Density. App pages compress vertically. No editorial rhythm to preserve.
- Voice. Gambetta italic disappears from chrome (nav, headers, dialogs).
  It can still appear in empty states and stat captions where editorial
  warmth helps. Never in functional UI labels.
- Layout gesture. Marketing uses asymmetric editorial spreads. App pages
  use predictable grid: rail + top bar + content area.
- Risk colors unlock. Dashboard badges, contract detail clause highlights,
  status indicators, progress steps. Still scoped to analysis contexts —
  they don't appear on settings, billing, profile, or other non-analysis
  surfaces.

### Layout

```
┌─────┬─────────────────────────────────────────────┐
│     │  Top bar  (56px, sticky, no scroll-frost)   │
│ Rail├─────────────────────────────────────────────┤
│ 72px│                                             │
│     │                                             │
│ ↓   │  Content area                               │
│     │  (max-width 1280px, left-aligned to rail)   │
│     │                                             │
└─────┴─────────────────────────────────────────────┘
```

**Rail (left navigation)**

- Width: `72px` fixed, no collapse for Phase 4B (revisit if we add many items)
- Background: `bg-sidebar` (already defined in tokens, palette-matched)
- Right border: `border-r border-sidebar-border`
- Sticky, full viewport height
- Logo mark at top (the same square-with-dot mark from marketing nav, no wordmark)
- Icon + caption stacked nav items: 24px Lucide icon, `text-caption` mono label
  beneath. No wordmark labels — the rail is too narrow.
- Active state: foreground icon + label + 2px left border in foreground color
  flush against the rail's outer edge
- Hover state: `bg-sidebar-accent` background, foreground color icon + label
- Mobile: rail collapses to a bottom bar (same items, horizontal layout)
  below `md` breakpoint

**Top bar**

- Height: `56px` (vs marketing's 72px — denser)
- Background: `bg-background` solid
- Bottom border: `border-b border-border/40`
- Sticky, no scroll-frost behavior (the bar already sits on a tool surface,
  there's no hero behind it earning the blur)
- Left side: page title (`text-heading-md`, foreground)
- Right side: account avatar with dropdown (sign out, settings)
- No mobile hamburger needed — the bottom rail handles primary nav

**Content area**

- Left padding: `pl-6 md:pl-10` (no margin-rule clearance — the rail already
  provides the left edge)
- Right padding: matches left
- Max width: `1280px` (narrower than marketing's 1400px because there's no
  side gesture room to fill)
- Top padding: `pt-8 md:pt-10`
- Bottom padding: `pb-16 md:pb-20`
- Content sections within a page: `py-8` to `py-12` for vertical rhythm,
  not the marketing `py-32+` scale

### Type usage in app chrome

The marketing type scale is correct. Specific app applications:

| Element                          | Token             |
|----------------------------------|-------------------|
| Page title (top bar)             | `heading-md`      |
| Page H1 (in content)             | `heading-lg`      |
| Section headings within a page   | `heading-md`      |
| Stat numbers (dashboard cards)   | `display-lg` (smaller stats), `display-md` (hero stats) |
| Stat labels                      | `caption` mono    |
| Table column headers             | `caption` mono    |
| Table cell text                  | `body-sm`         |
| Status badges                    | `caption` mono    |
| Empty state heading              | `heading-lg`      |
| Empty state body                 | `body`            |
| Empty state editorial accent     | `font-editorial` permitted, sparingly |
| Rail icon labels                 | `caption` mono    |

### Risk color usage (app chrome)

Risk colors are now in scope. They appear on:

- **Dashboard contract list**: risk level pill on each row
- **Contract detail page**: clause-level risk highlights, overall risk badge
- **Progress tracker**: completed/in-progress steps may use risk color tokens
  if conveying status (otherwise foreground)
- **Stats cards**: "high-risk contracts" stat may use `risk-high` for the
  number; "average risk" cards use neutral foreground

Risk colors do NOT appear on:

- Rail or top bar chrome
- Buttons (still ink-on-paper)
- Links (still ink-on-paper)
- Settings, billing, profile pages
- Empty states, loading states, error states (use `destructive` for errors)

Use `bg-risk-low-soft` / `bg-risk-med-soft` / `bg-risk-high-soft` for
fill backgrounds, with `text-risk-{level}` for the foreground text.

### Interaction states (app-specific)

**Rail nav item**

- Default: `text-muted-foreground`, transparent background
- Hover: `bg-sidebar-accent`, `text-sidebar-accent-foreground`
- Active: `text-foreground`, 2px left border foreground, no background fill
- Transition: 150ms colors, `ease-out-strong`

**Table row**

- Default: bottom border `border-border/40`
- Hover: `bg-muted/40` background
- Transition: 100ms background-color, `ease-out-strong`
- Click target: full row clickable, navigates to detail

**Risk pill**

- Default: `bg-risk-{level}-soft text-risk-{level}` rounded-sm, `text-caption` mono uppercase, 8px horizontal padding, 2px vertical
- No hover state (it's a label, not interactive)

**Status badge (queued/processing/complete/failed)**

- Default: `bg-muted text-muted-foreground` for non-active states
- Active (processing): pulsing dot + label, foreground color
- Complete: foreground color, no decoration
- Failed: `text-destructive` (NOT risk-high — failure is system error, not contract risk)

### Avatar (top bar)

The avatar is a 32px square with `rounded-sm`, foreground initials on
`bg-muted`, `text-caption` mono, foreground color. Subtle inset shadow
(no drop shadow) gives a slight pressed-in quality on bond paper.

Click opens an account dropdown:

- "Signed in as {email}" label (caption mono, muted-foreground, non-clickable)
- Settings link
- Sign out button (foreground, hover destructive)

If the user has a profile image (e.g. from Google OAuth), the image
replaces the initials inside the same 32px square frame, no border radius
change.

### What this looks like in practice

The app shell should feel like opening a well-organized dossier folder.
You see the work, not the chrome. The rail is quiet. The top bar is a
thin reference strip. The content fills the room without performance.

Compare to marketing: the landing page makes you feel something. The
app makes you do something. Both speak the same visual language, but
in different registers.

### Anti-patterns specific to app chrome

- Sidebar that uses sidebar-accent as a default background (kills the quiet)
- Top bar with marketing-style scroll-frost (no hero to frost over)
- Editorial Gambetta italic in chrome labels or button text
- Risk colors on settings or billing pages
- Section padding from the marketing scale (`py-32+`) inside app pages
- `min-h-screen` on app content (same rule as marketing — explicit rhythm)
- Drop shadows on cards (use border + minor inset, like marketing)
- Avatar that uses a colored gradient (use foreground initials on `bg-muted`,
  or the user's profile image)

---

## Auth chrome (public transactional surfaces)

Auth pages — `/login` and `/signup` — sit in a third register: public-facing
like marketing, transactional like app chrome. They use the marketing visual
language but compress to a single centered card. The bond paper persists.
The rail does not appear (the user has nothing to navigate yet). The top bar
is reduced to a logo-only strip with a single ghost link to the opposite auth
mode.

**What stays from marketing**

- Bond paper texture, color tokens, type families
- Section number gesture ("No. 005 — Sign in")
- Gambetta italic permitted on page heading (one word, max one usage per page)
- Editorial pacing in the supporting copy beneath the form

**What changes for auth chrome**

- No left rail. No app top bar.
- A simplified top strip with logo mark + wordmark on the left, ghost link
  on the right ("Already have an account? Sign in" or inverse).
- Centered card composition. The card is bond paper too — same surface as
  the page, set apart by a hairline rule and slightly more deliberate
  internal padding.
- Form inputs are bond-paper styled: no boxed input field. A single hairline
  rule beneath the label, value reads as ink on paper. Focus state thickens
  the rule and shifts it to foreground.
- Primary CTA: filled ink button (same as marketing primary).
- Google OAuth: ghost-bordered button with the Google G mark on the left.
  Sits below the email/password block, separated by a thin rule with "or"
  inset.
- No risk colors anywhere on auth pages.

### Layout

```
┌─────────────────────────────────────────────────┐
│  [Logo] ClauseGuard          Already have? →    │  56px strip
├─────────────────────────────────────────────────┤
│                                                 │
│                                                 │
│              ┌──────────────────┐               │
│              │ No. 005 — Sign in│               │
│              │                  │               │
│              │ Read the         │               │
│              │ *fine print.*    │               │  centered card
│              │                  │               │  max-w-[420px]
│              │ [Email]          │               │
│              │ [Password]       │               │
│              │                  │               │
│              │ [Sign in]        │               │
│              │ ────── or ─────  │               │
│              │ [G Continue with]│               │
│              └──────────────────┘               │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Top strip**

- Height: `56px` (matches app chrome top bar)
- Background: `bg-background` solid
- Bottom border: `border-b border-border/40`
- Left: logo mark (square+dot) + "ClauseGuard" wordmark, links to `/`
- Right: ghost text link to opposite auth mode ("Don't have an account?
  Sign up" or inverse), `text-caption` mono, hover underlines

**Card**

- Max width: `420px`
- Centered horizontally and vertically in the remaining viewport
- Padding: `p-10 md:p-12`
- Background: same `bg-background` as page (bond paper reads through)
- Border: `1px solid border-border/60`, no shadow, no rounding above `2px`
- Subtle inner top rule: 1px hairline at `border` color, sets off the
  section number from the form

**Form inputs (bond-paper style)**

- No `<input>` border-box treatment
- Label: `text-caption` mono uppercase, `text-muted-foreground`, sits above
  the input with `mb-2`
- Input: bare `<input>` with `border-b border-border/60` and `py-2.5`
  vertical padding, no horizontal padding (aligns with rule edges),
  `bg-transparent`, `text-body` foreground
- Focus: rule thickens to 2px, shifts to `border-foreground`. Transition
  150ms `ease-out-strong`. No box-shadow ring.
- Error: rule shifts to `border-destructive`, helper text below in
  `text-destructive`, `text-caption`
- Filled state: no visual change from default (the rule is enough)

**OAuth button (Google)**

- Variant: ghost (border-only)
- Border: `1px solid border-foreground/30`
- Hover: border thickens to `border-foreground/60`, no fill
- Padding: `py-3 px-4`, full width
- Layout: Google G mark (16px) left, label centered visually
- Label: "Continue with Google", `text-body-sm`
- No risk colors. The official Google G mark retains its colors only inside
  the icon mark itself, never on chrome

**"or" divider**

- Thin rule on either side of the word "or"
- "or" in `text-caption` mono lowercase, `text-muted-foreground`
- Margin: `my-6` between primary CTA block and OAuth block

### Type usage on auth pages

| Element                              | Token                                      |
|--------------------------------------|--------------------------------------------|
| Section number ("No. 005 — Sign in") | `caption` mono                             |
| Page heading                         | `display-lg`, with one Gambetta italic word permitted |
| Supporting copy beneath heading      | `body-sm`, muted-foreground                |
| Form label                           | `caption` mono uppercase                   |
| Form input value                     | `body`                                     |
| Helper text / error                  | `caption` mono                             |
| Primary CTA label                    | `body-sm` font-display medium              |
| OAuth button label                   | `body-sm`                                  |
| Footer link beneath card             | `caption` mono                             |

### Anti-patterns specific to auth chrome

- Boxed input fields (use the bond-paper rule treatment)
- Card with rounded corners > 2px (we are paper, not iOS)
- Drop shadow on the card (use border + persistent texture)
- Risk colors on auth pages (errors are `destructive`, success is
  foreground transition to next page)
- "Welcome back!" or other warmth tropes (the editorial pull-quote
  earns the warmth, not the chrome copy)
- Animated success states (the redirect is the success state)
- Showing/hiding password via inline eye icon (use a separate small
  text toggle below the input if needed; the eye icon is overused)

---

## Motion

**Easing curves** (exposed as CSS variables)

```
--ease-out-strong:    cubic-bezier(0.23, 1, 0.32, 1)
--ease-in-out-strong: cubic-bezier(0.77, 0, 0.175, 1)
--ease-drawer:        cubic-bezier(0.32, 0.72, 0, 1)
```

**Duration table**

| Interaction        | Duration |
|--------------------|----------|
| Button press       | 100-160ms|
| Hover state        | 150-200ms|
| Dropdown, popover  | 150-250ms|
| Modal, drawer      | 200-500ms|
| Focus ring         | 150ms    |

**Rules**

- Use `ease-out-strong` for hover/press and enter transitions
- Use `ease-in-out-strong` for on-screen movement/morphing
- Never use `ease-in` on UI — feels sluggish
- No animations on mount, scroll-reveal, or page load
- `prefers-reduced-motion` respected at the global CSS layer

---

## Interaction states

**Primary CTA (filled ink)**

- Default: `bg-foreground text-background`
- Hover: `scale-[1.01]` + `bg-foreground/90` + arrow nudge 2px
- Active: `scale-[0.98]`
- Transition: 200ms `ease-out-strong`

**Ghost CTA (text + underline)**

- Default: underlined in foreground/30
- Hover: underline strengthens to foreground/80 + arrow nudge 4px
- Active: color shifts to foreground/80
- Transition: 200ms `ease-out-strong`

**Desktop nav link**

- Default: `text-muted-foreground`, no underline
- Hover: `text-foreground` + 1px underline draws left-to-right
- Transition: 200ms for color, 200ms for scale-x on underline

**Nav Sign-in button**

- Default: bordered, foreground text
- Hover: fills with foreground, text inverts to background
- Active: `scale-[0.98]`

**Nav scroll state**

- At rest: solid `bg-background`, border `border-border/40`
- On scroll (>4px): `bg-background/70 backdrop-blur-md`, border `border-foreground/30`
- Transition: 200ms on `background-color, backdrop-filter, border-color`

**Step card (process)**

- Default: horizontal rule at `border` color, 1px tall
- Hover: rule thickens to 2px, shifts to foreground; step label intensifies
- No scale, no translate — they're reference, not buttons

**Annotation card (specimen)**

- Default: left border at `border` color
- Hover: left border intensifies to `border-foreground/60`
- Transition: 200ms colors

---

## Bond paper texture

Implemented as a fixed-positioned component (`components/bond-paper.tsx`)
that sits at the `<body>` level via `RootLayout`. It covers the full viewport
and does not scroll with content — the texture is a persistent backdrop.

- Two SVG filter layers: fractal noise (fiber grain) + horizontal turbulence (weave)
- Dynamic color matrix: reads `document.documentElement.classList.contains("dark")`
  via `MutationObserver` to swap fiber color between light and dark mode
- Light mode: `mix-blend-multiply` at 55%/38% opacity
- Dark mode: `mix-blend-screen` at 32%/24% opacity
- Seeded `<feTurbulence>` for deterministic pattern (no shimmer on repaint)

The bond paper reads through the nav and footer naturally — both use solid
`bg-background` so the texture behind them is visible via the fixed layer.

---

## Responsive strategy

Five breakpoints, each verified:

| Breakpoint       | Width     | Behavior                                    |
|------------------|-----------|---------------------------------------------|
| Mobile (sm)      | 375px     | Single-column everything, hamburger nav     |
| Tablet (md)      | 768px     | Still single-col mostly, Process 2×2        |
| Laptop (lg)      | 1024px    | Specimen + Provenance go two-column         |
| Desktop (xl)     | 1440px    | Full layout (reference width)               |
| Wide (2xl)       | 1920px+   | Content capped at 1400px, more whitespace   |

**Fluid type via clamp**

All type-scale tokens use `clamp(mobile, base + vw, desktop)`. Ceilings
are tuned so that at 1440px (our reference) the headline "Read the fine
print" fits on one line inside the `max-w-3xl` container. Going higher
breaks the intended line breaks.

---

## Component directory

```
components/
  bond-paper.tsx              # Fixed fiber+weave texture layer (client component)
  margin-rule.tsx             # Vertical rule at left edge
  site/
    nav.tsx                   # Sticky top navigation with scroll-frost
    footer.tsx                # Colophon with top dossier rule
  shell/
    rail.tsx                  # Left navigation rail (72px) + mobile bottom bar
    top-bar.tsx               # Sticky top bar with page title + account dropdown
  auth/
    auth-strip.tsx            # Simplified top strip (logo + ghost link)
    auth-card.tsx             # Centered card shell for /login and /signup
    auth-input.tsx            # Bond-paper styled form input
    google-button.tsx         # Google OAuth ghost button
  sections/
    hero.tsx                  # No. 001
    specimen.tsx              # No. 002
    process.tsx               # No. 003
    provenance.tsx            # No. 004
  ui/
    section-header.tsx        # "No. 00X — label" caption
    cta-button.tsx            # Primary and ghost CTA variants
    risk-pill.tsx             # Risk level label (analysis contexts only)
    status-badge.tsx          # Contract processing status indicator
```

---

## Anti-patterns

- Inter or system-ui fonts (we have distinctive locals)
- Purple gradients, colored blur blobs, neon accents
- Risk colors outside analysis contexts
- `transition-all` (always specify properties)
- `ease-in` on UI elements
- Scroll-reveal animations, page-load stagger effects
- `min-h-screen` on any content section (violates rhythm)
- Inline `text-[clamp(...)]` (use type tokens)
- Italic on body copy
- Decorative shadows (only functional)
- Drop-shadow on ivory paper (use subtle border + minimal shadow)
- Gradient text
- Emoji as icons (use Lucide)
- Smooth-scroll libraries like Lenis (use native `scroll-behavior: smooth`)

---

## When extending

For new sections or pages:

1. Start from the 4 section gestures — pick one that doesn't duplicate an
   existing section in scrolling order
2. Use type tokens, never `text-[clamp(...)]` inline
3. Use named spacing tokens (`space-tight/normal/loose`) where possible
4. Use the unified section padding: `py-32 md:py-40 lg:py-48 xl:py-56`
5. Check hover states against the interaction table
6. Verify at all 5 breakpoints before committing

---

## Changelog

**v1.3 (April 2026)**
- Added "Auth chrome (public transactional surfaces)" section
- Defined auth page layout: simplified top strip + centered card
- Specified bond-paper input treatment (hairline rule, no box)
- Specified Google OAuth ghost button pattern
- Reconciled component directory: `app/` → `shell/` (matches Phase 4B reality)
- Added `auth/` directory to component map
- Updated avatar spec to support profile images (Google OAuth) + dropdown
- Listed auth-specific anti-patterns

**v1.2 (April 2026)**
- Added "App chrome (authenticated surfaces)" section
- Defined rail (72px) + top bar (56px) + content area structure
- Unlocked risk colors for analysis contexts in app surfaces
- Documented type usage table for app-specific elements
- Added app chrome interaction states (rail nav, table row, risk pill, status badge)
- Added avatar placeholder spec (foreground initials on bg-muted)
- Updated component directory to include `app/` and new `ui/` primitives
- Listed app-specific anti-patterns

**v1.1 (April 2026)**
- Removed Pricing section (design + code)
- Walked back `min-h-screen` on Hero and Provenance → unified explicit padding
- Standardized all content sections on `py-32 md:py-40 lg:py-48 xl:py-56`
- Locked nav scroll state: solid at rest, frosted-glass on scroll
- Matched nav and footer backgrounds for visual consistency
- Updated Specimen composition gesture from centered to right-aligned caption
- Added bond paper implementation notes

**v1.0 (April 2026)**
- Initial design system
- Dark editorial bond paper philosophy
- Space Grotesk + Outfit + Azeret Mono + Gambetta type stack
- Cool monochrome palette (ivory paper / charcoal ink)
- Risk palette scoped to analysis contexts only