import { lazy, Suspense } from "react"
import { useSearchParams } from "react-router"
import { ArrowLeft, ArrowRight, Grid3X3, Loader2, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/layout/page-header"

// Lazy-load each wizard so the user only pays for the one they open.
const SimpleWizard = lazy(() => import("@/pages/execute/simple-wizard"))
const MatrixWizard = lazy(() => import("@/pages/execute/matrix-wizard"))

type ExecuteMode = "simple" | "matrix"

function isExecuteMode(value: string | null): value is ExecuteMode {
  return value === "simple" || value === "matrix"
}

function WizardFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export default function ExecutePage() {
  const [params, setParams] = useSearchParams()
  const mode = params.get("mode")

  const setMode = (next: ExecuteMode | null) => {
    const p = new URLSearchParams(params)
    if (next) p.set("mode", next)
    else p.delete("mode")
    setParams(p)
  }

  if (isExecuteMode(mode)) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" className="-ml-2 h-7 text-xs" onClick={() => setMode(null)}>
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
          Back to options
        </Button>
        <Suspense fallback={<WizardFallback />}>
          {mode === "simple" ? <SimpleWizard /> : <MatrixWizard />}
        </Suspense>
      </div>
    )
  }

  // ── Landing ──
  return (
    <div className="space-y-6">
      <PageHeader
        title="Execute"
        description="Pick how you want to run your benchmarks."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card
          onClick={() => setMode("simple")}
          className="cursor-pointer border-2 transition-colors hover:border-primary/60 hover:bg-primary/5"
        >
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Play className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold">Simple run</h3>
                <p className="text-xs text-muted-foreground">Four-step wizard</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Pick one or more pre-generated test sets, choose the models to run them against, tune
              sampling overrides, and launch every combination in a single batch.
            </p>
            <ul className="space-y-1 text-xs text-muted-foreground">
              <li>• Works with any existing test set</li>
              <li>• No new data is generated</li>
              <li>• Best when you already have the benchmark inputs you want</li>
            </ul>
            <Button className="w-full" onClick={(e) => { e.stopPropagation(); setMode("simple") }}>
              Start simple run
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <Card
          onClick={() => setMode("matrix")}
          className="cursor-pointer border-2 transition-colors hover:border-primary/60 hover:bg-primary/5"
        >
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Grid3X3 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold">Matrix run</h3>
                <p className="text-xs text-muted-foreground">Five-step wizard</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Sweep one plugin across prompt axes and field-level parameter variations, generate a
              test set per cell, and optionally launch every cell against every selected model.
            </p>
            <ul className="space-y-1 text-xs text-muted-foreground">
              <li>• Generates fresh test sets during the flow</li>
              <li>• Cartesian product of prompt styles, languages, and plugin fields</li>
              <li>• Generate Only or Generate and Run</li>
            </ul>
            <Button className="w-full" onClick={(e) => { e.stopPropagation(); setMode("matrix") }}>
              Start matrix run
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
