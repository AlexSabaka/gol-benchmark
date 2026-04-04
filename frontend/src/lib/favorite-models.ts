/**
 * localStorage-backed favorite models store.
 * Namespaced by provider to avoid collisions.
 */

const STORAGE_KEY = "gol-favorite-models"

function readStore(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return new Set()
    return new Set(JSON.parse(raw) as string[])
  } catch {
    return new Set()
  }
}

function writeStore(favorites: Set<string>): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites]))
}

/** Build a namespaced key: "ollama:llama3:8b" */
export function favoriteKey(provider: string, modelId: string): string {
  return `${provider}:${modelId}`
}

export function getFavorites(): Set<string> {
  return readStore()
}

export function toggleFavorite(key: string): Set<string> {
  const fav = readStore()
  if (fav.has(key)) fav.delete(key)
  else fav.add(key)
  writeStore(fav)
  return fav
}

export function isFavorite(key: string): boolean {
  return readStore().has(key)
}
