import { useMemo } from "react"
import { Loader2, Star } from "lucide-react"

import { Checkbox } from "@/components/ui/checkbox"
import { favoriteKey } from "@/lib/favorite-models"

import { selectedModelKey, type SelectedModel } from "./types"

export interface ModelListProps {
  models: { id: string; label: string }[]
  isLoading: boolean
  provider: SelectedModel["provider"]
  selected: Map<string, SelectedModel>
  onToggle: (m: SelectedModel) => void
  favorites: Set<string>
  onToggleFavorite: (fKey: string) => void
  searchTerm: string
  extraCtx?: { apiBase?: string; apiKey?: string; ollamaHost?: string }
}

export function ModelList({
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
