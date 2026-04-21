/**
 * Shared chart color constants and a theme resolver that has to survive PNG
 * export.
 *
 * `html-to-image` clones the target into a detached context where CSS variables
 * and `currentColor` inside SVG attributes don't resolve to the live theme.
 * We therefore pre-resolve the theme to explicit hex values at render time —
 * the resulting SVG has baked-in fills and exports the same regardless of the
 * cloning quirks.
 */

/** Mid-gray, readable against both near-white and near-black backgrounds. */
export const CI_STROKE_COLOR = "#737373"

/** Subtle hairline color for leader lines on scatter labels. */
export const LEADER_LINE_COLOR = "#9ca3af"

export interface ThemeColors {
  foreground: string
  mutedForeground: string
  /** Fill used for subtle chip backgrounds (already low opacity). */
  chipBg: string
  background: string
}

const LIGHT_THEME: ThemeColors = {
  foreground: "#0a0a0a",
  mutedForeground: "#52525b",
  chipBg: "rgba(0, 0, 0, 0.08)",
  background: "#ffffff",
}

const DARK_THEME: ThemeColors = {
  foreground: "#fafafa",
  mutedForeground: "#a1a1aa",
  chipBg: "rgba(255, 255, 255, 0.12)",
  background: "#0a0a0a",
}

/** Resolve explicit hex/rgba colors from the live theme. Called at render time. */
export function getThemeColors(): ThemeColors {
  if (typeof document === "undefined") return LIGHT_THEME
  return document.documentElement.classList.contains("dark") ? DARK_THEME : LIGHT_THEME
}
