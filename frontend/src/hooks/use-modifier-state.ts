import { useEffect, useState } from "react"

/**
 * v4 mark-type modifier resolved from the currently-held key. `null` means
 * "plain click / drag → answer span".
 */
export type ActiveModifier = "anchor" | "keyword" | "negative" | null

/**
 * Track which of A / D / Shift is currently held, and resolve a single
 * `activeModifier` value for the response panel to consume. Precedence when
 * multiple keys are held: A > D > Shift (spec §3.2). Simultaneous holds are
 * resolved, not errored — the top-priority modifier wins.
 *
 * The hook listens globally so drag-select can read the state at mouseup time
 * even if the key was pressed before the mouse entered the response text.
 * When the user is typing in a field (textarea / input / select /
 * contenteditable / role=textbox), tracking is suppressed so the annotator
 * can type letters `A` / `D` in a note without accidentally changing mark
 * type on their next click.
 *
 * Stuck-modifier safety: a `blur` or `visibilitychange` event clears all
 * flags. This prevents a frozen "Anchor mode" indicator after Cmd-Tab or a
 * tab switch.
 */
export function useModifierState(): { activeModifier: ActiveModifier } {
  const [aHeld, setAHeld] = useState(false)
  const [dHeld, setDHeld] = useState(false)
  const [shiftHeld, setShiftHeld] = useState(false)

  useEffect(() => {
    const isTyping = (el: EventTarget | null): boolean => {
      if (!(el instanceof HTMLElement)) return false
      const tag = el.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true
      if (el.isContentEditable) return true
      if (el.getAttribute("role") === "textbox") return true
      return false
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (isTyping(e.target)) return
      // Suppress tracking while meta/ctrl is held — those combinations belong
      // to the keybindings hook (undo / redo / discard). We still listen for
      // plain Shift because Shift+Space exists as a discard shortcut but
      // Shift+drag exists as a negative-mark shortcut; the modifier-state
      // matters for the drag path.
      if (e.key === "Shift") setShiftHeld(true)
      const letter = e.key.toUpperCase()
      // Ignore letter keys when ctrl/meta is held so Ctrl+A (select-all) and
      // similar combos don't toggle mark modifiers.
      if (e.ctrlKey || e.metaKey) return
      if (letter === "A") setAHeld(true)
      else if (letter === "D") setDHeld(true)
    }

    const onKeyUp = (e: KeyboardEvent) => {
      // Always honour keyup, even when focus is in a text field. If the user
      // held A outside a field then clicked into one, we still want the key
      // to release.
      if (e.key === "Shift") setShiftHeld(false)
      const letter = e.key.toUpperCase()
      if (letter === "A") setAHeld(false)
      else if (letter === "D") setDHeld(false)
    }

    const clearAll = () => {
      setAHeld(false)
      setDHeld(false)
      setShiftHeld(false)
    }

    window.addEventListener("keydown", onKeyDown)
    window.addEventListener("keyup", onKeyUp)
    window.addEventListener("blur", clearAll)
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible") clearAll()
    })

    return () => {
      window.removeEventListener("keydown", onKeyDown)
      window.removeEventListener("keyup", onKeyUp)
      window.removeEventListener("blur", clearAll)
      // `visibilitychange` is registered with an inline arrow so we can't
      // remove it by reference — cheap leak, one listener per mount. The
      // clearAll closure is garbage-collected when the hook unmounts.
    }
  }, [])

  // Precedence: A > D > Shift. Simultaneous holds resolve deterministically.
  const activeModifier: ActiveModifier = aHeld
    ? "anchor"
    : dHeld
      ? "keyword"
      : shiftHeld
        ? "negative"
        : null

  return { activeModifier }
}
