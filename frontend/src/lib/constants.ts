/**
 * UI-side enrichment for backend domain codes.
 * Language codes, styles, and other domain values come from /api/metadata.
 * Flags and display labels are presentation concerns that live here.
 */

export const LANGUAGE_META: Record<string, { flag: string; label: string }> = {
  en: { flag: "\u{1F1EC}\u{1F1E7}", label: "English" },       // 🇬🇧
  es: { flag: "\u{1F1EA}\u{1F1F8}", label: "Espa\u00f1ol" },  // 🇪🇸
  fr: { flag: "\u{1F1EB}\u{1F1F7}", label: "Fran\u00e7ais" }, // 🇫🇷
  de: { flag: "\u{1F1E9}\u{1F1EA}", label: "Deutsch" },        // 🇩🇪
  zh: { flag: "\u{1F1E8}\u{1F1F3}", label: "\u4e2d\u6587" },  // 🇨🇳
  ua: { flag: "\u{1F1FA}\u{1F1E6}", label: "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430" }, // 🇺🇦
}

export function languageFlag(code: string): string {
  return LANGUAGE_META[code]?.flag ?? code.toUpperCase()
}

export function languageLabel(code: string): string {
  return LANGUAGE_META[code]?.label ?? code.toUpperCase()
}
