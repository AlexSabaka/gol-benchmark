import { useState } from "react"
import { Plus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface Props {
  note: string
  onChangeNote: (next: string) => void
}

/**
 * Collapsible annotator-note editor. Split out of the removed `annotation-dock`
 * in Phase 1 so notes survive without re-introducing the pending-span round-
 * trip. Collapsed by default when empty; auto-expands when a note is present.
 */
export function NotePanel({ note, onChangeNote }: Props) {
  const [open, setOpen] = useState(note.trim().length > 0)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
      >
        <Plus className="h-3 w-3" />
        Add note
      </button>
    )
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Note
        </label>
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 text-muted-foreground"
          onClick={() => {
            onChangeNote("")
            setOpen(false)
          }}
          title="Discard note"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
      <Textarea
        value={note}
        onChange={(e) => onChangeNote(e.target.value)}
        placeholder="Optional context for this annotation…"
        className="min-h-[44px] text-sm"
      />
    </div>
  )
}
