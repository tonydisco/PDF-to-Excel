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
  pageCount: number
  pages: Record<string, number> // {CDKT: 7, ...} trang đầu mỗi báo cáo (1-based)
}

// URL ảnh PNG của 1 trang PDF do sidecar render (PyMuPDF).
export function pageUrl(path: string, page: number, dpi = 120): string {
  return `${BASE}/page?path=${encodeURIComponent(path)}&page=${page}&dpi=${dpi}`
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

export interface RatioItem {
  label: string
  value: number | null
  unit: "x" | "%" | "vnd"
  formula: string
  tone: "ok" | "warn" | "bad" | "neutral"
}
export interface RatioGroup { key: string; label: string; items: RatioItem[] }
export interface RatiosResult {
  groups: RatioGroup[]
  altman: { value: number; zone: string; label: string } | null
  flags: string[]
}

export async function ratios(path: string, hq = false): Promise<RatiosResult> {
  const r = await fetch(`${BASE}/ratios`, {
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
