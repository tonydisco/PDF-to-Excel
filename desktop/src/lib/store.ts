import { create } from "zustand"
import { convert, type ConvertResult } from "./api"
import { MOCK_FILES } from "./mock"

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

// Seed hàng đợi bằng các file mẫu (đường dẫn thật, trạng thái "chờ" -> bấm
// Chuyển đổi sẽ OCR thật). Người dùng thêm file riêng qua picker.
const SEED: QFile[] = MOCK_FILES.map((m) => newFile(m.path, m.name))

interface Store {
  files: QFile[]
  results: Record<string, ConvertResult>
  converting: boolean
  addPaths: (paths: string[]) => number
  removeFile: (id: string) => void
  clearAll: () => void
  convertAll: () => Promise<void>
  result: (id: string) => ConvertResult | undefined
  file: (id: string) => QFile | undefined
}

export const useStore = create<Store>((set, get) => ({
  files: SEED,
  results: {},
  converting: false,

  result: (id) => get().results[id],
  file: (id) => get().files.find((f) => f.id === id),

  addPaths: (paths) => {
    const exist = new Set(get().files.map((f) => f.path))
    const add = paths
      .filter((p) => p.toLowerCase().endsWith(".pdf") && !exist.has(p))
      .map((p) => newFile(p))
    if (add.length) set((s) => ({ files: [...s.files, ...add] }))
    return add.length
  },

  removeFile: (id) =>
    set((s) => {
      const { [id]: _, ...rest } = s.results
      return { files: s.files.filter((f) => f.id !== id), results: rest }
    }),

  clearAll: () => set({ files: [], results: {} }),

  convertAll: async () => {
    if (get().converting) return
    set({ converting: true })
    const todo = get().files.filter((f) => f.status === "queued" || f.status === "error")
    for (const f of todo) {
      set((s) => ({ files: s.files.map((x) => (x.id === f.id ? { ...x, status: "processing", error: undefined } : x)) }))
      try {
        const r = await convert(f.path)
        set((s) => ({
          results: { ...s.results, [f.id]: r },
          files: s.files.map((x) =>
            x.id === f.id
              ? { ...x, status: "done", sizeMB: r.sizeMB, pages: r.pageCount, found: r.found as QFile["found"], conflicts: r.conflicts, balanceOk: r.balanceOk }
              : x,
          ),
        }))
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        set((s) => ({ files: s.files.map((x) => (x.id === f.id ? { ...x, status: "error", error: msg } : x)) }))
      }
    }
    set({ converting: false })
  },
}))
