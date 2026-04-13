const BASE = ""  // Relative — works with Vite proxy in dev and same-origin in prod

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, text)
  }
  return res.json()
}

export function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v) url.searchParams.set(k, v)
    }
  }
  return fetch(url.toString()).then(r => handleResponse<T>(r))
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  }).then(r => handleResponse<T>(r))
}

export function postFormData<T>(path: string, formData: FormData): Promise<T> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    body: formData,
  }).then(r => handleResponse<T>(r))
}

export function del<T>(path: string): Promise<T> {
  return fetch(`${BASE}${path}`, { method: "DELETE" }).then(r => handleResponse<T>(r))
}

export async function postText(path: string, body?: unknown): Promise<string> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, text)
  }
  return res.text()
}
