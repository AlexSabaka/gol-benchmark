import { languageFlag as _languageFlag } from "@/lib/constants"

export function langFlag(code: string): string {
  return _languageFlag(code)
}

export function langFlags(codes: string[]): string {
  if (codes.length === 0) return ""
  return codes.map(langFlag).join(" ")
}
