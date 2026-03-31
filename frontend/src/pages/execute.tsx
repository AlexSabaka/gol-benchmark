import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router"
import { toast } from "sonner"
import { Loader2, Play, XCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/layout/page-header"
import { JobStateBadge } from "@/components/job-state-badge"
import { useTestsets } from "@/hooks/use-testsets"
import { useOllamaModels, useOpenAIModels } from "@/hooks/use-models"
import { useJobs, useRunBenchmark, useCancelJob } from "@/hooks/use-jobs"
import type { Provider, RunRequest } from "@/types"

export default function ExecutePage() {
  const [params] = useSearchParams()
  const { data: testsets } = useTestsets()
  const { data: jobs } = useJobs()
  const runMutation = useRunBenchmark()
  const cancelMutation = useCancelJob()

  // Form state
  const [testsetFilename, setTestsetFilename] = useState(params.get("testset") ?? "")
  const [provider, setProvider] = useState<Provider>("ollama")
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [apiBase, setApiBase] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [noThink, setNoThink] = useState(true)

  // Auto-select testset from URL
  useEffect(() => {
    const ts = params.get("testset")
    if (ts) setTestsetFilename(ts)
  }, [params])

  // Model discovery
  const { data: ollamaData, isLoading: ollamaLoading } = useOllamaModels(ollamaHost, provider === "ollama")
  const { data: openaiData, isLoading: openaiLoading } = useOpenAIModels(apiBase, apiKey, provider === "openai_compatible" && !!apiBase)

  const models =
    provider === "ollama"
      ? (ollamaData?.models ?? []).map((m) => ({ id: m.name, label: `${m.display_name} (${m.size_human})` }))
      : provider === "openai_compatible"
        ? (openaiData?.models ?? []).map((m) => ({ id: m.name, label: m.display_name }))
        : []

  const isDiscovering = (provider === "ollama" && ollamaLoading) || (provider === "openai_compatible" && openaiLoading)

  // Reset model selection when provider changes
  useEffect(() => { setSelectedModels(new Set()) }, [provider])

  const toggleModel = useCallback((id: string) => {
    setSelectedModels((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleRun = async () => {
    if (!testsetFilename) { toast.error("Select a test set"); return }
    if (selectedModels.size === 0) { toast.error("Select at least one model"); return }

    const req: RunRequest = {
      testset_filename: testsetFilename,
      models: Array.from(selectedModels),
      provider,
      temperature,
      max_tokens: maxTokens,
      no_think: noThink,
      ...(provider === "ollama" && ollamaHost !== "http://localhost:11434" && { ollama_host: ollamaHost }),
      ...(provider === "openai_compatible" && { api_base: apiBase, api_key: apiKey }),
    }

    try {
      const res = await runMutation.mutateAsync(req)
      toast.success(`Started ${res.jobs.length} job(s)`)
    } catch (err) {
      toast.error(`Run failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const activeJobs = (jobs ?? []).filter((j) => j.state === "running" || j.state === "pending")

  return (
    <div className="space-y-6">
      <PageHeader title="Execute" description="Run test sets on model(s) and track progress" />

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        {/* Left — config */}
        <div className="space-y-6">
          {/* Test set selector */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Test Set</CardTitle></CardHeader>
            <CardContent>
              <Select value={testsetFilename} onValueChange={setTestsetFilename}>
                <SelectTrigger className="max-w-lg">
                  <SelectValue placeholder="Select a test set…" />
                </SelectTrigger>
                <SelectContent>
                  {(testsets ?? []).map((ts) => (
                    <SelectItem key={ts.filename} value={ts.filename}>
                      {ts.filename.replace(".json.gz", "")} ({ts.test_count} tests)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Provider + model selection */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Provider & Models</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Tabs value={provider} onValueChange={(v) => setProvider(v as Provider)}>
                <TabsList>
                  <TabsTrigger value="ollama">Ollama</TabsTrigger>
                  <TabsTrigger value="openai_compatible">OpenAI-Compatible</TabsTrigger>
                  <TabsTrigger value="huggingface">HuggingFace</TabsTrigger>
                </TabsList>

                <TabsContent value="ollama" className="mt-3 space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Ollama Host</Label>
                    <Input value={ollamaHost} onChange={(e) => setOllamaHost(e.target.value)} className="h-8 max-w-sm" />
                  </div>
                </TabsContent>

                <TabsContent value="openai_compatible" className="mt-3 space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Base URL</Label>
                      <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} placeholder="https://api.groq.com/openai/v1" className="h-8" />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">API Key</Label>
                      <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className="h-8" />
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="huggingface" className="mt-3">
                  <p className="text-xs text-muted-foreground">HuggingFace model discovery is not yet integrated. Enter model IDs manually in a future update.</p>
                </TabsContent>
              </Tabs>

              <Separator />

              <div className="space-y-2">
                <Label className="text-xs">Available Models {isDiscovering && <Loader2 className="inline h-3 w-3 animate-spin ml-1" />}</Label>
                {models.length === 0 && !isDiscovering && (
                  <p className="text-xs text-muted-foreground">No models found. Check your provider settings.</p>
                )}
                <div className="grid gap-1.5 sm:grid-cols-2 max-h-[300px] overflow-y-auto">
                  {models.map((m) => (
                    <label key={m.id} className="flex items-center gap-2 text-xs cursor-pointer">
                      <Checkbox checked={selectedModels.has(m.id)} onCheckedChange={() => toggleModel(m.id)} />
                      <span className="truncate" title={m.id}>{m.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

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

          <div className="flex justify-end">
            <Button onClick={handleRun} disabled={runMutation.isPending || !testsetFilename || selectedModels.size === 0}>
              {runMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Run on {selectedModels.size} Model{selectedModels.size !== 1 ? "s" : ""}
            </Button>
          </div>
        </div>

        {/* Right — job progress */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium">Active Jobs ({activeJobs.length})</h3>
          {activeJobs.length === 0 && (
            <p className="text-xs text-muted-foreground">No running jobs</p>
          )}
          {activeJobs.map((job) => {
            const pct = job.progress_total > 0 ? (job.progress_current / job.progress_total) * 100 : 0
            return (
              <Card key={job.id}>
                <CardContent className="pt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium truncate">{job.model_name}</span>
                    <JobStateBadge state={job.state} />
                  </div>
                  <Progress value={pct} className="h-2" />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      {job.progress_current}/{job.progress_total}
                    </span>
                    {job.state === "running" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2 text-destructive"
                        onClick={() => cancelMutation.mutate(job.id)}
                      >
                        <XCircle className="mr-1 h-3 w-3" /> Cancel
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}

          {/* Recent completed */}
          {(jobs ?? []).filter((j) => j.state === "completed" || j.state === "failed").length > 0 && (
            <>
              <Separator />
              <h3 className="text-sm font-medium">Recent</h3>
              {(jobs ?? [])
                .filter((j) => j.state === "completed" || j.state === "failed")
                .slice(0, 5)
                .map((job) => (
                  <div key={job.id} className="flex items-center justify-between text-xs py-1">
                    <span className="truncate">{job.model_name}</span>
                    <JobStateBadge state={job.state} />
                  </div>
                ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
