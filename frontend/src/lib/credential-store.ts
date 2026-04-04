/**
 * Encrypted localStorage credential store for API endpoints.
 * Uses Web Crypto API (AES-GCM) for at-rest encryption.
 * This provides obfuscation — not true security against local access.
 */

const STORAGE_KEY = "gol-api-credentials"
const SALT = new TextEncoder().encode("gol-bench-credential-salt-v1")

interface StoredCredential {
  apiBase: string
  apiKey: string
}

async function deriveKey(): Promise<CryptoKey> {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(navigator.userAgent.slice(0, 64)),
    "PBKDF2",
    false,
    ["deriveKey"]
  )
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: SALT, iterations: 100_000, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  )
}

async function encrypt(data: string): Promise<string> {
  const key = await deriveKey()
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const encoded = new TextEncoder().encode(data)
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoded
  )
  // Store as iv:ciphertext (both base64)
  const ivB64 = btoa(String.fromCharCode(...iv))
  const ctB64 = btoa(String.fromCharCode(...new Uint8Array(ciphertext)))
  return `${ivB64}:${ctB64}`
}

async function decrypt(stored: string): Promise<string> {
  const key = await deriveKey()
  const [ivB64, ctB64] = stored.split(":")
  const iv = Uint8Array.from(atob(ivB64), (c) => c.charCodeAt(0))
  const ciphertext = Uint8Array.from(atob(ctB64), (c) => c.charCodeAt(0))
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    key,
    ciphertext
  )
  return new TextDecoder().decode(decrypted)
}

export async function saveCredential(apiBase: string, apiKey: string): Promise<void> {
  const creds = await loadCredentials()
  const existing = creds.findIndex((c) => c.apiBase === apiBase)
  if (existing >= 0) {
    creds[existing].apiKey = apiKey
  } else {
    creds.push({ apiBase, apiKey })
  }
  const encrypted = await encrypt(JSON.stringify(creds))
  localStorage.setItem(STORAGE_KEY, encrypted)
}

export async function loadCredentials(): Promise<StoredCredential[]> {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    const decrypted = await decrypt(raw)
    return JSON.parse(decrypted) as StoredCredential[]
  } catch {
    return []
  }
}

export async function deleteCredential(apiBase: string): Promise<void> {
  const creds = await loadCredentials()
  const filtered = creds.filter((c) => c.apiBase !== apiBase)
  if (filtered.length === 0) {
    localStorage.removeItem(STORAGE_KEY)
  } else {
    const encrypted = await encrypt(JSON.stringify(filtered))
    localStorage.setItem(STORAGE_KEY, encrypted)
  }
}
