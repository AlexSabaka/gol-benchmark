import { useQuery } from "@tanstack/react-query"
import { fetchPluginSchema } from "@/api/plugins"
import { FieldRenderer } from "./field-renderer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown } from "lucide-react"
import { useState } from "react"

interface Props {
  taskType: string
  values: Record<string, unknown>
  onChange: (taskType: string, name: string, value: unknown) => void
}

export function ConfigForm({ taskType, values, onChange }: Props) {
  const { data: schema, isLoading } = useQuery({
    queryKey: ["plugin-schema", taskType],
    queryFn: () => fetchPluginSchema(taskType),
    staleTime: Infinity,
  })
  const [advOpen, setAdvOpen] = useState(false)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="h-4 w-48 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const fields = schema?.fields ?? []
  const basic = fields.filter((f) => !f.group || f.group === "basic")
  const advanced = fields.filter((f) => f.group === "advanced")

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm capitalize">
          {taskType.replace(/_/g, " ")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Basic fields */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {basic.map((f) => (
            <FieldRenderer
              key={f.name}
              field={f}
              value={values[f.name]}
              onChange={(name, val) => onChange(taskType, name, val)}
            />
          ))}
        </div>

        {/* Advanced fields */}
        {advanced.length > 0 && (
          <Collapsible open={advOpen} onOpenChange={setAdvOpen}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
              <ChevronDown
                className={`h-3 w-3 transition-transform ${advOpen ? "rotate-0" : "-rotate-90"}`}
              />
              Advanced options ({advanced.length})
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-3">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {advanced.map((f) => (
                  <FieldRenderer
                    key={f.name}
                    field={f}
                    value={values[f.name]}
                    onChange={(name, val) => onChange(taskType, name, val)}
                  />
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  )
}
