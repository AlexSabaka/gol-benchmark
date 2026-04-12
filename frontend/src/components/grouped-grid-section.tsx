import { useState } from "react"
import { ChevronDown } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

interface GroupedGridSectionProps {
  title: string
  subtitle?: string
  countLabel?: string
  children: React.ReactNode
  headerExtras?: React.ReactNode
  defaultOpen?: boolean
}

export function GroupedGridSection({
  title,
  subtitle,
  countLabel,
  children,
  headerExtras,
  defaultOpen = false,
}: GroupedGridSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <Collapsible open={open} onOpenChange={setOpen}>
        <div className="flex items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-accent/30">
          <CollapsibleTrigger asChild>
            <button className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">{title}</h3>
                  {countLabel && <Badge variant="secondary">{countLabel}</Badge>}
                </div>
                {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
              </div>
              <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
            </button>
          </CollapsibleTrigger>
          {headerExtras && <div className="flex items-center gap-3">{headerExtras}</div>}
        </div>
        <CollapsibleContent>
          <CardContent className="border-t bg-muted/10 py-5">{children}</CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}