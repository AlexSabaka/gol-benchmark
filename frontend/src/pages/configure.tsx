import { useCallback, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  Link2,
  Loader2,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/layout/page-header"
import { StepButton, StepFooter } from "@/components/wizard"
import { ConfigForm } from "@/components/plugin-config/config-form"
import { fetchPromptFromUrl, configToYaml } from "@/api/testsets"
import { usePlugins } from "@/hooks/use-plugins"
import { useGenerateTestset } from "@/hooks/use-testsets"
import { useMetadata } from "@/hooks/use-metadata"
import { useLocalStorageState } from "@/lib/local-storage"
import { LANGUAGE_META } from "@/lib/constants"
import type { GenerateRequest, PromptConfig } from "@/types"

// ── Step types ─────────────────────────────────────────────────────────────────

type ConfigureStepId = "setup" | "plugins" | "prompts" | "review"

const CONFIGURE_STEPS: Array<{
  id: ConfigureStepId
  label: string
  description: string
}> = [
  { id: "setup",   label: "Setup",   description: "Name, seed, or import config" },
  { id: "plugins", label: "Plugins", description: "Select & configure tasks" },
  { id: "prompts", label: "Prompts", description: "Prompt matrix & languages" },
  { id: "review",  label: "Review",  description: "Summary & generate" },
]


// ── Main page ──────────────────────────────────────────────────────────────────

export default function ConfigurePage() {
  const nav = useNavigate()
  const { data: plugins } = usePlugins()
  const { data: meta } = useMetadata()
  const genMutation = useGenerateTestset()

  // ── Derived from metadata ──
  const userStylesList = meta?.user_styles ?? []
  const systemStylesList = meta?.system_styles ?? []
  const languagesList = (meta?.languages ?? []).map((code) => ({
    code,
    flag: LANGUAGE_META[code]?.flag ?? code,
    label: LANGUAGE_META[code]?.label ?? code,
  }))

  // ── Wizard step ──
  const [activeStep, setActiveStep] = useLocalStorageState<ConfigureStepId>(
    "configure-page-active-step",
    "setup",
    {
      sanitize: (v) =>
        typeof v === "string" && ["setup", "plugins", "prompts", "review"].includes(v)
          ? (v as ConfigureStepId)
          : "setup",
    },
  )

  // ── Step 1 — Setup ──
  const [name, setName] = useState("web_benchmark")
  const [description, setDescription] = useState("")
  const [seed, setSeed] = useState(42)

  // ── Step 2 — Plugins ──
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
  const [taskConfigs, setTaskConfigs] = useState<Record<string, Record<string, unknown>>>({})
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

  // ── Step 3 — Prompts ──
  const [userStyles, setUserStyles] = useState<Set<string>>(new Set())
  const [systemStyles, setSystemStyles] = useState<Set<string>>(new Set())
  const [languages, setLanguages] = useState<Set<string>>(new Set())
  const [useCustomPrompt, setUseCustomPrompt] = useState(false)
  const [customSystemPrompt, setCustomSystemPrompt] = useState("")
  const [promptUrl, setPromptUrl] = useState("")
  const [fetchingUrl, setFetchingUrl] = useState(false)
  const promptFileRef = useRef<HTMLInputElement>(null)

  // ── Review ──
  const [copyingYaml, setCopyingYaml] = useState(false)

  // ── Derived ──
  const combos =
    userStyles.size > 0 && systemStyles.size > 0 && languages.size > 0
      ? userStyles.size * systemStyles.size * languages.size
      : 0

  const stepIndex = CONFIGURE_STEPS.findIndex((s) => s.id === activeStep)
  const isComplete = (id: ConfigureStepId) =>
    CONFIGURE_STEPS.findIndex((s) => s.id === id) < stepIndex

  const stepSummary = (id: ConfigureStepId): string => {
    switch (id) {
      case "setup":
        return name || "Unnamed"
      case "plugins":
        return selectedTasks.size > 0
          ? `${selectedTasks.size} plugin${selectedTasks.size !== 1 ? "s" : ""} selected`
          : "No plugins selected"
      case "prompts":
        return combos > 0 ? `${combos} combination${combos !== 1 ? "s" : ""}` : "No combinations selected"
      case "review":
        return selectedTasks.size > 0 && combos > 0 ? "Ready to generate" : "Incomplete"
    }
  }

  // ── Handlers ──

  const toggleCheckboxSet = useCallback(
    (value: string, setter: React.Dispatch<React.SetStateAction<Set<string>>>) => {
      setter((prev) => {
        const next = new Set(prev)
        if (next.has(value)) next.delete(value)
        else next.add(value)
        return next
      })
    },
    [],
  )

  const handleFieldChange = useCallback(
    (taskType: string, fieldName: string, value: unknown) => {
      setTaskConfigs((prev) => ({
        ...prev,
        [taskType]: { ...prev[taskType], [fieldName]: value },
      }))
    },
    [],
  )

  const toggleTask = useCallback((taskType: string, checked: boolean) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev)
      if (checked) next.add(taskType)
      else next.delete(taskType)
      return next
    })
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (checked) next.add(taskType)
      else next.delete(taskType)
      return next
    })
  }, [])

  const toggleExpanded = useCallback((taskType: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskType)) next.delete(taskType)
      else next.add(taskType)
      return next
    })
  }, [])

  // Build the GenerateRequest from current state
  const buildRequest = useCallback((): GenerateRequest => {
    const promptConfigs: PromptConfig[] = []
    for (const us of userStyles) {
      for (const ss of systemStyles) {
        for (const lang of languages) {
          promptConfigs.push({ user_style: us, system_style: ss, language: lang })
        }
      }
    }
    return {
      name,
      description,
      seed,
      cell_markers: ["1", "0"],
      tasks: Array.from(selectedTasks).map((type) => ({
        type,
        generation: { ...taskConfigs[type], seed },
        prompt_configs: promptConfigs,
      })),
      ...(useCustomPrompt && customSystemPrompt
        ? { custom_system_prompt: customSystemPrompt }
        : {}),
    }
  }, [
    name,
    description,
    seed,
    selectedTasks,
    taskConfigs,
    userStyles,
    systemStyles,
    languages,
    useCustomPrompt,
    customSystemPrompt,
  ])

  const handleGenerate = async () => {
    if (selectedTasks.size === 0) {
      toast.error("Select at least one task")
      return
    }
    try {
      const res = await genMutation.mutateAsync(buildRequest())
      toast.success(`Test set generated: ${res.filename}`)
      nav("/testsets")
    } catch (err) {
      toast.error(
        `Generation failed: ${err instanceof Error ? err.message : "Unknown error"}`,
      )
    }
  }

  const handleCopyYaml = async () => {
    setCopyingYaml(true)
    try {
      const yaml = await configToYaml(buildRequest())
      await navigator.clipboard.writeText(yaml)
      toast.success("YAML config copied to clipboard")
    } catch {
      toast.error("Failed to copy YAML")
    } finally {
      setCopyingYaml(false)
    }
  }

  const handleDownloadYaml = async () => {
    try {
      const yaml = await configToYaml(buildRequest())
      const blob = new Blob([yaml], { type: "text/yaml" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${name}_config.yaml`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to download YAML")
    }
  }

  const isGenerating = genMutation.isPending

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <PageHeader title="Configure" />

      {/* ── Step navigation ── */}
      <div className="flex items-stretch divide-x overflow-hidden rounded-lg border bg-card">
        {CONFIGURE_STEPS.map((step, i) => (
          <StepButton
            key={step.id}
            step={step}
            index={i}
            active={activeStep === step.id}
            complete={isComplete(step.id)}
            summary={stepSummary(step.id)}
            onClick={() => setActiveStep(step.id)}
          />
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════
          STEP 1 — Setup
      ══════════════════════════════════════════════════════ */}
      {activeStep === "setup" && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Global Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Name</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="h-8"
                    placeholder="web_benchmark"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Seed</Label>
                  <Input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(Number(e.target.value))}
                    className="h-8 w-28"
                  />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label className="text-xs">Description</Label>
                  <Input
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="h-8"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <StepFooter
            nextLabel="Continue to Plugins"
            onNext={() => setActiveStep("plugins")}
            nextDisabled={!name.trim()}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 2 — Plugins
      ══════════════════════════════════════════════════════ */}
      {activeStep === "plugins" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Select plugins</p>
            <Badge variant="secondary" className="text-xs">
              {selectedTasks.size} selected
            </Badge>
          </div>

          <div className="space-y-2">
            {plugins?.map((p) => {
              const selected = selectedTasks.has(p.task_type)
              const expanded = expandedTasks.has(p.task_type)
              return (
                <Collapsible
                  key={p.task_type}
                  open={expanded}
                  onOpenChange={() => toggleExpanded(p.task_type)}
                >
                  <div
                    className={`overflow-hidden rounded-lg border transition-colors ${
                      selected ? "border-primary/30 bg-primary/5" : "border-border bg-card"
                    }`}
                  >
                    {/* Row header */}
                    <div className="flex items-center gap-3 px-4 py-3">
                      <Checkbox
                        checked={selected}
                        onCheckedChange={(c) => toggleTask(p.task_type, !!c)}
                        aria-label={`Select ${p.display_name}`}
                      />
                      <CollapsibleTrigger asChild>
                        <button
                          type="button"
                          className="flex flex-1 items-center gap-2 text-left min-w-0"
                        >
                          <ChevronRight
                            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
                              expanded ? "rotate-90" : ""
                            }`}
                          />
                          <div className="min-w-0">
                            <span className="text-sm font-medium">{p.display_name}</span>
                            {p.description && (
                              <p className="text-xs text-muted-foreground">{p.description}</p>
                            )}
                          </div>
                        </button>
                      </CollapsibleTrigger>
                      {selected && (
                        <Badge variant="secondary" className="shrink-0 text-[10px]">
                          active
                        </Badge>
                      )}
                    </div>

                    {/* Expanded config */}
                    <CollapsibleContent>
                      <div
                        className={`border-t px-4 py-4 transition-opacity ${
                          !selected ? "pointer-events-none opacity-50" : ""
                        }`}
                      >
                        <ConfigForm
                          taskType={p.task_type}
                          values={taskConfigs[p.task_type] ?? {}}
                          onChange={handleFieldChange}
                        />
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              )
            })}

            {!plugins && (
              <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading plugins…
              </div>
            )}

            {plugins?.length === 0 && (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No plugins available.
              </div>
            )}
          </div>

          <StepFooter
            onPrevious={() => setActiveStep("setup")}
            previousLabel="Back to Setup"
            nextLabel="Continue to Prompts"
            onNext={() => setActiveStep("prompts")}
            nextDisabled={selectedTasks.size === 0}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 3 — Prompts
      ══════════════════════════════════════════════════════ */}
      {activeStep === "prompts" && (
        <div className="space-y-4">
          {/* Prompt matrix card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Prompt Configuration</CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {combos} combination{combos !== 1 ? "s" : ""}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 sm:grid-cols-3">
                {/* User Styles */}
                <div className="space-y-2">
                  <Label className="text-xs">User Styles</Label>
                  <div className="space-y-1.5">
                    {userStylesList.map((s) => (
                      <label
                        key={s}
                        className="flex items-center gap-2 text-xs cursor-pointer"
                      >
                        <Checkbox
                          checked={userStyles.has(s)}
                          onCheckedChange={() => toggleCheckboxSet(s, setUserStyles)}
                        />
                        {s}
                      </label>
                    ))}
                  </div>
                </div>

                {/* System Styles */}
                <div className="space-y-2">
                  <Label className="text-xs">System Styles</Label>
                  <div className="space-y-1.5">
                    {systemStylesList.map((s) => (
                      <label
                        key={s}
                        className="flex items-center gap-2 text-xs cursor-pointer"
                      >
                        <Checkbox
                          checked={systemStyles.has(s)}
                          onCheckedChange={() => toggleCheckboxSet(s, setSystemStyles)}
                        />
                        {s}
                      </label>
                    ))}
                    <Separator className="my-1" />
                    {/* Custom prompt toggle */}
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <Checkbox
                        checked={useCustomPrompt}
                        onCheckedChange={(c) => setUseCustomPrompt(!!c)}
                      />
                      <span className="font-medium">custom</span>
                    </label>
                  </div>
                </div>

                {/* Languages */}
                <div className="space-y-2">
                  <Label className="text-xs">Languages</Label>
                  <div className="space-y-1.5">
                    {languagesList.map((l) => (
                      <label
                        key={l.code}
                        className="flex items-center gap-2 text-xs cursor-pointer"
                      >
                        <Checkbox
                          checked={languages.has(l.code)}
                          onCheckedChange={() => toggleCheckboxSet(l.code, setLanguages)}
                        />
                        <span>{l.flag}</span>
                        <span>{l.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Custom System Prompt — only shown when toggle is active */}
          {useCustomPrompt && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">
                  Custom System Prompt
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    overrides style-based system prompt
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Tabs defaultValue="text">
                  <TabsList className="h-7">
                    <TabsTrigger value="text" className="text-xs h-6 px-2">
                      Text
                    </TabsTrigger>
                    <TabsTrigger value="file" className="text-xs h-6 px-2">
                      File Upload
                    </TabsTrigger>
                    <TabsTrigger value="url" className="text-xs h-6 px-2">
                      From URL
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="text" className="mt-2">
                    <Textarea
                      value={customSystemPrompt}
                      onChange={(e) => setCustomSystemPrompt(e.target.value)}
                      placeholder="Enter a custom system prompt…"
                      className="min-h-[100px] text-xs"
                    />
                  </TabsContent>

                  <TabsContent value="file" className="mt-2">
                    <Input
                      ref={promptFileRef}
                      type="file"
                      accept=".txt,.md"
                      className="h-8 max-w-md"
                      onChange={async (e) => {
                        const file = e.target.files?.[0]
                        if (!file) return
                        const text = await file.text()
                        setCustomSystemPrompt(text)
                        toast.success(
                          `Loaded ${text.length} characters from ${file.name}`,
                        )
                      }}
                    />
                  </TabsContent>

                  <TabsContent value="url" className="mt-2">
                    <div className="flex gap-2">
                      <Input
                        value={promptUrl}
                        onChange={(e) => setPromptUrl(e.target.value)}
                        placeholder="https://gist.githubusercontent.com/…"
                        className="h-8"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!promptUrl || fetchingUrl}
                        onClick={async () => {
                          setFetchingUrl(true)
                          try {
                            const res = await fetchPromptFromUrl(promptUrl)
                            setCustomSystemPrompt(res.text)
                            toast.success(`Fetched ${res.text.length} characters`)
                          } catch (err) {
                            toast.error(
                              `Fetch failed: ${err instanceof Error ? err.message : "Unknown error"}`,
                            )
                          } finally {
                            setFetchingUrl(false)
                          }
                        }}
                      >
                        {fetchingUrl ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Link2 className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>

                {customSystemPrompt && (
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{customSystemPrompt.length} characters</span>
                    {customSystemPrompt.length > 4000 && (
                      <span className="text-yellow-600">
                        Long prompt — may exceed some model context windows
                      </span>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 text-[10px] px-1"
                      onClick={() => setCustomSystemPrompt("")}
                    >
                      Clear
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {combos === 0 && (
            <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p className="text-sm">
                No prompt combinations selected — choose at least one option from each column (User Style, System Style, Language).
              </p>
            </div>
          )}

          <StepFooter
            onPrevious={() => setActiveStep("plugins")}
            previousLabel="Back to Plugins"
            nextLabel="Continue to Review"
            onNext={() => setActiveStep("review")}
            nextDisabled={combos === 0}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 4 — Review & Generate
      ══════════════════════════════════════════════════════ */}
      {activeStep === "review" && (
        <div className="space-y-4">
          {/* Summary grid */}
          <div className="grid gap-4 sm:grid-cols-3">
            {/* Testset column */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                  Testset
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <p className="text-sm font-semibold">{name || "Unnamed"}</p>
                  <p className="text-xs text-muted-foreground">
                    Seed: <span className="font-mono">{seed}</span>
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    {description || (
                      <span className="italic">No description</span>
                    )}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Plugins column */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                    Plugins
                  </CardTitle>
                  <Badge variant="secondary" className="text-[10px]">
                    {selectedTasks.size} selected
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {selectedTasks.size === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No plugins selected
                  </p>
                ) : (
                  <ul className="space-y-0.5">
                    {Array.from(selectedTasks).map((taskType) => {
                      const plugin = plugins?.find((p) => p.task_type === taskType)
                      return (
                        <li key={taskType} className="text-xs">
                          {plugin?.display_name ?? taskType}
                        </li>
                      )
                    })}
                  </ul>
                )}
                {selectedTasks.size > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-0.5 text-[11px] text-muted-foreground">
                      <p>
                        Est. cases/plugin:{" "}
                        <span className="font-medium text-foreground">{combos}</span>
                      </p>
                      <p>
                        Total est. cases:{" "}
                        <span className="font-medium text-foreground">
                          {selectedTasks.size * combos}
                        </span>
                      </p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Prompts column */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                    Prompts
                  </CardTitle>
                  <Badge variant="secondary" className="text-[10px]">
                    {combos} combo{combos !== 1 ? "s" : ""}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2.5">
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    User
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {Array.from(userStyles).map((s) => (
                      <Badge key={s} variant="outline" className="text-[10px]">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    System
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {Array.from(systemStyles).map((s) => (
                      <Badge key={s} variant="outline" className="text-[10px]">
                        {s}
                      </Badge>
                    ))}
                    {useCustomPrompt && (
                      <Badge variant="secondary" className="text-[10px]">
                        custom prompt set
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    Languages
                  </p>
                  <p className="text-sm">
                    {Array.from(languages)
                      .map((code) => LANGUAGE_META[code]?.flag ?? code)
                      .join(" ")}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Warnings — shown between summary and action area */}
          {(selectedTasks.size === 0 || combos === 0) && (
            <div className="space-y-3">
              {selectedTasks.size === 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    No plugins selected — go back to{" "}
                    <button
                      type="button"
                      className="font-medium underline underline-offset-2 hover:no-underline"
                      onClick={() => setActiveStep("plugins")}
                    >
                      Plugins
                    </button>{" "}
                    and select at least one task before generating.
                  </p>
                </div>
              )}
              {combos === 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    No prompt combinations selected — go back to{" "}
                    <button
                      type="button"
                      className="font-medium underline underline-offset-2 hover:no-underline"
                      onClick={() => setActiveStep("prompts")}
                    >
                      Prompts
                    </button>{" "}
                    and select at least one User Style, System Style, and Language.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Action area */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
            <Button
              variant="outline"
              onClick={() => setActiveStep("prompts")}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Prompts
            </Button>

            <div className="flex items-center gap-3">
              {/* Split button: Copy YAML + Download dropdown */}
              <div className="flex">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyYaml}
                  disabled={copyingYaml || selectedTasks.size === 0 || combos === 0}
                  className="rounded-r-none border-r-0"
                >
                  {copyingYaml ? (
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Copy className="mr-2 h-3.5 w-3.5" />
                  )}
                  Copy YAML Config
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={selectedTasks.size === 0 || combos === 0}
                      className="rounded-l-none px-2"
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={handleDownloadYaml}>
                      <Download className="mr-2 h-4 w-4" />
                      Download YAML Config
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Generate */}
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || selectedTasks.size === 0 || combos === 0}
              >
                {isGenerating && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Generate Test Set
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
