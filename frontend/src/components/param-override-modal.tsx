import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  PromptPicker,
  type PromptRef,
} from "@/components/prompts/prompt-picker"
import { useTestset } from "@/hooks/use-testsets"
import { useGenerateTestset } from "@/hooks/use-testsets"
import { useMetadata } from "@/hooks/use-metadata"
import { LANGUAGE_META } from "@/lib/constants"
import type {
  GenerateRequest,
  ParamOverrides,
  PromptConfig,
  TaskConfig,
} from "@/types"

interface ParamOverrideModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** The .json.gz filename of the testset */
  testsetFilename: string
  mode: "rerun" | "regenerate"
}

export function ParamOverrideModal({
  open,
  onOpenChange,
  testsetFilename,
  mode,
}: ParamOverrideModalProps) {
  const nav = useNavigate()
  const { data: detail, isLoading: detailLoading } = useTestset(
    open ? testsetFilename : null,
  )
  const generateMutation = useGenerateTestset()
  const { data: meta } = useMetadata()

  const userStylesList = meta?.user_styles ?? []
  const languagesList = (meta?.languages ?? []).map((code) => ({
    code,
    label: `${LANGUAGE_META[code]?.flag ?? ""} ${LANGUAGE_META[code]?.label ?? code}`.trim(),
  }))

  const [overrides, setOverrides] = useState<ParamOverrides>({})
  const [promptOverride, setPromptOverride] = useState<PromptRef[]>([])
  const [customPrompt, setCustomPrompt] = useState("")
  const [useCustomPrompt, setUseCustomPrompt] = useState(false)

  // ── Dirty detection — when ANY prompt-related field is touched, the
  // rerun path forks into "regenerate-then-run" (one new testset on the
  // fly) instead of just navigating. Sampling-only changes flow through
  // the existing /execute wizard untouched.
  const isPromptDirty = useMemo(
    () =>
      overrides.user_style != null ||
      overrides.language != null ||
      promptOverride.length > 0 ||
      useCustomPrompt,
    [overrides, promptOverride, useCustomPrompt],
  )

  const buildModifiedRequest = (): GenerateRequest | null => {
    if (!detail) return null

    const genParams = detail.generation_params
    let rawTasks: Array<Record<string, unknown>>
    if (Array.isArray(genParams)) {
      rawTasks = genParams as Array<Record<string, unknown>>
    } else {
      const gp = genParams as Record<string, unknown>
      if (Array.isArray(gp.tasks)) {
        rawTasks = gp.tasks as Array<Record<string, unknown>>
      } else if (gp.task) {
        rawTasks = [gp.task as Record<string, unknown>]
      } else {
        rawTasks = detail.task_types.map((t) => ({
          type: t,
          generation: {},
          prompt_configs: [
            { user_style: "minimal", system_style: "analytical", language: "en" },
          ],
        }))
      }
    }

    const overrideRef = promptOverride[0] ?? null

    const modifiedTasks: TaskConfig[] = rawTasks.map((t) => {
      const origConfigs = (t.prompt_configs ?? [
        { user_style: "minimal", system_style: "analytical", language: "en" },
      ]) as PromptConfig[]

      return {
        type: (t.type as string) ?? "unknown",
        generation: (t.generation ?? {}) as Record<string, unknown>,
        prompt_configs: origConfigs.map((pc): PromptConfig => {
          const base: PromptConfig = {
            user_style: overrides.user_style ?? pc.user_style,
            system_style: useCustomPrompt
              ? "none"
              : overrideRef
                ? "" // backend derives from prompt_id
                : pc.system_style,
            language: overrides.language ?? pc.language,
          }
          if (useCustomPrompt) return base
          if (overrideRef) {
            base.prompt_id = overrideRef.id
            if (overrideRef.version != null)
              base.prompt_version = overrideRef.version
            return base
          }
          if (pc.prompt_id) {
            base.prompt_id = pc.prompt_id
            if (pc.prompt_version != null) base.prompt_version = pc.prompt_version
          }
          return base
        }),
      }
    })

    const metaName = (detail.metadata as Record<string, string>)?.name ?? "regen"
    return {
      name: `${metaName}_variant`,
      description: `Regenerated with parameter overrides (${mode})`,
      tasks: modifiedTasks,
      cell_markers: ["1", "0"],
      seed: 42,
      ...(useCustomPrompt && customPrompt
        ? { custom_system_prompt: customPrompt }
        : {}),
    }
  }

  const handleConfirm = async () => {
    if (mode === "rerun") {
      // Clean path — no prompt fields touched. Just open Execute pointed
      // at the existing testset. Sampling overrides happen on that page.
      if (!isPromptDirty) {
        nav(`/execute?testset=${encodeURIComponent(testsetFilename)}`)
        onOpenChange(false)
        return
      }
      // Dirty path — regenerate first, then point Execute at the new file.
      if (!detail) {
        toast.error("Test set details not loaded yet")
        return
      }
      const req = buildModifiedRequest()
      if (!req) return
      try {
        const res = await generateMutation.mutateAsync(req)
        toast.success(`Generated ${res.filename} — opening Execute…`)
        nav(`/execute?testset=${encodeURIComponent(res.filename)}`)
        onOpenChange(false)
      } catch (err) {
        toast.error(
          `Regenerate-and-run failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        )
      }
      return
    }

    // ── Regenerate ──
    if (!detail) {
      toast.error("Test set details not loaded yet")
      return
    }
    const req = buildModifiedRequest()
    if (!req) return
    try {
      const res = await generateMutation.mutateAsync(req)
      toast.success(`Test set regenerated: ${res.filename}`)
      onOpenChange(false)
    } catch (err) {
      toast.error(
        `Regeneration failed: ${err instanceof Error ? err.message : "Unknown error"}`,
      )
    }
  }

  const primaryLabel =
    mode === "rerun"
      ? isPromptDirty
        ? "Regenerate & open Execute"
        : "Go to Execute"
      : "Regenerate"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="pr-8">
            {mode === "rerun" ? "Rerun with Different Params" : "Regenerate with Different Params"}
          </DialogTitle>
          <DialogDescription>
            Override prompt parameters for{" "}
            <span className="block max-w-full truncate font-mono text-xs" title={testsetFilename}>
              {testsetFilename.replace(".json.gz", "")}
            </span>
          </DialogDescription>
        </DialogHeader>

        {detailLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading test set details...
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {mode === "rerun" && isPromptDirty && (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
                Changing prompts creates a new testset before opening Execute.
              </div>
            )}

            {/* User style */}
            <div className="space-y-1.5">
              <Label className="text-xs">User Prompt Style</Label>
              <Select
                value={overrides.user_style ?? "__default__"}
                onValueChange={(v) =>
                  setOverrides((o) => ({
                    ...o,
                    user_style: v === "__default__" ? undefined : v,
                  }))
                }
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Keep original" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">Keep original</SelectItem>
                  {userStylesList.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Prompt (Prompt Studio) */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">System Prompt</Label>
                <button
                  type="button"
                  onClick={() => setUseCustomPrompt((v) => !v)}
                  className="text-[10px] text-muted-foreground underline-offset-2 hover:underline"
                >
                  {useCustomPrompt ? "Use catalog" : "Use one-off textarea"}
                </button>
              </div>
              {useCustomPrompt ? (
                <>
                  <Textarea
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    placeholder="Enter a custom system prompt..."
                    className="min-h-20 text-xs"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    {customPrompt.length} characters · bypasses the prompt catalog
                  </p>
                </>
              ) : (
                <>
                  <PromptPicker
                    mode="single"
                    value={promptOverride}
                    onChange={setPromptOverride}
                  />
                  <p className="text-[10px] text-muted-foreground">
                    {promptOverride.length === 0
                      ? "No override — every cell keeps its original prompt."
                      : "Override applied to every cell on regeneration."}
                  </p>
                </>
              )}
            </div>

            {/* Language */}
            <div className="space-y-1.5">
              <Label className="text-xs">Language</Label>
              <Select
                value={overrides.language ?? "__default__"}
                onValueChange={(v) =>
                  setOverrides((o) => ({
                    ...o,
                    language: v === "__default__" ? undefined : v,
                  }))
                }
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Keep original" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">Keep original</SelectItem>
                  {languagesList.map((l) => (
                    <SelectItem key={l.code} value={l.code}>
                      {l.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={generateMutation.isPending || detailLoading}
          >
            {generateMutation.isPending && (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            )}
            {primaryLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
