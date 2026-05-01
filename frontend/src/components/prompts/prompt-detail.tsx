import { useMemo, useState } from "react"
import {
  ArchiveRestore,
  ArchiveX,
  CopyPlus,
  Loader2,
  MoreHorizontal,
  PencilLine,
} from "lucide-react"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"

import {
  useArchivePrompt,
  usePrompt,
  usePromptVersion,
  usePromptVersions,
  useRestorePrompt,
} from "@/hooks/use-prompts"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { LanguageTabs } from "@/components/prompts/language-tabs"
import { PromptContent } from "@/components/prompts/prompt-content"
import { VersionTimeline } from "@/components/prompts/version-timeline"
import { cn } from "@/lib/utils"
import type {
  LanguageCode,
  PromptDetail as PromptDetailType,
  PromptVersionMeta,
} from "@/types"

interface Props {
  promptId: string
  /** Active version (from `?v=N`). When null, uses latest. */
  version: number | null
  onVersionChange: (version: number | null) => void
}

export function PromptDetail({ promptId, version, onVersionChange }: Props) {
  const promptQuery = usePrompt(promptId)
  const versionsQuery = usePromptVersions(promptId)

  const latest = promptQuery.data?.latest_version ?? null
  const effectiveVersion = version ?? latest

  // For latest version we already have content from `usePrompt`; for older
  // versions, hit the dedicated endpoint (cached forever — versions are
  // immutable on the backend).
  const isLatest = effectiveVersion != null && effectiveVersion === latest
  const versionDetailQuery = usePromptVersion(
    promptId,
    !isLatest ? effectiveVersion : null,
  )

  const activeContent = useMemo(() => {
    if (isLatest && promptQuery.data) return promptQuery.data.content
    if (versionDetailQuery.data) return versionDetailQuery.data.content
    return null
  }, [isLatest, promptQuery.data, versionDetailQuery.data])

  if (promptQuery.isLoading || versionsQuery.isLoading) {
    return <DetailSkeleton />
  }
  if (promptQuery.error || !promptQuery.data) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        Failed to load prompt: {String(promptQuery.error ?? "unknown error")}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PromptDetailHeader
        prompt={promptQuery.data}
        showingVersion={effectiveVersion}
        latestVersion={latest}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px]">
        <div className="min-w-0">
          <ContentArea
            promptId={promptId}
            activeContent={activeContent}
            isLoading={!isLatest && versionDetailQuery.isLoading}
            error={!isLatest ? versionDetailQuery.error : null}
            isHistoricalView={!isLatest}
          />
        </div>

        {/* History rail — desktop only */}
        <aside className="hidden lg:block">
          <HistoryRail
            versions={versionsQuery.data ?? []}
            activeVersion={effectiveVersion}
            latest={latest}
            onSelect={(v) => onVersionChange(v === latest ? null : v)}
          />
        </aside>

        {/* History — mobile (Sheet) */}
        <div className="lg:hidden">
          <HistorySheet
            versions={versionsQuery.data ?? []}
            activeVersion={effectiveVersion}
            latest={latest}
            onSelect={(v) => onVersionChange(v === latest ? null : v)}
          />
        </div>
      </div>
    </div>
  )
}

// ── Header ─────────────────────────────────────────────────────────────────

function PromptDetailHeader({
  prompt,
  showingVersion,
  latestVersion,
}: {
  prompt: PromptDetailType
  showingVersion: number | null
  latestVersion: number | null
}) {
  const navigate = useNavigate()
  const archive = useArchivePrompt()
  const restore = useRestorePrompt()
  const isArchived = Boolean(prompt.archived_at)

  const editLabel = prompt.is_builtin && latestVersion != null
    ? `Edit (creates v${latestVersion + 1})`
    : "Edit"

  const onArchive = () => {
    archive.mutate(prompt.id, {
      onSuccess: () => toast.success("Prompt archived"),
      onError: (err) => toast.error(String(err)),
    })
  }
  const onRestore = () => {
    restore.mutate(prompt.id, {
      onSuccess: () => toast.success("Prompt restored"),
      onError: (err) => toast.error(String(err)),
    })
  }

  const isHistoricalView =
    showingVersion != null && showingVersion !== latestVersion
  return (
    <header className="flex flex-col gap-4">
      <Link
        to="/prompts"
        className="text-xs text-muted-foreground hover:text-foreground"
      >
        ← Prompt Studio
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            {prompt.is_builtin && !isArchived && (
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Built-in
              </span>
            )}
            {isArchived && (
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-400">
                Archived
              </span>
            )}
          </div>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight">
            {prompt.name}
          </h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {prompt.slug}
            <span className="mx-2 text-border">·</span>
            {latestVersion != null
              ? `${latestVersion} version${latestVersion > 1 ? "s" : ""}`
              : "no versions"}
          </p>
          {prompt.description && (
            <p className="mt-3 max-w-prose text-sm text-muted-foreground">
              {prompt.description}
            </p>
          )}
          {prompt.tags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {prompt.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px]">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          <Button asChild>
            <Link to={`/prompts/${prompt.id}/edit`}>
              <PencilLine className="size-4" />
              {editLabel}
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to={`/prompts/new?fork=${encodeURIComponent(prompt.id)}`}>
              <CopyPlus className="size-4" />
              Duplicate
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="More actions">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {isArchived ? (
                <DropdownMenuItem onSelect={onRestore}>
                  <ArchiveRestore className="size-4" />
                  Restore
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem onSelect={onArchive} variant="destructive">
                  <ArchiveX className="size-4" />
                  Archive
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {isHistoricalView && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-4 py-2 text-xs text-amber-800 dark:text-amber-300">
          Viewing version <span className="font-mono font-semibold">v{showingVersion}</span>.
          {latestVersion != null && (
            <button
              type="button"
              className="ml-2 underline-offset-2 hover:underline"
              onClick={() => navigate(`/prompts/${prompt.id}`, { replace: true })}
            >
              Jump to latest (v{latestVersion}).
            </button>
          )}
        </div>
      )}

      {isArchived && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-amber-500/30 bg-amber-500/5 px-4 py-2 text-xs">
          <span className="text-amber-800 dark:text-amber-300">
            This prompt is archived. New testsets won't see it unless restored.
          </span>
          <Button size="sm" variant="outline" onClick={onRestore}>
            Restore
          </Button>
        </div>
      )}
    </header>
  )
}

// ── Content area ───────────────────────────────────────────────────────────

function ContentArea({
  promptId,
  activeContent,
  isLoading,
  error,
  isHistoricalView,
}: {
  promptId: string
  activeContent: Record<string, string> | null
  isLoading: boolean
  error: unknown
  isHistoricalView: boolean
}) {
  const [activeLang, setActiveLang] = useState<LanguageCode>("en")

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading version…
      </div>
    )
  }
  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        Failed to load version: {String(error)}
      </div>
    )
  }
  if (!activeContent) return null

  return (
    <div
      className={cn(
        "rounded-xl border bg-card p-5",
        isHistoricalView && "border-amber-500/20",
      )}
      data-prompt-id={promptId}
    >
      <LanguageTabs
        value={activeLang}
        onValueChange={setActiveLang}
        content={activeContent}
      >
        {(lang, present) => {
          const text = present
            ? activeContent[lang]
            : activeContent.en ?? ""
          return (
            <PromptContent
              text={text}
              fallbackToEnglish={!present && lang !== "en"}
            />
          )
        }}
      </LanguageTabs>
    </div>
  )
}

// ── History rail / sheet ───────────────────────────────────────────────────

function HistoryRail({
  versions,
  activeVersion,
  latest,
  onSelect,
}: {
  versions: PromptVersionMeta[]
  activeVersion: number | null
  latest: number | null
  onSelect: (v: number) => void
}) {
  return (
    <div className="sticky top-2">
      <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        History
      </h3>
      <VersionTimeline
        versions={versions}
        activeVersion={activeVersion ?? latest ?? null}
        onSelect={onSelect}
      />
    </div>
  )
}

function HistorySheet({
  versions,
  activeVersion,
  latest,
  onSelect,
}: {
  versions: PromptVersionMeta[]
  activeVersion: number | null
  latest: number | null
  onSelect: (v: number) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="w-full">
          History · {versions.length} version{versions.length === 1 ? "" : "s"}
        </Button>
      </SheetTrigger>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Version history</SheetTitle>
        </SheetHeader>
        <div className="px-4 pb-6">
          <VersionTimeline
            versions={versions}
            activeVersion={activeVersion ?? latest ?? null}
            onSelect={(v) => {
              onSelect(v)
              setOpen(false)
            }}
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}

// ── Skeleton ───────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6">
      <div className="h-8 w-1/3 rounded bg-muted" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px]">
        <div className="h-96 rounded-xl border bg-muted/30" />
        <div className="hidden h-96 rounded-md bg-muted/20 lg:block" />
      </div>
    </div>
  )
}

