import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { AlertTriangle, ArrowLeft, Loader2, Play, Plus, Search, Star, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/layout/page-header"
import { ConfigForm } from "@/components/plugin-config/config-form"
import { FieldRenderer } from "@/components/plugin-config/field-renderer"
import { StepButton, StepFooter } from "@/components/wizard"
import {
  HuggingFaceSection,
  OllamaSection,
  OpenAIEndpointSection,
  selectedModelKey,
  type OpenAIEndpoint,
  type SelectedModel,
} from "@/components/model-selection"
import { useRunMatrixExecution } from "@/hooks/use-matrix"
import { usePlugins, usePluginSchema } from "@/hooks/use-plugins"
import { useMetadata } from "@/hooks/use-metadata"
import { loadCredentials } from "@/lib/credential-store"
import { favoriteKey, getFavorites, toggleFavorite } from "@/lib/favorite-models"
import { useLocalStorageState } from "@/lib/local-storage"
import { LANGUAGE_META } from "@/lib/constants"
import type { ConfigField, MatrixFieldAxis, MatrixModelGroup, MatrixRunRequest } from "@/types"

// ── Constants ──────────────────────────────────────────────────────────────────

const SUPPORTED_AXIS_TYPES = new Set(["number", "select", "boolean", "multi-select"])

// ── Types ──────────────────────────────────────────────────────────────────────

type MatrixStepId = "setup" | "axes" | "models" | "settings" | "review"

const MATRIX_STEPS: Array<{ id: MatrixStepId; label: string; description: string }> = [
  { id: "setup",    label: "Setup",    description: "Plugin, name, seed, base config" },
  { id: "axes",     label: "Axes",     description: "Prompt + field variation axes" },
  { id: "models",   label: "Models",   description: "Pick providers and models" },
  { id: "settings", label: "Settings", description: "Tune sampling overrides" },
  { id: "review",   label: "Review",   description: "Summary & launch" },
]

interface FieldAxisState {
  draft: unknown
  values: unknown[]
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function serializeVariant(value: unknown): string {
  return JSON.stringify(value)
}

function formatVariant(value: unknown): string {
  if (typeof value === "boolean") return value ? "true" : "false"
  if (Array.isArray(value)) return value.length > 0 ? value.join(", ") : "(empty)"
  return String(value)
}

function getDefaultFieldValue(field: ConfigField, baseValue: unknown, draftValue: unknown): unknown {
  if (draftValue !== undefined) return draftValue
  if (baseValue !== undefined) return baseValue
  return field.default
}

function productOf(values: number[]): number {
  return values.reduce((acc, value) => acc * value, 1)
}

// ── Field axis editor (matrix-specific) ───────────────────────────────────────

function FieldAxisEditor({
  field,
  baseValue,
  axisState,
  onDraftChange,
  onAddVariant,
  onRemoveVariant,
}: {
  field: ConfigField
  baseValue: unknown
  axisState: FieldAxisState
  onDraftChange: (value: unknown) => void
  onAddVariant: () => void
  onRemoveVariant: (value: unknown) => void
}) {
  return (
    <div className="rounded border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{field.label}</p>
          <p className="text-xs text-muted-foreground">{field.type} axis</p>
        </div>
        <Badge variant="outline" className="text-[10px]">
          {axisState.values.length} variant{axisState.values.length !== 1 ? "s" : ""}
        </Badge>
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <FieldRenderer
          field={field}
          value={getDefaultFieldValue(field, baseValue, axisState.draft)}
          onChange={(_name, value) => onDraftChange(value)}
        />
        <Button variant="outline" size="sm" className="h-8 text-xs" onClick={onAddVariant}>
          <Plus className="mr-1 h-3 w-3" /> Add Variant
        </Button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {axisState.values.length === 0 ? (
          <span className="text-xs text-muted-foreground">No variants added yet</span>
        ) : (
          axisState.values.map((value) => (
            <Badge key={serializeVariant(value)} variant="secondary" className="gap-1 pr-1 text-[10px]">
              <span>{formatVariant(value)}</span>
              <button
                onClick={() => onRemoveVariant(value)}
                aria-label={`Remove ${field.name} variant`}
                type="button"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))
        )}
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

let endpointCounter = 1

export default function MatrixExecutionPage() {
  const navigate = useNavigate()
  const { data: plugins } = usePlugins()
  const { data: meta } = useMetadata()
  const runMutation = useRunMatrixExecution()

  const userStylesList = meta?.user_styles ?? []
  const systemStylesList = meta?.system_styles ?? []
  const languagesList = (meta?.languages ?? []).map((code) => ({
    code,
    flag: LANGUAGE_META[code]?.flag ?? code,
    label: LANGUAGE_META[code]?.label ?? code,
  }))

  // Wizard step
  const [activeStep, setActiveStep] = useLocalStorageState<MatrixStepId>(
    "matrix-page-active-step",
    "setup",
    {
      sanitize: (v) =>
        typeof v === "string" && ["setup", "axes", "models", "settings", "review"].includes(v)
          ? (v as MatrixStepId)
          : "setup",
    },
  )

  // Step 1 — Setup
  const [pluginType, setPluginType] = useState("")
  const { data: pluginSchema } = usePluginSchema(pluginType || null)
  const [namePrefix, setNamePrefix] = useState("matrix")
  const [description, setDescription] = useState("")
  const [seed, setSeed] = useState(42)
  const [baseConfig, setBaseConfig] = useState<Record<string, unknown>>({})

  // Step 2 — Axes
  const [userStyles, setUserStyles] = useState<Set<string>>(new Set())
  const [systemStyles, setSystemStyles] = useState<Set<string>>(new Set())
  const [languages, setLanguages] = useState<Set<string>>(new Set())
  const [fieldAxes, setFieldAxes] = useState<Record<string, FieldAxisState>>({})
  const [useCustomPrompt, setUseCustomPrompt] = useState(false)
  const [customSystemPrompt, setCustomSystemPrompt] = useState("")

  // Step 3 — Models
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [openaiEndpoints, setOpenaiEndpoints] = useState<OpenAIEndpoint[]>([
    { key: "ep_0", apiBase: "", apiKey: "" },
  ])
  const [selectedModels, setSelectedModels] = useState<Map<string, SelectedModel>>(new Map())
  const [modelSearch, setModelSearch] = useState("")
  const [favorites, setFavorites] = useState<Set<string>>(() => getFavorites())
  const [savedCredentials, setSavedCredentials] = useState<Array<{ apiBase: string; apiKey: string }>>([])
  const [ollamaOpen, setOllamaOpen] = useState(true)
  const [openaiOpen, setOpenaiOpen] = useState(true)
  const [hfOpen, setHfOpen] = useState(false)

  // Step 4 — Settings
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [noThink, setNoThink] = useState(true)

  useEffect(() => {
    loadCredentials().then(setSavedCredentials)
  }, [])

  // ── Derived values ──

  const plugin = useMemo(
    () => plugins?.find((candidate) => candidate.task_type === pluginType),
    [pluginType, plugins],
  )

  const matrixableFields = useMemo(
    () => (pluginSchema?.fields ?? []).filter((field) => SUPPORTED_AXIS_TYPES.has(field.type)),
    [pluginSchema],
  )
  const fixedOnlyFields = useMemo(
    () => (pluginSchema?.fields ?? []).filter((field) => !SUPPORTED_AXIS_TYPES.has(field.type)),
    [pluginSchema],
  )

  const activeFieldAxes = useMemo(() => Object.entries(fieldAxes), [fieldAxes])

  const promptCombos =
    userStyles.size > 0 && systemStyles.size > 0 && languages.size > 0
      ? userStyles.size * systemStyles.size * languages.size
      : 0
  const fieldCombos =
    activeFieldAxes.length === 0
      ? 1
      : productOf(activeFieldAxes.map(([, axis]) => Math.max(axis.values.length, 1)))
  const totalCells = promptCombos * fieldCombos
  const totalJobs = totalCells * selectedModels.size

  // Validation: every enabled field axis must have at least one variant
  const invalidFieldAxes = activeFieldAxes.filter(([, axis]) => axis.values.length === 0).map(([n]) => n)
  const axesReady =
    userStyles.size > 0 &&
    systemStyles.size > 0 &&
    languages.size > 0 &&
    invalidFieldAxes.length === 0

  const selectionSummary = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const model of selectedModels.values()) {
      counts[model.provider] = (counts[model.provider] ?? 0) + 1
    }
    return counts
  }, [selectedModels])

  const groupedFavorites = useMemo(() => {
    const groups: Record<string, string[]> = {}
    for (const key of favorites) {
      const separatorIndex = key.indexOf(":")
      if (separatorIndex === -1) continue
      const provider = key.slice(0, separatorIndex)
      const modelId = key.slice(separatorIndex + 1)
      ;(groups[provider] ??= []).push(modelId)
    }
    for (const ids of Object.values(groups)) ids.sort()
    return groups
  }, [favorites])

  const hasFavorites = favorites.size > 0

  const providerLabel: Record<string, string> = {
    ollama: "Ollama",
    openai_compatible: "OpenAI / Groq / OpenRouter",
    huggingface: "HuggingFace",
  }

  // Step completion / navigation
  const stepIndex = MATRIX_STEPS.findIndex((s) => s.id === activeStep)
  const isComplete = (id: MatrixStepId) => MATRIX_STEPS.findIndex((s) => s.id === id) < stepIndex
  const previousStep = stepIndex > 0 ? MATRIX_STEPS[stepIndex - 1] : null
  const nextStep = stepIndex < MATRIX_STEPS.length - 1 ? MATRIX_STEPS[stepIndex + 1] : null
  const goToPrevious = () => previousStep && setActiveStep(previousStep.id)
  const goToNext = () => nextStep && setActiveStep(nextStep.id)

  const stepSummary = (id: MatrixStepId): string => {
    switch (id) {
      case "setup":
        return plugin?.display_name ?? (pluginType ? pluginType : "No plugin selected")
      case "axes":
        return promptCombos > 0
          ? `${totalCells} cell${totalCells !== 1 ? "s" : ""} • ${promptCombos} prompt × ${fieldCombos} field`
          : "Axes incomplete"
      case "models":
        return selectedModels.size > 0
          ? `${selectedModels.size} model${selectedModels.size !== 1 ? "s" : ""} selected`
          : "No models selected"
      case "settings":
        return `Temp ${temperature.toFixed(2)} • ${noThink ? "no-think" : "thinking"}`
      case "review":
        return totalJobs > 0 ? `${totalJobs} jobs ready` : totalCells > 0 ? `${totalCells} cells ready` : "Incomplete"
    }
  }

  const nextDisabled =
    activeStep === "setup"
      ? !pluginType
      : activeStep === "axes"
        ? !axesReady
        : false

  // ── Handlers ──

  const togglePromptAxis = useCallback(
    (value: string, setter: React.Dispatch<React.SetStateAction<Set<string>>>) => {
      setter((previous) => {
        const next = new Set(previous)
        if (next.has(value)) next.delete(value)
        else next.add(value)
        return next
      })
    },
    [],
  )

  const handlePluginChange = useCallback((nextPluginType: string) => {
    setPluginType(nextPluginType)
    setBaseConfig({})
    setFieldAxes({})
  }, [])

  const handleBaseConfigChange = useCallback(
    (taskType: string, fieldName: string, value: unknown) => {
      if (taskType !== pluginType) return
      setBaseConfig((previous) => ({ ...previous, [fieldName]: value }))
    },
    [pluginType],
  )

  const toggleModelSelection = useCallback((model: SelectedModel) => {
    setSelectedModels((previous) => {
      const next = new Map(previous)
      const key = selectedModelKey(model)
      if (next.has(key)) next.delete(key)
      else next.set(key, model)
      return next
    })
  }, [])

  const handleToggleFavorite = useCallback((key: string) => {
    const next = toggleFavorite(key)
    setFavorites(new Set(next))
  }, [])

  const addOpenAIEndpoint = useCallback(() => {
    endpointCounter += 1
    setOpenaiEndpoints((previous) => [...previous, { key: `ep_${endpointCounter}`, apiBase: "", apiKey: "" }])
  }, [])

  const updateOpenAIEndpoint = useCallback((key: string, endpoint: OpenAIEndpoint) => {
    setOpenaiEndpoints((previous) => previous.map((candidate) => (candidate.key === key ? endpoint : candidate)))
  }, [])

  const removeOpenAIEndpoint = useCallback(
    (key: string) => {
      const removed = openaiEndpoints.find((candidate) => candidate.key === key)
      setOpenaiEndpoints((previous) => previous.filter((candidate) => candidate.key !== key))
      setSelectedModels((previous) => {
        const next = new Map(previous)
        for (const [modelKey, selectedModel] of previous.entries()) {
          if (selectedModel.provider === "openai_compatible" && selectedModel.apiBase === removed?.apiBase) {
            next.delete(modelKey)
          }
        }
        return next
      })
    },
    [openaiEndpoints],
  )

  const enableFieldAxis = useCallback(
    (field: ConfigField, enabled: boolean) => {
      setFieldAxes((previous) => {
        if (!enabled) {
          const next = { ...previous }
          delete next[field.name]
          return next
        }
        return {
          ...previous,
          [field.name]: {
            draft: baseConfig[field.name] ?? field.default,
            values: previous[field.name]?.values ?? [],
          },
        }
      })
    },
    [baseConfig],
  )

  const updateFieldAxisDraft = useCallback((fieldName: string, value: unknown) => {
    setFieldAxes((previous) => ({
      ...previous,
      [fieldName]: {
        draft: value,
        values: previous[fieldName]?.values ?? [],
      },
    }))
  }, [])

  const addFieldAxisVariant = useCallback(
    (field: ConfigField) => {
      setFieldAxes((previous) => {
        const current = previous[field.name]
        if (!current) return previous
        const candidateValue = getDefaultFieldValue(field, baseConfig[field.name], current.draft)
        if (
          candidateValue === undefined ||
          candidateValue === null ||
          (Array.isArray(candidateValue) && candidateValue.length === 0)
        ) {
          return previous
        }
        const exists = current.values.some(
          (value) => serializeVariant(value) === serializeVariant(candidateValue),
        )
        if (exists) return previous
        return {
          ...previous,
          [field.name]: {
            draft: candidateValue,
            values: [...current.values, candidateValue],
          },
        }
      })
    },
    [baseConfig],
  )

  const removeFieldAxisVariant = useCallback((fieldName: string, value: unknown) => {
    setFieldAxes((previous) => ({
      ...previous,
      [fieldName]: {
        draft: previous[fieldName]?.draft,
        values: (previous[fieldName]?.values ?? []).filter(
          (candidate) => serializeVariant(candidate) !== serializeVariant(value),
        ),
      },
    }))
  }, [])

  // ── Submission ──

  const handleSubmit = async (generateOnly: boolean) => {
    if (!pluginType) {
      toast.error("Select a benchmark plugin")
      return
    }
    if (!axesReady) {
      toast.error("Complete the axes step first")
      return
    }
    if (!generateOnly && selectedModels.size === 0) {
      toast.error("Select at least one model")
      return
    }

    const fieldAxisPayload: MatrixFieldAxis[] = []
    for (const [fieldName, axis] of activeFieldAxes) {
      if (axis.values.length === 0) {
        toast.error(`Add at least one variant for ${fieldName}`)
        return
      }
      fieldAxisPayload.push({ field_name: fieldName, values: axis.values })
    }

    const groupedModels = new Map<string, MatrixModelGroup>()
    for (const model of selectedModels.values()) {
      const key =
        model.provider === "openai_compatible"
          ? `openai_compatible:${model.apiBase ?? ""}`
          : model.provider
      if (!groupedModels.has(key)) {
        groupedModels.set(key, {
          provider: model.provider,
          models: [],
          ...(model.ollamaHost && { ollama_host: model.ollamaHost }),
          ...(model.apiBase && { api_base: model.apiBase, api_key: model.apiKey ?? "" }),
        })
      }
      groupedModels.get(key)!.models.push(model.id)
    }

    const request: MatrixRunRequest = {
      plugin_type: pluginType,
      name_prefix: namePrefix || "matrix",
      description,
      generate_only: generateOnly,
      seed,
      temperature,
      max_tokens: maxTokens,
      no_think: noThink,
      cell_markers: ["1", "0"],
      ...(useCustomPrompt && customSystemPrompt.trim() && {
        custom_system_prompt: customSystemPrompt.trim(),
      }),
      base_generation: baseConfig,
      prompt_axes: {
        user_styles: Array.from(userStyles),
        system_styles: Array.from(systemStyles),
        languages: Array.from(languages),
      },
      field_axes: fieldAxisPayload,
      model_groups: Array.from(groupedModels.values()),
    }

    try {
      const response = await runMutation.mutateAsync(request)
      if (generateOnly) {
        toast.success(`Generated ${response.total_cells} test set(s)`)
        navigate("/testsets")
      } else {
        toast.success(
          `Generated ${response.total_cells} test set(s) and started ${response.total_jobs} job(s)`,
        )
        navigate("/jobs")
      }
    } catch (error) {
      toast.error(
        `Matrix ${generateOnly ? "generation" : "execution"} failed: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      )
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <PageHeader
        title="Matrix Execution"
        description="Generate a cartesian matrix for one benchmark plugin, then optionally run every cell across selected models."
      />

      {/* Step navigation */}
      <div className="flex items-stretch divide-x overflow-hidden rounded-lg border bg-card">
        {MATRIX_STEPS.map((step, i) => (
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
              <CardTitle className="text-sm">Matrix Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Benchmark Plugin</Label>
                  <Select value={pluginType} onValueChange={handlePluginChange}>
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="Select a plugin..." />
                    </SelectTrigger>
                    <SelectContent>
                      {(plugins ?? []).map((candidate) => (
                        <SelectItem key={candidate.task_type} value={candidate.task_type}>
                          {candidate.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {plugin?.description && (
                    <p className="text-xs text-muted-foreground">{plugin.description}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Test Set Prefix</Label>
                  <Input
                    value={namePrefix}
                    onChange={(event) => setNamePrefix(event.target.value)}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Seed</Label>
                  <Input
                    type="number"
                    value={seed}
                    onChange={(event) => setSeed(Number(event.target.value))}
                    className="h-8 w-28"
                  />
                </div>
                <div className="space-y-1.5 sm:col-span-2 lg:col-span-1">
                  <Label className="text-xs">Description</Label>
                  <Input
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    className="h-8"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {pluginType && (
            <ConfigForm
              taskType={pluginType}
              values={baseConfig}
              onChange={handleBaseConfigChange}
            />
          )}

          {!pluginType && (
            <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p className="text-sm">
                Select a benchmark plugin to unlock base configuration and axis options.
              </p>
            </div>
          )}

          <StepFooter
            nextLabel="Continue to Axes"
            onNext={goToNext}
            nextDisabled={nextDisabled}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 2 — Axes
      ══════════════════════════════════════════════════════ */}
      {activeStep === "axes" && (
        <div className="space-y-4">
          {/* Prompt axes */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Prompt Axes</CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {promptCombos} combination{promptCombos !== 1 ? "s" : ""}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label className="text-xs">User Styles</Label>
                  <div className="space-y-1.5">
                    {userStylesList.map((style) => (
                      <label key={style} className="flex cursor-pointer items-center gap-2 text-xs">
                        <Checkbox
                          checked={userStyles.has(style)}
                          onCheckedChange={() => togglePromptAxis(style, setUserStyles)}
                        />
                        <span>{style}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">System Styles</Label>
                  <div className="space-y-1.5">
                    {systemStylesList.map((style) => (
                      <label key={style} className="flex cursor-pointer items-center gap-2 text-xs">
                        <Checkbox
                          checked={systemStyles.has(style)}
                          onCheckedChange={() => togglePromptAxis(style, setSystemStyles)}
                        />
                        <span>{style}</span>
                      </label>
                    ))}
                    <Separator className="my-1" />
                    <label className="flex cursor-pointer items-center gap-2 text-xs">
                      <Checkbox
                        checked={useCustomPrompt}
                        onCheckedChange={(c) => setUseCustomPrompt(!!c)}
                      />
                      <span className="font-medium">custom</span>
                    </label>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Languages</Label>
                  <div className="space-y-1.5">
                    {languagesList.map((language) => (
                      <label key={language.code} className="flex cursor-pointer items-center gap-2 text-xs">
                        <Checkbox
                          checked={languages.has(language.code)}
                          onCheckedChange={() => togglePromptAxis(language.code, setLanguages)}
                        />
                        <span>{language.flag}</span>
                        <span>{language.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Custom system prompt — only when toggle is on */}
          {useCustomPrompt && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">
                  Custom System Prompt
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    global override applied to every cell
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Tabs defaultValue="text">
                  <TabsList className="h-7">
                    <TabsTrigger value="text" className="text-xs h-6 px-2">Text</TabsTrigger>
                  </TabsList>
                  <TabsContent value="text" className="mt-2">
                    <Textarea
                      value={customSystemPrompt}
                      onChange={(event) => setCustomSystemPrompt(event.target.value)}
                      className="min-h-25 text-xs"
                      placeholder="Enter a custom system prompt…"
                    />
                  </TabsContent>
                </Tabs>
                {customSystemPrompt && (
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{customSystemPrompt.length} characters</span>
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

          {/* Plugin field variation axes */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Plugin Variation Axes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!pluginType ? (
                <p className="text-xs text-muted-foreground">
                  Select a plugin in Setup to unlock matrixable parameters.
                </p>
              ) : matrixableFields.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  This plugin does not expose any matrixable fields.
                </p>
              ) : (
                <>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {matrixableFields.map((field) => (
                      <label
                        key={field.name}
                        className="flex cursor-pointer items-center gap-2 rounded border px-3 py-2 text-xs"
                      >
                        <Checkbox
                          checked={fieldAxes[field.name] !== undefined}
                          onCheckedChange={(checked) => enableFieldAxis(field, !!checked)}
                        />
                        <span className="font-medium">{field.label}</span>
                        <span className="text-muted-foreground">{field.type}</span>
                      </label>
                    ))}
                  </div>
                  {activeFieldAxes.length > 0 && (
                    <div className="space-y-3">
                      {matrixableFields
                        .filter((field) => fieldAxes[field.name] !== undefined)
                        .map((field) => (
                          <FieldAxisEditor
                            key={field.name}
                            field={field}
                            baseValue={baseConfig[field.name]}
                            axisState={fieldAxes[field.name]!}
                            onDraftChange={(value) => updateFieldAxisDraft(field.name, value)}
                            onAddVariant={() => addFieldAxisVariant(field)}
                            onRemoveVariant={(value) => removeFieldAxisVariant(field.name, value)}
                          />
                        ))}
                    </div>
                  )}
                  {fixedOnlyFields.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Fixed-only: {fixedOnlyFields.map((field) => field.label).join(", ")}
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Warnings */}
          {(promptCombos === 0 || invalidFieldAxes.length > 0) && (
            <div className="space-y-3">
              {promptCombos === 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    No prompt combinations selected — choose at least one option from each of User Styles, System Styles, and Languages.
                  </p>
                </div>
              )}
              {invalidFieldAxes.length > 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    These field axes have no variants yet: {invalidFieldAxes.join(", ")}. Add at least one variant to each or disable the axis.
                  </p>
                </div>
              )}
            </div>
          )}

          <StepFooter
            previousLabel="Back to Setup"
            onPrevious={goToPrevious}
            nextLabel="Continue to Models"
            onNext={goToNext}
            nextDisabled={nextDisabled}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 3 — Models
      ══════════════════════════════════════════════════════ */}
      {activeStep === "models" && (
        <div className="space-y-4">
          <div className={hasFavorites ? "flex gap-6" : "space-y-6"}>
            {hasFavorites && (
              <div className="w-56 shrink-0">
                <Card className="sticky top-4">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-1.5 text-sm">
                      <Star className="h-3.5 w-3.5 fill-yellow-500 text-yellow-500" />
                      Favorites
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="max-h-[calc(100vh-260px)] space-y-3 overflow-y-auto">
                    {Object.entries(groupedFavorites).map(([provider, modelIds]) => (
                      <div key={provider}>
                        <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                          {providerLabel[provider] ?? provider}
                        </p>
                        <div className="space-y-0.5">
                          {modelIds.map((modelId) => {
                            const isSelected = [...selectedModels.values()].some(
                              (selectedModel) =>
                                selectedModel.id === modelId && selectedModel.provider === provider,
                            )
                            return (
                              <div key={modelId} className="group flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => {
                                    const existing = [...selectedModels.entries()].find(
                                      ([, selectedModel]) =>
                                        selectedModel.id === modelId && selectedModel.provider === provider,
                                    )
                                    if (existing) {
                                      setSelectedModels((previous) => {
                                        const next = new Map(previous)
                                        next.delete(existing[0])
                                        return next
                                      })
                                      return
                                    }
                                    const candidate: SelectedModel = {
                                      id: modelId,
                                      provider: provider as SelectedModel["provider"],
                                      ...(provider === "ollama" && { ollamaHost }),
                                      ...(provider === "openai_compatible" &&
                                        openaiEndpoints[0] && {
                                          apiBase: openaiEndpoints[0].apiBase,
                                          apiKey: openaiEndpoints[0].apiKey,
                                        }),
                                    }
                                    toggleModelSelection(candidate)
                                  }}
                                  className={`flex-1 truncate rounded px-1.5 py-0.5 text-left text-xs transition-colors ${
                                    isSelected
                                      ? "bg-primary/10 font-medium text-primary"
                                      : "hover:bg-accent"
                                  }`}
                                  title={`${modelId} (${provider})`}
                                >
                                  {modelId.length > 22 ? `${modelId.slice(0, 20)}…` : modelId}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleToggleFavorite(favoriteKey(provider, modelId))}
                                  className="shrink-0 p-0.5 text-muted-foreground/50 opacity-0 transition-all group-hover:opacity-100 hover:text-destructive"
                                >
                                  <X className="h-2.5 w-2.5" />
                                </button>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}

            <div className="flex-1 space-y-6">
              <div className="relative max-w-sm">
                <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  placeholder="Filter models across all providers..."
                  value={modelSearch}
                  onChange={(event) => setModelSearch(event.target.value)}
                  className="h-8 pl-8 text-xs"
                />
              </div>

              <Collapsible open={ollamaOpen} onOpenChange={setOllamaOpen}>
                <Card>
                  <CardHeader className="pb-2">
                    <CollapsibleTrigger asChild>
                      <button className="flex w-full items-center justify-between">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          Ollama
                          {selectionSummary.ollama && (
                            <Badge variant="secondary" className="text-[10px]">
                              {selectionSummary.ollama} selected
                            </Badge>
                          )}
                        </CardTitle>
                        <span className="text-xs text-muted-foreground">
                          {ollamaOpen ? "collapse" : "expand"}
                        </span>
                      </button>
                    </CollapsibleTrigger>
                  </CardHeader>
                  <CollapsibleContent>
                    <CardContent>
                      <OllamaSection
                        host={ollamaHost}
                        onHostChange={setOllamaHost}
                        selected={selectedModels}
                        onToggle={toggleModelSelection}
                        favorites={favorites}
                        onToggleFavorite={handleToggleFavorite}
                        searchTerm={modelSearch}
                      />
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>

              <Collapsible open={openaiOpen} onOpenChange={setOpenaiOpen}>
                <Card>
                  <CardHeader className="pb-2">
                    <CollapsibleTrigger asChild>
                      <button className="flex w-full items-center justify-between">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          OpenAI-Compatible
                          {selectionSummary.openai_compatible && (
                            <Badge variant="secondary" className="text-[10px]">
                              {selectionSummary.openai_compatible} selected
                            </Badge>
                          )}
                        </CardTitle>
                        <span className="text-xs text-muted-foreground">
                          {openaiOpen ? "collapse" : "expand"}
                        </span>
                      </button>
                    </CollapsibleTrigger>
                  </CardHeader>
                  <CollapsibleContent>
                    <CardContent className="space-y-3">
                      {openaiEndpoints.map((endpoint) => (
                        <OpenAIEndpointSection
                          key={endpoint.key}
                          endpoint={endpoint}
                          onChange={(updated) => updateOpenAIEndpoint(endpoint.key, updated)}
                          onRemove={() => removeOpenAIEndpoint(endpoint.key)}
                          selected={selectedModels}
                          onToggle={toggleModelSelection}
                          favorites={favorites}
                          onToggleFavorite={handleToggleFavorite}
                          searchTerm={modelSearch}
                          savedCredentials={savedCredentials}
                          canRemove={openaiEndpoints.length > 1}
                        />
                      ))}
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full text-xs"
                        onClick={addOpenAIEndpoint}
                      >
                        <Plus className="mr-1.5 h-3 w-3" /> Add Another Endpoint
                      </Button>
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>

              <Collapsible open={hfOpen} onOpenChange={setHfOpen}>
                <Card>
                  <CardHeader className="pb-2">
                    <CollapsibleTrigger asChild>
                      <button className="flex w-full items-center justify-between">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          HuggingFace
                          {selectionSummary.huggingface && (
                            <Badge variant="secondary" className="text-[10px]">
                              {selectionSummary.huggingface} selected
                            </Badge>
                          )}
                        </CardTitle>
                        <span className="text-xs text-muted-foreground">
                          {hfOpen ? "collapse" : "expand"}
                        </span>
                      </button>
                    </CollapsibleTrigger>
                  </CardHeader>
                  <CollapsibleContent>
                    <CardContent>
                      <HuggingFaceSection
                        selected={selectedModels}
                        onToggle={toggleModelSelection}
                        favorites={favorites}
                        onToggleFavorite={handleToggleFavorite}
                        searchTerm={modelSearch}
                      />
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>
            </div>
          </div>

          <StepFooter
            previousLabel="Back to Axes"
            onPrevious={goToPrevious}
            nextLabel="Continue to Settings"
            onNext={goToNext}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 4 — Settings
      ══════════════════════════════════════════════════════ */}
      {activeStep === "settings" && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Execution Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Temperature</Label>
                  <Input
                    type="number"
                    value={temperature}
                    min={0}
                    max={2}
                    step={0.05}
                    onChange={(event) => setTemperature(Number(event.target.value))}
                    className="h-8 w-28"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Max Tokens</Label>
                  <Input
                    type="number"
                    value={maxTokens}
                    min={64}
                    max={32768}
                    step={64}
                    onChange={(event) => setMaxTokens(Number(event.target.value))}
                    className="h-8 w-32"
                  />
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <Checkbox
                    id="matrix-no-think"
                    checked={noThink}
                    onCheckedChange={(checked) => setNoThink(!!checked)}
                  />
                  <Label htmlFor="matrix-no-think" className="cursor-pointer text-xs">
                    Disable thinking
                  </Label>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-sm font-medium">Current matrix shape</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {totalCells} cell{totalCells !== 1 ? "s" : ""} will be generated. If models are selected,
              each cell runs against every model — {totalJobs} projected job{totalJobs !== 1 ? "s" : ""} total.
            </p>
          </div>

          <StepFooter
            previousLabel="Back to Models"
            onPrevious={goToPrevious}
            nextLabel="Continue to Review"
            onNext={goToNext}
          />
        </div>
      )}

      {/* ══════════════════════════════════════════════════════
          STEP 5 — Review & Run
      ══════════════════════════════════════════════════════ */}
      {activeStep === "review" && (
        <div className="space-y-4">
          {/* 3-column summary */}
          <div className="grid gap-4 sm:grid-cols-3">
            {/* Plugin & cells */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                  Plugin & Cells
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <p className="text-sm font-semibold">
                    {plugin?.display_name ?? (pluginType || "No plugin selected")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Seed: <span className="font-mono">{seed}</span> • Prefix:{" "}
                    <span className="font-mono">{namePrefix || "matrix"}</span>
                  </p>
                </div>
                <Separator />
                <div className="space-y-0.5 text-[11px] text-muted-foreground">
                  <p>
                    Prompt combos:{" "}
                    <span className="font-medium text-foreground">{promptCombos}</span>
                  </p>
                  <p>
                    Field combos:{" "}
                    <span className="font-medium text-foreground">{fieldCombos}</span>
                  </p>
                  <p>
                    Total cells:{" "}
                    <span className="font-medium text-foreground">{totalCells}</span>
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Axes */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                    Axes
                  </CardTitle>
                  <Badge variant="secondary" className="text-[10px]">
                    {activeFieldAxes.length} field
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2.5">
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">User</p>
                  <div className="flex flex-wrap gap-1">
                    {Array.from(userStyles).map((s) => (
                      <Badge key={s} variant="outline" className="text-[10px]">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">System</p>
                  <div className="flex flex-wrap gap-1">
                    {Array.from(systemStyles).map((s) => (
                      <Badge key={s} variant="outline" className="text-[10px]">
                        {s}
                      </Badge>
                    ))}
                    {useCustomPrompt && (
                      <Badge variant="secondary" className="text-[10px]">
                        custom prompt
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Languages</p>
                  <p className="text-sm">
                    {Array.from(languages)
                      .map((code) => LANGUAGE_META[code]?.flag ?? code)
                      .join(" ")}
                  </p>
                </div>
                {activeFieldAxes.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-1">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Fields</p>
                      <div className="flex flex-wrap gap-1">
                        {activeFieldAxes.map(([name, axis]) => (
                          <Badge key={name} variant="outline" className="text-[10px]">
                            {name}: {axis.values.length}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Models & jobs */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs text-muted-foreground uppercase tracking-wide">
                    Models & Jobs
                  </CardTitle>
                  <Badge variant="secondary" className="text-[10px]">
                    {selectedModels.size} models
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {selectedModels.size === 0 ? (
                  <p className="text-xs italic text-muted-foreground">
                    No models selected — only <span className="font-medium">Generate Only</span> is available.
                  </p>
                ) : (
                  <div className="space-y-0.5 text-xs text-muted-foreground">
                    {Object.entries(selectionSummary).map(([provider, count]) => (
                      <p key={provider}>
                        {providerLabel[provider] ?? provider}:{" "}
                        <span className="font-medium text-foreground">{count}</span>
                      </p>
                    ))}
                  </div>
                )}
                <Separator />
                <div className="space-y-0.5 text-[11px] text-muted-foreground">
                  <p>
                    Temperature:{" "}
                    <span className="font-medium text-foreground">{temperature.toFixed(2)}</span>
                  </p>
                  <p>
                    Max tokens: <span className="font-medium text-foreground">{maxTokens}</span>
                  </p>
                  <p>
                    Projected jobs:{" "}
                    <span className="font-medium text-foreground">{totalJobs}</span>
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Warnings */}
          {(!pluginType || promptCombos === 0 || invalidFieldAxes.length > 0) && (
            <div className="space-y-3">
              {!pluginType && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    No plugin selected — go back to{" "}
                    <button
                      type="button"
                      className="font-medium underline underline-offset-2 hover:no-underline"
                      onClick={() => setActiveStep("setup")}
                    >
                      Setup
                    </button>{" "}
                    and pick a benchmark plugin.
                  </p>
                </div>
              )}
              {promptCombos === 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    No prompt combinations selected — go back to{" "}
                    <button
                      type="button"
                      className="font-medium underline underline-offset-2 hover:no-underline"
                      onClick={() => setActiveStep("axes")}
                    >
                      Axes
                    </button>{" "}
                    and pick at least one user style, system style, and language.
                  </p>
                </div>
              )}
              {invalidFieldAxes.length > 0 && (
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="text-sm">
                    Field axes without variants: {invalidFieldAxes.join(", ")}. Go back to{" "}
                    <button
                      type="button"
                      className="font-medium underline underline-offset-2 hover:no-underline"
                      onClick={() => setActiveStep("axes")}
                    >
                      Axes
                    </button>{" "}
                    to add variants or disable them.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Action area */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
            <Button variant="outline" onClick={goToPrevious}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Settings
            </Button>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => handleSubmit(true)}
                disabled={runMutation.isPending || !pluginType || !axesReady}
              >
                {runMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Generate Only
              </Button>
              <Button
                onClick={() => handleSubmit(false)}
                disabled={
                  runMutation.isPending || !pluginType || !axesReady || selectedModels.size === 0
                }
                size="lg"
              >
                {runMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                {totalJobs > 0 ? `Generate & Run ${totalJobs} Job${totalJobs !== 1 ? "s" : ""}` : "Generate and Run"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
