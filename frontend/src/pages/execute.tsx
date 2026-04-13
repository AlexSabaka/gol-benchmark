import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { toast } from "sonner"
import { ArrowLeft, ArrowRight, Check, Loader2, Play, Plus, Save, Search, Star, Trash2, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { DataTable, type ColumnDef } from "@/components/data-table/data-table"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/layout/page-header"
import { TaskBadge } from "@/components/task-badge"
import { useTestsets } from "@/hooks/use-testsets"
import { useOllamaModels, useOpenAIModels, useHFModels } from "@/hooks/use-models"
import { useRunBenchmark } from "@/hooks/use-jobs"
import { saveCredential, loadCredentials } from "@/lib/credential-store"
import { favoriteKey, getFavorites, toggleFavorite } from "@/lib/favorite-models"
import { langFlags } from "@/lib/language-flags"
import { makeStorageKey, useLocalStorageSetState, useLocalStorageState } from "@/lib/local-storage"
import { formatBytes, formatDate, stripArchiveExtension, suffixDisplay } from "@/lib/utils"
import type { RunRequest, TestsetSummary } from "@/types"

// ── Types ──

/** A selected model carries its provider context so we can group at run-time. */
interface SelectedModel {
  id: string
  provider: "ollama" | "openai_compatible" | "huggingface"
  /** Only for openai_compatible */
  apiBase?: string
  apiKey?: string
  /** Only for ollama */
  ollamaHost?: string
}

interface OpenAIEndpoint {
  key: string // unique UI key
  apiBase: string
  apiKey: string
}

type ExecuteStepId = "testsets" | "models" | "settings" | "review"

const EXECUTE_STEPS: Array<{
  id: ExecuteStepId
  label: string
  description: string
}> = [
  { id: "testsets", label: "Test Sets", description: "Choose benchmark inputs" },
  { id: "models", label: "Models", description: "Pick providers and models" },
  { id: "settings", label: "Settings", description: "Tune run overrides" },
  { id: "review", label: "Review", description: "Check summary before launch" },
]

const EXECUTE_STEP_IDS = new Set<ExecuteStepId>(EXECUTE_STEPS.map((step) => step.id))

function selectedModelKey(m: SelectedModel): string {
  if (m.provider === "openai_compatible") return `openai_compatible:${m.apiBase}:${m.id}`
  return `${m.provider}:${m.id}`
}

function CompactTaskBadges({ tasks }: { tasks: string[] }) {
  const visible = tasks.slice(0, 2)
  const remaining = Math.max(tasks.length - visible.length, 0)

  return (
    <div className="flex max-w-52 items-center gap-1 overflow-hidden whitespace-nowrap">
      {visible.map((task) => (
        <div key={task} className="shrink-0">
          <TaskBadge task={task} />
        </div>
      ))}
      {remaining > 0 && (
        <Badge variant="outline" className="shrink-0 text-[10px]">
          +{remaining}
        </Badge>
      )}
    </div>
  )
}

function CompactLanguageList({ languages }: { languages: string[] }) {
  if (languages.length === 0) {
    return <span className="text-xs text-muted-foreground">-</span>
  }

  const visible = languages.slice(0, 3)
  const remaining = Math.max(languages.length - visible.length, 0)

  return (
    <div className="inline-flex items-center gap-1 whitespace-nowrap" title={languages.join(", ")}>
      <span>{langFlags(visible)}</span>
      {remaining > 0 && (
        <Badge variant="outline" className="text-[10px]">
          +{remaining}
        </Badge>
      )}
    </div>
  )
}

function StepButton({
  step,
  index,
  active,
  complete,
  summary,
  onClick,
}: {
  step: { id: ExecuteStepId; label: string; description: string }
  index: number
  active: boolean
  complete: boolean
  summary: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border px-4 py-3 text-left transition-colors ${
        active
          ? "border-primary bg-primary/5 shadow-sm"
          : complete
            ? "border-border bg-card hover:border-primary/50 hover:bg-accent/30"
            : "border-border bg-card hover:bg-accent/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
            active
              ? "bg-primary text-primary-foreground"
              : complete
                ? "bg-emerald-600 text-white"
                : "bg-muted text-muted-foreground"
          }`}
        >
          {complete && !active ? <Check className="h-3.5 w-3.5" /> : index + 1}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium">{step.label}</p>
          <p className="text-xs text-muted-foreground">{step.description}</p>
          <p className="mt-2 truncate text-xs text-muted-foreground">{summary}</p>
        </div>
      </div>
    </button>
  )
}

function StepFooter({
  previousLabel,
  nextLabel,
  onPrevious,
  onNext,
  nextDisabled,
}: {
  previousLabel?: string
  nextLabel?: string
  onPrevious?: () => void
  onNext?: () => void
  nextDisabled?: boolean
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
      <div>
        {onPrevious ? (
          <Button variant="outline" onClick={onPrevious}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {previousLabel ?? "Back"}
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">You can jump between steps at any time.</span>
        )}
      </div>
      {onNext ? (
        <Button onClick={onNext} disabled={nextDisabled}>
          {nextLabel ?? "Continue"}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      ) : null}
    </div>
  )
}

// ── Sub-components for per-provider model discovery ──

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
}: {
  models: { id: string; label: string }[]
  isLoading: boolean
  provider: "ollama" | "openai_compatible" | "huggingface"
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
  extraCtx?: { apiBase?: string; apiKey?: string; ollamaHost?: string }
}) {
  const filtered = useMemo(() => {
    let list = models
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      list = list.filter((m) => m.id.toLowerCase().includes(q) || m.label.toLowerCase().includes(q))
    }
    return [...list].sort((a, b) => {
      const aFav = favorites.has(favoriteKey(provider, a.id)) ? 0 : 1
      const bFav = favorites.has(favoriteKey(provider, b.id)) ? 0 : 1
      if (aFav !== bFav) return aFav - bFav
      return a.label.localeCompare(b.label)
    })
  }, [models, searchTerm, favorites, provider])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-3 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Discovering models...
      </div>
    )
  }

  if (filtered.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        {searchTerm ? "No models match your search" : "No models found"}
      </p>
    )
  }

  return (
    <div className="grid max-h-55 gap-1 overflow-y-auto sm:grid-cols-2">
      {filtered.map((m) => {
        const sm: SelectedModel = { id: m.id, provider, ...extraCtx }
        const key = selectedModelKey(sm)
        const isSelected = selected.has(key)
        const fKey = favoriteKey(provider, m.id)
        const isFav = favorites.has(fKey)
        return (
          <div key={m.id} className="flex items-center gap-1.5 text-xs">
            <button
              onClick={() => onToggleFavorite(fKey)}
              className="shrink-0 p-0.5 hover:text-yellow-500 transition-colors"
            >
              <Star className={`h-3 w-3 ${isFav ? "fill-yellow-500 text-yellow-500" : "text-muted-foreground/40"}`} />
            </button>
            <label className="flex items-center gap-1.5 cursor-pointer min-w-0">
              <Checkbox checked={isSelected} onCheckedChange={() => onToggle(sm)} />
              <span className="truncate" title={m.id}>{m.label}</span>
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
  onHostChange: (h: string) => void
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
}) {
  const { data, isLoading } = useOllamaModels(host, true)
  const models = useMemo(
    () => (data?.models ?? []).map((m) => ({ id: m.name, label: `${m.display_name} (${m.size_human})` })),
    [data]
  )

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <Label className="text-xs">Host</Label>
        <Input value={host} onChange={(e) => onHostChange(e.target.value)} className="h-7 text-xs max-w-sm" />
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
  onChange: (ep: OpenAIEndpoint) => void
  onRemove: () => void
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
  savedCredentials: Array<{ apiBase: string; apiKey: string }>
  canRemove: boolean
}) {
  const { data, isLoading } = useOpenAIModels(endpoint.apiBase, endpoint.apiKey, !!endpoint.apiBase)
  const models = useMemo(
    () => (data?.models ?? []).map((m) => ({ id: m.name, label: m.display_name })),
    [data]
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
            onChange={(e) => onChange({ ...endpoint, apiBase: e.target.value })}
            placeholder="https://api.groq.com/openai/v1"
            className="h-7 text-xs"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">API Key</Label>
          <Input
            type="password"
            value={endpoint.apiKey}
            onChange={(e) => onChange({ ...endpoint, apiKey: e.target.value })}
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
          <Select onValueChange={(v) => {
            const cred = savedCredentials.find((c) => c.apiBase === v)
            if (cred) onChange({ ...endpoint, apiBase: cred.apiBase, apiKey: cred.apiKey })
          }}>
            <SelectTrigger className="h-6 w-40 text-xs">
              <SelectValue placeholder="Load saved..." />
            </SelectTrigger>
            <SelectContent>
              {savedCredentials.map((c) => (
                <SelectItem key={c.apiBase} value={c.apiBase} className="text-xs">
                  {c.apiBase.replace(/^https?:\/\//, "").slice(0, 28)}
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
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
}) {
  const [hfQuery, setHfQuery] = useState("")
  const [hfApiKey, setHfApiKey] = useState("")
  const { data, isLoading } = useHFModels(hfQuery, hfApiKey || undefined, hfQuery.length >= 2)
  const models = useMemo(
    () => (data?.models ?? []).map((m) => ({ id: m.id, label: `${m.display_name} (${m.likes} likes, ${m.pipeline_tag || "unknown"})` })),
    [data]
  )

  return (
    <div className="space-y-2">
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label className="text-xs">Search Models</Label>
          <Input
            value={hfQuery}
            onChange={(e) => setHfQuery(e.target.value)}
            placeholder="e.g. microsoft/phi-2, meta-llama..."
            className="h-7 text-xs"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">API Key (optional)</Label>
          <Input
            type="password"
            value={hfApiKey}
            onChange={(e) => setHfApiKey(e.target.value)}
            placeholder="hf_..."
            className="h-7 text-xs"
          />
        </div>
      </div>
      {hfQuery.length < 2 ? (
        <p className="text-xs text-muted-foreground py-2">Type at least 2 characters to search HuggingFace Hub</p>
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

// ── Main page ──

let _endpointCounter = 1

export default function ExecutePage() {
  const storageScope = "execute-page"
  const nav = useNavigate()
  const [params] = useSearchParams()
  const { data: testsets, isLoading: testsetsLoading } = useTestsets()
  const runMutation = useRunBenchmark()
  const requestedTestset = params.get("testset")

  // Form state
  const [selectedTestsets, setSelectedTestsets] = useLocalStorageSetState<string>(
    makeStorageKey(storageScope, "selected-testsets"),
    requestedTestset ? [requestedTestset] : [],
  )
  const [activeStep, setActiveStep] = useLocalStorageState<ExecuteStepId>(
    makeStorageKey(storageScope, "active-step"),
    "testsets",
    {
      sanitize: (value) => (
        typeof value === "string" && EXECUTE_STEP_IDS.has(value as ExecuteStepId)
          ? value as ExecuteStepId
          : "testsets"
      ),
    },
  )
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [openaiEndpoints, setOpenaiEndpoints] = useState<OpenAIEndpoint[]>([
    { key: "ep_0", apiBase: "", apiKey: "" },
  ])
  const [selected, setSelected] = useState<Map<string, SelectedModel>>(new Map())
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [noThink, setNoThink] = useState(true)
  const [modelSearch, setModelSearch] = useState("")
  const [favorites, setFavorites] = useState<Set<string>>(() => getFavorites())
  const [savedCredentials, setSavedCredentials] = useState<Array<{ apiBase: string; apiKey: string }>>([])

  // Section open/closed
  const [ollamaOpen, setOllamaOpen] = useState(true)
  const [openaiOpen, setOpenaiOpen] = useState(true)
  const [hfOpen, setHfOpen] = useState(false)

  useEffect(() => {
    loadCredentials().then(setSavedCredentials)
  }, [])

  useEffect(() => {
    if (!requestedTestset) return
    setSelectedTestsets(new Set([requestedTestset]))
    setActiveStep("testsets")
  }, [requestedTestset, setActiveStep, setSelectedTestsets])

  useEffect(() => {
    if (!testsets?.length) return

    const valid = new Set(testsets.map((summary) => summary.filename))
    setSelectedTestsets((previous) => {
      const next = new Set([...previous].filter((filename) => valid.has(filename)))
      if (next.size === previous.size && [...next].every((filename) => previous.has(filename))) {
        return previous
      }
      return next
    })
  }, [setSelectedTestsets, testsets])

  const sortedTestsets = useMemo(
    () => [...(testsets ?? [])].sort((left, right) => new Date(right.created).getTime() - new Date(left.created).getTime()),
    [testsets],
  )

  const testsetLookup = useMemo(
    () => new Map(sortedTestsets.map((summary) => [summary.filename, summary])),
    [sortedTestsets],
  )

  const selectedTestsetSummaries = useMemo(
    () => Array.from(selectedTestsets)
      .map((filename) => testsetLookup.get(filename))
      .filter((summary): summary is TestsetSummary => summary !== undefined),
    [selectedTestsets, testsetLookup],
  )

  const toggleModelSelection = useCallback((m: SelectedModel) => {
    setSelected((prev) => {
      const next = new Map(prev)
      const key = selectedModelKey(m)
      if (next.has(key)) next.delete(key)
      else next.set(key, m)
      return next
    })
  }, [])

  const handleToggleFavorite = useCallback((fKey: string) => {
    const next = toggleFavorite(fKey)
    setFavorites(new Set(next))
  }, [])

  const addOpenaiEndpoint = useCallback(() => {
    _endpointCounter++
    setOpenaiEndpoints((prev) => [...prev, { key: `ep_${_endpointCounter}`, apiBase: "", apiKey: "" }])
  }, [])

  const updateOpenaiEndpoint = useCallback((key: string, ep: OpenAIEndpoint) => {
    setOpenaiEndpoints((prev) => prev.map((e) => (e.key === key ? ep : e)))
  }, [])

  const removeOpenaiEndpoint = useCallback((key: string) => {
    setOpenaiEndpoints((prev) => prev.filter((e) => e.key !== key))
  }, [])

  // Group favorites by provider for the sidebar
  const groupedFavorites = useMemo(() => {
    const groups: Record<string, string[]> = {}
    for (const key of favorites) {
      const sepIdx = key.indexOf(":")
      if (sepIdx === -1) continue
      const prov = key.slice(0, sepIdx)
      const modelId = key.slice(sepIdx + 1)
      ;(groups[prov] ??= []).push(modelId)
    }
    for (const arr of Object.values(groups)) arr.sort()
    return groups
  }, [favorites])

  const hasFavorites = favorites.size > 0
  const selectedCount = selected.size
  const selectedTestsetCount = selectedTestsets.size

  const providerLabel: Record<string, string> = {
    ollama: "Ollama",
    openai_compatible: "OpenAI / Groq / OpenRouter",
    huggingface: "HuggingFace",
  }

  const selectedModelGroups = useMemo(() => {
    const groups = new Map<string, {
      provider: SelectedModel["provider"]
      modelIds: string[]
      apiBase?: string
      apiKey?: string
      ollamaHost?: string
    }>()

    for (const model of selected.values()) {
      const groupKey = model.provider === "openai_compatible"
        ? `openai_compatible:${model.apiBase ?? ""}`
        : model.provider

      const existing = groups.get(groupKey) ?? {
        provider: model.provider,
        modelIds: [],
        apiBase: model.apiBase,
        apiKey: model.apiKey,
        ollamaHost: model.ollamaHost,
      }

      existing.modelIds.push(model.id)
      groups.set(groupKey, existing)
    }

    return Array.from(groups.values()).map((group) => ({
      ...group,
      modelIds: [...group.modelIds].sort(),
    }))
  }, [selected])

  const selectionSummary = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const m of selected.values()) {
      counts[m.provider] = (counts[m.provider] ?? 0) + 1
    }
    return counts
  }, [selected])

  const projectedJobCount = selectedTestsetCount * selectedCount
  const runDisabled = runMutation.isPending || selectedTestsetCount === 0 || selectedCount === 0
  const runButtonLabel = projectedJobCount > 0
    ? `Run ${projectedJobCount} Job${projectedJobCount !== 1 ? "s" : ""}`
    : selectedTestsetCount === 0 && selectedCount === 0
      ? "Select test sets and models"
      : selectedTestsetCount === 0
        ? "Select test sets"
        : "Select models"

  const currentStepIndex = Math.max(EXECUTE_STEPS.findIndex((step) => step.id === activeStep), 0)
  const previousStep = currentStepIndex > 0 ? EXECUTE_STEPS[currentStepIndex - 1] : null
  const nextStep = currentStepIndex < EXECUTE_STEPS.length - 1 ? EXECUTE_STEPS[currentStepIndex + 1] : null

  const stepSummaries: Record<ExecuteStepId, string> = {
    testsets: selectedTestsetCount > 0 ? `${selectedTestsetCount} selected` : "Choose one or more test sets",
    models: selectedCount > 0 ? `${selectedCount} selected` : "Pick models across providers",
    settings: `Temp ${temperature.toFixed(2)} • ${noThink ? "no think" : "thinking"}`,
    review: projectedJobCount > 0 ? `${projectedJobCount} projected jobs` : "Summary appears here before the run",
  }

  const stepComplete: Record<ExecuteStepId, boolean> = {
    testsets: selectedTestsetCount > 0,
    models: selectedCount > 0,
    settings: true,
    review: !runDisabled,
  }

  const nextStepDisabled = activeStep === "testsets"
    ? selectedTestsetCount === 0
    : activeStep === "models"
      ? selectedCount === 0
      : false

  const goToNextStep = useCallback(() => {
    if (nextStep) setActiveStep(nextStep.id)
  }, [nextStep, setActiveStep])

  const goToPreviousStep = useCallback(() => {
    if (previousStep) setActiveStep(previousStep.id)
  }, [previousStep, setActiveStep])

  const testsetColumns = useMemo<ColumnDef<TestsetSummary>[]>(() => [
    {
      id: "pick",
      header: "Pick",
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => (
        <Checkbox
          checked={selectedTestsets.has(row.original.filename)}
          onCheckedChange={() => {
            setSelectedTestsets((previous) => {
              const next = new Set(previous)
              if (next.has(row.original.filename)) next.delete(row.original.filename)
              else next.add(row.original.filename)
              return next
            })
          }}
          aria-label={`Select ${row.original.filename}`}
        />
      ),
    },
    {
      id: "testset",
      accessorFn: (row) => [
        row.filename,
        row.matrix_label ?? "",
        row.matrix_plugin ?? "",
        row.task_types.join(" "),
        row.languages.join(" "),
      ].join(" "),
      header: "Test Set",
      enableHiding: false,
      cell: ({ row }) => {
        const title = stripArchiveExtension(row.original.filename)
        const tooltipParts = [title, row.original.matrix_label].filter(Boolean)

        return (
          <div className="min-w-0" title={tooltipParts.join(" • ")}>
            <span className="block max-w-[44ch] truncate font-medium">
              {suffixDisplay(title, 50)}
            </span>
          </div>
        )
      },
    },
    {
      id: "tasks",
      accessorFn: (row) => row.task_types.join(" "),
      header: "Tasks",
      enableSorting: false,
      cell: ({ row }) => <CompactTaskBadges tasks={row.original.task_types} />,
    },
    {
      id: "languages",
      accessorFn: (row) => row.languages.join(" "),
      header: "Lang",
      enableSorting: false,
      cell: ({ row }) => <CompactLanguageList languages={row.original.languages} />,
    },
    {
      accessorKey: "test_count",
      header: "Tests",
      cell: ({ row }) => <span className="text-xs tabular-nums text-muted-foreground">{row.original.test_count}</span>,
    },
    {
      accessorKey: "size_bytes",
      header: "Size",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatBytes(row.original.size_bytes)}</span>,
    },
    {
      accessorKey: "created",
      header: "Created",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDate(row.original.created)}</span>,
    },
  ], [selectedTestsets, setSelectedTestsets])

  const handleRun = async () => {
    if (selectedTestsetCount === 0) { toast.error("Select at least one test set"); return }
    if (selectedCount === 0) { toast.error("Select at least one model"); return }

    const testsetFilenames = Array.from(selectedTestsets).sort()
    const sharedRunGroupId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().slice(0, 8)
      : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.slice(0, 8)

    let totalJobs = 0
    for (const group of selectedModelGroups) {
      const req: RunRequest = {
        testset_filenames: testsetFilenames,
        models: group.modelIds,
        provider: group.provider,
        run_group_id: sharedRunGroupId,
        temperature,
        max_tokens: maxTokens,
        no_think: noThink,
        ...(group.ollamaHost && group.ollamaHost !== "http://localhost:11434" && { ollama_host: group.ollamaHost }),
        ...(group.apiBase && { api_base: group.apiBase, api_key: group.apiKey ?? "" }),
      }
      try {
        const res = await runMutation.mutateAsync(req)
        totalJobs += res.jobs.length
      } catch (err) {
        toast.error(`Run failed (${group.provider}): ${err instanceof Error ? err.message : "Unknown"}`)
      }
    }
    if (totalJobs > 0) {
      toast.success(`Started ${totalJobs} job(s) across ${testsetFilenames.length} testset(s)`)
      nav("/jobs")
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Execute"
        description="Step through test set selection, model selection, overrides, and a final review before launching jobs."
        actions={activeStep === "review" ? (
          <Button onClick={handleRun} disabled={runDisabled}>
            {runMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            {runButtonLabel}
          </Button>
        ) : undefined}
      />

      <div className="grid gap-3 xl:grid-cols-4">
        {EXECUTE_STEPS.map((step, index) => (
          <StepButton
            key={step.id}
            step={step}
            index={index}
            active={activeStep === step.id}
            complete={stepComplete[step.id]}
            summary={stepSummaries[step.id]}
            onClick={() => setActiveStep(step.id)}
          />
        ))}
      </div>

      {activeStep === "testsets" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Step 1. Select Test Sets</CardTitle>
            <CardDescription>
              Choose one or more generated test sets. The table state follows the shared app pattern, including persisted sorting, filters, columns, and pagination.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <DataTable
              columns={testsetColumns}
              data={sortedTestsets}
              searchKey="testset"
              searchPlaceholder="Filter test sets..."
              loading={testsetsLoading}
              persistKey="execute-testset-table"
              getRowId={(row) => row.filename}
              initialPageSize={10}
              toolbar={(table) => {
                const pageFilenames = table.getRowModel().rows.map((row) => row.original.filename)
                const allPageSelected = pageFilenames.length > 0 && pageFilenames.every((filename) => selectedTestsets.has(filename))

                return (
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{selectedTestsetCount} selected</Badge>
                    <Badge variant="outline">{table.getFilteredRowModel().rows.length} visible</Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedTestsets((previous) => {
                          const next = new Set(previous)
                          for (const filename of pageFilenames) next.add(filename)
                          return next
                        })
                      }}
                      disabled={pageFilenames.length === 0 || allPageSelected}
                    >
                      Select Page
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedTestsets(new Set())}
                      disabled={selectedTestsetCount === 0}
                    >
                      Clear Selection
                    </Button>
                  </div>
                )
              }}
            />

            <StepFooter
              nextLabel={nextStep ? `Continue to ${nextStep.label}` : undefined}
              onNext={nextStep ? goToNextStep : undefined}
              nextDisabled={nextStepDisabled}
            />
          </CardContent>
        </Card>
      )}

      {activeStep === "models" && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Step 2. Select Models</CardTitle>
                <CardDescription>
                  Pick models across providers. Favorites stay pinned for quick reuse, and saved API credentials remain available inside each OpenAI-compatible endpoint block.
                </CardDescription>
              </div>
              <Badge variant="secondary">{selectedCount} selected</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
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
                      {Object.entries(groupedFavorites).map(([prov, modelIds]) => (
                        <div key={prov}>
                          <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                            {providerLabel[prov] ?? prov}
                          </p>
                          <div className="space-y-0.5">
                            {modelIds.map((modelId) => {
                              const isSelected = [...selected.values()].some((entry) => entry.id === modelId && entry.provider === prov)

                              return (
                                <div key={modelId} className="group flex items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const existing = [...selected.entries()].find(([, entry]) => entry.id === modelId && entry.provider === prov)

                                      if (existing) {
                                        setSelected((previous) => {
                                          const next = new Map(previous)
                                          next.delete(existing[0])
                                          return next
                                        })
                                        return
                                      }

                                      const candidate: SelectedModel = {
                                        id: modelId,
                                        provider: prov as SelectedModel["provider"],
                                        ...(prov === "ollama" && { ollamaHost }),
                                        ...(prov === "openai_compatible" && openaiEndpoints[0] && {
                                          apiBase: openaiEndpoints[0].apiBase,
                                          apiKey: openaiEndpoints[0].apiKey,
                                        }),
                                      }
                                      toggleModelSelection(candidate)
                                    }}
                                    className={`flex-1 truncate rounded px-1.5 py-0.5 text-left text-xs transition-colors ${
                                      isSelected ? "bg-primary/10 font-medium text-primary" : "hover:bg-accent"
                                    }`}
                                    title={`${modelId} (${prov})`}
                                  >
                                    {modelId.length > 22 ? `${modelId.slice(0, 20)}…` : modelId}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleToggleFavorite(favoriteKey(prov, modelId))}
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
                    onChange={(e) => setModelSearch(e.target.value)}
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
                            {selectionSummary.ollama && <Badge variant="secondary" className="text-[10px]">{selectionSummary.ollama} selected</Badge>}
                          </CardTitle>
                          <span className="text-xs text-muted-foreground">{ollamaOpen ? "collapse" : "expand"}</span>
                        </button>
                      </CollapsibleTrigger>
                    </CardHeader>
                    <CollapsibleContent>
                      <CardContent>
                        <OllamaSection
                          host={ollamaHost}
                          onHostChange={setOllamaHost}
                          selected={selected}
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
                            {selectionSummary.openai_compatible && <Badge variant="secondary" className="text-[10px]">{selectionSummary.openai_compatible} selected</Badge>}
                          </CardTitle>
                          <span className="text-xs text-muted-foreground">{openaiOpen ? "collapse" : "expand"}</span>
                        </button>
                      </CollapsibleTrigger>
                    </CardHeader>
                    <CollapsibleContent>
                      <CardContent className="space-y-3">
                        {openaiEndpoints.map((ep) => (
                          <OpenAIEndpointSection
                            key={ep.key}
                            endpoint={ep}
                            onChange={(updated) => updateOpenaiEndpoint(ep.key, updated)}
                            onRemove={() => removeOpenaiEndpoint(ep.key)}
                            selected={selected}
                            onToggle={toggleModelSelection}
                            favorites={favorites}
                            onToggleFavorite={handleToggleFavorite}
                            searchTerm={modelSearch}
                            savedCredentials={savedCredentials}
                            canRemove={openaiEndpoints.length > 1}
                          />
                        ))}
                        <Button variant="outline" size="sm" className="w-full text-xs" onClick={addOpenaiEndpoint}>
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
                            {selectionSummary.huggingface && <Badge variant="secondary" className="text-[10px]">{selectionSummary.huggingface} selected</Badge>}
                          </CardTitle>
                          <span className="text-xs text-muted-foreground">{hfOpen ? "collapse" : "expand"}</span>
                        </button>
                      </CollapsibleTrigger>
                    </CardHeader>
                    <CollapsibleContent>
                      <CardContent>
                        <HuggingFaceSection
                          selected={selected}
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
              previousLabel={previousStep ? `Back to ${previousStep.label}` : undefined}
              onPrevious={previousStep ? goToPreviousStep : undefined}
              nextLabel={nextStep ? `Continue to ${nextStep.label}` : undefined}
              onNext={nextStep ? goToNextStep : undefined}
              nextDisabled={nextStepDisabled}
            />
          </CardContent>
        </Card>
      )}

      {activeStep === "settings" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Step 3. Settings</CardTitle>
            <CardDescription>
              Apply shared execution overrides for every queued job in this batch.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Temperature</Label>
                <Input type="number" value={temperature} min={0} max={2} step={0.05} onChange={(e) => setTemperature(Number(e.target.value))} className="h-8 w-28" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Max Tokens</Label>
                <Input type="number" value={maxTokens} min={64} max={32768} step={64} onChange={(e) => setMaxTokens(Number(e.target.value))} className="h-8 w-32" />
              </div>
              <div className="flex items-center gap-2 pt-5">
                <Checkbox id="exec-no-think" checked={noThink} onCheckedChange={(checked) => setNoThink(!!checked)} />
                <Label htmlFor="exec-no-think" className="cursor-pointer text-xs">Disable thinking</Label>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-sm font-medium">Current run shape</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Each selected test set will run once per selected model. Provider-specific connection settings stay attached to the selected models, while these overrides apply to the whole batch.
              </p>
            </div>

            <StepFooter
              previousLabel={previousStep ? `Back to ${previousStep.label}` : undefined}
              onPrevious={previousStep ? goToPreviousStep : undefined}
              nextLabel={nextStep ? `Continue to ${nextStep.label}` : undefined}
              onNext={nextStep ? goToNextStep : undefined}
            />
          </CardContent>
        </Card>
      )}

      {activeStep === "review" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Step 4. Review & Run</CardTitle>
            <CardDescription>
              Final sanity check before jobs are submitted.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 xl:grid-cols-3">
              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium">Test Sets</h3>
                  <Badge variant="secondary">{selectedTestsetCount}</Badge>
                </div>
                {selectedTestsetSummaries.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {selectedTestsetSummaries.slice(0, 5).map((summary) => (
                      <div key={summary.filename} className="flex items-center justify-between gap-3 text-sm">
                        <span className="truncate font-medium" title={stripArchiveExtension(summary.filename)}>
                          {suffixDisplay(stripArchiveExtension(summary.filename), 46)}
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">{summary.test_count} tests</span>
                      </div>
                    ))}
                    {selectedTestsetSummaries.length > 5 && (
                      <p className="text-xs text-muted-foreground">+{selectedTestsetSummaries.length - 5} more test set(s)</p>
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-muted-foreground">No test sets selected yet.</p>
                )}
              </div>

              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium">Models</h3>
                  <Badge variant="secondary">{selectedCount}</Badge>
                </div>
                {selectedModelGroups.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {selectedModelGroups.map((group) => (
                      <div key={`${group.provider}:${group.apiBase ?? group.ollamaHost ?? "default"}`} className="space-y-1">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium">{providerLabel[group.provider]}</p>
                          <Badge variant="outline">{group.modelIds.length}</Badge>
                        </div>
                        {group.provider === "openai_compatible" && group.apiBase ? (
                          <p className="text-xs text-muted-foreground">{group.apiBase.replace(/^https?:\/\//, "")}</p>
                        ) : group.provider === "ollama" && group.ollamaHost && group.ollamaHost !== "http://localhost:11434" ? (
                          <p className="text-xs text-muted-foreground">{group.ollamaHost}</p>
                        ) : null}
                        <p className="text-xs leading-5 text-muted-foreground">
                          {group.modelIds.slice(0, 3).map((modelId) => suffixDisplay(modelId, 28)).join(", ")}
                          {group.modelIds.length > 3 ? ` +${group.modelIds.length - 3} more` : ""}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-muted-foreground">No models selected yet.</p>
                )}
              </div>

              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium">Overrides</h3>
                  <Badge variant="outline">{noThink ? "No think" : "Thinking on"}</Badge>
                </div>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-muted-foreground">Temperature</span>
                    <span className="font-medium">{temperature.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-muted-foreground">Max tokens</span>
                    <span className="font-medium">{maxTokens.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-muted-foreground">Providers</span>
                    <span className="font-medium">{Object.keys(selectionSummary).length}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-muted-foreground">Projected jobs</span>
                    <span className="font-medium">{projectedJobCount}</span>
                  </div>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Each selected test set runs against every selected model. Jobs are grouped by provider or endpoint, but the review count reflects the full cartesian launch set.
                </p>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-sm font-medium">
                {runDisabled ? "Selections incomplete" : `${projectedJobCount} job${projectedJobCount !== 1 ? "s" : ""} ready to launch`}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {runDisabled
                  ? "Pick at least one test set and one model before launching the batch."
                  : "Use the Run button in the header to queue the full batch."}
              </p>
            </div>

            <StepFooter
              previousLabel={previousStep ? `Back to ${previousStep.label}` : undefined}
              onPrevious={previousStep ? goToPreviousStep : undefined}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
