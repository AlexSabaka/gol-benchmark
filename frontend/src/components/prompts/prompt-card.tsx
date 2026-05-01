import { Link } from "react-router"

import { Badge } from "@/components/ui/badge"
import { LanguageDots } from "@/components/prompts/language-dots"
import { cn } from "@/lib/utils"
import type { PromptSummary } from "@/types"

interface Props {
  prompt: PromptSummary
}

/**
 * Catalog card. Inset-left ribbon (BUILT-IN / ARCHIVED) instead of a corner
 * badge; hairline rule between header and description; coverage dots + version
 * chip in the footer. The whole card is the click target.
 */
export function PromptCard({ prompt }: Props) {
  const isArchived = Boolean(prompt.archived_at)
  return (
    <Link
      to={`/prompts/${prompt.id}`}
      className={cn(
        "group relative flex flex-col rounded-xl border bg-card p-5 shadow-sm",
        "transition-all hover:bg-muted/40 hover:shadow-md",
        isArchived && "opacity-70",
      )}
    >
      {/* Inset ribbon */}
      {prompt.is_builtin && !isArchived && (
        <span
          className={cn(
            "absolute inset-y-3 left-0 w-[3px] rounded-r-sm",
            "bg-foreground/40 transition-colors group-hover:bg-foreground/65",
          )}
          aria-hidden="true"
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {prompt.is_builtin && !isArchived && (
            <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/85">
              Built-in
            </span>
          )}
          {isArchived && (
            <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700 dark:text-amber-400">
              Archived
            </span>
          )}
          <h3 className="truncate text-base font-semibold tracking-tight">
            {prompt.name}
          </h3>
          <p className="truncate font-mono text-xs text-muted-foreground">
            {prompt.slug}
          </p>
        </div>
      </div>

      {/* Hairline */}
      <div className="my-3 h-px bg-border/60" />

      {/* Description */}
      <p
        className={cn(
          "text-sm text-muted-foreground",
          "line-clamp-2 min-h-[2.5rem]",
        )}
      >
        {prompt.description || (
          <span className="italic text-muted-foreground/60">No description.</span>
        )}
      </p>

      {/* Tags row (if any) */}
      {prompt.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {prompt.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
            >
              {tag}
            </span>
          ))}
          {prompt.tags.length > 3 && (
            <span className="text-[10px] text-muted-foreground/70">
              +{prompt.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-auto flex items-center justify-between gap-2 pt-4">
        <LanguageDots present={prompt.language_codes} />
        {prompt.latest_version != null && (
          <Badge
            variant="outline"
            className="font-mono text-[10px] tracking-wider"
          >
            v{prompt.latest_version}
          </Badge>
        )}
      </div>
    </Link>
  )
}
