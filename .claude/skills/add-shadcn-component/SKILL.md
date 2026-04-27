---
name: add-shadcn-component
description: Install or extend a shadcn/ui primitive in the GoL Benchmark frontend. Use when the user asks to "add a shadcn component", "install <primitive>" (button, dialog, dropdown-menu, etc.), or wants to add a variant to an existing primitive. Walks the npx shadcn CLI invocation, the cn() + class-variance-authority pattern, and the named-export convention.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Add a shadcn/ui Component

shadcn/ui isn't a package you import — it's a CLI that **copies** primitive source into your repo, where you own and customize them. Once installed, they're your code.

The frontend is configured for shadcn at [`frontend/components.json`](../../../frontend/components.json):

- Style: `new-york`
- Base color: `neutral`
- CSS variables: `true` (consume tokens from `src/index.css` `@theme` block)
- Icon library: `lucide`
- Aliases: `@/components/ui` for primitives, `@/lib/utils` for `cn()`, `@/hooks` for hooks

For broader frontend conventions see [docs/FRONTEND_GUIDE.md](../../../docs/FRONTEND_GUIDE.md).

---

## Step 1 — Install the primitive

```bash
cd frontend
npx shadcn add <component-name>
```

Examples (the 20 primitives currently installed): `button`, `card`, `dialog`, `dropdown-menu`, `sheet`, `select`, `tabs`, `table`, `tooltip`, `popover`, `collapsible`, `command`, `label`, `input`, `textarea`, `checkbox`, `progress`, `badge`, `separator`, `sonner`.

The CLI:

- Copies `<component-name>.tsx` into `frontend/src/components/ui/`
- Adds Radix dependencies to `package.json` if needed
- Wires up imports automatically (uses the aliases from `components.json`)

For the canonical list of available primitives, see [ui.shadcn.com/docs/components](https://ui.shadcn.com/docs/components).

---

## Step 2 — Confirm the primitive

After install, the new file should:

- Live at `frontend/src/components/ui/<component-name>.tsx`
- Use **named exports** (e.g. `export function Button(...)`, not `export default`)
- Import `cn` from `@/lib/utils`
- Import Radix primitives via `radix-ui` aggregator OR per-package `@radix-ui/react-*`
- Define variants via `class-variance-authority` if it has visual variants (button, badge, alert)

Quick check:

```bash
head -20 frontend/src/components/ui/<component-name>.tsx
```

If the import paths don't use the `@/` alias, the install is wrong — re-run with the latest CLI version.

---

## Step 3 — Use the primitive

Always import from `@/components/ui/<component-name>`:

```tsx
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

export function MyComponent() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Open</Button>
      </DialogTrigger>
      <DialogContent>...</DialogContent>
    </Dialog>
  )
}
```

Two non-obvious conventions:

### Always use `cn()` for class composition

```tsx
// Good
<div className={cn("rounded-md border", isActive && "border-primary")} />

// Bad — Tailwind conflict resolution doesn't run
<div className={`rounded-md border ${isActive ? "border-primary" : ""}`} />
```

`cn()` (from `@/lib/utils`) is `twMerge(clsx(inputs))` — it composes conditionally AND resolves Tailwind conflicts (e.g. `p-2 p-4` → `p-4`). String concatenation skips the merge.

### Use `asChild` to delegate rendering

Most shadcn primitives accept an `asChild` prop. When set, the primitive forwards its props to its child via Radix `Slot` — so you can render the primitive AS another component:

```tsx
// Render a Link as a button visually + behave as a button (radix focus ring, variant styling)
<Button asChild>
  <Link to="/foo">Go to Foo</Link>
</Button>
```

This is preferred over `<Link><Button>...</Button></Link>` (nested interactive elements break a11y).

---

## Step 4 (optional) — Add a variant to an existing primitive

shadcn primitives use `class-variance-authority` (CVA) to define variant systems. Open the primitive file (e.g. `frontend/src/components/ui/button.tsx`), find the `<name>Variants` declaration:

```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center ...",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground ...",
        destructive: "bg-destructive text-destructive-foreground ...",
        outline: "border border-input bg-background ...",
        secondary: "bg-secondary text-secondary-foreground ...",
        ghost: "hover:bg-accent hover:text-accent-foreground ...",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
)
```

To add a new variant, extend the `variants.<axis>` object. The TypeScript types update automatically via `VariantProps<typeof buttonVariants>`.

**When to add a variant** vs use `className` override:
- **Variant**: a re-usable visual mode the rest of the app will adopt (e.g. a new `"warning"` button variant)
- **className override**: one-off styling for a specific use site (`<Button className="w-full">`)

If you find yourself writing the same className override in 3+ places, promote it to a variant.

---

## Step 5 (optional) — Compose a domain component

For app-specific composites (cards, sheets, badges that bundle data + UI), don't put them in `components/ui/`. Use the appropriate domain folder:

| Folder | Purpose |
|---|---|
| `components/ui/` | shadcn primitives — minimal, reusable |
| `components/layout/` | AppShell, PageHeader, navigation |
| `components/wizard/` | StepButton, StepFooter (multi-step forms) |
| `components/charts/` | recharts wrappers + chart-specific helpers |
| `components/data-table/` | TanStack Table wrapper + faceted filters |
| `components/review/` | Annotation workspace |
| `components/prompts/` | Prompt Studio editor + picker |
| `components/model-selection/` | Model provider forms |
| `components/plugin-config/` | Dynamic plugin config form |

Domain components can use any number of UI primitives + their own state. Default-export OR named-export is fine — but be consistent within a folder. (Most domain folders use named exports + a `index.ts` barrel.)

---

## Step 6 — Smoke test

```bash
cd frontend
npm run dev      # verify it renders
npm run build    # verify TypeScript is happy
npm run lint     # verify ESLint passes
```

Hook H2 (`eslint-frontend-on-edit`) runs ESLint on every save automatically — you'll see violations as advisory output.

---

## What NOT to do

- **Don't `npm install` shadcn-ui.** It's not a runtime package; the CLI copies source.
- **Don't put shadcn primitives outside `components/ui/`.** The aliases in `components.json` and the codebase mental model both rely on that location.
- **Don't default-export primitives.** Named exports only. Default exports are reserved for pages.
- **Don't hand-concatenate class names.** Always `cn(...)`.
- **Don't add a `variant` for one-off styling.** That's what `className` is for. Promote to a variant only when you have 3+ uses.
- **Don't introduce CSS-in-JS** (styled-components, Emotion, vanilla-extract). Tailwind v4 + `cn()` + CVA is the entire styling stack.
- **Don't add color classes that aren't theme tokens.** Use `bg-primary`, `text-foreground`, etc. — the `@theme` block in `index.css` defines all of them. Inline `bg-[oklch(...)]` literals can't be theme-shifted.
