import { useEffect } from "react"

/**
 * Keyboard-handler contract for the /review workspace.
 *
 * v4 (Phase 1) — hand-ergonomics-first layout:
 *   - Plain drag-select commits immediately (no modifier).
 *   - Hold A/D/Shift to alter the mark type at drag-commit time
 *     (see `useModifierState`, Checkpoint C).
 *   - Q/E/F letter shortcuts (left-hand WASD cluster) + 1–5 number
 *     shortcuts both toggle classifications, so the annotator can
 *     stay on letters during a drag-heavy run without jumping to
 *     the number row.
 *   - Space does the two actions the annotator needs 95% of the
 *     time: if the draft has content, save + advance; otherwise
 *     advance (skip-equivalent). Ctrl/Meta+Space is the deliberate
 *     “discard the draft” escape hatch — pinky-friction prevents
 *     accidental data loss.
 *   - Ctrl/Meta+Z / Ctrl/Meta+Shift+Z drive the per-case undo stack
 *     (populated in Checkpoint D; pass no-ops until then).
 *   - `?` toggles the help dialog.
 *
 * Removed vs v3: `S` (skip) and `ArrowRight` (advance). Space covers
 * both and frees up the right-hand pinky for navigation (ArrowLeft)
 * and modifier combinations.
 */
export interface ReviewKeybindings {
  /** Toggle a class by its canonical key ("2"–"5"). */
  onClassifyByKey: (key: string) => void
  /** Toggle a class by its letter shortcut ("Q"/"E"/"F"). */
  onClassifyByLetter: (letter: "Q" | "E" | "F") => void
  /** Space — save and advance (or skip+advance if the draft is empty). */
  onSpace: () => void
  /** Ctrl/Meta+Space — discard the active draft and advance. */
  onCtrlSpace: () => void
  /** ArrowLeft — navigate to the previous case (saves dirty draft first). */
  onPrev: () => void
  /** Ctrl/Meta+Z — undo the last draft edit in the current case. */
  onUndo: () => void
  /** Ctrl/Meta+Shift+Z — redo the last undone edit. */
  onRedo: () => void
  /** `?` — toggle the help dialog. */
  onToggleHelp: () => void
}

/**
 * Returns true iff the event's target is a text-editing surface, in which
 * case shortcuts should be suppressed (the user is typing, not annotating).
 * Also covers Radix/headless widgets that implement `role="textbox"`.
 */
function isTypingInField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true
  if (target.isContentEditable) return true
  if (target.getAttribute("role") === "textbox") return true
  return false
}

export function useReviewKeybindings(handlers: ReviewKeybindings): void {
  const {
    onClassifyByKey,
    onClassifyByLetter,
    onSpace,
    onCtrlSpace,
    onPrev,
    onUndo,
    onRedo,
    onToggleHelp,
  } = handlers

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingInField(e.target)) return

      const ctrl = e.ctrlKey || e.metaKey

      // Undo / redo — checked before plain-letter handlers so Ctrl+Z doesn't
      // fall through to any single-letter matcher that might be added later.
      if (ctrl && e.key.toLowerCase() === "z") {
        e.preventDefault()
        if (e.shiftKey) onRedo()
        else onUndo()
        return
      }

      // Space semantics: plain → save/skip advance, Ctrl/Meta → reject.
      if (e.key === " ") {
        e.preventDefault()
        if (ctrl) onCtrlSpace()
        else onSpace()
        return
      }

      // Navigation: ArrowLeft only. ArrowRight is gone — Space replaces it.
      if (e.key === "ArrowLeft") {
        e.preventDefault()
        onPrev()
        return
      }

      // Classification by numeric key (kept for muscle-memory compat).
      if (/^[1-5]$/.test(e.key)) {
        e.preventDefault()
        onClassifyByKey(e.key)
        return
      }

      // Classification by WASD-cluster letter. Uppercase the comparison so
      // capslock / shift-held doesn't defeat the shortcut.
      const letter = e.key.toUpperCase()
      if (letter === "Q" || letter === "E" || letter === "F") {
        e.preventDefault()
        onClassifyByLetter(letter)
        return
      }

      if (e.key === "?") {
        e.preventDefault()
        onToggleHelp()
        return
      }
    }

    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [
    onClassifyByKey,
    onClassifyByLetter,
    onSpace,
    onCtrlSpace,
    onPrev,
    onUndo,
    onRedo,
    onToggleHelp,
  ])
}
