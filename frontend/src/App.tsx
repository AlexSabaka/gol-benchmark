import { BrowserRouter, Routes, Route } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/components/theme-provider"
import { AppShell } from "@/components/layout/app-shell"

import DashboardPage from "@/pages/dashboard"
import ConfigurePage from "@/pages/configure"
import TestSetsPage from "@/pages/testsets"
import ExecutePage from "@/pages/execute"
import ResultsPage from "@/pages/results"
import ReportsPage from "@/pages/reports"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<DashboardPage />} />
                <Route path="configure" element={<ConfigurePage />} />
                <Route path="testsets" element={<TestSetsPage />} />
                <Route path="execute" element={<ExecutePage />} />
                <Route path="results" element={<ResultsPage />} />
                <Route path="reports" element={<ReportsPage />} />
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
