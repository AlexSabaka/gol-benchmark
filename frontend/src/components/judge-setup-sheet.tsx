import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { ChevronDown, Loader2, Save } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { useOllamaModels, useOpenAIModels } from "@/hooks/use-models"
import { useSubmitJudge } from "@/hooks/use-results"
import { loadCredentials, saveCredential } from "@/lib/credential-store"
import type { JudgeRequest } from "@/types"

// ── Default prompts (matching backend judge.py) ──

const DEFAULT_SYSTEM_PROMPT = `You are an evaluation auditor reviewing model responses that were marked INCORRECT by an automated scoring pipeline. Your job is to determine WHY each response was marked incorrect.

You will receive:
- QUESTION: the original prompt given to the model
- RESPONSE: the model's full raw response
- PARSED: what the automated parser extracted as the model's answer
- EXPECTED: the ground-truth correct answer

## Your task

Classify each case into exactly one verdict:

**true_incorrect** — The model's reasoning and/or final answer is genuinely wrong. The expected answer is correct and the model failed to reach it.

**false_negative** — The model actually produced a correct or defensibly correct answer, but the scorer marked it wrong (e.g. the expected answer is too strict, the model's answer is equivalent but phrased differently, or the task has multiple valid answers).

**parser_failure** — The model's response contains the correct answer (or clearly implies it), but the parser extracted the wrong token. The model itself is not at fault; the extraction logic failed.

## Parser issue types
If verdict is \`parser_failure\`, also classify the failure mode:

- \`format_mismatch\` — answer is present but in an unexpected format (e.g. "twelve" vs "12", "12:23am" vs "12:23 AM")
- \`wrong_occurrence\` — correct answer appears in the response but parser grabbed a different occurrence (e.g. from a wrong intermediate step rather than the final answer)
- \`answer_buried\` — correct answer exists but is not in the expected location (e.g. inside a table, list, or verification block rather than at the end)
- \`hedged_correct\` — model gives the right answer but wraps it in so much hedging/alternatives that the parser picks up noise
- \`other\` — parser failure that doesn't fit above categories

## Output format
Respond ONLY with a JSON object. No prose, no markdown fences. Example:

{"verdict": "parser_failure", "parser_issue": "wrong_occurrence", "confidence": "high", "notes": "Model correctly computed 12:23 AM in step 3 but self-corrected to wrong value in conclusion"}

{"verdict": "true_incorrect", "parser_issue": null, "confidence": "high", "notes": "Model recommends walking but car is needed at the destination"}

{"verdict": "false_negative", "parser_issue": null, "confidence": "medium", "notes": "Model answer '3' is correct; expected '3' — possible case sensitivity or whitespace issue in parser"}

## Confidence field
- \`high\` — unambiguous
- \`medium\` — defensible but could be argued either way
- \`low\` — genuinely unclear, edge case

Keep notes under 25 words.`

const DEFAULT_USER_TEMPLATE = `QUESTION:
{user_prompt}

RESPONSE:
{raw_response}

PARSED:
{parsed_answer}

EXPECTED:
{expected_answer}`

// ── Component ──

interface JudgeSetupSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  selectedFiles: string[]
}

export function JudgeSetupSheet({ open, onOpenChange, selectedFiles }: JudgeSetupSheetProps) {
  const nav = useNavigate()
  const judgeMutation = useSubmitJudge()

  // Judge scope
  const [onlyIncorrect, setOnlyIncorrect] = useState(true)

  // Provider tab
  const [providerTab, setProviderTab] = useState<"ollama" | "openai">("ollama")

  // Ollama state
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [ollamaModel, setOllamaModel] = useState("")
  const { data: ollamaData, isLoading: ollamaLoading } = useOllamaModels(ollamaHost, open && providerTab === "ollama")

  // OpenAI state
  const [apiBase, setApiBase] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [openaiModel, setOpenaiModel] = useState("")
  const { data: openaiData, isLoading: openaiLoading } = useOpenAIModels(apiBase, apiKey || undefined, open && providerTab === "openai" && !!apiBase)
  const [savedCredentials, setSavedCredentials] = useState<Array<{ apiBase: string; apiKey: string }>>([])

  // Prompts
  const [promptsOpen, setPromptsOpen] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT)
  const [userTemplate, setUserTemplate] = useState(DEFAULT_USER_TEMPLATE)

  // Sampling
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(500)

  // Load saved credentials on open
  useEffect(() => {
    if (open) {
      loadCredentials().then(setSavedCredentials)
    }
  }, [open])

  const ollamaModels = useMemo(
    () => (ollamaData?.models ?? []).map((m) => ({ id: m.name, label: `${m.display_name} (${m.size_human})` })),
    [ollamaData]
  )

  const openaiModels = useMemo(
    () => (openaiData?.models ?? []).map((m) => ({ id: m.name, label: m.display_name })),
    [openaiData]
  )

  const selectedModel = providerTab === "ollama" ? ollamaModel : openaiModel
  const canSubmit = selectedModel !== "" && selectedFiles.length > 0

  const handleSaveCredential = async () => {
    if (!apiBase) return
    await saveCredential(apiBase, apiKey)
    toast.success("Credential saved")
    setSavedCredentials(await loadCredentials())
  }

  const handleSubmit = async () => {
    if (!canSubmit) return

    const req: JudgeRequest = {
      result_filenames: selectedFiles,
      provider: providerTab === "ollama" ? "ollama" : "openai_compatible",
      model: selectedModel,
      only_incorrect: onlyIncorrect,
      temperature,
      max_tokens: maxTokens,
    }

    // Add provider-specific fields
    if (providerTab === "ollama") {
      if (ollamaHost !== "http://localhost:11434") {
        req.ollama_host = ollamaHost
      }
    } else {
      req.api_base = apiBase
      req.api_key = apiKey
    }

    // Add custom prompts only if modified from defaults
    if (systemPrompt !== DEFAULT_SYSTEM_PROMPT) {
      req.system_prompt = systemPrompt
    }
    if (userTemplate !== DEFAULT_USER_TEMPLATE) {
      req.user_prompt_template = userTemplate
    }

    try {
      const res = await judgeMutation.mutateAsync(req)
      toast.success(`Judge job started: ${res.model} (${res.job_id.slice(0, 8)})`)
      onOpenChange(false)
      nav("/jobs")
    } catch (err) {
      toast.error(`Judge submission failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>LLM Judge Setup</SheetTitle>
          <SheetDescription>
            Review incorrect results with an LLM judge to classify verdicts
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 px-4">
          {/* Section 1: Judge Scope */}
          <section className="space-y-3">
            <h4 className="text-sm font-medium">Judge Scope</h4>
            <div className="flex items-center gap-2">
              <Checkbox
                id="judge-only-incorrect"
                checked={onlyIncorrect}
                onCheckedChange={(c) => setOnlyIncorrect(!!c)}
              />
              <Label htmlFor="judge-only-incorrect" className="text-xs cursor-pointer">
                Only incorrect results
              </Label>
            </div>
            <p className="text-xs text-muted-foreground">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? "s" : ""} selected
            </p>
          </section>

          <Separator />

          {/* Section 2: Judge Model */}
          <section className="space-y-3">
            <h4 className="text-sm font-medium">Judge Model</h4>
            <Tabs value={providerTab} onValueChange={(v) => setProviderTab(v as "ollama" | "openai")}>
              <TabsList className="h-8">
                <TabsTrigger value="ollama" className="text-xs px-3 h-6">Ollama</TabsTrigger>
                <TabsTrigger value="openai" className="text-xs px-3 h-6">OpenAI-Compatible</TabsTrigger>
              </TabsList>

              <TabsContent value="ollama" className="space-y-3 mt-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Host</Label>
                  <Input
                    value={ollamaHost}
                    onChange={(e) => setOllamaHost(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Model</Label>
                  {ollamaLoading ? (
                    <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" /> Loading models...
                    </div>
                  ) : (
                    <Select value={ollamaModel} onValueChange={setOllamaModel}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select a model..." />
                      </SelectTrigger>
                      <SelectContent>
                        {ollamaModels.map((m) => (
                          <SelectItem key={m.id} value={m.id} className="text-xs">
                            {m.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="openai" className="space-y-3 mt-3">
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Base URL</Label>
                    <Input
                      value={apiBase}
                      onChange={(e) => setApiBase(e.target.value)}
                      placeholder="https://api.groq.com/openai/v1"
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">API Key</Label>
                    <Input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="h-8 text-xs"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={handleSaveCredential} disabled={!apiBase}>
                    <Save className="mr-1 h-3 w-3" /> Save
                  </Button>
                  {savedCredentials.length > 0 && (
                    <Select onValueChange={(v) => {
                      const cred = savedCredentials.find((c) => c.apiBase === v)
                      if (cred) { setApiBase(cred.apiBase); setApiKey(cred.apiKey) }
                    }}>
                      <SelectTrigger className="h-6 w-[160px] text-xs">
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
                <div className="space-y-1.5">
                  <Label className="text-xs">Model</Label>
                  {openaiLoading ? (
                    <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" /> Loading models...
                    </div>
                  ) : (
                    <Select value={openaiModel} onValueChange={setOpenaiModel}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select a model..." />
                      </SelectTrigger>
                      <SelectContent>
                        {openaiModels.map((m) => (
                          <SelectItem key={m.id} value={m.id} className="text-xs">
                            {m.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </TabsContent>
            </Tabs>

            {selectedModel && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Selected:</span>
                <Badge variant="secondary" className="text-xs">
                  {selectedModel}
                </Badge>
              </div>
            )}
          </section>

          <Separator />

          {/* Section 3: Prompts (collapsible) */}
          <Collapsible open={promptsOpen} onOpenChange={setPromptsOpen}>
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center justify-between py-1">
                <h4 className="text-sm font-medium">Prompts</h4>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${promptsOpen ? "rotate-180" : ""}`} />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <Label className="text-xs">System Prompt</Label>
                <Textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="min-h-[120px] text-xs font-mono"
                />
                <p className="text-[10px] text-muted-foreground">
                  {systemPrompt.length} characters
                  {systemPrompt !== DEFAULT_SYSTEM_PROMPT && (
                    <> &middot; <button className="underline" onClick={() => setSystemPrompt(DEFAULT_SYSTEM_PROMPT)}>Reset to default</button></>
                  )}
                </p>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">User Prompt Template</Label>
                <Textarea
                  value={userTemplate}
                  onChange={(e) => setUserTemplate(e.target.value)}
                  className="min-h-[80px] text-xs font-mono"
                />
                <p className="text-[10px] text-muted-foreground">
                  Placeholders: {"{user_prompt}"}, {"{raw_response}"}, {"{parsed_answer}"}, {"{expected_answer}"}
                  {userTemplate !== DEFAULT_USER_TEMPLATE && (
                    <> &middot; <button className="underline" onClick={() => setUserTemplate(DEFAULT_USER_TEMPLATE)}>Reset to default</button></>
                  )}
                </p>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Separator />

          {/* Section 4: Sampling */}
          <section className="space-y-3">
            <h4 className="text-sm font-medium">Sampling</h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Temperature</Label>
                <Input
                  type="number"
                  value={temperature}
                  min={0}
                  max={2}
                  step={0.05}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="h-8 w-28"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Max Tokens</Label>
                <Input
                  type="number"
                  value={maxTokens}
                  min={100}
                  max={4000}
                  step={50}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                  className="h-8 w-28"
                />
              </div>
            </div>
          </section>
        </div>

        <SheetFooter>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || judgeMutation.isPending}
            className="w-full"
          >
            {judgeMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Run Judge
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
