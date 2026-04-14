import { useMemo, useState } from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useHFModels } from "@/hooks/use-models"

import { ModelList } from "./model-list"
import type { SelectedModel } from "./types"

export interface HuggingFaceSectionProps {
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
}

export function HuggingFaceSection({
  selected,
  onToggle,
  favorites,
  onToggleFavorite,
  searchTerm,
}: HuggingFaceSectionProps) {
  const [hfQuery, setHfQuery] = useState("")
  const [hfApiKey, setHfApiKey] = useState("")
  const { data, isLoading } = useHFModels(hfQuery, hfApiKey || undefined, hfQuery.length >= 2)
  const models = useMemo(
    () =>
      (data?.models ?? []).map((m) => ({
        id: m.id,
        label: `${m.display_name} (${m.likes} likes, ${m.pipeline_tag || "unknown"})`,
      })),
    [data],
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
        <p className="text-xs text-muted-foreground py-2">
          Type at least 2 characters to search HuggingFace Hub
        </p>
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
