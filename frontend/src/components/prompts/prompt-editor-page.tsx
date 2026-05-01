import { useEffect, useMemo, useRef, useState } from "react"
import { useBlocker, useNavigate, useSearchParams, Link } from "react-router"
import { Languages, Loader2, Save, X } from "lucide-react"
import { toast } from "sonner"

import {
  useCreatePrompt,
  useCreatePromptVersion,
  usePrompt,
  useTranslatePrompt,
  useUpdatePromptMetadata,
} from "@/hooks/use-prompts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LanguageTabs } from "@/components/prompts/language-tabs"
import { TagInput } from "@/components/prompts/tag-input"
import { cn } from "@/lib/utils"
import {
  LANGUAGE_NAMES,
  LANGUAGE_ORDER,
  type LanguageCode,
  type CreatePromptRequest,
  type CreateVersionRequest,
  type UpdatePromptRequest,
} from "@/types"

type Mode = "new" | "edit"

interface Props {
  mode: Mode
  promptId?: string
}

interface DraftState {
  name: string
  slug: string
  description: string
  tags: string[]
  /** Per-language content. Always has all six keys (possibly empty). */
  content: Record<LanguageCode, string>
  changeNote: string
  /** True once the user has typed in the slug input — disables auto-derive. */
  slugTouched: boolean
}

const EMPTY_CONTENT = (): Record<LanguageCode, string> =>
  Object.fromEntries(LANGUAGE_ORDER.map((c) => [c, ""])) as Record<LanguageCode, string>

export function PromptEditorPage({ mode, promptId }: Props) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const forkSourceId = searchParams.get("fork") ?? undefined

  // For edit mode: the prompt being edited.
  const editQuery = usePrompt(mode === "edit" ? promptId : undefined)
  // For new mode with ?fork=X: pre-fill from another prompt.
  const forkQuery = usePrompt(mode === "new" ? forkSourceId : undefined)

  const sourcePrompt = mode === "edit" ? editQuery.data : forkQuery.data
  const sourceLoading =
    mode === "edit" ? editQuery.isLoading : forkSourceId ? forkQuery.isLoading : false

  // ── Draft state ──────────────────────────────────────────────────────────
  const [draft, setDraft] = useState<DraftState>(() => ({
    name: "",
    slug: "",
    description: "",
    tags: [],
    content: EMPTY_CONTENT(),
    changeNote: "",
    slugTouched: false,
  }))
  const [activeLang, setActiveLang] = useState<LanguageCode>("en")
  const [error, setError] = useState<string | null>(null)
  const initialisedRef = useRef(false)

  // Initialise draft once source prompt loads (or immediately for blank /new).
  useEffect(() => {
    if (initialisedRef.current) return
    if (mode === "edit" && !sourcePrompt) return
    if (mode === "new" && forkSourceId && !sourcePrompt) return

    if (sourcePrompt) {
      const newName =
        mode === "edit"
          ? sourcePrompt.name
          : `${sourcePrompt.name} (copy)`
      const filledContent = EMPTY_CONTENT()
      for (const code of LANGUAGE_ORDER) {
        filledContent[code] = sourcePrompt.content[code] ?? ""
      }
      setDraft({
        name: newName,
        slug: mode === "edit" ? sourcePrompt.slug : "",
        description: sourcePrompt.description,
        tags: [...sourcePrompt.tags],
        content: filledContent,
        changeNote: "",
        slugTouched: false,
      })
    }
    initialisedRef.current = true
  }, [mode, sourcePrompt, forkSourceId])

  // Auto-derive slug from name in new-mode while user hasn't touched it.
  useEffect(() => {
    if (mode !== "new" || draft.slugTouched) return
    setDraft((d) => ({ ...d, slug: slugify(d.name) }))
  }, [mode, draft.name, draft.slugTouched])

  // ── Baseline (for diff view in edit mode) ────────────────────────────────
  const baselineContent: Record<LanguageCode, string> = useMemo(() => {
    if (mode !== "edit" || !sourcePrompt) return EMPTY_CONTENT()
    const filled = EMPTY_CONTENT()
    for (const code of LANGUAGE_ORDER) {
      filled[code] = sourcePrompt.content[code] ?? ""
    }
    return filled
  }, [mode, sourcePrompt])

  // ── Dirty check ──────────────────────────────────────────────────────────
  const isDirty = useMemo(() => {
    if (!initialisedRef.current) return false
    if (mode === "new") {
      // Any non-empty field counts.
      return Boolean(
        draft.name.trim() ||
          draft.description.trim() ||
          draft.tags.length > 0 ||
          LANGUAGE_ORDER.some((c) => draft.content[c]?.trim()),
      )
    }
    // edit mode — compare against source.
    if (!sourcePrompt) return false
    if (draft.name.trim() !== sourcePrompt.name) return true
    if (draft.description !== sourcePrompt.description) return true
    if (!arraysEqual(draft.tags, sourcePrompt.tags)) return true
    return LANGUAGE_ORDER.some(
      (c) => (draft.content[c] ?? "") !== (baselineContent[c] ?? ""),
    )
  }, [draft, mode, sourcePrompt, baselineContent])

  // Content-only change matters for "Save as v(n+1)" no-op guard.
  const isContentChanged = useMemo(() => {
    if (mode === "new") {
      return LANGUAGE_ORDER.some((c) => draft.content[c]?.trim())
    }
    return LANGUAGE_ORDER.some(
      (c) => (draft.content[c] ?? "") !== (baselineContent[c] ?? ""),
    )
  }, [draft.content, baselineContent, mode])

  // ── Mutations ────────────────────────────────────────────────────────────
  const createPrompt = useCreatePrompt()
  const createVersion = useCreatePromptVersion(promptId ?? "")
  const updateMetadata = useUpdatePromptMetadata(promptId ?? "")
  const translateMut = useTranslatePrompt()
  const [overwriteConfirmOpen, setOverwriteConfirmOpen] = useState(false)

  const enText = (draft.content.en ?? "").trim()
  // In edit mode, metadata-only edits PATCH the prompt row (no new version).
  // Content edits create v(N+1). New mode always creates a prompt + v1.
  const canSave =
    !sourceLoading &&
    draft.name.trim().length > 0 &&
    enText.length > 0 &&
    isDirty &&
    !createPrompt.isPending &&
    !createVersion.isPending &&
    !updateMetadata.isPending

  // ── Translate-from-English ──────────────────────────────────────────────
  const nonEnTargets = useMemo(
    () => LANGUAGE_ORDER.filter((c) => c !== "en"),
    [],
  )
  const populatedNonEnLangs = useMemo(
    () =>
      nonEnTargets.filter((c) => (draft.content[c] ?? "").trim().length > 0),
    [draft.content, nonEnTargets],
  )

  const runTranslate = async () => {
    if (!enText) return
    try {
      const res = await translateMut.mutateAsync({
        text: enText,
        sourceLang: "en",
        targetLangs: [...nonEnTargets],
      })
      setDraft((d) => ({
        ...d,
        content: { ...d.content, ...res.translations },
      }))
      const ok = Object.keys(res.translations).length
      if (res.failed.length === 0) {
        toast.success(`Translated ${ok} language${ok === 1 ? "" : "s"}`)
      } else {
        toast.warning(
          `Translated ${ok}; failed: ${res.failed.join(", ")}`,
        )
      }
    } catch (err) {
      toast.error(
        `Translate failed: ${err instanceof Error ? err.message : "Unknown error"}`,
      )
    }
  }

  const handleTranslateClick = () => {
    if (populatedNonEnLangs.length > 0) {
      setOverwriteConfirmOpen(true)
    } else {
      void runTranslate()
    }
  }

  const submit = () => {
    setError(null)

    if (mode === "new") {
      const body: CreatePromptRequest = {
        name: draft.name.trim(),
        slug: draft.slug.trim() || undefined,
        description: draft.description.trim(),
        content: pickNonEmpty(draft.content, "en"),
        tags: draft.tags,
      }
      createPrompt.mutate(body, {
        onSuccess: (res) => {
          toast.success("Prompt created")
          // Mark form clean so the unsaved-changes guard doesn't fire.
          initialisedRef.current = false
          navigate(`/prompts/${res.prompt_id}`)
        },
        onError: (err: Error) => {
          const msg = err.message || "Failed to create prompt"
          setError(msg)
          toast.error(msg)
        },
      })
    } else {
      if (!promptId) return
      if (isContentChanged) {
        const body: CreateVersionRequest = {
          content: pickNonEmpty(draft.content, "en"),
          change_note: draft.changeNote.trim(),
        }
        createVersion.mutate(body, {
          onSuccess: (res) => {
            toast.success(`Saved as v${res.version}`)
            initialisedRef.current = false
            navigate(`/prompts/${promptId}`)
          },
          onError: (err: Error) => {
            const msg = err.message || "Failed to save version"
            setError(msg)
            toast.error(msg)
          },
        })
      } else {
        // Metadata-only edit — PATCH the prompt row, no new version cut.
        const body: UpdatePromptRequest = {
          name: draft.name.trim(),
          description: draft.description.trim(),
          tags: draft.tags,
        }
        updateMetadata.mutate(body, {
          onSuccess: () => {
            toast.success("Metadata updated")
            initialisedRef.current = false
            navigate(`/prompts/${promptId}`)
          },
          onError: (err: Error) => {
            const msg = err.message || "Failed to update metadata"
            setError(msg)
            toast.error(msg)
          },
        })
      }
    }
  }

  // ── Unsaved-changes guard ────────────────────────────────────────────────
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isDirty &&
      !createPrompt.isPending &&
      !createVersion.isPending &&
      !updateMetadata.isPending &&
      currentLocation.pathname !== nextLocation.pathname,
  )

  // ── Render ───────────────────────────────────────────────────────────────
  if (sourceLoading) {
    return (
      <div className="flex items-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading…
      </div>
    )
  }
  if (mode === "edit" && editQuery.error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        Failed to load prompt: {String(editQuery.error)}
      </div>
    )
  }

  const latestVersion =
    mode === "edit" ? sourcePrompt?.latest_version ?? null : null
  const nextVersion = latestVersion != null ? latestVersion + 1 : 1
  const saveLabel =
    mode === "edit"
      ? isContentChanged
        ? `Save as v${nextVersion}`
        : "Save metadata"
      : "Create prompt"
  const isBuiltin = Boolean(sourcePrompt?.is_builtin)

  return (
    <div className="flex flex-col gap-6 pb-32">
      <header className="flex flex-col gap-2">
        <Link
          to={mode === "edit" && promptId ? `/prompts/${promptId}` : "/prompts"}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back
        </Link>
        <div className="flex items-center gap-3">
          {isBuiltin && mode === "edit" && (
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Built-in · creating v{nextVersion}
            </span>
          )}
          {mode === "new" && forkSourceId && (
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Duplicate
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold tracking-tight">
          {mode === "edit" ? `Edit · ${sourcePrompt?.name ?? ""}` : "New prompt"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {mode === "edit"
            ? "Saving creates a new immutable version on top of the existing history."
            : "Author a system prompt with a name, optional translations, and at minimum English content."}
        </p>
      </header>

      {/* Metadata fields */}
      <div className="grid gap-4 rounded-xl border bg-card p-5">
        <div className="grid gap-2">
          <Label htmlFor="prompt-name">Name</Label>
          <Input
            id="prompt-name"
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            placeholder="My Debug Prompt"
            maxLength={200}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="prompt-slug">Slug</Label>
          <Input
            id="prompt-slug"
            value={draft.slug}
            onChange={(e) =>
              setDraft((d) => ({ ...d, slug: e.target.value, slugTouched: true }))
            }
            placeholder="my-debug-prompt"
            disabled={mode === "edit"}
            className={cn("font-mono", mode === "edit" && "opacity-70")}
          />
          {mode === "edit" ? (
            <p className="text-xs text-muted-foreground">
              Slugs are immutable so existing testsets stay resolvable.
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              URL-safe identifier. Auto-derived from name; edit to override.
            </p>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="prompt-description">Description</Label>
          <Textarea
            id="prompt-description"
            value={draft.description}
            onChange={(e) =>
              setDraft((d) => ({ ...d, description: e.target.value }))
            }
            placeholder="A short summary used in the catalog."
            className="min-h-[60px] resize-none"
            maxLength={2000}
          />
        </div>
        <div className="grid gap-2">
          <Label>Tags</Label>
          <TagInput
            value={draft.tags}
            onChange={(tags) => setDraft((d) => ({ ...d, tags }))}
          />
        </div>
      </div>

      {/* Content editor */}
      <div className="rounded-xl border bg-card p-5">
        <header className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Content</h2>
          <div className="flex items-center gap-3">
            <p className="text-xs text-muted-foreground">
              English required · others fall back to English at runtime
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              disabled={!enText || translateMut.isPending}
              onClick={handleTranslateClick}
              title={
                !enText
                  ? "Fill the English content first"
                  : "Machine-translate from English to the other 5 languages"
              }
            >
              {translateMut.isPending ? (
                <Loader2 className="size-3 animate-spin" />
              ) : (
                <Languages className="size-3" />
              )}
              Translate from English
            </Button>
          </div>
        </header>
        <LanguageTabs
          value={activeLang}
          onValueChange={setActiveLang}
          content={draft.content}
          markEnglishRequired
        >
          {(lang) => {
            const baseline = baselineContent[lang] ?? ""
            const showBaseline = mode === "edit" && baseline.length > 0
            return (
              <LanguagePane
                lang={lang}
                value={draft.content[lang]}
                baseline={showBaseline ? baseline : null}
                onChange={(v) =>
                  setDraft((d) => ({
                    ...d,
                    content: { ...d.content, [lang]: v },
                  }))
                }
              />
            )
          }}
        </LanguageTabs>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Sticky footer */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t bg-background/95 px-4 py-3 backdrop-blur md:px-6">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {mode === "edit" && isContentChanged ? (
            <div className="flex flex-1 items-center gap-2">
              <Label
                htmlFor="change-note"
                className="text-xs text-muted-foreground"
              >
                Change note
              </Label>
              <Input
                id="change-note"
                value={draft.changeNote}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, changeNote: e.target.value }))
                }
                placeholder="What changed?"
                className="h-9 max-w-md"
                maxLength={1000}
              />
            </div>
          ) : mode === "edit" ? (
            <div className="text-xs text-muted-foreground">
              {isDirty
                ? "Metadata-only update — no new version will be cut."
                : "No changes yet."}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">
              {!enText
                ? "English content is required to save."
                : "Ready to create."}
            </div>
          )}
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              onClick={() => {
                if (mode === "edit" && promptId)
                  navigate(`/prompts/${promptId}`)
                else navigate("/prompts")
              }}
              disabled={
                createPrompt.isPending ||
                createVersion.isPending ||
                updateMetadata.isPending
              }
            >
              Cancel
            </Button>
            <Button onClick={submit} disabled={!canSave}>
              {createPrompt.isPending ||
              createVersion.isPending ||
              updateMetadata.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Save className="size-4" />
              )}
              {saveLabel}
            </Button>
          </div>
        </div>
      </div>

      <UnsavedChangesDialog blocker={blocker} />

      <Dialog open={overwriteConfirmOpen} onOpenChange={setOverwriteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Overwrite existing translations?</DialogTitle>
            <DialogDescription>
              {populatedNonEnLangs.length} non-English tab
              {populatedNonEnLangs.length === 1 ? " has" : "s have"} content
              already (
              {populatedNonEnLangs
                .map((c) => LANGUAGE_NAMES[c])
                .join(", ")}
              ). Translating from English will replace
              {populatedNonEnLangs.length === 1 ? " it" : " them"}.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOverwriteConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                setOverwriteConfirmOpen(false)
                void runTranslate()
              }}
            >
              Overwrite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ── Per-language pane ──────────────────────────────────────────────────────

function LanguagePane({
  lang,
  value,
  baseline,
  onChange,
}: {
  lang: LanguageCode
  value: string
  baseline: string | null
  onChange: (value: string) => void
}) {
  const isEmpty = (value ?? "").trim().length === 0
  const isEnglish = lang === "en"
  return (
    <div className="flex flex-col gap-3">
      {baseline != null && (
        <div className="flex flex-col gap-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Previous version · read-only
          </p>
          <div
            className={cn(
              "max-h-[180px] overflow-auto rounded-md border border-border/60 bg-muted/40 p-4",
              "font-mono text-[13px] leading-7 text-muted-foreground",
              "whitespace-pre-wrap break-words",
            )}
          >
            {baseline}
          </div>
        </div>
      )}
      <div className="flex flex-col gap-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Draft · {LANGUAGE_NAMES[lang]}
          {isEnglish && <span className="ml-1 text-foreground/70">★</span>}
        </p>
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            isEnglish
              ? "Write the system prompt your model should receive…"
              : `Optional — leave empty to fall back to English.`
          }
          className={cn(
            "min-h-[280px] resize-y",
            "font-mono text-[13px] leading-7",
          )}
          spellCheck={false}
        />
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          {isEmpty && !isEnglish ? (
            <span>Empty → falls back to EN at runtime.</span>
          ) : (
            <span />
          )}
          <span className="tabular-nums">{(value ?? "").length} chars</span>
        </div>
      </div>
    </div>
  )
}

// ── Unsaved-changes blocker dialog ─────────────────────────────────────────

function UnsavedChangesDialog({
  blocker,
}: {
  blocker: ReturnType<typeof useBlocker>
}) {
  const open = blocker.state === "blocked"
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o && open) blocker.reset?.()
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Discard your changes?</DialogTitle>
          <DialogDescription>
            You have unsaved edits. Leaving will lose them — versions are only
            written when you save.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => blocker.reset?.()}>
            Keep editing
          </Button>
          <Button
            variant="destructive"
            onClick={() => blocker.proceed?.()}
          >
            <X className="size-4" />
            Discard
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

const SLUG_NON_ALNUM = /[^a-z0-9]+/g

function slugify(value: string): string {
  return value.toLowerCase().replace(SLUG_NON_ALNUM, "-").replace(/^-+|-+$/g, "")
}

function arraysEqual<T>(a: T[], b: T[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false
  return true
}

/**
 * Drop empty languages so the wire payload stays compact. EN is always
 * included even if the user typed only whitespace (backend will reject —
 * we never reach this code with empty EN because canSave gates it).
 */
function pickNonEmpty(
  content: Record<LanguageCode, string>,
  alwaysInclude: LanguageCode,
): Record<string, string> {
  const out: Record<string, string> = {}
  for (const code of LANGUAGE_ORDER) {
    const text = content[code]
    if ((text ?? "").trim().length > 0 || code === alwaysInclude) {
      out[code] = text ?? ""
    }
  }
  return out
}
