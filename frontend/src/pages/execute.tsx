import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { toast } from "sonner"
import { Loader2, Play, Search, Star, Save, X, Plus, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
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
import { formatBytes, formatDate } from "@/lib/utils"
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

function selectedModelKey(m: SelectedModel): string {
  if (m.provider === "openai_compatible") return `openai_compatible:${m.apiBase}:${m.id}`
  return `${m.provider}:${m.id}`
}

function ExecuteTestsetGridRow({
  summary,
  selected,
  onToggle,
}: {
  summary: TestsetSummary
  selected: boolean
  onToggle: () => void
}) {
  const title = summary.filename.replace(".json.gz", "")
  const languages = summary.languages ?? []

  return (
    <tr className={selected ? "bg-primary/5" : "hover:bg-muted/30"}>
      <td className="px-3 py-3 align-top">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle()}
          aria-label={`Select ${title}`}
        />
      </td>
      <td className="px-3 py-3 align-top">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" title={title}>{title}</p>
          {summary.matrix_label && (
            <p className="mt-1 truncate text-[11px] text-muted-foreground" title={summary.matrix_label}>
              {summary.matrix_label}
            </p>
          )}
        </div>
      </td>
      <td className="px-3 py-3 align-top">
        <div className="flex min-w-40 flex-wrap gap-1">
          {summary.task_types.map((task) => (
            <TaskBadge key={task} task={task} />
          ))}
        </div>
      </td>
      <td className="px-3 py-3 align-top text-sm">
        {languages.length > 0 ? (
          <span title={languages.join(", ")}>{langFlags(languages)}</span>
        ) : (
          <span className="text-xs text-muted-foreground">-</span>
        )}
      </td>
      <td className="px-3 py-3 align-top text-xs text-muted-foreground">{summary.test_count}</td>
      <td className="px-3 py-3 align-top text-xs text-muted-foreground">{formatBytes(summary.size_bytes)}</td>
      <td className="px-3 py-3 align-top text-xs text-muted-foreground whitespace-nowrap">{formatDate(summary.created)}</td>
    </tr>
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
  const { data: testsets } = useTestsets()
  const runMutation = useRunBenchmark()
  const requestedTestset = params.get("testset")

  // Form state
  const [selectedTestsets, setSelectedTestsets] = useLocalStorageSetState<string>(
    makeStorageKey(storageScope, "selected-testsets"),
    requestedTestset ? [requestedTestset] : [],
  )
  const [testsetSearch, setTestsetSearch] = useLocalStorageState<string>(makeStorageKey(storageScope, "testset-search"), "")
  const [testsetPage, setTestsetPage] = useLocalStorageState<number>(makeStorageKey(storageScope, "testset-page"), 1)
  const [testsetPageSize, setTestsetPageSize] = useLocalStorageState<number>(makeStorageKey(storageScope, "testset-page-size"), 9)
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
    setTestsetPage(1)
  }, [requestedTestset, setSelectedTestsets, setTestsetPage])

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

  const filteredTestsets = useMemo(() => {
    const query = testsetSearch.trim().toLowerCase()
    return [...(testsets ?? [])]
      .filter((summary) => {
        if (!query) return true
        const haystack = [
          summary.filename,
          summary.matrix_label ?? "",
          summary.matrix_plugin ?? "",
          summary.matrix_batch_id ?? "",
          summary.task_types.join(" "),
          summary.languages.join(" "),
        ].join(" ").toLowerCase()
        return haystack.includes(query)
      })
      .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())
  }, [testsetSearch, testsets])

  const totalTestsetPages = Math.max(1, Math.ceil(filteredTestsets.length / Math.max(testsetPageSize, 1)))
  const currentTestsetPage = Math.min(Math.max(testsetPage, 1), totalTestsetPages)

  useEffect(() => {
    if (currentTestsetPage !== testsetPage) {
      setTestsetPage(currentTestsetPage)
    }
  }, [currentTestsetPage, setTestsetPage, testsetPage])

  const paginatedTestsets = useMemo(() => {
    const start = (currentTestsetPage - 1) * testsetPageSize
    return filteredTestsets.slice(start, start + testsetPageSize)
  }, [currentTestsetPage, filteredTestsets, testsetPageSize])

  const visibleTestsetNames = useMemo(
    () => paginatedTestsets.map((summary) => summary.filename),
    [paginatedTestsets],
  )

  const allVisibleTestsetsSelected = visibleTestsetNames.length > 0 && visibleTestsetNames.every((filename) => selectedTestsets.has(filename))

  const handleRun = async () => {
    if (selectedTestsetCount === 0) { toast.error("Select at least one test set"); return }
    if (selectedCount === 0) { toast.error("Select at least one model"); return }

    const testsetFilenames = Array.from(selectedTestsets).sort()
    const sharedRunGroupId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().slice(0, 8)
      : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.slice(0, 8)

    // Group selected models by provider + endpoint
    const groups = new Map<string, { provider: string; models: string[]; ollamaHost?: string; apiBase?: string; apiKey?: string }>()
    for (const m of selected.values()) {
      let groupKey: string
      if (m.provider === "openai_compatible") {
        groupKey = `openai_compatible:${m.apiBase ?? ""}`
      } else {
        groupKey = m.provider
      }
      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          provider: m.provider,
          models: [],
          ollamaHost: m.ollamaHost,
          apiBase: m.apiBase,
          apiKey: m.apiKey,
        })
      }
      groups.get(groupKey)!.models.push(m.id)
    }

    let totalJobs = 0
    for (const group of groups.values()) {
      const req: RunRequest = {
        testset_filenames: testsetFilenames,
        models: group.models,
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

  // Summary of selected models by provider
  const selectionSummary = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const m of selected.values()) {
      counts[m.provider] = (counts[m.provider] ?? 0) + 1
    }
    return counts
  }, [selected])

  return (
    <div className="space-y-6">
      <PageHeader title="Execute" description="Run test sets on model(s) from multiple providers" />

      <div className="flex gap-6">
        {/* Favorites sidebar */}
        {hasFavorites && (
          <div className="w-56 shrink-0">
            <Card className="sticky top-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-1.5">
                  <Star className="h-3.5 w-3.5 fill-yellow-500 text-yellow-500" />
                  Favorites
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto">
                {Object.entries(groupedFavorites).map(([prov, modelIds]) => (
                  <div key={prov}>
                    <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                      {providerLabel[prov] ?? prov}
                    </p>
                    <div className="space-y-0.5">
                      {modelIds.map((modelId) => {
                        // Check if any selection matches this model
                        const isSelected = [...selected.values()].some(
                          (s) => s.id === modelId && s.provider === prov
                        )
                        return (
                          <div key={modelId} className="flex items-center gap-1 group">
                            <button
                              onClick={() => {
                                // Toggle: find if already selected, else add with default context
                                const existing = [...selected.entries()].find(
                                  ([, s]) => s.id === modelId && s.provider === prov
                                )
                                if (existing) {
                                  setSelected((prev) => { const n = new Map(prev); n.delete(existing[0]); return n })
                                } else {
                                  const sm: SelectedModel = {
                                    id: modelId,
                                    provider: prov as SelectedModel["provider"],
                                    ...(prov === "ollama" && { ollamaHost }),
                                    ...(prov === "openai_compatible" && openaiEndpoints[0] && {
                                      apiBase: openaiEndpoints[0].apiBase,
                                      apiKey: openaiEndpoints[0].apiKey,
                                    }),
                                  }
                                  toggleModelSelection(sm)
                                }
                              }}
                              className={`flex-1 text-left text-xs px-1.5 py-0.5 rounded truncate transition-colors ${
                                isSelected ? "bg-primary/10 text-primary font-medium" : "hover:bg-accent"
                              }`}
                              title={`${modelId} (${prov})`}
                            >
                              {modelId.length > 22 ? modelId.slice(0, 20) + "\u2026" : modelId}
                            </button>
                            <button
                              onClick={() => handleToggleFavorite(favoriteKey(prov, modelId))}
                              className="opacity-0 group-hover:opacity-100 shrink-0 p-0.5 text-muted-foreground/50 hover:text-destructive transition-all"
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

        <div className="flex-1 max-w-3xl space-y-6">
          {/* Test set selector */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <CardTitle className="text-sm">Test Sets</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{selectedTestsetCount} selected</Badge>
                  <Badge variant="outline">{filteredTestsets.length} visible</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-60 flex-1 sm:max-w-sm">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={testsetSearch}
                    onChange={(event) => {
                      setTestsetSearch(event.target.value)
                      setTestsetPage(1)
                    }}
                    placeholder="Filter test sets..."
                    className="pl-8"
                  />
                </div>
                <Select value={String(testsetPageSize)} onValueChange={(value) => {
                  setTestsetPageSize(Number(value))
                  setTestsetPage(1)
                }}>
                  <SelectTrigger className="h-9 w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[6, 9, 12, 18].map((size) => (
                      <SelectItem key={size} value={String(size)}>{size} / page</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 text-xs"
                  onClick={() => {
                    setSelectedTestsets((previous) => {
                      const next = new Set(previous)
                      for (const filename of visibleTestsetNames) next.add(filename)
                      return next
                    })
                  }}
                  disabled={visibleTestsetNames.length === 0 || allVisibleTestsetsSelected}
                >
                  Select Page
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 text-xs"
                  onClick={() => setSelectedTestsets(new Set())}
                  disabled={selectedTestsetCount === 0}
                >
                  Clear Selection
                </Button>
              </div>

              {paginatedTestsets.length === 0 ? (
                <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
                  No test sets match the current filter.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="min-w-[940px] w-full text-sm">
                    <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
                      <tr>
                        <th className="w-12 px-3 py-2 font-medium">Pick</th>
                        <th className="px-3 py-2 font-medium">Test Set</th>
                        <th className="w-56 px-3 py-2 font-medium">Tasks</th>
                        <th className="w-24 px-3 py-2 font-medium">Lang</th>
                        <th className="w-20 px-3 py-2 font-medium">Tests</th>
                        <th className="w-24 px-3 py-2 font-medium">Size</th>
                        <th className="w-40 px-3 py-2 font-medium">Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedTestsets.map((summary) => (
                        <ExecuteTestsetGridRow
                          key={summary.filename}
                          summary={summary}
                          selected={selectedTestsets.has(summary.filename)}
                          onToggle={() => {
                            setSelectedTestsets((previous) => {
                              const next = new Set(previous)
                              if (next.has(summary.filename)) next.delete(summary.filename)
                              else next.add(summary.filename)
                              return next
                            })
                          }}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                <span>Page {currentTestsetPage} of {totalTestsetPages}</span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setTestsetPage((page) => Math.max(1, page - 1))}
                    disabled={currentTestsetPage <= 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setTestsetPage((page) => Math.min(totalTestsetPages, page + 1))}
                    disabled={currentTestsetPage >= totalTestsetPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Global model search */}
          <div className="relative max-w-sm">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Filter models across all providers..."
              value={modelSearch}
              onChange={(e) => setModelSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>

          {/* Ollama */}
          <Collapsible open={ollamaOpen} onOpenChange={setOllamaOpen}>
            <Card>
              <CardHeader className="pb-2">
                <CollapsibleTrigger asChild>
                  <button className="flex w-full items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      Ollama
                      {selectionSummary.ollama && (
                        <Badge variant="secondary" className="text-[10px]">{selectionSummary.ollama} selected</Badge>
                      )}
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

          {/* OpenAI-Compatible (multiple endpoints) */}
          <Collapsible open={openaiOpen} onOpenChange={setOpenaiOpen}>
            <Card>
              <CardHeader className="pb-2">
                <CollapsibleTrigger asChild>
                  <button className="flex w-full items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      OpenAI-Compatible
                      {selectionSummary.openai_compatible && (
                        <Badge variant="secondary" className="text-[10px]">{selectionSummary.openai_compatible} selected</Badge>
                      )}
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

          {/* HuggingFace */}
          <Collapsible open={hfOpen} onOpenChange={setHfOpen}>
            <Card>
              <CardHeader className="pb-2">
                <CollapsibleTrigger asChild>
                  <button className="flex w-full items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      HuggingFace
                      {selectionSummary.huggingface && (
                        <Badge variant="secondary" className="text-[10px]">{selectionSummary.huggingface} selected</Badge>
                      )}
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

          {/* Sampling overrides */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Sampling Overrides</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Temperature</Label>
                  <Input type="number" value={temperature} min={0} max={2} step={0.05} onChange={(e) => setTemperature(Number(e.target.value))} className="h-8 w-28" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Max Tokens</Label>
                  <Input type="number" value={maxTokens} min={64} max={32768} step={64} onChange={(e) => setMaxTokens(Number(e.target.value))} className="h-8 w-28" />
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <Checkbox id="exec-no-think" checked={noThink} onCheckedChange={(c) => setNoThink(!!c)} />
                  <Label htmlFor="exec-no-think" className="text-xs cursor-pointer">Disable thinking</Label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Run button with summary */}
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">
              {(selectedCount > 0 || selectedTestsetCount > 0) && (
                <span>
                  <Badge variant="outline" className="mr-1 text-[10px]">
                    Test Sets: {selectedTestsetCount}
                  </Badge>
                  {Object.entries(selectionSummary).map(([p, c]) => (
                    <Badge key={p} variant="outline" className="mr-1 text-[10px]">
                      {providerLabel[p] ?? p}: {c}
                    </Badge>
                  ))}
                </span>
              )}
            </div>
            <Button onClick={handleRun} disabled={runMutation.isPending || selectedTestsetCount === 0 || selectedCount === 0}>
              {runMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Run {selectedTestsetCount * selectedCount} Job{selectedTestsetCount * selectedCount !== 1 ? "s" : ""}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
