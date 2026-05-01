import { lazy, Suspense } from "react"
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router"
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
const JobsPage = lazy(() => import("@/pages/jobs"))
const ResultsPage = lazy(() => import("@/pages/results"))
const ChartsPage = lazy(() => import("@/pages/charts"))
const ReportsPage = lazy(() => import("@/pages/reports"))
const JudgePage = lazy(() => import("@/pages/judge"))
const ReviewPage = lazy(() => import("@/pages/review"))
const PromptsPage = lazy(() => import("@/pages/prompts"))
const PromptNewPage = lazy(() => import("@/pages/prompts/new"))
const PromptDetailPage = lazy(() => import("@/pages/prompts/[id]"))
const PromptEditPage = lazy(() => import("@/pages/prompts/[id].edit"))

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

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground mt-2">Page not found</p>
    </div>
  )
}

const wrap = (Page: React.ComponentType) => (
  <Suspense fallback={<PageLoader />}>
    <Page />
  </Suspense>
)

// Data router enables features like ``useBlocker`` (used by the prompt
// editor for unsaved-changes guards). Conceptually equivalent to the prior
// ``<BrowserRouter><Routes>`` tree — same layout shell, same nested routes.
const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "configure", element: wrap(ConfigurePage) },
      { path: "testsets", element: wrap(TestSetsPage) },
      { path: "execute", element: wrap(ExecutePage) },
      { path: "matrix-execution", element: <Navigate to="/execute?mode=matrix" replace /> },
      { path: "jobs", element: wrap(JobsPage) },
      { path: "results", element: wrap(ResultsPage) },
      { path: "charts", element: wrap(ChartsPage) },
      { path: "reports", element: wrap(ReportsPage) },
      { path: "judge", element: wrap(JudgePage) },
      { path: "review", element: wrap(ReviewPage) },
      { path: "prompts", element: wrap(PromptsPage) },
      { path: "prompts/new", element: wrap(PromptNewPage) },
      { path: "prompts/:id", element: wrap(PromptDetailPage) },
      { path: "prompts/:id/edit", element: wrap(PromptEditPage) },
      { path: "*", element: <NotFound /> },
    ],
  },
])

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <RouterProvider router={router} />
          <Toaster richColors position="top-right" />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
