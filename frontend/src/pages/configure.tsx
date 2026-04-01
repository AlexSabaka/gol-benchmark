import { useCallback, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { Upload, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/layout/page-header"
import { ConfigForm } from "@/components/plugin-config/config-form"
import { usePlugins } from "@/hooks/use-plugins"
import { useGenerateTestset, useUploadYaml, useUploadGz } from "@/hooks/use-testsets"
import type { GenerateRequest, PromptConfig } from "@/types"

const USER_STYLES = ["minimal", "casual", "linguistic", "examples", "rules_math"]
const SYSTEM_STYLES = ["analytical", "casual", "adversarial", "none"]
const LANGUAGES: { code: string; flag: string; label: string }[] = [
  { code: "en", flag: "🇬🇧", label: "English" },
  { code: "es", flag: "🇪🇸", label: "Español" },
  { code: "fr", flag: "🇫🇷", label: "Français" },
  { code: "de", flag: "🇩🇪", label: "Deutsch" },
  { code: "zh", flag: "🇨🇳", label: "中文" },
  { code: "uk", flag: "🇺🇦", label: "Українська" },
]

export default function ConfigurePage() {
  const nav = useNavigate()
  const { data: plugins } = usePlugins()
  const genMutation = useGenerateTestset()
  const yamlMutation = useUploadYaml()
  const gzMutation = useUploadGz()

  // Global config state
  const [name, setName] = useState("web_benchmark")
  const [description, setDescription] = useState("")
  const [seed, setSeed] = useState(42)

  // Task selection + per-task config
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
  const [taskConfigs, setTaskConfigs] = useState<Record<string, Record<string, unknown>>>({})

  // Prompt matrix
  const [userStyles, setUserStyles] = useState<Set<string>>(new Set(["minimal"]))
  const [systemStyles, setSystemStyles] = useState<Set<string>>(new Set(["analytical"]))
  const [languages, setLanguages] = useState<Set<string>>(new Set(["en"]))

  // File refs
  const yamlRef = useRef<HTMLInputElement>(null)
  const gzRef = useRef<HTMLInputElement>(null)

  const combos = Math.max(userStyles.size, 1) * Math.max(systemStyles.size, 1) * Math.max(languages.size, 1)

  const toggleTask = useCallback((task: string, checked: boolean) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev)
      if (checked) next.add(task)
      else next.delete(task)
      return next
    })
  }, [])

  const handleFieldChange = useCallback((taskType: string, fieldName: string, value: unknown) => {
    setTaskConfigs((prev) => ({
      ...prev,
      [taskType]: { ...prev[taskType], [fieldName]: value },
    }))
  }, [])

  const toggleCheckboxSet = useCallback((value: string, setter: React.Dispatch<React.SetStateAction<Set<string>>>) => {
    setter((prev) => {
      const next = new Set(prev)
      if (next.has(value)) next.delete(value)
      else next.add(value)
      return next
    })
  }, [])

  const handleGenerate = async () => {
    if (selectedTasks.size === 0) {
      toast.error("Select at least one task")
      return
    }

    const promptConfigs: PromptConfig[] = []
    for (const us of userStyles.size > 0 ? userStyles : ["minimal"]) {
      for (const ss of systemStyles.size > 0 ? systemStyles : ["analytical"]) {
        for (const lang of languages.size > 0 ? languages : ["en"]) {
          promptConfigs.push({ user_style: us, system_style: ss, language: lang })
        }
      }
    }

    const req: GenerateRequest = {
      name,
      description,
      tasks: Array.from(selectedTasks).map((type) => ({
        type,
        generation: { ...taskConfigs[type], seed },
        prompt_configs: promptConfigs,
      })),
      cell_markers: ["1", "0"],
      seed,
    }

    try {
      const res = await genMutation.mutateAsync(req)
      toast.success(`Test set generated: ${res.filename}`)
      nav("/testsets")
    } catch (err) {
      toast.error(`Generation failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const handleYamlUpload = async () => {
    const file = yamlRef.current?.files?.[0]
    if (!file) return
    try {
      const res = await yamlMutation.mutateAsync(file)
      toast.success(`Uploaded & generated: ${res.filename}`)
      nav("/testsets")
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const handleGzUpload = async () => {
    const file = gzRef.current?.files?.[0]
    if (!file) return
    try {
      const res = await gzMutation.mutateAsync(file)
      toast.success(`Uploaded: ${res.filename}`)
      nav("/testsets")
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const isGenerating = genMutation.isPending

  return (
    <div className="space-y-6">
      <PageHeader title="Configure" description="Create a new test set or upload an existing one" />

      <Tabs defaultValue="build">
        <TabsList>
          <TabsTrigger value="build">Build Configuration</TabsTrigger>
          <TabsTrigger value="upload">Upload</TabsTrigger>
        </TabsList>

        {/* ── Build tab ── */}
        <TabsContent value="build" className="space-y-6 mt-4">
          {/* Global settings */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Global Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Name</Label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} className="h-8" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Seed</Label>
                  <Input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="h-8 w-28" />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label className="text-xs">Description</Label>
                  <Input value={description} onChange={(e) => setDescription(e.target.value)} className="h-8" placeholder="Optional" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Task selection */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">
                Tasks
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {selectedTasks.size} selected
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {plugins?.map((p) => (
                  <label key={p.task_type} className="flex items-center gap-2 text-xs cursor-pointer">
                    <Checkbox
                      checked={selectedTasks.has(p.task_type)}
                      onCheckedChange={(c) => toggleTask(p.task_type, !!c)}
                    />
                    <span className="capitalize">{p.display_name}</span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Per-task config panels */}
          {Array.from(selectedTasks).map((task) => {
            const plugin = plugins?.find((p) => p.task_type === task)
            return (
              <div key={task} className="space-y-2">
                <ConfigForm
                  taskType={task}
                  description={plugin?.description}
                  values={taskConfigs[task] ?? {}}
                  onChange={handleFieldChange}
                />
              </div>
            )
          })}

          {/* Prompt matrix */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">
                Prompt Configuration
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {combos} combination{combos !== 1 ? "s" : ""}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label className="text-xs">User Styles</Label>
                  <div className="space-y-1">
                    {USER_STYLES.map((s) => (
                      <label key={s} className="flex items-center gap-2 text-xs cursor-pointer">
                        <Checkbox checked={userStyles.has(s)} onCheckedChange={() => toggleCheckboxSet(s, setUserStyles)} />
                        {s}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">System Styles</Label>
                  <div className="space-y-1">
                    {SYSTEM_STYLES.map((s) => (
                      <label key={s} className="flex items-center gap-2 text-xs cursor-pointer">
                        <Checkbox checked={systemStyles.has(s)} onCheckedChange={() => toggleCheckboxSet(s, setSystemStyles)} />
                        {s}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Languages</Label>
                  <div className="space-y-1">
                    {LANGUAGES.map((l) => (
                      <label key={l.code} className="flex items-center gap-2 text-xs cursor-pointer">
                        <Checkbox checked={languages.has(l.code)} onCheckedChange={() => toggleCheckboxSet(l.code, setLanguages)} />
                        <span>{l.flag}</span>
                        <span>{l.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Separator />

          <div className="flex justify-end">
            <Button onClick={handleGenerate} disabled={isGenerating || selectedTasks.size === 0}>
              {isGenerating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Generate Test Set
            </Button>
          </div>
        </TabsContent>

        {/* ── Upload tab ── */}
        <TabsContent value="upload" className="space-y-6 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Upload YAML Config</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground">Upload a YAML configuration file to generate a test set</p>
              <div className="flex items-center gap-3">
                <Input ref={yamlRef} type="file" accept=".yaml,.yml" className="h-9 max-w-md" />
                <Button variant="outline" onClick={handleYamlUpload} disabled={yamlMutation.isPending}>
                  {yamlMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                  Upload & Generate
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Upload Pre-Generated Test Set</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground">Upload an existing .json.gz test set file</p>
              <div className="flex items-center gap-3">
                <Input ref={gzRef} type="file" accept=".gz" className="h-9 max-w-md" />
                <Button variant="outline" onClick={handleGzUpload} disabled={gzMutation.isPending}>
                  {gzMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                  Upload
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
