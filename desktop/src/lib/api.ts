// Client gọi Python sidecar (lõi OCR bctc). Sidecar chạy local trên 127.0.0.1.
import type { Statement, BalanceCheck } from "@/lib/mock"

const BASE = "http://127.0.0.1:8756"

export interface ConvertResult {
  name: string
  found: number
  conflicts: number
  balanceOk: boolean | null
  statements: Statement[]
  balance: BalanceCheck[]
  warnings: string[]
}

export async function health(): Promise<{ ok: boolean; has_vie: boolean; tesseract: string | null }> {
  const r = await fetch(`${BASE}/health`)
  return r.json()
}

export async function convert(path: string, hq = false): Promise<ConvertResult> {
  const r = await fetch(`${BASE}/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, hq }),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.error || `Sidecar lỗi ${r.status}`)
  }
  return r.json()
}

export async function exportXlsx(path: string, outDir?: string): Promise<{ out_path: string }> {
  const r = await fetch(`${BASE}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, out_dir: outDir }),
  })
  return r.json()
}
