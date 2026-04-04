import { useCallback } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Check, ListFilter } from "lucide-react"

interface FilterGroupProps {
  label: string
  options: string[]
  selected: Set<string>
  onChange: (next: Set<string>) => void
}

function FilterGroup({ label, options, selected, onChange }: FilterGroupProps) {
  const toggle = useCallback(
    (value: string) => {
      const next = new Set(selected)
      if (next.has(value)) next.delete(value)
      else next.add(value)
      onChange(next)
    },
    [selected, onChange]
  )

  if (options.length === 0) return null

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-7 gap-1 text-xs">
          <ListFilter className="h-3 w-3" />
          {label}
          {selected.size > 0 && (
            <Badge variant="secondary" className="ml-1 h-4 min-w-4 px-1 text-[10px]">
              {selected.size}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-52 p-2" align="start">
        <div className="space-y-0.5 max-h-56 overflow-y-auto">
          {options.map((opt) => {
            const active = selected.has(opt)
            return (
              <button
                key={opt}
                onClick={() => toggle(opt)}
                className="flex w-full items-center gap-2 rounded px-2 py-1 text-xs hover:bg-accent transition-colors"
              >
                <div
                  className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm border ${
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-muted-foreground/30"
                  }`}
                >
                  {active && <Check className="h-2.5 w-2.5" />}
                </div>
                <span className="truncate">
                  {opt.replace(/_/g, " ")}
                </span>
              </button>
            )
          })}
        </div>
        {selected.size > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-1 w-full h-6 text-xs"
            onClick={() => onChange(new Set())}
          >
            Clear filter
          </Button>
        )}
      </PopoverContent>
    </Popover>
  )
}

interface ChartFiltersProps {
  availableTaskTypes: string[]
  availableLanguages: string[]
  selectedTaskTypes: Set<string>
  selectedLanguages: Set<string>
  onTaskTypesChange: (next: Set<string>) => void
  onLanguagesChange: (next: Set<string>) => void
}

export function ChartFilters({
  availableTaskTypes,
  availableLanguages,
  selectedTaskTypes,
  selectedLanguages,
  onTaskTypesChange,
  onLanguagesChange,
}: ChartFiltersProps) {
  return (
    <div className="flex items-center gap-2">
      <FilterGroup
        label="Task Type"
        options={availableTaskTypes}
        selected={selectedTaskTypes}
        onChange={onTaskTypesChange}
      />
      {availableLanguages.length > 1 && (
        <FilterGroup
          label="Language"
          options={availableLanguages}
          selected={selectedLanguages}
          onChange={onLanguagesChange}
        />
      )}
    </div>
  )
}
