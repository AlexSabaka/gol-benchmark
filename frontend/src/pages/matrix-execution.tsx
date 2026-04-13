import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { Loader2, Play, Plus, Save, Search, Star, Trash2, X } from "lucide-react"

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
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/layout/page-header"
import { ConfigForm } from "@/components/plugin-config/config-form"
import { FieldRenderer } from "@/components/plugin-config/field-renderer"
import { useOllamaModels, useOpenAIModels, useHFModels } from "@/hooks/use-models"
import { useRunMatrixExecution } from "@/hooks/use-matrix"
import { usePlugins, usePluginSchema } from "@/hooks/use-plugins"
import { loadCredentials, saveCredential } from "@/lib/credential-store"
import { favoriteKey, getFavorites, toggleFavorite } from "@/lib/favorite-models"
import type { ConfigField, MatrixFieldAxis, MatrixModelGroup, MatrixRunRequest, Provider } from "@/types"

const USER_STYLES = ["minimal", "casual", "linguistic", "examples", "rules_math"]
const SYSTEM_STYLES = ["analytical", "casual", "adversarial", "none"]
const LANGUAGES: { code: string; flag: string; label: string }[] = [
  { code: "en", flag: "🇬🇧", label: "English" },
  { code: "es", flag: "🇪🇸", label: "Español" },
  { code: "fr", flag: "🇫🇷", label: "Français" },
  { code: "de", flag: "🇩🇪", label: "Deutsch" },
  { code: "zh", flag: "🇨🇳", label: "中文" },
  { code: "ua", flag: "🇺🇦", label: "Українська" },
]
const SUPPORTED_AXIS_TYPES = new Set(["number", "select", "boolean", "multi-select"])

interface SelectedModel {
  id: string
  provider: Provider
  apiBase?: string
  apiKey?: string
  ollamaHost?: string
}

interface OpenAIEndpoint {
  key: string
  apiBase: string
  apiKey: string
}

interface FieldAxisState {
  draft: unknown
  values: unknown[]
}

interface ModelListProps {
  models: { id: string; label: string }[]
  isLoading: boolean
  provider: Provider
  selected: Map<string, SelectedModel>
  onToggle: (model: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (key: string) => void
  searchTerm: string
  extraCtx?: { apiBase?: string; apiKey?: string; ollamaHost?: string }
}

function selectedModelKey(model: SelectedModel): string {
  if (model.provider === "openai_compatible") {
    return `openai_compatible:${model.apiBase ?? ""}:${model.id}`
  }
  return `${model.provider}:${model.id}`
}

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

function ModelList({
  models,
  isLoading,
  provider,
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
  extraCtx,
}: ModelListProps) {
  const filtered = useMemo(() => {
    let list = models
    const query = searchTerm.trim().toLowerCase()
    if (query) {
      list = list.filter((model) =>
        model.id.toLowerCase().includes(query) || model.label.toLowerCase().includes(query),
      )
    }
    return [...list].sort((left, right) => {
      const leftFav = favorites.has(favoriteKey(provider, left.id)) ? 0 : 1
      const rightFav = favorites.has(favoriteKey(provider, right.id)) ? 0 : 1
      if (leftFav !== rightFav) return leftFav - rightFav
      return left.label.localeCompare(right.label)
    })
  }, [favorites, models, provider, searchTerm])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-3 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Discovering models...
      </div>
    )
  }

  if (filtered.length === 0) {
    return <p className="py-2 text-xs text-muted-foreground">No models found</p>
  }

  return (
    <div className="grid max-h-55 gap-1 overflow-y-auto sm:grid-cols-2">
      {filtered.map((model) => {
        const candidate: SelectedModel = { id: model.id, provider, ...extraCtx }
        const isSelected = selected.has(selectedModelKey(candidate))
        const modelFavoriteKey = favoriteKey(provider, model.id)
        const isFavorite = favorites.has(modelFavoriteKey)
        return (
          <div key={`${provider}:${model.id}`} className="flex items-center gap-1.5 text-xs">
            <button
              onClick={() => onToggleFavorite(modelFavoriteKey)}
              className="shrink-0 p-0.5 transition-colors hover:text-yellow-500"
              type="button"
            >
              <Star className={`h-3 w-3 ${isFavorite ? "fill-yellow-500 text-yellow-500" : "text-muted-foreground/40"}`} />
            </button>
            <label className="flex min-w-0 cursor-pointer items-center gap-1.5">
              <Checkbox checked={isSelected} onCheckedChange={() => onToggle(candidate)} />
              <span className="truncate" title={model.id}>{model.label}</span>
            </label>
          </div>
        )
      })}
    </div>
  )
}

function OllamaSection({
  host,
  onHostChange,
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
}: {
  host: string
  onHostChange: (host: string) => void
  selected: Map<string, SelectedModel>
  onToggle: (model: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (key: string) => void
  searchTerm: string
}) {
  const { data, isLoading } = useOllamaModels(host, true)
  const models = useMemo(
    () => (data?.models ?? []).map((model) => ({ id: model.name, label: `${model.display_name} (${model.size_human})` })),
    [data],
  )

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <Label className="text-xs">Host</Label>
        <Input value={host} onChange={(event) => onHostChange(event.target.value)} className="h-7 max-w-sm text-xs" />
      </div>
      <ModelList
        models={models}
        isLoading={isLoading}
        provider="ollama"
        selected={selected}
        onToggle={onToggle}
        favorites={favorites}
        onToggleFavorite={onToggleFavorite}
        searchTerm={searchTerm}
        extraCtx={{ ollamaHost: host }}
      />
    </div>
  )
}

function OpenAIEndpointSection({
  endpoint,
  onChange,
  onRemove,
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
  savedCredentials,
  canRemove,
}: {
  endpoint: OpenAIEndpoint
  onChange: (endpoint: OpenAIEndpoint) => void
  onRemove: () => void
  selected: Map<string, SelectedModel>
  onToggle: (model: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (key: string) => void
  searchTerm: string
  savedCredentials: Array<{ apiBase: string; apiKey: string }>
  canRemove: boolean
}) {
  const { data, isLoading } = useOpenAIModels(endpoint.apiBase, endpoint.apiKey, !!endpoint.apiBase)
  const models = useMemo(
    () => (data?.models ?? []).map((model) => ({ id: model.name, label: model.display_name })),
    [data],
  )

  const handleSave = useCallback(async () => {
    if (!endpoint.apiBase) return
    await saveCredential(endpoint.apiBase, endpoint.apiKey)
    toast.success("Credential saved")
  }, [endpoint])

  const shortLabel = endpoint.apiBase
    ? endpoint.apiBase.replace(/^https?:\/\//, "").replace(/\/openai\/v1\/?$|\/v1\/?$/, "").slice(0, 30)
    : "New endpoint"

  return (
    <div className="space-y-2 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{shortLabel}</span>
        {canRemove && (
          <Button variant="ghost" size="icon" className="h-5 w-5" onClick={onRemove}>
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label className="text-xs">Base URL</Label>
          <Input
            value={endpoint.apiBase}
            onChange={(event) => onChange({ ...endpoint, apiBase: event.target.value })}
            placeholder="https://api.groq.com/openai/v1"
            className="h-7 text-xs"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">API Key</Label>
          <Input
            type="password"
            value={endpoint.apiKey}
            onChange={(event) => onChange({ ...endpoint, apiKey: event.target.value })}
            placeholder="sk-..."
            className="h-7 text-xs"
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={handleSave} disabled={!endpoint.apiBase}>
          <Save className="mr-1 h-3 w-3" /> Save
        </Button>
        {savedCredentials.length > 0 && (
          <Select onValueChange={(value) => {
            const credential = savedCredentials.find((candidate) => candidate.apiBase === value)
            if (credential) onChange({ ...endpoint, apiBase: credential.apiBase, apiKey: credential.apiKey })
          }}>
            <SelectTrigger className="h-6 w-40 text-xs">
              <SelectValue placeholder="Load saved..." />
            </SelectTrigger>
            <SelectContent>
              {savedCredentials.map((credential) => (
                <SelectItem key={credential.apiBase} value={credential.apiBase} className="text-xs">
                  {credential.apiBase.replace(/^https?:\/\//, "").slice(0, 28)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <ModelList
        models={models}
        isLoading={isLoading}
        provider="openai_compatible"
        selected={selected}
        onToggle={onToggle}
        favorites={favorites}
        onToggleFavorite={onToggleFavorite}
        searchTerm={searchTerm}
        extraCtx={{ apiBase: endpoint.apiBase, apiKey: endpoint.apiKey }}
      />
    </div>
  )
}

function HuggingFaceSection({
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
}: {
  selected: Map<string, SelectedModel>
  onToggle: (model: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (key: string) => void
  searchTerm: string
}) {
  const [hfQuery, setHfQuery] = useState("")
  const [hfApiKey, setHfApiKey] = useState("")
  const { data, isLoading } = useHFModels(hfQuery, hfApiKey || undefined, hfQuery.length >= 2)
  const models = useMemo(
    () => (data?.models ?? []).map((model) => ({ id: model.id, label: `${model.display_name} (${model.likes} likes)` })),
    [data],
  )

  return (
    <div className="space-y-2">
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label className="text-xs">Search Models</Label>
          <Input
            value={hfQuery}
            onChange={(event) => setHfQuery(event.target.value)}
            placeholder="e.g. qwen, gemma, llama"
            className="h-7 text-xs"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">API Key (optional)</Label>
          <Input
            type="password"
            value={hfApiKey}
            onChange={(event) => setHfApiKey(event.target.value)}
            placeholder="hf_..."
            className="h-7 text-xs"
          />
        </div>
      </div>
      {hfQuery.length < 2 ? (
        <p className="py-2 text-xs text-muted-foreground">Type at least 2 characters to search HuggingFace Hub</p>
      ) : (
        <ModelList
          models={models}
          isLoading={isLoading}
          provider="huggingface"
          selected={selected}
          onToggle={onToggle}
          favorites={favorites}
          onToggleFavorite={onToggleFavorite}
          searchTerm={searchTerm}
        />
      )}
    </div>
  )
}

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
        <Badge variant="outline" className="text-[10px]">{axisState.values.length} variant{axisState.values.length !== 1 ? "s" : ""}</Badge>
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
              <button onClick={() => onRemoveVariant(value)} aria-label={`Remove ${field.name} variant`}>
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))
        )}
      </div>
    </div>
  )
}

let endpointCounter = 1

export default function MatrixExecutionPage() {
  const navigate = useNavigate()
  const { data: plugins } = usePlugins()
  const [pluginType, setPluginType] = useState("")
  const { data: pluginSchema } = usePluginSchema(pluginType || null)
  const runMutation = useRunMatrixExecution()

  const [namePrefix, setNamePrefix] = useState("matrix")
  const [description, setDescription] = useState("")
  const [seed, setSeed] = useState(42)
  const [baseConfig, setBaseConfig] = useState<Record<string, unknown>>({})
  const [fieldAxes, setFieldAxes] = useState<Record<string, FieldAxisState>>({})

  const [userStyles, setUserStyles] = useState<Set<string>>(new Set(["minimal"]))
  const [systemStyles, setSystemStyles] = useState<Set<string>>(new Set(["analytical"]))
  const [languages, setLanguages] = useState<Set<string>>(new Set(["en"]))

  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [openaiEndpoints, setOpenaiEndpoints] = useState<OpenAIEndpoint[]>([
    { key: "ep_0", apiBase: "", apiKey: "" },
  ])
  const [selectedModels, setSelectedModels] = useState<Map<string, SelectedModel>>(new Map())
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [noThink, setNoThink] = useState(true)
  const [customSystemPrompt, setCustomSystemPrompt] = useState("")
  const [modelSearch, setModelSearch] = useState("")
  const [favorites, setFavorites] = useState<Set<string>>(() => getFavorites())
  const [savedCredentials, setSavedCredentials] = useState<Array<{ apiBase: string; apiKey: string }>>([])

  const [ollamaOpen, setOllamaOpen] = useState(true)
  const [openaiOpen, setOpenaiOpen] = useState(true)
  const [hfOpen, setHfOpen] = useState(false)

  useEffect(() => {
    loadCredentials().then(setSavedCredentials)
  }, [])

  const handlePluginChange = useCallback((nextPluginType: string) => {
    setPluginType(nextPluginType)
    setBaseConfig({})
    setFieldAxes({})
  }, [])

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

  const togglePromptAxis = useCallback((value: string, setter: React.Dispatch<React.SetStateAction<Set<string>>>) => {
    setter((previous) => {
      const next = new Set(previous)
      if (next.has(value)) next.delete(value)
      else next.add(value)
      return next
    })
  }, [])

  const handleBaseConfigChange = useCallback((taskType: string, fieldName: string, value: unknown) => {
    if (taskType !== pluginType) return
    setBaseConfig((previous) => ({ ...previous, [fieldName]: value }))
  }, [pluginType])

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
    setOpenaiEndpoints((previous) => previous.map((candidate) => candidate.key === key ? endpoint : candidate))
  }, [])

  const removeOpenAIEndpoint = useCallback((key: string) => {
    setOpenaiEndpoints((previous) => previous.filter((candidate) => candidate.key !== key))
    setSelectedModels((previous) => {
      const next = new Map(previous)
      for (const [modelKey, selectedModel] of previous.entries()) {
        if (selectedModel.provider === "openai_compatible" && selectedModel.apiBase === openaiEndpoints.find((candidate) => candidate.key === key)?.apiBase) {
          next.delete(modelKey)
        }
      }
      return next
    })
  }, [openaiEndpoints])

  const enableFieldAxis = useCallback((field: ConfigField, enabled: boolean) => {
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
  }, [baseConfig])

  const updateFieldAxisDraft = useCallback((fieldName: string, value: unknown) => {
    setFieldAxes((previous) => ({
      ...previous,
      [fieldName]: {
        draft: value,
        values: previous[fieldName]?.values ?? [],
      },
    }))
  }, [])

  const addFieldAxisVariant = useCallback((field: ConfigField) => {
    setFieldAxes((previous) => {
      const current = previous[field.name]
      if (!current) return previous
      const candidateValue = getDefaultFieldValue(field, baseConfig[field.name], current.draft)
      if (candidateValue === undefined || candidateValue === null || (Array.isArray(candidateValue) && candidateValue.length === 0)) {
        return previous
      }
      const exists = current.values.some((value) => serializeVariant(value) === serializeVariant(candidateValue))
      if (exists) return previous
      return {
        ...previous,
        [field.name]: {
          draft: candidateValue,
          values: [...current.values, candidateValue],
        },
      }
    })
  }, [baseConfig])

  const removeFieldAxisVariant = useCallback((fieldName: string, value: unknown) => {
    setFieldAxes((previous) => ({
      ...previous,
      [fieldName]: {
        draft: previous[fieldName]?.draft,
        values: (previous[fieldName]?.values ?? []).filter((candidate) => serializeVariant(candidate) !== serializeVariant(value)),
      },
    }))
  }, [])

  const activeFieldAxes = useMemo(
    () => Object.entries(fieldAxes),
    [fieldAxes],
  )
  const promptCombinationCount = Math.max(userStyles.size, 1) * Math.max(systemStyles.size, 1) * Math.max(languages.size, 1)
  const fieldCombinationCount = activeFieldAxes.length === 0 ? 1 : productOf(activeFieldAxes.map(([, axis]) => Math.max(axis.values.length, 1)))
  const totalCells = promptCombinationCount * fieldCombinationCount
  const totalJobs = totalCells * selectedModels.size

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

  const handleSubmit = async (generateOnly: boolean) => {
    if (!pluginType) {
      toast.error("Select a benchmark plugin")
      return
    }
    if (!generateOnly && selectedModels.size === 0) {
      toast.error("Select at least one model")
      return
    }
    if (userStyles.size === 0 || systemStyles.size === 0 || languages.size === 0) {
      toast.error("Select at least one user style, system style, and language")
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
      const key = model.provider === "openai_compatible"
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
      ...(customSystemPrompt.trim() && { custom_system_prompt: customSystemPrompt.trim() }),
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
        toast.success(`Generated ${response.total_cells} test set(s) and started ${response.total_jobs} job(s)`)
        navigate("/jobs")
      }
    } catch (error) {
      toast.error(`Matrix ${generateOnly ? "generation" : "execution"} failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Matrix Execution"
        description="Generate a cartesian matrix for one benchmark plugin, then optionally run every cell across selected models."
      />

      <Card className="border-dashed bg-muted/20">
        <CardContent className="flex flex-wrap items-start justify-between gap-3 pt-4">
          <div className="space-y-1">
            <p className="text-sm font-medium">Use Configure for one test set. Use Matrix Execution when you need the cartesian product of prompt axes, plugin field variants, and selected models.</p>
            <p className="text-xs text-muted-foreground">Each matrix cell becomes a normal test set, and Generate and Run continues into execution jobs for every selected model.</p>
          </div>
          <Badge variant="outline" className="shrink-0">Cartesian batch builder</Badge>
        </CardContent>
      </Card>

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
              {plugin?.description && <p className="text-xs text-muted-foreground">{plugin.description}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Test Set Prefix</Label>
              <Input value={namePrefix} onChange={(event) => setNamePrefix(event.target.value)} className="h-8" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Seed</Label>
              <Input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} className="h-8 w-28" />
            </div>
            <div className="space-y-1.5 sm:col-span-2 lg:col-span-1">
              <Label className="text-xs">Description</Label>
              <Input value={description} onChange={(event) => setDescription(event.target.value)} className="h-8" placeholder="Optional" />
            </div>
          </div>
        </CardContent>
      </Card>

      {pluginType && (
        <ConfigForm
          taskType={pluginType}
          description={plugin?.description}
          values={baseConfig}
          onChange={handleBaseConfigChange}
        />
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">
            Prompt Axes
            <span className="ml-2 text-xs font-normal text-muted-foreground">{promptCombinationCount} combination{promptCombinationCount !== 1 ? "s" : ""}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label className="text-xs">User Styles</Label>
            <div className="space-y-1">
              {USER_STYLES.map((style) => (
                <label key={style} className="flex cursor-pointer items-center gap-2 text-xs">
                  <Checkbox checked={userStyles.has(style)} onCheckedChange={() => togglePromptAxis(style, setUserStyles)} />
                  <span>{style}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">System Styles</Label>
            <div className="space-y-1">
              {SYSTEM_STYLES.map((style) => (
                <label key={style} className="flex cursor-pointer items-center gap-2 text-xs">
                  <Checkbox checked={systemStyles.has(style)} onCheckedChange={() => togglePromptAxis(style, setSystemStyles)} />
                  <span>{style}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Languages</Label>
            <div className="space-y-1">
              {LANGUAGES.map((language) => (
                <label key={language.code} className="flex cursor-pointer items-center gap-2 text-xs">
                  <Checkbox checked={languages.has(language.code)} onCheckedChange={() => togglePromptAxis(language.code, setLanguages)} />
                  <span>{language.flag}</span>
                  <span>{language.label}</span>
                </label>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Plugin Variation Axes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!pluginType ? (
            <p className="text-xs text-muted-foreground">Select a plugin to unlock matrixable task parameters.</p>
          ) : matrixableFields.length === 0 ? (
            <p className="text-xs text-muted-foreground">This plugin does not expose any matrixable fields in V1.</p>
          ) : (
            <>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {matrixableFields.map((field) => (
                  <label key={field.name} className="flex cursor-pointer items-center gap-2 rounded border px-3 py-2 text-xs">
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
                  Fixed-only in V1: {fixedOnlyFields.map((field) => field.label).join(", ")}
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Custom System Prompt</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">Optional global override applied to every generated cell.</p>
          <Textarea
            value={customSystemPrompt}
            onChange={(event) => setCustomSystemPrompt(event.target.value)}
            className="min-h-25 text-xs"
            placeholder="Leave blank to use style-based system prompts"
          />
        </CardContent>
      </Card>

      <div className="flex gap-6">
        {hasFavorites && (
          <div className="w-56 shrink-0">
            <Card className="sticky top-4">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-1.5 text-sm">
                  <Star className="h-3.5 w-3.5 fill-yellow-500 text-yellow-500" />
                  Favorites
                </CardTitle>
              </CardHeader>
              <CardContent className="max-h-[calc(100vh-200px)] space-y-3 overflow-y-auto">
                {Object.entries(groupedFavorites).map(([provider, modelIds]) => (
                  <div key={provider}>
                    <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      {providerLabel[provider] ?? provider}
                    </p>
                    <div className="space-y-0.5">
                      {modelIds.map((modelId) => {
                        const isSelected = [...selectedModels.values()].some(
                          (selectedModel) => selectedModel.id === modelId && selectedModel.provider === provider,
                        )
                        return (
                          <div key={modelId} className="group flex items-center gap-1">
                            <button
                              onClick={() => {
                                const existing = [...selectedModels.entries()].find(
                                  ([, selectedModel]) => selectedModel.id === modelId && selectedModel.provider === provider,
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
                                  ...(provider === "openai_compatible" && openaiEndpoints[0] && {
                                    apiBase: openaiEndpoints[0].apiBase,
                                    apiKey: openaiEndpoints[0].apiKey,
                                  }),
                                }
                                toggleModelSelection(candidate)
                              }}
                              className={`flex-1 truncate rounded px-1.5 py-0.5 text-left text-xs transition-colors ${
                                isSelected ? "bg-primary/10 font-medium text-primary" : "hover:bg-accent"
                              }`}
                              title={`${modelId} (${provider})`}
                              type="button"
                            >
                              {modelId.length > 22 ? `${modelId.slice(0, 20)}…` : modelId}
                            </button>
                            <button
                              onClick={() => handleToggleFavorite(favoriteKey(provider, modelId))}
                              className="shrink-0 p-0.5 text-muted-foreground/50 opacity-0 transition-all group-hover:opacity-100 hover:text-destructive"
                              type="button"
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
                    <CardTitle className="text-sm">Ollama</CardTitle>
                    <span className="text-xs text-muted-foreground">{ollamaOpen ? "collapse" : "expand"}</span>
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
                    <CardTitle className="text-sm">OpenAI-Compatible</CardTitle>
                    <span className="text-xs text-muted-foreground">{openaiOpen ? "collapse" : "expand"}</span>
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
                  <Button variant="outline" size="sm" className="w-full text-xs" onClick={addOpenAIEndpoint}>
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
                    <CardTitle className="text-sm">HuggingFace</CardTitle>
                    <span className="text-xs text-muted-foreground">{hfOpen ? "collapse" : "expand"}</span>
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

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Execution Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Temperature</Label>
              <Input type="number" value={temperature} min={0} max={2} step={0.05} onChange={(event) => setTemperature(Number(event.target.value))} className="h-8 w-28" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Max Tokens</Label>
              <Input type="number" value={maxTokens} min={64} max={32768} step={64} onChange={(event) => setMaxTokens(Number(event.target.value))} className="h-8 w-28" />
            </div>
            <div className="flex items-center gap-2 pt-5">
              <Checkbox id="matrix-no-think" checked={noThink} onCheckedChange={(checked) => setNoThink(!!checked)} />
              <Label htmlFor="matrix-no-think" className="cursor-pointer text-xs">Disable thinking</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Matrix Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant="secondary">Prompt combos: {promptCombinationCount}</Badge>
            <Badge variant="secondary">Field combos: {fieldCombinationCount}</Badge>
            <Badge variant="secondary">Matrix cells: {totalCells}</Badge>
            <Badge variant="secondary">Selected models: {selectedModels.size}</Badge>
            <Badge variant="secondary">Projected jobs: {totalJobs}</Badge>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {Object.entries(selectionSummary).map(([provider, count]) => (
              <span key={provider}>{provider}: {count}</span>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Generate Only writes one test set per matrix cell. Generate and Run continues into execution jobs for the selected models.
          </p>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Each matrix cell generates one normal test set. Execution is optional and uses the same generated artifacts.
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => handleSubmit(true)} disabled={runMutation.isPending || !pluginType}>
            {runMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
            Generate Only
          </Button>
          <Button onClick={() => handleSubmit(false)} disabled={runMutation.isPending || !pluginType || selectedModels.size === 0}>
            {runMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Generate and Run
          </Button>
        </div>
      </div>
    </div>
  )
}