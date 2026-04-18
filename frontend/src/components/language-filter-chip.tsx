import { LANGUAGE_META } from "@/lib/constants"

/** Format a language code as "flag Full Name" for display in filters */
export function languageLabel(code: string): string {
  const entry = LANGUAGE_META[code.toLowerCase()]
  if (!entry) return code.toUpperCase()
  return `${entry.flag} ${entry.label}`
}

/** Build filter options with flag + name labels from raw language codes */
export function languageFilterOptions(codes: string[]): Array<{ label: string; value: string }> {
  return codes.map((code) => ({ label: languageLabel(code), value: code }))
}
