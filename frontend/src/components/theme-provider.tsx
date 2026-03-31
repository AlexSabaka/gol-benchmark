import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

type Theme = "dark" | "light" | "system"

interface ThemeCtx {
  theme: Theme
  setTheme: (t: Theme) => void
}

const ThemeContext = createContext<ThemeCtx>({ theme: "system", setTheme: () => {} })

const STORAGE_KEY = "gol-bench-theme"

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return (stored as Theme) || "system"
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove("light", "dark")

    if (theme === "system") {
      const sys = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
      root.classList.add(sys)
    } else {
      root.classList.add(theme)
    }

    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  // Listen for OS theme changes when in system mode
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => {
      if (theme === "system") {
        const root = document.documentElement
        root.classList.remove("light", "dark")
        root.classList.add(mq.matches ? "dark" : "light")
      }
    }
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
