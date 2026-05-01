import { useState } from "react"
import { Check, Copy, ScrollText } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface Props {
  text: string
  /** Show a "falls back to English" banner above when the requested lang is empty. */
  fallbackToEnglish?: boolean
  className?: string
}

/**
 * Read-only typeset reading column. Monospace, generous line-height, capped at
 * ~68ch. Toggleable raw mode disables soft-wrap for inspecting long lines.
 */
export function PromptContent({ text, fallbackToEnglish, className }: Props) {
  const [raw, setRaw] = useState(false)
  const [copied, setCopied] = useState(false)
  const isEmpty = text.trim().length === 0

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success("Copied to clipboard")
      setTimeout(() => setCopied(false), 1400)
    } catch {
      toast.error("Failed to copy")
    }
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {fallbackToEnglish && (
        <p className="text-xs text-muted-foreground">
          This language has no content on this version.{" "}
          <span className="text-foreground/80">Showing English fallback.</span>
        </p>
      )}
      <div className="flex items-center justify-end gap-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => setRaw((r) => !r)}
              aria-pressed={raw}
              aria-label={raw ? "Soft-wrap" : "Show raw (no wrap)"}
            >
              <ScrollText className="size-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <span className="text-xs">{raw ? "Soft-wrap" : "Raw view"}</span>
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onCopy}
              aria-label="Copy to clipboard"
              disabled={isEmpty}
            >
              {copied ? (
                <Check className="size-3.5 text-emerald-600" />
              ) : (
                <Copy className="size-3.5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <span className="text-xs">Copy</span>
          </TooltipContent>
        </Tooltip>
      </div>
      <div
        className={cn(
          "rounded-md border border-border/60 bg-muted/30 p-6",
          "font-mono text-sm leading-7 text-foreground",
          raw
            ? "overflow-x-auto whitespace-pre"
            : "whitespace-pre-wrap break-words",
          "max-w-[68ch]",
        )}
      >
        {isEmpty ? (
          <span className="italic text-muted-foreground/60">
            (no content for this language)
          </span>
        ) : (
          text
        )}
      </div>
    </div>
  )
}
