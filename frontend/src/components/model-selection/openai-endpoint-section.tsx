import { useCallback, useMemo } from "react"
import { toast } from "sonner"
import { Save, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useOpenAIModels } from "@/hooks/use-models"
import { saveCredential } from "@/lib/credential-store"

import { ModelList } from "./model-list"
import type { OpenAIEndpoint, SelectedModel } from "./types"

export interface OpenAIEndpointSectionProps {
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
}

export function OpenAIEndpointSection({
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
}: OpenAIEndpointSectionProps) {
  const { data, isLoading } = useOpenAIModels(endpoint.apiBase, endpoint.apiKey, !!endpoint.apiBase)
  const models = useMemo(
    () => (data?.models ?? []).map((m) => ({ id: m.name, label: m.display_name })),
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
