const FLAGS: Record<string, string> = {
  en: "\u{1F1EC}\u{1F1E7}", // 🇬🇧
  es: "\u{1F1EA}\u{1F1F8}", // 🇪🇸
  fr: "\u{1F1EB}\u{1F1F7}", // 🇫🇷
  de: "\u{1F1E9}\u{1F1EA}", // 🇩🇪
  zh: "\u{1F1E8}\u{1F1F3}", // 🇨🇳
  ua: "\u{1F1FA}\u{1F1E6}", // 🇺🇦
}

export function langFlag(code: string): string {
  return FLAGS[code] ?? code.toUpperCase()
}

export function langFlags(codes: string[]): string {
  if (codes.length === 0) return ""
  return codes.map(langFlag).join(" ")
}
