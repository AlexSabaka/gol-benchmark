import { useRef, useState } from "react"
import { toast } from "sonner"
import { toBlob, toPng } from "html-to-image"
import { Camera, ChevronDown, Download, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface ChartCardProps {
  title: string
  description?: string
  children: React.ReactNode
  actions?: React.ReactNode
}

/** Options for html-to-image. Pixel ratio 2 for crisp retina exports; background matches popover bg. */
const EXPORT_OPTIONS = {
  pixelRatio: 2,
  backgroundColor: undefined as string | undefined,
  cacheBust: true,
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "") || "chart"
}

function ExportChartButton({ target, filename }: { target: React.RefObject<HTMLDivElement | null>; filename: string }) {
  const [busy, setBusy] = useState(false)

  const resolveBg = (): string => {
    // Grab the current card background from computed styles so light/dark mode
    // both render without a transparent slice. Fallback to solid white.
    if (target.current) {
      const bg = getComputedStyle(target.current).getPropertyValue("background-color").trim()
      if (bg && bg !== "rgba(0, 0, 0, 0)") return bg
    }
    return "#ffffff"
  }

  const handleCopy = async () => {
    if (!target.current) return
    setBusy(true)
    try {
      const blob = await toBlob(target.current, { ...EXPORT_OPTIONS, backgroundColor: resolveBg() })
      if (!blob) throw new Error("Blob creation failed")
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })])
      toast.success("Chart copied to clipboard")
    } catch (err) {
      toast.error(`Copy failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setBusy(false)
    }
  }

  const handleDownload = async () => {
    if (!target.current) return
    setBusy(true)
    try {
      const dataUrl = await toPng(target.current, { ...EXPORT_OPTIONS, backgroundColor: resolveBg() })
      const a = document.createElement("a")
      a.href = dataUrl
      a.download = `${filename}.png`
      a.click()
      toast.success(`Downloaded ${filename}.png`)
    } catch (err) {
      toast.error(`Download failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex">
      <Button
        variant="outline"
        size="sm"
        onClick={handleCopy}
        disabled={busy}
        className="rounded-r-none border-r-0"
        title="Copy chart as PNG to clipboard"
      >
        {busy ? (
          <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Camera className="mr-2 h-3.5 w-3.5" />
        )}
        Copy PNG
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            className="rounded-l-none px-2"
            title="More export options"
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Download PNG
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

export function ChartCard({ title, description, children, actions }: ChartCardProps) {
  const contentRef = useRef<HTMLDivElement | null>(null)
  const filename = `gol-${slugify(title)}`

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          <div className="flex flex-wrap items-center gap-2 xl:justify-end">
            {actions}
            <ExportChartButton target={contentRef} filename={filename} />
          </div>
        </div>
      </CardHeader>
      <CardContent ref={contentRef}>{children}</CardContent>
    </Card>
  )
}
