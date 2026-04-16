import { useEffect, useLayoutEffect, useState } from "react"
import { Loader2, Pin, PinOff, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useTranslation } from "@/hooks/use-review"
import { languageLabel } from "@/components/language-filter-chip"
import type { TranslateChunk } from "./translate-chunks"

interface BarPosition {
  top: number
  height: number
}

interface ChunkGutterProps {
  chunks: TranslateChunk[]
  /** Ref to the scroll container that holds the response text (and this gutter). */
  containerRef: React.RefObject<HTMLDivElement | null>
  /** Array of refs (one per chunk) pointing at the chunk's wrapper span in the
   *  rendered response text. Used to measure each chunk's visual range. */
  chunkElementRefs: React.RefObject<(HTMLSpanElement | null)[]>
  sourceLang: string
  targetLang: string
}

/**
 * Left-edge gutter of vertical bars, one per translation chunk. Hovering a bar
 * opens a popover with that chunk's translation; clicking pins it open until
 * another bar is clicked (or the same bar is clicked again to unpin).
 *
 * The gutter sits *inside* the scroll container as an absolutely-positioned
 * column, so bars scroll in sync with their chunks.
 */
export function ChunkGutter({
  chunks,
  containerRef,
  chunkElementRefs,
  sourceLang,
  targetLang,
}: ChunkGutterProps) {
  const [positions, setPositions] = useState<BarPosition[]>([])
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [pinnedIdx, setPinnedIdx] = useState<number | null>(null)

  // Measure chunk positions relative to the scroll container. Re-runs on
  // chunk changes (case switch) + resize. offsetTop walks up through
  // `position: relative` ancestors; we rely on the response container being
  // relatively-positioned (set via `relative` class at the call site).
  useLayoutEffect(() => {
    const measure = () => {
      const container = containerRef.current
      if (!container) return
      const containerRect = container.getBoundingClientRect()
      const elems = chunkElementRefs.current ?? []
      const next: BarPosition[] = chunks.map((_, i) => {
        const el = elems[i]
        if (!el) return { top: 0, height: 0 }
        const rect = el.getBoundingClientRect()
        return {
          top: rect.top - containerRect.top + container.scrollTop,
          height: Math.max(rect.height, 12),
        }
      })
      setPositions(next)
    }
    measure()
    window.addEventListener("resize", measure)
    return () => window.removeEventListener("resize", measure)
    // Re-measure whenever the chunk set changes — a case switch rebuilds the
    // chunks prop with new offsets.
  }, [chunks, containerRef, chunkElementRefs])

  // Unpin when the chunk set changes (new case). Pin should be local to the
  // case the annotator was working on.
  useEffect(() => {
    setPinnedIdx(null)
    setHoveredIdx(null)
  }, [chunks])

  if (chunks.length === 0) return null

  return (
    <div
      className="pointer-events-none absolute left-0 top-0 z-20 h-full w-4 select-none"
      aria-hidden="false"
    >
      {chunks.map((chunk, i) => {
        const pos = positions[i]
        if (!pos || pos.height === 0) return null
        const active = hoveredIdx === i || pinnedIdx === i
        const pinned = pinnedIdx === i
        return (
          <ChunkBar
            key={`${chunk.start}-${chunk.end}`}
            chunk={chunk}
            top={pos.top}
            height={pos.height}
            active={active}
            pinned={pinned}
            sourceLang={sourceLang}
            targetLang={targetLang}
            onHover={(enter) => setHoveredIdx(enter ? i : (prev) => (prev === i ? null : prev))}
            onClickPin={() => {
              setPinnedIdx((prev) => (prev === i ? null : i))
            }}
          />
        )
      })}
    </div>
  )
}

interface ChunkBarProps {
  chunk: TranslateChunk
  top: number
  height: number
  active: boolean
  pinned: boolean
  sourceLang: string
  targetLang: string
  onHover: (enter: boolean) => void
  onClickPin: () => void
}

function ChunkBar({
  chunk,
  top,
  height,
  active,
  pinned,
  sourceLang,
  targetLang,
  onHover,
  onClickPin,
}: ChunkBarProps) {
  // Only fetch when the annotator actually peeks. React Query caches by
  // `[text, source, target]` so re-hovering is instant and chunks shared
  // across cases (rare but possible) dedupe automatically.
  const query = useTranslation(chunk.text, sourceLang || null, targetLang, active)

  return (
    <Popover open={active} onOpenChange={(open) => { if (!open && !pinned) onHover(false) }} modal={false}>
      <PopoverTrigger asChild>
        <button
          type="button"
          onMouseEnter={() => onHover(true)}
          onMouseLeave={() => { if (!pinned) onHover(false) }}
          onClick={(e) => {
            e.stopPropagation()
            onClickPin()
          }}
          style={{ top, height }}
          className={`pointer-events-auto absolute left-1 w-1.5 rounded-full transition-colors ${
            pinned
              ? "bg-sky-500 ring-2 ring-sky-300/50"
              : active
                ? "bg-sky-400"
                : "bg-border hover:bg-sky-300"
          }`}
          // Deliberately no `title` — the native tooltip floats near the mouse
          // and overlaps the translation popover. `aria-label` keeps the bar
          // discoverable for assistive tech without the visual collision.
          aria-label={pinned ? "Unpin translation" : "Peek translation · click to pin"}
        />
      </PopoverTrigger>
      <PopoverContent
        side="right"
        align="start"
        sideOffset={8}
        className="w-80 select-none p-3"
        onOpenAutoFocus={(e) => e.preventDefault()}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <div className="mb-1.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className="font-medium uppercase tracking-wider">
            Translation · {languageLabel((targetLang || "en").toLowerCase())}
          </span>
          {query.data?.provider && (
            <span className="opacity-70">via {query.data.provider}</span>
          )}
          <div className="ml-auto flex items-center gap-0.5">
            {query.isError && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => query.refetch()}
                className="h-5 w-5 text-muted-foreground"
                title="Retry translation"
              >
                <RefreshCw className="h-3 w-3" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onClickPin}
              className={`h-5 w-5 ${pinned ? "text-sky-500" : "text-muted-foreground"}`}
              title={pinned ? "Unpin" : "Pin open"}
            >
              {pinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
            </Button>
          </div>
        </div>

        {query.isLoading && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Translating…
          </div>
        )}
        {query.isError && (
          <div className="text-xs text-rose-600">
            Translation unavailable.{" "}
            <span className="text-muted-foreground">
              {query.error instanceof Error ? query.error.message : "Unknown error"}
            </span>
          </div>
        )}
        {query.data && (
          <div className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground">
            {query.data.translated}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
