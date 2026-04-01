import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import { ThemeContext, type Theme } from "@/hooks/use-theme"

const STORAGE_KEY = "gol-bench-theme"

function getStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === "dark" || stored === "light" || stored === "system") return stored
  } catch {
    // localStorage may throw in private browsing
  }
  return "system"
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.classList.remove("light", "dark")
  if (theme === "system") {
    root.classList.add(
      window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
    )
  } else {
    root.classList.add(theme)
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getStoredTheme)

  useEffect(() => {
    applyTheme(theme)
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // localStorage may throw in private browsing
    }
  }, [theme])

  // Listen for OS theme changes — re-apply only when in "system" mode.
  // The handler reads `theme` via closure but the effect only runs once (stable listener).
  // We use a ref-like pattern: applyTheme("system") only changes the DOM when the
  // current stored theme is "system", but since we can't read state in a stable handler,
  // we read localStorage directly.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => {
      if (getStoredTheme() === "system") applyTheme("system")
    }
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [])

  const handleSetTheme = useCallback((t: Theme) => setTheme(t), [])
  const value = useMemo(() => ({ theme, setTheme: handleSetTheme }), [theme, handleSetTheme])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}
