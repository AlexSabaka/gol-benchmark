import { useState } from "react"
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
import { useTestset } from "@/hooks/use-testsets"
import { useGenerateTestset } from "@/hooks/use-testsets"
import type { ParamOverrides } from "@/types"

const USER_STYLES = ["minimal", "casual", "linguistic", "examples", "rules_math"]
const SYSTEM_STYLES = ["analytical", "casual", "adversarial", "none"]
const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Espanol" },
  { value: "fr", label: "Francais" },
  { value: "de", label: "Deutsch" },
  { value: "zh", label: "Chinese" },
  { value: "ua", label: "Ukrainian" },
]

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
  const { data: detail, isLoading: detailLoading } = useTestset(open ? testsetFilename : null)
  const generateMutation = useGenerateTestset()

  const [overrides, setOverrides] = useState<ParamOverrides>({})
  const [customPrompt, setCustomPrompt] = useState("")
  const [useCustomPrompt, setUseCustomPrompt] = useState(false)

  const handleConfirm = async () => {
    if (mode === "rerun") {
      // Navigate to Execute page with the testset filename
      nav(`/execute?testset=${encodeURIComponent(testsetFilename)}`)
      onOpenChange(false)
    } else {
      // Regenerate: build a new testset with modified params
      if (!detail) { toast.error("Test set details not loaded yet"); return }

      // generation_params is either a list of task configs or a dict with task/tasks
      const genParams = detail.generation_params
      let rawTasks: Array<Record<string, unknown>>

      if (Array.isArray(genParams)) {
        // generation_params IS the tasks array
        rawTasks = genParams as Array<Record<string, unknown>>
      } else {
        // generation_params is a dict — may have .tasks or .task
        const gp = genParams as Record<string, unknown>
        if (Array.isArray(gp.tasks)) {
          rawTasks = gp.tasks as Array<Record<string, unknown>>
        } else if (gp.task) {
          rawTasks = [gp.task as Record<string, unknown>]
        } else {
          // Fallback: construct from detail.task_types
          rawTasks = detail.task_types.map((t) => ({
            type: t,
            generation: {},
            prompt_configs: [{ user_style: "minimal", system_style: "analytical", language: "en" }],
          }))
        }
      }

      const modifiedTasks = rawTasks.map((t) => {
        const origConfigs = (t.prompt_configs ?? [{ user_style: "minimal", system_style: "analytical", language: "en" }]) as Array<{
          user_style: string; system_style: string; language: string
        }>

        return {
          type: (t.type as string) ?? "unknown",
          generation: (t.generation ?? {}) as Record<string, unknown>,
          prompt_configs: origConfigs.map((pc) => ({
            user_style: overrides.user_style ?? pc.user_style,
            system_style: useCustomPrompt ? "none" : (overrides.system_style ?? pc.system_style),
            language: overrides.language ?? pc.language,
          })),
        }
      })

      const metaName = (detail.metadata as Record<string, string>)?.name ?? "regen"

      try {
        const res = await generateMutation.mutateAsync({
          name: `${metaName}_variant`,
          description: "Regenerated with parameter overrides",
          tasks: modifiedTasks,
          cell_markers: ["1", "0"],
          seed: 42,
          custom_system_prompt: useCustomPrompt ? customPrompt : undefined,
        })
        toast.success(`Test set regenerated: ${res.filename}`)
        onOpenChange(false)
      } catch (err) {
        toast.error(`Regeneration failed: ${err instanceof Error ? err.message : "Unknown error"}`)
      }
    }
  }

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

        {detailLoading && mode === "regenerate" ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading test set details...
          </div>
        ) : (
          <div className="space-y-4 py-2">
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
                  {USER_STYLES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* System style */}
            <div className="space-y-1.5">
              <Label className="text-xs">System Prompt Style</Label>
              <Select
                value={useCustomPrompt ? "__custom__" : (overrides.system_style ?? "__default__")}
                onValueChange={(v) => {
                  if (v === "__custom__") {
                    setUseCustomPrompt(true)
                    setOverrides((o) => ({ ...o, system_style: undefined }))
                  } else {
                    setUseCustomPrompt(false)
                    setOverrides((o) => ({
                      ...o,
                      system_style: v === "__default__" ? undefined : v,
                    }))
                  }
                }}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Keep original" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">Keep original</SelectItem>
                  {SYSTEM_STYLES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                  <SelectItem value="__custom__">Custom prompt...</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom system prompt textarea */}
            {useCustomPrompt && (
              <div className="space-y-1.5">
                <Label className="text-xs">Custom System Prompt</Label>
                <Textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Enter a custom system prompt..."
                  className="min-h-20 text-xs"
                />
                <p className="text-[10px] text-muted-foreground">
                  {customPrompt.length} characters
                </p>
              </div>
            )}

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
                  {LANGUAGES.map((l) => (
                    <SelectItem key={l.value} value={l.value}>
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
            disabled={generateMutation.isPending || (mode === "regenerate" && detailLoading)}
          >
            {generateMutation.isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
            {mode === "rerun" ? "Go to Execute" : "Regenerate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
