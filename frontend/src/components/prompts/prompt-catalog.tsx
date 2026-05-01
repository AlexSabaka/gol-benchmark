import { useMemo, useState } from "react"
import { BookOpenText, LayoutGrid, List, Plus, Search } from "lucide-react"
import { Link } from "react-router"

import { usePrompts } from "@/hooks/use-prompts"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import type { PromptSummary } from "@/types"
import { PromptCard } from "@/components/prompts/prompt-card"

type ViewMode = "grid" | "list"

export function PromptCatalog() {
  const [includeArchived, setIncludeArchived] = useState(false)
  const [search, setSearch] = useState("")
  const [viewMode, setViewMode] = useState<ViewMode>("grid")
  const { data: prompts, isLoading, error } = usePrompts(includeArchived)

  const { canon, drafts } = useMemo(() => {
    const canon: PromptSummary[] = []
    const drafts: PromptSummary[] = []
    const q = search.trim().toLowerCase()
    for (const p of prompts ?? []) {
      if (q && !matchesQuery(p, q)) continue
      ;(p.is_builtin ? canon : drafts).push(p)
    }
    return { canon, drafts }
  }, [prompts, search])

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        Failed to load prompts: {String(error)}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-10">
      {/* Canon — built-ins, always shown in fixed order */}
      <CatalogSection
        title="Canon"
        subtitle="Built-in prompts seeded from PromptEngine. Editing creates a new version on top."
      >
        {isLoading ? (
          <SkeletonGrid count={4} />
        ) : canon.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {canon.map((p) => (
              <PromptCard key={p.id} prompt={p} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<BookOpenText className="size-6 text-muted-foreground/60" />}
            title="No matching built-in prompts"
            body="Clear the search to see the canonical four."
          />
        )}
      </CatalogSection>

      {/* Hairline divider with section label */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border/60" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-background px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            My Drafts
          </span>
        </div>
      </div>

      {/* Drafts — user-authored, with search & toolbar */}
      <CatalogSection
        title="My Drafts"
        subtitle="Custom prompts you've authored. Each save creates a new immutable version."
        toolbar={
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/70" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, slug, tag…"
                className="h-9 w-64 pl-8"
              />
            </div>
            <div className="flex items-center gap-1 rounded-md border bg-background p-0.5">
              <ViewToggleButton
                active={viewMode === "grid"}
                onClick={() => setViewMode("grid")}
                label="Grid"
              >
                <LayoutGrid className="size-3.5" />
              </ViewToggleButton>
              <ViewToggleButton
                active={viewMode === "list"}
                onClick={() => setViewMode("list")}
                label="List"
              >
                <List className="size-3.5" />
              </ViewToggleButton>
            </div>
            <Label className="flex items-center gap-2 text-xs text-muted-foreground">
              <Checkbox
                checked={includeArchived}
                onCheckedChange={(c) => setIncludeArchived(Boolean(c))}
              />
              Show archived
            </Label>
          </div>
        }
      >
        {isLoading ? (
          <SkeletonGrid count={3} />
        ) : drafts.length === 0 ? (
          <EmptyDrafts hasQuery={Boolean(search.trim())} />
        ) : viewMode === "grid" ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {drafts.map((p) => (
              <PromptCard key={p.id} prompt={p} />
            ))}
          </div>
        ) : (
          <PromptListView prompts={drafts} />
        )}
      </CatalogSection>
    </div>
  )
}

function matchesQuery(prompt: PromptSummary, q: string): boolean {
  if (prompt.name.toLowerCase().includes(q)) return true
  if (prompt.slug.toLowerCase().includes(q)) return true
  if (prompt.description.toLowerCase().includes(q)) return true
  if (prompt.tags.some((t) => t.toLowerCase().includes(q))) return true
  return false
}

interface SectionProps {
  title: string
  subtitle: string
  toolbar?: React.ReactNode
  children: React.ReactNode
}

function CatalogSection({ title, subtitle, toolbar, children }: SectionProps) {
  return (
    <section>
      <header className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            {title}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {toolbar}
      </header>
      {children}
    </section>
  )
}

function ViewToggleButton({
  active,
  onClick,
  label,
  children,
}: {
  active: boolean
  onClick: () => void
  label: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-sm p-1.5 text-muted-foreground transition-colors",
        active && "bg-muted text-foreground",
        !active && "hover:bg-muted/60",
      )}
    >
      {children}
    </button>
  )
}

function SkeletonGrid({ count }: { count: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex h-44 animate-pulse flex-col rounded-xl border bg-muted/30"
        />
      ))}
    </div>
  )
}

function EmptyState({
  icon,
  title,
  body,
  cta,
}: {
  icon: React.ReactNode
  title: string
  body: string
  cta?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-muted/20 px-6 py-12 text-center">
      {icon}
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{body}</p>
      {cta}
    </div>
  )
}

function EmptyDrafts({ hasQuery }: { hasQuery: boolean }) {
  if (hasQuery) {
    return (
      <p className="px-1 text-sm text-muted-foreground">
        No drafts match the current search.
      </p>
    )
  }
  return (
    <EmptyState
      icon={<BookOpenText className="size-7 text-muted-foreground/60" />}
      title="No drafts yet"
      body="Author your first prompt — describe a system directive in English (and optionally other languages) and use it as a benchmark axis."
      cta={
        <Button asChild className="mt-2">
          <Link to="/prompts/new">
            <Plus className="size-4" />
            New prompt
          </Link>
        </Button>
      }
    />
  )
}

function PromptListView({ prompts }: { prompts: PromptSummary[] }) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      {prompts.map((p, i) => (
        <Link
          key={p.id}
          to={`/prompts/${p.id}`}
          className={cn(
            "group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-muted/40",
            i > 0 && "border-t",
            p.archived_at && "opacity-70",
          )}
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-semibold">{p.name}</span>
              <span className="truncate font-mono text-xs text-muted-foreground">
                {p.slug}
              </span>
            </div>
            <p className="line-clamp-1 text-xs text-muted-foreground">
              {p.description || "—"}
            </p>
          </div>
          <span className="font-mono text-[10px] tracking-wider text-muted-foreground">
            v{p.latest_version ?? "?"}
          </span>
          {p.archived_at && (
            <span className="text-[10px] font-medium uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Archived
            </span>
          )}
        </Link>
      ))}
    </div>
  )
}

