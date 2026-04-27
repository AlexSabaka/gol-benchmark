---
name: frontend-design-tokens
description: Work with design tokens in the GoL Benchmark frontend's Tailwind v4 setup. Use when the user asks to "add a color", "fix dark mode", "change the sidebar palette", "extend the chart palette", or anything theme-related. Covers the @theme block in index.css (no tailwind.config.ts), OKLCH conventions, dark-mode plumbing, sidebar/chart token families, and when to extend tokens vs use raw classes.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Frontend Design Tokens

The frontend uses **Tailwind CSS v4**, which reads design tokens from CSS, not from a JS config file. **There is no `tailwind.config.ts` in this repo** — all tokens live in [`frontend/src/index.css`](../../../frontend/src/index.css) inside an `@theme { ... }` block.

shadcn/ui primitives consume these tokens via CSS variable references (`var(--color-primary)` etc.), so adding a primitive automatically inherits the theme. Custom components should do the same — never inline OKLCH literals.

For the slim agent index see [frontend/CLAUDE.md](../../../frontend/CLAUDE.md). For the full frontend reference see [docs/FRONTEND_GUIDE.md](../../../docs/FRONTEND_GUIDE.md).

---

## Where tokens live

```css
/* frontend/src/index.css */
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

@theme {
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.145 0 0);
  --color-primary: oklch(0.205 0 0);
  --color-primary-foreground: oklch(0.985 0 0);
  --color-destructive: oklch(0.577 0.245 27.325);
  --color-border: oklch(0.922 0 0);
  /* … */
  --color-chart-1: oklch(0.646 0.222 41.116);
  --color-chart-2: oklch(0.6 0.118 184.704);
  /* … */
  --color-sidebar: oklch(0.985 0 0);
  --color-sidebar-primary: oklch(0.205 0 0);
  /* … */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
}
```

After this block, the file has standard Tailwind layers (`@layer base`, etc.) for global resets and dark-mode variable overrides.

---

## Token families

The codebase splits tokens into **three palettes**. Keep them separate — bleeding the sidebar palette into the base palette breaks the sidebar's visual distinction.

### 1. Base palette (consumed by shadcn primitives)

| Variable | Used for |
|---|---|
| `--color-background` / `--color-foreground` | Page background, default text |
| `--color-card` / `--color-card-foreground` | Card surfaces |
| `--color-popover` / `--color-popover-foreground` | Popovers, tooltips, dropdowns |
| `--color-primary` / `--color-primary-foreground` | Primary buttons, accents |
| `--color-secondary` / `--color-secondary-foreground` | Secondary buttons |
| `--color-muted` / `--color-muted-foreground` | Disabled / less-important text |
| `--color-accent` / `--color-accent-foreground` | Hover surfaces |
| `--color-destructive` / `--color-destructive-foreground` | Error states, destructive actions |
| `--color-border` | Default border color |
| `--color-input` | Input border color |
| `--color-ring` | Focus rings |

Use as Tailwind classes: `bg-background`, `text-foreground`, `bg-primary`, `text-primary-foreground`, `border-border`, `ring-ring`, etc.

### 2. Sidebar palette (consumed only by AppShell)

`--color-sidebar`, `--color-sidebar-foreground`, `--color-sidebar-primary`, `--color-sidebar-primary-foreground`, `--color-sidebar-accent`, `--color-sidebar-accent-foreground`, `--color-sidebar-border`, `--color-sidebar-ring`.

These exist so the sidebar can have a distinct neutral tone from the main content area without changing every shadcn primitive. **Don't use these tokens outside `components/layout/app-shell.tsx`** — the visual mental model breaks if other surfaces start adopting them.

### 3. Chart palette (consumed by recharts wrappers)

`--color-chart-1` through `--color-chart-5` are five categorical colors for chart series. Designed to be visually distinct AND theme-shift between light and dark mode.

```tsx
// In a recharts component
<Bar dataKey="accuracy" fill="var(--color-chart-1)" />
<Bar dataKey="latency" fill="var(--color-chart-2)" />
```

If you need a 6th color, **add `--color-chart-6` to `@theme`**, don't inline an OKLCH literal at the call site.

### Radii

`--radius-sm` (0.25rem), `--radius-md` (0.375rem), `--radius-lg` (0.5rem), `--radius-xl` (0.75rem). Use as `rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-xl`. shadcn primitives use these.

---

## Dark mode

Dark mode is toggled by adding `.dark` to `<html>` (set by the `ThemeProvider` in `App.tsx`, which reads localStorage `light` / `dark` / `system`).

The `@custom-variant dark (&:is(.dark *))` declaration teaches Tailwind v4 to interpret `dark:` prefixed classes correctly:

```tsx
<div className="bg-background text-foreground dark:bg-card" />
```

**To override a token in dark mode**, add a `.dark { --color-X: ...; }` rule somewhere outside `@theme` (typically in a `@layer base` block). Look at the existing `.dark { ... }` rule in `index.css` for the canonical example — every base/sidebar/chart variable is overridden there.

```css
/* in index.css after @theme */
.dark {
  --color-background: oklch(0.145 0 0);
  --color-foreground: oklch(0.985 0 0);
  /* … override every variable that should differ in dark mode */
  --color-chart-1: oklch(0.488 0.243 264.376);
  --color-sidebar: oklch(0.205 0 0);
}
```

When adding a new token, define BOTH the light value (in `@theme`) AND the dark value (in `.dark { ... }`). Forgetting the dark override produces unreadable text on dark backgrounds — a common regression.

---

## Adding a new token — checklist

1. Identify the family (base / sidebar / chart / radius / spacing). If it doesn't fit, propose a new family.
2. Pick a name. Convention: `--<family>-<role>` (e.g. `--color-warning`, `--color-warning-foreground`).
3. Add the light value to `@theme`:
   ```css
   --color-warning: oklch(0.764 0.166 70.0);
   --color-warning-foreground: oklch(0.145 0 0);
   ```
4. Add the dark override in `.dark { ... }`:
   ```css
   .dark {
     /* … existing overrides */
     --color-warning: oklch(0.488 0.243 70.0);
     --color-warning-foreground: oklch(0.985 0 0);
   }
   ```
5. Use as Tailwind class: `bg-warning text-warning-foreground`.
6. (If consumed by recharts) reference as `fill="var(--color-warning)"`.
7. Smoke-test in BOTH light and dark mode (toggle via the Theme toggle in the header).

---

## OKLCH conventions

This codebase uses OKLCH (`oklch(L C H)`) for all colors. OKLCH is perceptually uniform — equal numeric distance ≈ equal perceived color difference. This matters for dark mode because OKLCH lightness can be flipped without color shifting:

- `oklch(0.985 0 0)` (near-white) ↔ `oklch(0.145 0 0)` (near-black) — same chroma + hue, lightness inverted

For chart colors, keep chroma high (`0.15`–`0.25`) and vary hue widely between series for visual separation.

**Don't mix color spaces.** Don't use `hsl(...)`, `rgb(...)`, hex, or named colors anywhere. The whole palette is OKLCH; introducing other spaces makes future theme work brittle.

---

## When to use raw Tailwind colors vs tokens

| Use case | Use |
|---|---|
| Component styling that should match the theme | Tokens (`bg-primary`, `text-muted-foreground`) |
| Brand-specific accents (rare) | Token (add to `@theme` first) |
| One-off semantic state (success / warning / info) | Add a token — these are reusable |
| Quick prototyping | Raw Tailwind colors (`bg-blue-500`) — but PROMOTE to a token before merging |

**Rule of thumb**: if the same color appears in 3+ places, it deserves a token. If you find yourself writing `bg-amber-500` in production code, that's a missing token.

---

## What NOT to do

- **Don't create `tailwind.config.ts`.** It would be ignored by Tailwind v4 and confuse future maintainers. All config is in `index.css`.
- **Don't inline OKLCH literals in component classes** (`bg-[oklch(0.5_0.2_30)]`). The token can't be theme-shifted.
- **Don't use the sidebar palette outside the AppShell.** It's a distinct visual surface; bleeding it elsewhere defeats the design.
- **Don't add a token without the `.dark` override.** Light-only tokens produce unreadable surfaces in dark mode.
- **Don't introduce a new color space (hex, hsl, rgb).** Stay in OKLCH for consistency and future theme safety.
- **Don't bump radius values without reason.** They define the entire UI's visual language; small changes are large user-facing changes.

---

*See also: [docs/FRONTEND_GUIDE.md § Design tokens](../../../docs/FRONTEND_GUIDE.md#design-tokens-tailwind-v4).*
