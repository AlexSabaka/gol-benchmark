import { useState, type KeyboardEvent } from "react"
import { X } from "lucide-react"

import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface Props {
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  maxTags?: number
  className?: string
}

const MAX_TAG_LEN = 64

/**
 * Chip-input. Comma or Enter commits a tag; Backspace on empty removes the last.
 * Caps at `maxTags`. Strips leading/trailing whitespace; rejects duplicates.
 */
export function TagInput({
  value,
  onChange,
  placeholder = "Add tag…",
  maxTags = 32,
  className,
}: Props) {
  const [draft, setDraft] = useState("")

  const commit = (raw: string) => {
    const tag = raw.trim()
    if (!tag) return
    if (tag.length > MAX_TAG_LEN) return
    if (value.includes(tag)) return
    if (value.length >= maxTags) return
    onChange([...value, tag])
    setDraft("")
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      commit(draft)
    } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const removeAt = (i: number) => onChange(value.filter((_, j) => j !== i))

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5",
        "focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50",
        className,
      )}
    >
      {value.map((tag, i) => (
        <span
          key={`${tag}-${i}`}
          className="inline-flex items-center gap-1 rounded-sm bg-muted px-2 py-0.5 text-xs font-medium text-foreground"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeAt(i)}
            className="rounded-sm text-muted-foreground hover:text-foreground"
            aria-label={`Remove ${tag}`}
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => commit(draft)}
        placeholder={value.length === 0 ? placeholder : ""}
        className="h-6 w-32 min-w-0 flex-1 border-0 bg-transparent px-1 py-0 text-sm shadow-none focus-visible:ring-0"
      />
    </div>
  )
}
