import { useRef, useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { Link2, Loader2, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { fetchPromptFromUrl } from "@/api/testsets"
import { useUploadYaml, useUploadGz } from "@/hooks/use-testsets"
import { cn } from "@/lib/utils"

type ImportMode = "url" | "yaml" | "gz"

const MODES: { id: ImportMode; label: string }[] = [
  { id: "url",  label: "From URL" },
  { id: "yaml", label: "YAML config" },
  { id: "gz",   label: "Test set file" },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ImportTestsetDialog({ open, onOpenChange }: Props) {
  const nav = useNavigate()
  const yamlMutation = useUploadYaml()
  const gzMutation = useUploadGz()

  const [mode, setMode] = useState<ImportMode>("url")
  const [url, setUrl] = useState("")
  const [paste, setPaste] = useState("")
  const [fetching, setFetching] = useState(false)
  const yamlFileRef = useRef<HTMLInputElement>(null)
  const gzFileRef = useRef<HTMLInputElement>(null)

  const isPending = yamlMutation.isPending || gzMutation.isPending || fetching

  const close = () => onOpenChange(false)

  const handleUrlImport = async () => {
    if (!url) return
    setFetching(true)
    try {
      const res = await fetchPromptFromUrl(url)
      const blob = new File([res.text], "fetched.yaml", { type: "text/plain" })
      const result = await yamlMutation.mutateAsync(blob)
      toast.success(`Generated from URL: ${result.filename}`)
      close()
      nav("/testsets")
    } catch (err) {
      toast.error(`Fetch failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setFetching(false)
    }
  }

  const handleYamlFileUpload = async () => {
    const file = yamlFileRef.current?.files?.[0]
    if (!file) return
    try {
      const res = await yamlMutation.mutateAsync(file)
      toast.success(`Uploaded & generated: ${res.filename}`)
      close()
      nav("/testsets")
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const handlePasteImport = async () => {
    if (!paste.trim()) return
    setFetching(true)
    try {
      const blob = new File([paste], "pasted.yaml", { type: "text/plain" })
      const result = await yamlMutation.mutateAsync(blob)
      toast.success(`Generated from pasted config: ${result.filename}`)
      close()
      nav("/testsets")
    } catch (err) {
      toast.error(`Failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setFetching(false)
    }
  }

  const handleGzUpload = async () => {
    const file = gzFileRef.current?.files?.[0]
    if (!file) return
    try {
      const res = await gzMutation.mutateAsync(file)
      toast.success(`Uploaded: ${res.filename}`)
      close()
      nav("/testsets")
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Import</DialogTitle>
        </DialogHeader>

        {/* Mode segmented control */}
        <div className="flex w-fit items-center gap-1 rounded-lg border bg-muted/40 p-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setMode(m.id)}
              className={cn(
                "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === m.id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {m.label}
            </button>
          ))}
        </div>

        {mode === "url" && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Fetch a YAML configuration from a URL — e.g. a raw GitHub Gist.
            </p>
            <div className="space-y-1.5">
              <Label className="text-xs">URL</Label>
              <div className="flex gap-2">
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://gist.githubusercontent.com/..."
                  className="h-8"
                  onKeyDown={(e) => e.key === "Enter" && handleUrlImport()}
                />
                <Button size="sm" disabled={!url || isPending} onClick={handleUrlImport}>
                  {isPending
                    ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    : <Link2 className="mr-1.5 h-3.5 w-3.5" />}
                  Fetch
                </Button>
              </div>
            </div>
          </div>
        )}

        {mode === "yaml" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-xs font-medium">Upload file</p>
              <div className="flex items-center gap-2">
                <Input
                  ref={yamlFileRef}
                  type="file"
                  accept=".yaml,.yml"
                  className="h-8"
                />
                <Button size="sm" onClick={handleYamlFileUpload} disabled={isPending}>
                  {isPending
                    ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    : <Upload className="mr-1.5 h-3.5 w-3.5" />}
                  Upload
                </Button>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-background px-2 text-xs text-muted-foreground">or paste</span>
              </div>
            </div>

            <div className="space-y-2">
              <Textarea
                value={paste}
                onChange={(e) => setPaste(e.target.value)}
                placeholder={"metadata:\n  name: my_benchmark\n  ..."}
                className="min-h-[120px] font-mono text-xs"
              />
              <div className="flex justify-end">
                <Button size="sm" onClick={handlePasteImport} disabled={!paste.trim() || isPending}>
                  {isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                  Use this config
                </Button>
              </div>
            </div>
          </div>
        )}

        {mode === "gz" && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Upload an existing <code className="text-[11px]">.json.gz</code> test set file — skips generation entirely.
            </p>
            <div className="flex items-center gap-2">
              <Input ref={gzFileRef} type="file" accept=".gz" className="h-8" />
              <Button size="sm" onClick={handleGzUpload} disabled={isPending}>
                {isPending
                  ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  : <Upload className="mr-1.5 h-3.5 w-3.5" />}
                Upload
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
