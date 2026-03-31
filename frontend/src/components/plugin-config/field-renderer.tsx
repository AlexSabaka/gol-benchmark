import type { ConfigField } from "@/types"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { HelpCircle } from "lucide-react"

interface Props {
  field: ConfigField
  value: unknown
  onChange: (name: string, value: unknown) => void
}

export function FieldRenderer({ field, value, onChange }: Props) {
  const { name, label, type: field_type, help } = field

  const helpIcon = help ? (
    <Tooltip>
      <TooltipTrigger asChild>
        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground inline ml-1 cursor-help" />
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{help}</TooltipContent>
    </Tooltip>
  ) : null

  switch (field_type) {
    case "number":
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <Input
            type="number"
            value={value != null ? String(value) : field.default != null ? String(field.default) : ""}
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
            className="h-8 w-28"
            onChange={(e) => onChange(name, e.target.value === "" ? null : Number(e.target.value))}
          />
        </div>
      )

    case "select":
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <Select
            value={String(value ?? field.default ?? "")}
            onValueChange={(v) => onChange(name, v)}
          >
            <SelectTrigger className="h-8 w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(field.options ?? []).map((opt) => (
                <SelectItem key={String(opt)} value={String(opt)}>
                  {String(opt) || "(none)"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )

    case "multi-select": {
      const selected = (value as (string | number)[]) ?? (field.default as (string | number)[]) ?? []
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <div className="flex flex-wrap gap-2">
            {(field.options ?? []).map((opt) => {
              const checked = selected.includes(opt)
              return (
                <label key={String(opt)} className="flex items-center gap-1.5 text-xs cursor-pointer">
                  <Checkbox
                    checked={checked}
                    onCheckedChange={(c) => {
                      const next = c
                        ? [...selected, opt]
                        : selected.filter((v) => v !== opt)
                      onChange(name, next)
                    }}
                  />
                  {String(opt)}
                </label>
              )
            })}
          </div>
        </div>
      )
    }

    case "text":
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <Input
            value={(value as string) ?? (field.default as string) ?? ""}
            className="h-8 w-64"
            onChange={(e) => onChange(name, e.target.value)}
          />
        </div>
      )

    case "boolean":
      return (
        <div className="flex items-center gap-2 pt-5">
          <Checkbox
            id={`field-${name}`}
            checked={(value as boolean) ?? (field.default as boolean) ?? false}
            onCheckedChange={(c) => onChange(name, !!c)}
          />
          <Label htmlFor={`field-${name}`} className="text-xs cursor-pointer">
            {label}{helpIcon}
          </Label>
        </div>
      )

    case "range": {
      const rv = (value as [number, number]) ?? [
        field.range_min_default ?? field.min ?? 0,
        field.range_max_default ?? field.max ?? 100,
      ]
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              value={rv[0]}
              min={field.min}
              max={field.max}
              step={field.step ?? 1}
              className="h-8 w-24"
              onChange={(e) => onChange(name, [Number(e.target.value), rv[1]])}
            />
            <span className="text-xs text-muted-foreground">to</span>
            <Input
              type="number"
              value={rv[1]}
              min={field.min}
              max={field.max}
              step={field.step ?? 1}
              className="h-8 w-24"
              onChange={(e) => onChange(name, [rv[0], Number(e.target.value)])}
            />
          </div>
        </div>
      )
    }

    case "weight_map": {
      const keys = field.weight_keys ?? Object.keys((field.default as Record<string, number>) ?? {})
      const wv = (value as Record<string, number>) ?? (field.default as Record<string, number>) ?? {}
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">{label}{helpIcon}</Label>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {keys.map((k) => (
              <div key={k} className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground w-24 truncate">{k}</span>
                <Input
                  type="number"
                  value={wv[k] ?? 1}
                  step={0.1}
                  min={0}
                  className="h-7 w-20"
                  onChange={(e) => onChange(name, { ...wv, [k]: Number(e.target.value) })}
                />
              </div>
            ))}
          </div>
        </div>
      )
    }

    default:
      return null
  }
}
