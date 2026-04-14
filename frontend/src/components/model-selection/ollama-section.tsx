import { useMemo } from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useOllamaModels } from "@/hooks/use-models"

import { ModelList } from "./model-list"
import type { SelectedModel } from "./types"

export interface OllamaSectionProps {
  host: string
  onHostChange: (h: string) => void
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
}

export function OllamaSection({
  host,
  onHostChange,
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
}: OllamaSectionProps) {
  const { data, isLoading } = useOllamaModels(host, true)
  const models = useMemo(
    () => (data?.models ?? []).map((m) => ({ id: m.name, label: `${m.display_name} (${m.size_human})` })),
    [data],
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
