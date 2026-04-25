import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Generic per-case undo/redo over a single value. Snapshot-based — cheap
 * because `T` is small (a draft annotation dict; spans are char offsets, not
 * the raw text). Snapshots are deep-copied via structuredClone so callers
 * don't need to worry about shared references.
 *
 * Semantics (Phase 1, spec §3.5):
 *   - `push(snapshot)`: record the *previous* value before it's mutated.
 *     Clears the redo stack (standard command-stack discipline).
 *   - `undo()`: restores the most recent snapshot and pushes the current
 *     value onto the redo stack.
 *   - `redo()`: inverse of undo.
 *   - `reset()`: clears both stacks. Called when the active case changes
 *     so undo never crosses case boundaries.
 *   - Bounded history (`maxDepth`, default 10). Older entries are dropped
 *     off the bottom when the stack overflows.
 */
export interface UndoStack<T> {
  push: (snapshot: T) => void
  undo: () => void
  redo: () => void
  reset: () => void
  canUndo: boolean
  canRedo: boolean
}

function clone<T>(value: T): T {
  if (typeof structuredClone === "function") return structuredClone(value)
  return JSON.parse(JSON.stringify(value))
}

export function useUndoStack<T>(
  current: T,
  onRestore: (snapshot: T) => void,
  maxDepth = 10,
): UndoStack<T> {
  // Stacks held in state so `canUndo` / `canRedo` stay reactive without a
  // manual re-render bump. Snapshots are immutable once pushed (clone on
  // entry), so the arrays themselves are swapped on every push/undo/redo.
  const [undoStack, setUndoStack] = useState<T[]>([])
  const [redoStack, setRedoStack] = useState<T[]>([])

  // Mirror the live value into a ref so `undo` / `redo` can snapshot the
  // current draft without the caller threading it through. Updated in an
  // effect to stay within the React-Compiler rules (no ref writes during
  // render).
  const currentRef = useRef<T>(current)
  useEffect(() => {
    currentRef.current = current
  }, [current])

  const push = useCallback(
    (snapshot: T) => {
      const snap = clone(snapshot)
      setUndoStack((prev) => {
        const next = prev.length >= maxDepth ? prev.slice(prev.length - maxDepth + 1) : prev.slice()
        next.push(snap)
        return next
      })
      setRedoStack((prev) => (prev.length === 0 ? prev : []))
    },
    [maxDepth],
  )

  const undo = useCallback(() => {
    setUndoStack((prev) => {
      if (prev.length === 0) return prev
      const next = prev.slice(0, -1)
      const restored = prev[prev.length - 1]
      setRedoStack((r) => [...r, clone(currentRef.current)])
      onRestore(restored)
      return next
    })
  }, [onRestore])

  const redo = useCallback(() => {
    setRedoStack((prev) => {
      if (prev.length === 0) return prev
      const next = prev.slice(0, -1)
      const restored = prev[prev.length - 1]
      setUndoStack((u) => [...u, clone(currentRef.current)])
      onRestore(restored)
      return next
    })
  }, [onRestore])

  const reset = useCallback(() => {
    setUndoStack((prev) => (prev.length === 0 ? prev : []))
    setRedoStack((prev) => (prev.length === 0 ? prev : []))
  }, [])

  return {
    push,
    undo,
    redo,
    reset,
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
  }
}
