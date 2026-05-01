import { useMemo, useState } from "react"
import { Link } from "react-router"
import {
  CheckSquare,
  ChevronDown,
  Lock,
  LockOpen,
  Plus,
  Search,
  Square,
  X,
} from "lucide-react"

import { useMetadata } from "@/hooks/use-metadata"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { LanguageDots } from "@/components/prompts/language-dots"
import { cn } from "@/lib/utils"
import type { MetadataPromptEntry } from "@/api/metadata"

// ─── Wire format helpers ────────────────────────────────────────────────────

export type PromptRef = { id: string; version: number | null }

export const promptRefToWire = (r: PromptRef): string =>
  r.version == null ? r.id : `${r.id}@${r.version}`

export const wireToPromptRef = (s: string): PromptRef => {
  const at = s.lastIndexOf("@")
  if (at === -1) return { id: s, version: null }
  const version = Number(s.slice(at + 1))
  if (!Number.isFinite(version)) return { id: s, version: null }
  return { id: s.slice(0, at), version }
}

// ─── Component ──────────────────────────────────────────────────────────────

interface Props {
  value: PromptRef[]
  onChange: (next: PromptRef[]) => void
  /** "multi" for cartesian-axis use; "single" for the override modal. */
  mode: "multi" | "single"
  className?: string
}

export function PromptPicker({ value, onChange, mode, className }: Props) {
  const { data: meta, isLoading } = useMetadata()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")

  const catalog = meta?.prompts ?? []
  const byId = useMemo(() => {
    const out = new Map<string, MetadataPromptEntry>()
    for (const p of catalog) out.set(p.id, p)
    return out
  }, [catalog])

  const { builtins, drafts } = useMemo(() => {
    const q = search.trim().toLowerCase()
    const matches = (p: MetadataPromptEntry) =>
      !q || p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)
    const builtins = catalog.filter((p) => p.is_builtin && matches(p))
    const drafts = catalog.filter((p) => !p.is_builtin && matches(p))
    // Built-ins keep a stable order: analytical / casual / adversarial / none
    const builtinOrder = [
      "builtin_analytical",
      "builtin_casual",
      "builtin_adversarial",
      "builtin_none",
    ]
    builtins.sort(
      (a, b) => builtinOrder.indexOf(a.id) - builtinOrder.indexOf(b.id),
    )
    drafts.sort((a, b) => a.name.localeCompare(b.name))
    return { builtins, drafts }
  }, [catalog, search])

  const toggleSelect = (id: string) => {
    const exists = value.find((r) => r.id === id)
    if (exists) {
      onChange(value.filter((r) => r.id !== id))
      return
    }
    if (mode === "single") {
      onChange([{ id, version: null }])
      setOpen(false)
      return
    }
    onChange([...value, { id, version: null }])
  }

  const togglePin = (id: string) => {
    onChange(
      value.map((r) => {
        if (r.id !== id) return r
        // Pin → unpin
        if (r.version != null) return { ...r, version: null }
        // Unpinned → pin to current latest
        const latest = byId.get(id)?.latest_version ?? null
        if (latest == null) return r
        return { ...r, version: latest }
      }),
    )
  }

  const removeAt = (id: string) => onChange(value.filter((r) => r.id !== id))

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* Selected chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((r) => (
            <SelectedChip
              key={r.id}
              ref_={r}
              entry={byId.get(r.id)}
              onTogglePin={() => togglePin(r.id)}
              onRemove={() => removeAt(r.id)}
            />
          ))}
        </div>
      )}

      {/* Trigger */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 w-fit gap-1.5"
          >
            <Plus className="size-3.5" />
            {mode === "single" && value.length > 0
              ? "Change prompt"
              : value.length > 0
                ? "Add another prompt"
                : "Add prompt"}
            <ChevronDown className="size-3 text-muted-foreground" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-[min(420px,calc(100vw-2rem))] p-0"
          // Prevent the popover from auto-closing when interacting with the
          // search input — radix focus heuristics can otherwise dismiss it.
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="border-b p-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground/70" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or slug…"
                className="h-8 pl-8 text-sm"
                autoFocus
              />
            </div>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            {isLoading ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                Loading…
              </div>
            ) : (
              <>
                <CatalogSection
                  title="Built-in"
                  entries={builtins}
                  value={value}
                  mode={mode}
                  onSelect={toggleSelect}
                />
                <CatalogSection
                  title="My Drafts"
                  entries={drafts}
                  value={value}
                  mode={mode}
                  onSelect={toggleSelect}
                  empty={
                    <p className="px-3 py-3 text-xs text-muted-foreground">
                      No user-authored prompts.{" "}
                      <Link
                        to="/prompts/new"
                        className="underline underline-offset-2 hover:text-foreground"
                      >
                        Author one
                      </Link>
                      .
                    </p>
                  }
                />
              </>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}

// ─── Selected chip ──────────────────────────────────────────────────────────

function SelectedChip({
  ref_,
  entry,
  onTogglePin,
  onRemove,
}: {
  ref_: PromptRef
  entry: MetadataPromptEntry | undefined
  onTogglePin: () => void
  onRemove: () => void
}) {
  const isBuiltin = entry?.is_builtin ?? ref_.id.startsWith("builtin_")
  const name = entry?.name ?? ref_.id
  const latest = entry?.latest_version ?? null
  const pinned = ref_.version != null
  const versionLabel = pinned ? `v${ref_.version}` : latest != null ? `v${latest}` : ""

  return (
    <span
      className={cn(
        "group inline-flex max-w-full items-center gap-1.5 rounded-md border bg-card px-2 py-1 text-xs",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-1.5 shrink-0 rounded-full",
          isBuiltin ? "bg-foreground/40" : "bg-violet-500/70",
        )}
      />
      <span className="truncate font-medium">{name}</span>
      {entry?.language_codes && (
        <LanguageDots
          present={entry.language_codes}
          compact
          className="ml-0.5"
        />
      )}
      {versionLabel && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={onTogglePin}
              className={cn(
                "inline-flex items-center gap-0.5 rounded-sm px-1 font-mono tabular-nums transition-colors",
                pinned
                  ? "bg-amber-500/15 text-amber-700 hover:bg-amber-500/25 dark:text-amber-300"
                  : "text-muted-foreground hover:bg-muted",
              )}
              aria-label={pinned ? "Unpin (use latest)" : `Pin to ${versionLabel}`}
            >
              {pinned ? (
                <Lock className="size-3" />
              ) : (
                <LockOpen className="size-3 opacity-70" />
              )}
              <span className="text-[10px]">{versionLabel}</span>
            </button>
          </TooltipTrigger>
          <TooltipContent>
            <span className="text-xs">
              {pinned
                ? `Pinned to ${versionLabel}. Click to use latest.`
                : `Latest version (${versionLabel}). Click to pin.`}
            </span>
          </TooltipContent>
        </Tooltip>
      )}
      <button
        type="button"
        onClick={onRemove}
        className="ml-0.5 rounded-sm text-muted-foreground hover:text-foreground"
        aria-label={`Remove ${name}`}
      >
        <X className="size-3" />
      </button>
    </span>
  )
}

// ─── Catalog section ────────────────────────────────────────────────────────

function CatalogSection({
  title,
  entries,
  value,
  mode,
  onSelect,
  empty,
}: {
  title: string
  entries: MetadataPromptEntry[]
  value: PromptRef[]
  mode: "multi" | "single"
  onSelect: (id: string) => void
  empty?: React.ReactNode
}) {
  if (entries.length === 0 && !empty) return null
  return (
    <div className="px-1 py-1">
      <div className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </div>
      {entries.length === 0 ? (
        empty
      ) : (
        <ul>
          {entries.map((p) => {
            const selected = value.some((r) => r.id === p.id)
            return (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onSelect(p.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                    selected && "bg-muted/60",
                  )}
                >
                  {mode === "multi" ? (
                    selected ? (
                      <CheckSquare className="size-3.5 text-foreground" />
                    ) : (
                      <Square className="size-3.5 text-muted-foreground" />
                    )
                  ) : (
                    <span
                      className={cn(
                        "size-3.5 rounded-full border",
                        selected ? "border-foreground bg-foreground" : "border-border",
                      )}
                    />
                  )}
                  <LanguageDots present={p.language_codes} compact />
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {p.name}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                    v{p.latest_version ?? "?"}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
