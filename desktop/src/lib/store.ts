import { create } from "zustand"
import { convert, sizes, type ConvertResult, type CellEdit } from "./api"

const EXPORT_DIR_KEY = "bctc.exportDir"
const loadExportDir = (): string | null => {
  try { return localStorage.getItem(EXPORT_DIR_KEY) || null } catch { return null }
}

type Col = "cur" | "prior"
const cellKey = (key: string, code: string, col: Col) => `${key}|${code}|${col}`

export type AnalysisMode = "each" | "compare"
export interface AnalysisItem { path: string; name: string; kind: "pdf" | "excel" }
const baseNoExt = (p: string) => (p.split(/[/\\]/).pop() || p).replace(/\.(xlsx|xls|pdf)$/i, "")

export type FileStatus = "queued" | "processing" | "done" | "error"

export interface QFile {
  id: string // = path (duy nhất)
  name: string
  path: string
  sizeMB: number | null
  pages: number | null
  status: FileStatus
  found: 0 | 1 | 2 | 3
  conflicts: number
  balanceOk: boolean | null
  error?: string
}

function baseName(p: string): string {
  return p.split(/[/\\]/).pop() || p
}

function newFile(path: string, name?: string): QFile {
  return {
    id: path, name: name ?? baseName(path), path,
    sizeMB: null, pages: null, status: "queued",
    found: 0, conflicts: 0, balanceOk: null,
  }
}

// Cờ điều khiển vòng chuyển đổi — để ngoài state cho loop đọc đồng bộ tức thì.
const control: {
  paused: boolean
  cancelled: boolean
  currentId: string | null
  currentAbort: AbortController | null
  aborted: Set<string>
} = { paused: false, cancelled: false, currentId: null, currentAbort: null, aborted: new Set() }

const isPending = (f: QFile) => f.status === "queued" || f.status === "error"

interface Store {
  files: QFile[]
  results: Record<string, ConvertResult>
  converting: boolean
  paused: boolean
  selected: Set<string>
  editsByFile: Record<string, Record<string, number | null>>
  exportDir: string | null
  // chọn file
  toggleSelect: (id: string) => void
  selectAll: () => void
  selectNone: () => void
  // hàng đợi
  addPaths: (paths: string[]) => number
  removeFile: (id: string) => void
  clearAll: () => void
  convertAll: () => Promise<void>
  convertSelected: () => Promise<void>
  pauseQueue: () => void
  resumeQueue: () => void
  cancelQueue: () => void
  cancelFile: (id: string) => void
  // chỉnh sửa giá trị (Review) -> dùng khi xuất Excel
  setEdit: (fileId: string, key: string, code: string, col: Col, value: number | null) => void
  clearFileEdits: (fileId: string) => void
  cellEdit: (fileId: string, key: string, code: string, col: Col) => number | null | undefined
  fileEdits: (fileId: string) => CellEdit[]
  hasEdits: (fileId: string) => boolean
  // nơi lưu Excel
  setExportDir: (dir: string | null) => void
  // phân tích tài chính (đa file)
  analysis: AnalysisItem[]
  analysisMode: AnalysisMode
  setAnalysisItems: (items: AnalysisItem[]) => void
  addAnalysisExcel: (path: string) => boolean
  removeAnalysisItem: (path: string) => void
  setAnalysisMode: (mode: AnalysisMode) => void
  pushSelectedToAnalysis: () => number // file đã chọn + đã chuyển đổi -> Phân tích
  result: (id: string) => ConvertResult | undefined
  file: (id: string) => QFile | undefined
}

export const useStore = create<Store>((set, get) => ({
  files: [],
  results: {},
  converting: false,
  paused: false,
  selected: new Set<string>(),
  editsByFile: {},
  exportDir: loadExportDir(),
  analysis: [],
  analysisMode: "each",

  result: (id) => get().results[id],
  file: (id) => get().files.find((f) => f.id === id),

  setAnalysisItems: (items) => set({ analysis: items }),
  addAnalysisExcel: (path) => {
    if (!/\.(xlsx|xls)$/i.test(path)) return false
    if (get().analysis.some((a) => a.path === path)) return false
    set((s) => ({ analysis: [...s.analysis, { path, name: baseNoExt(path), kind: "excel" }] }))
    return true
  },
  removeAnalysisItem: (path) => set((s) => ({ analysis: s.analysis.filter((a) => a.path !== path) })),
  setAnalysisMode: (analysisMode) => set({ analysisMode }),
  pushSelectedToAnalysis: () => {
    const sel = get().selected
    const items: AnalysisItem[] = get()
      .files.filter((f) => f.status === "done" && sel.has(f.id))
      .map((f) => ({ path: f.path, name: f.name.replace(/\.pdf$/i, ""), kind: "pdf" as const }))
    set({ analysis: items })
    return items.length
  },

  setEdit: (fileId, key, code, col, value) =>
    set((s) => ({
      editsByFile: { ...s.editsByFile, [fileId]: { ...(s.editsByFile[fileId] ?? {}), [cellKey(key, code, col)]: value } },
    })),
  clearFileEdits: (fileId) =>
    set((s) => {
      if (!s.editsByFile[fileId]) return {}
      const { [fileId]: _, ...rest } = s.editsByFile
      return { editsByFile: rest }
    }),
  cellEdit: (fileId, key, code, col) => get().editsByFile[fileId]?.[cellKey(key, code, col)],
  hasEdits: (fileId) => Object.keys(get().editsByFile[fileId] ?? {}).length > 0,
  fileEdits: (fileId) => {
    const m = get().editsByFile[fileId] ?? {}
    return Object.entries(m).map(([k, value]) => {
      const [key, code, col] = k.split("|")
      return { key, code, col: col as Col, value }
    })
  },

  setExportDir: (dir) => {
    try {
      dir ? localStorage.setItem(EXPORT_DIR_KEY, dir) : localStorage.removeItem(EXPORT_DIR_KEY)
    } catch {
      /* ignore */
    }
    set({ exportDir: dir })
  },

  toggleSelect: (id) =>
    set((s) => {
      const next = new Set(s.selected)
      next.has(id) ? next.delete(id) : next.add(id)
      return { selected: next }
    }),
  selectAll: () => set((s) => ({ selected: new Set(s.files.map((f) => f.id)) })),
  selectNone: () => set({ selected: new Set<string>() }),

  addPaths: (paths) => {
    const exist = new Set(get().files.map((f) => f.path))
    const add = paths
      .filter((p) => p.toLowerCase().endsWith(".pdf") && !exist.has(p))
      .map((p) => newFile(p))
    if (add.length) {
      set((s) => {
        const sel = new Set(s.selected)
        add.forEach((f) => sel.add(f.id)) // mặc định tick hết file mới thêm
        return { files: [...add, ...s.files], selected: sel } // file mới lên ĐẦU bảng
      })
      void hydrateSizes(add.map((f) => f.path), set) // lấy dung lượng ngay (không OCR)
    }
    return add.length
  },

  removeFile: (id) =>
    set((s) => {
      const { [id]: _r, ...rest } = s.results
      const { [id]: _e, ...restEdits } = s.editsByFile
      const sel = new Set(s.selected)
      sel.delete(id)
      return { files: s.files.filter((f) => f.id !== id), results: rest, editsByFile: restEdits, selected: sel }
    }),

  clearAll: () => set({ files: [], results: {}, editsByFile: {}, selected: new Set<string>() }),

  convertAll: async () => {
    const ids = get().files.filter(isPending).map((f) => f.id)
    await runQueue(ids, get, set)
  },
  convertSelected: async () => {
    const sel = get().selected
    const ids = get().files.filter((f) => sel.has(f.id) && isPending(f)).map((f) => f.id)
    await runQueue(ids, get, set)
  },

  pauseQueue: () => {
    control.paused = true
    set({ paused: true })
  },
  resumeQueue: () => {
    control.paused = false
    set({ paused: false })
  },
  cancelQueue: () => {
    control.cancelled = true
    control.paused = false
    if (control.currentId && control.currentAbort) {
      control.aborted.add(control.currentId)
      control.currentAbort.abort()
    }
    set({ paused: false })
  },
  cancelFile: (id) => {
    if (control.currentId === id && control.currentAbort) {
      // File đang OCR -> abort ngay (huỷ, đưa về Chờ).
      control.aborted.add(id)
      control.currentAbort.abort()
    } else {
      // File đang chờ -> bỏ tick để vòng chạy bỏ qua (vẫn ở trạng thái Chờ).
      set((s) => {
        const sel = new Set(s.selected)
        sel.delete(id)
        return { selected: sel }
      })
    }
  },
}))

// Lấy dung lượng file (MB) ngay khi thêm — không OCR — rồi vá vào state.
async function hydrateSizes(
  paths: string[],
  set: (partial: Partial<Store> | ((s: Store) => Partial<Store>)) => void,
) {
  try {
    const map = await sizes(paths)
    set((s) => ({
      files: s.files.map((f) => (f.path in map && f.sizeMB == null ? { ...f, sizeMB: map[f.path] } : f)),
    }))
  } catch {
    /* sidecar offline -> bỏ qua, cột dung lượng vẫn "—" */
  }
}

// Vòng chuyển đổi tuần tự, có hỗ trợ tạm dừng (chờ giữa các file) và huỷ
// (dừng sau file đang chạy). OCR 1 file là liền mạch nên không cắt giữa chừng.
async function runQueue(
  ids: string[],
  get: () => Store,
  set: (partial: Partial<Store> | ((s: Store) => Partial<Store>)) => void,
) {
  if (get().converting || ids.length === 0) return
  control.paused = false
  control.cancelled = false
  control.aborted.clear()
  control.currentId = null
  control.currentAbort = null
  set({ converting: true, paused: false })

  for (const id of ids) {
    if (control.cancelled) break
    // Tạm dừng: chờ tới khi tiếp tục hoặc huỷ.
    while (control.paused && !control.cancelled) {
      await new Promise((r) => setTimeout(r, 200))
    }
    if (control.cancelled) break

    const f = get().files.find((x) => x.id === id)
    if (!f || !isPending(f)) continue
    if (!get().selected.has(id)) continue // bỏ tick (huỷ file chờ) -> bỏ qua

    const ac = new AbortController()
    control.currentId = id
    control.currentAbort = ac
    set((s) => {
      const { [id]: _drop, ...restEdits } = s.editsByFile // OCR lại -> bỏ chỉnh sửa cũ
      return {
        editsByFile: restEdits,
        files: s.files.map((x) => (x.id === id ? { ...x, status: "processing", error: undefined } : x)),
      }
    })
    try {
      const r = await convert(f.path, false, ac.signal)
      set((s) => ({
        results: { ...s.results, [id]: r },
        files: s.files.map((x) =>
          x.id === id
            ? { ...x, status: "done", sizeMB: r.sizeMB, pages: r.pageCount, found: r.found as QFile["found"], conflicts: r.conflicts, balanceOk: r.balanceOk }
            : x,
        ),
      }))
    } catch (e) {
      const isAbort = control.aborted.has(id) || (e instanceof DOMException && e.name === "AbortError") || (e instanceof Error && e.name === "AbortError")
      if (isAbort) {
        // Người dùng huỷ file này -> đưa về Chờ (không phải lỗi).
        set((s) => ({ files: s.files.map((x) => (x.id === id ? { ...x, status: "queued", error: undefined } : x)) }))
      } else {
        const msg = e instanceof Error ? e.message : String(e)
        set((s) => ({ files: s.files.map((x) => (x.id === id ? { ...x, status: "error", error: msg } : x)) }))
      }
    } finally {
      control.aborted.delete(id)
      control.currentId = null
      control.currentAbort = null
    }
  }

  control.cancelled = false
  control.paused = false
  control.currentId = null
  control.currentAbort = null
  set({ converting: false, paused: false })
}
