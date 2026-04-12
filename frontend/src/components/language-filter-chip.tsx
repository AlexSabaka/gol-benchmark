/**
 * Maps language codes to flag + full name for filter display.
 * Used by DataTableFacetedFilter on TestSets and Results pages.
 */

const LANGUAGE_LABELS: Record<string, { flag: string; name: string }> = {
  en: { flag: "\u{1F1EC}\u{1F1E7}", name: "English" },
  es: { flag: "\u{1F1EA}\u{1F1F8}", name: "Espa\u00f1ol" },
  fr: { flag: "\u{1F1EB}\u{1F1F7}", name: "Fran\u00e7ais" },
  de: { flag: "\u{1F1E9}\u{1F1EA}", name: "Deutsch" },
  zh: { flag: "\u{1F1E8}\u{1F1F3}", name: "\u4e2d\u6587" },
  ua: { flag: "\u{1F1FA}\u{1F1E6}", name: "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430" },
}

/** Format a language code as "flag Full Name" for display in filters */
export function languageLabel(code: string): string {
  const entry = LANGUAGE_LABELS[code.toLowerCase()]
  if (!entry) return code.toUpperCase()
  return `${entry.flag} ${entry.name}`
}

/** Build filter options with flag + name labels from raw language codes */
export function languageFilterOptions(codes: string[]): Array<{ label: string; value: string }> {
  return codes.map((code) => ({ label: languageLabel(code), value: code }))
}
