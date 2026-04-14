import { NavLink, Outlet } from "react-router"
import { ThemeToggle } from "@/components/theme-toggle"
import { ErrorBoundary } from "@/components/error-boundary"
import {
  LayoutDashboard,
  Settings2,
  Database,
  Play,
  Activity,
  BarChart3,
  LineChart,
  FileText,
  Scale,
  Dna,
} from "lucide-react"

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/configure", icon: Settings2, label: "Configure" },
  { to: "/testsets", icon: Database, label: "Test Sets" },
  { to: "/execute", icon: Play, label: "Execute" },
  { to: "/jobs", icon: Activity, label: "Jobs" },
  { to: "/results", icon: BarChart3, label: "Results" },
  { to: "/charts", icon: LineChart, label: "Charts" },
  { to: "/reports", icon: FileText, label: "Reports" },
  { to: "/judge", icon: Scale, label: "Judge" },
]

export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="hidden w-56 flex-col border-r bg-sidebar md:flex">
        {/* Brand */}
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <Dna className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">GoL Benchmark</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t p-3 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">v{__APP_VERSION__}</span>
          <ThemeToggle />
        </div>
      </aside>

      {/* Mobile header */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center gap-4 border-b px-4 md:hidden">
          <Dna className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm flex-1">GoL Benchmark</span>
          <ThemeToggle />
        </header>

        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-b px-2 py-1 md:hidden">
          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
