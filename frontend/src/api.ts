export interface ApiError { code: string; message: string; fields: Record<string, string[]> }

export async function apiGet<T = any>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) {
    const body: ApiError = await r.json()
    throw new Error(body.message || `请求失败: ${r.status}`)
  }
  return r.json()
}
