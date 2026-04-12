import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/components/theme-provider"
import { AppShell } from "@/components/layout/app-shell"
import { Loader2 } from "lucide-react"

// Eager-load the dashboard (landing page)
import DashboardPage from "@/pages/dashboard"

// Lazy-load all other pages for code splitting
const ConfigurePage = lazy(() => import("@/pages/configure"))
const TestSetsPage = lazy(() => import("@/pages/testsets"))
const ExecutePage = lazy(() => import("@/pages/execute"))
const MatrixExecutionPage = lazy(() => import("@/pages/matrix-execution"))
const JobsPage = lazy(() => import("@/pages/jobs"))
const ResultsPage = lazy(() => import("@/pages/results"))
const ChartsPage = lazy(() => import("@/pages/charts"))
const ReportsPage = lazy(() => import("@/pages/reports"))
const JudgePage = lazy(() => import("@/pages/judge"))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<DashboardPage />} />
                <Route path="configure" element={<Suspense fallback={<PageLoader />}><ConfigurePage /></Suspense>} />
                <Route path="testsets" element={<Suspense fallback={<PageLoader />}><TestSetsPage /></Suspense>} />
                <Route path="execute" element={<Suspense fallback={<PageLoader />}><ExecutePage /></Suspense>} />
                <Route path="matrix-execution" element={<Suspense fallback={<PageLoader />}><MatrixExecutionPage /></Suspense>} />
                <Route path="jobs" element={<Suspense fallback={<PageLoader />}><JobsPage /></Suspense>} />
                <Route path="results" element={<Suspense fallback={<PageLoader />}><ResultsPage /></Suspense>} />
                <Route path="charts" element={<Suspense fallback={<PageLoader />}><ChartsPage /></Suspense>} />
                <Route path="reports" element={<Suspense fallback={<PageLoader />}><ReportsPage /></Suspense>} />
                <Route path="judge" element={<Suspense fallback={<PageLoader />}><JudgePage /></Suspense>} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster richColors position="top-right" />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground mt-2">Page not found</p>
    </div>
  )
}
