// Client gọi Python sidecar (lõi OCR bctc). Sidecar chạy local trên 127.0.0.1.
import type { Statement, BalanceCheck } from "@/lib/types"

const BASE = "http://127.0.0.1:8756"

export interface ConvertResult {
  name: string
  sizeMB: number | null
  found: number
  conflicts: number
  balanceOk: boolean | null
  statements: Statement[]
  balance: BalanceCheck[]
  warnings: string[]
  pageCount: number
  pages: Record<string, number> // {CDKT: 7, ...} trang đầu mỗi báo cáo (1-based)
}

export async function listDir(dir: string): Promise<string[]> {
  const r = await fetch(`${BASE}/listdir?dir=${encodeURIComponent(dir)}`)
  if (!r.ok) return []
  const d = await r.json()
  return d.files ?? []
}

// Dung lượng (MB) cho nhiều file — KHÔNG OCR, để hiển thị ngay khi thêm.
export async function sizes(paths: string[]): Promise<Record<string, number | null>> {
  if (!paths.length) return {}
  const r = await fetch(`${BASE}/sizes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths }),
  })
  if (!r.ok) return {}
  const d = await r.json().catch(() => ({}))
  return d.sizes ?? {}
}

// URL ảnh PNG của 1 trang PDF do sidecar render (PyMuPDF).
export function pageUrl(path: string, page: number, dpi = 120): string {
  return `${BASE}/page?path=${encodeURIComponent(path)}&page=${page}&dpi=${dpi}`
}

export async function health(): Promise<{ ok: boolean; has_vie: boolean; tesseract: string | null }> {
  const r = await fetch(`${BASE}/health`)
  return r.json()
}

export async function convert(path: string, hq = false, signal?: AbortSignal): Promise<ConvertResult> {
  const r = await fetch(`${BASE}/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, hq }),
    signal,
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

export interface CellEdit { key: string; code: string; col: "cur" | "prior"; value: number | null }

// Xuất Excel TỪ số đã OCR (cache) + áp chỉnh sửa của người dùng (không OCR lại).
export async function exportXlsx(path: string, outDir?: string | null, edits?: CellEdit[]): Promise<{ out_path: string }> {
  const r = await fetch(`${BASE}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, out_dir: outDir || undefined, edits: edits && edits.length ? edits : undefined }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d
}

// Đọc lại 1 ô ở DPI cao (re-OCR toàn tài liệu, có cache) -> giá trị mới.
export async function reocr(path: string, key: string, code: string, col: "cur" | "prior"): Promise<number | null> {
  const r = await fetch(`${BASE}/reocr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, key, code, col }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d.value ?? null
}

// ---- Diễn giải bằng LLM (BYOK). Key lưu OS keychain; chỉ tỉ số rời máy. ----
export type Provider = "anthropic" | "google"
export interface ProviderStatus {
  hasKey: boolean
  inKeychain: boolean
  envVar: string
  sdk: boolean
  models: string[]
}
export type LlmStatus = Record<Provider, ProviderStatus>

export interface AnalysisResult {
  risk_rating: "thap" | "trung_binh" | "cao"
  risk_label: string
  summary: string
  strengths: string[]
  weaknesses: string[]
  warnings: string[]
  recommendations: string[]
}
export interface AnalyzeResponse {
  payload: string
  provider: Provider
  model: string | null
  result: AnalysisResult
}

const JSON_HEADERS = { "Content-Type": "application/json" }

export async function llmStatus(): Promise<LlmStatus> {
  const r = await fetch(`${BASE}/llm/status`)
  if (!r.ok) throw new Error("Không lấy được trạng thái LLM (sidecar offline?)")
  return r.json()
}

export async function saveKey(provider: Provider, key: string): Promise<{ ok: boolean; status: LlmStatus }> {
  const r = await fetch(`${BASE}/llm/key`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ provider, key }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d
}

// Xem trước CHÍNH chuỗi sắp gửi (dryRun = KHÔNG gọi mạng).
export async function analyzePreview(path: string): Promise<string> {
  const r = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ path, dryRun: true }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d.payload ?? ""
}

// Gọi cloud diễn giải (egress chỉ xảy ra ở đây, sau khi người dùng đồng ý).
export async function analyze(path: string, provider: Provider, model?: string): Promise<AnalyzeResponse> {
  const r = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ path, provider, model: model || undefined }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d
}

// ---- So sánh nhiều báo cáo ----
export interface CompareItem { path: string; label: string }
export interface CompareResult {
  summary: string
  ranking: string[]
  highlights: string[]
  recommendations: string[]
}
export interface CompareResponse { payload: string; provider: Provider; model: string | null; result: CompareResult }

export async function analyzeComparePreview(items: CompareItem[]): Promise<string> {
  const r = await fetch(`${BASE}/analyze/compare`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ items, dryRun: true }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d.payload ?? ""
}

export async function analyzeCompare(items: CompareItem[], provider: Provider, model?: string): Promise<CompareResponse> {
  const r = await fetch(`${BASE}/analyze/compare`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ items, provider, model: model || undefined }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Lỗi ${r.status}`)
  return d
}
