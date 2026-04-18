import { Check, PlusCircle, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface PageFacetFilterProps {
  title: string
  options: { label: string; value: string }[]
  selectedValues: string[]
  onChange: (values: string[]) => void
}

export function PageFacetFilter({ title, options, selectedValues, onChange }: PageFacetFilterProps) {
  const selected = new Set(selectedValues)
  const isActive = selected.size > 0

  const activeLabel = selected.size === 1
    ? (options.find((o) => selected.has(o.value))?.label ?? "")
    : `${selected.size} selected`

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={isActive ? "secondary" : "outline"}
          size="sm"
          className={cn(
            "h-8 gap-1 text-xs font-medium",
            !isActive && "border-dashed text-muted-foreground hover:text-foreground",
            isActive && "pr-1.5",
          )}
        >
          {!isActive && <PlusCircle className="h-3.5 w-3.5" />}
          {title}
          {isActive && (
            <>
              <span className="text-muted-foreground">:</span>
              <span className="max-w-28 truncate">{activeLabel}</span>
              <span
                role="button"
                aria-label={`Clear ${title} filter`}
                className="ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm hover:bg-foreground/10"
                onClick={(e) => { e.stopPropagation(); onChange([]) }}
              >
                <X className="h-3 w-3" />
              </span>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-55 p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selected.has(option.value)
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => {
                      const next = new Set(selected)
                      if (isSelected) {
                        next.delete(option.value)
                      } else {
                        next.add(option.value)
                      }
                      onChange(Array.from(next))
                    }}
                  >
                    <div
                      className={cn(
                        "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected ? "bg-primary text-primary-foreground" : "opacity-50 [&_svg]:invisible",
                      )}
                    >
                      <Check className="h-4 w-4" />
                    </div>
                    <span>{option.label}</span>
                  </CommandItem>
                )
              })}
            </CommandGroup>
            {selected.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem onSelect={() => onChange([])} className="justify-center text-center">
                    Clear filters
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
