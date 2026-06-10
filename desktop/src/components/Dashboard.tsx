import { useEffect, useMemo, useRef, useState } from "react"
import {
  FilePlus, FolderPlus, FolderOpen, Play, Pause, StopCircle, FilePdf, Eye, Trash, FileXls, CheckCircle,
  WarningCircle, CircleNotch, Clock, UploadSimple, Sparkle, CheckSquare, Square, X, ChartLineUp,
  CaretUp, CaretDown, ArrowsDownUp,
} from "@phosphor-icons/react"

const IS_MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPod|iPad/i.test(navigator.userAgent)
const HOTKEY = IS_MAC ? "⌘K" : "Ctrl K"

type SortKey = "name" | "size" | "status" | "found" | "balance"
type SortState = { key: SortKey; dir: "asc" | "desc" } | null
const STATUS_RANK: Record<string, number> = { error: 0, queued: 1, processing: 2, done: 3 }
import { motion } from "motion/react"
import { open } from "@tauri-apps/plugin-dialog"
import { getCurrentWebview } from "@tauri-apps/api/webview"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { fmtSize } from "@/lib/format"
import { listDir, exportXlsx } from "@/lib/api"
import { useStore, type QFile } from "@/lib/store"

function StatusCell({ f }: { f: QFile }) {
  if (f.status === "done")
    return <span className="inline-flex items-center gap-1.5 text-primary"><CheckCircle weight="fill" className="size-4" /> Hoàn tất</span>
  if (f.status === "error")
    return <span className="inline-flex items-center gap-1.5 text-destructive" title={f.error}><WarningCircle weight="fill" className="size-4" /> {f.found === 0 ? "Không nhận diện" : "Lỗi"}</span>
  if (f.status === "processing")
    return (
      <div className="flex items-center gap-2">
        <CircleNotch className="size-4 animate-spin text-primary" />
        <Progress value={null} className="h-1.5 w-16" />
        <span className="text-xs text-muted-foreground">OCR…</span>
      </div>
    )
  return <span className="inline-flex items-center gap-1.5 text-muted-foreground"><Clock className="size-4" /> Chờ</span>
}

function FoundBadge({ found, status }: { found: number; status: string }) {
  if (status !== "done") return <span className="text-xs text-muted-foreground/40">—</span>
  const tone = found === 3 ? "text-primary" : found === 0 ? "text-muted-foreground" : "text-warn"
  return (
    <div className="flex items-center gap-1">
      <span className={cn("font-mono text-xs font-medium", tone)}>{found}/3</span>
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => <span key={i} className={cn("h-3.5 w-1 rounded-full", i < found ? "bg-primary" : "bg-muted")} />)}
      </div>
    </div>
  )
}

function BalanceCell({ f }: { f: QFile }) {
  if (f.status !== "done" || f.balanceOk === null) return <span className="text-xs text-muted-foreground">—</span>
  return f.balanceOk ? (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/12 px-2 py-0.5 text-xs font-medium text-primary"><CheckCircle weight="fill" className="size-3.5" /> Khớp</span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-warn/12 px-2 py-0.5 text-xs font-medium text-warn"><WarningCircle weight="fill" className="size-3.5" /> Lệch</span>
  )
}

function CheckBox({ on, onClick, title }: { on: boolean; onClick: (e: React.MouseEvent) => void; title?: string }) {
  return (
    <button onClick={onClick} title={title} className="grid size-5 place-items-center text-muted-foreground transition-colors hover:text-foreground cursor-pointer">
      {on ? <CheckSquare weight="fill" className="size-[18px] text-primary" /> : <Square className="size-[18px]" />}
    </button>
  )
}

function SortHeader({ label, sortKey, sort, onSort, align }: {
  label: string; sortKey: SortKey; sort: SortState; onSort: (k: SortKey) => void; align?: "right"
}) {
  const active = sort?.key === sortKey
  return (
    <button onClick={() => onSort(sortKey)} className={cn("inline-flex items-center gap-1 uppercase tracking-wide transition-colors hover:text-foreground cursor-pointer", active && "text-foreground", align === "right" && "justify-end")}>
      {label}
      {active ? (sort!.dir === "asc" ? <CaretUp weight="bold" className="size-3" /> : <CaretDown weight="bold" className="size-3" />) : <ArrowsDownUp className="size-3 opacity-30" />}
    </button>
  )
}

const COLS = "grid-cols-[32px_1fr_88px_140px_92px_110px_104px]"

export function Dashboard({ onOpenReview, onAnalyze }: { onOpenReview: (id: string) => void; onAnalyze: () => void }) {
  const {
    files, addPaths, removeFile, converting, paused, selected, exportDir, setExportDir,
    convertSelected, pauseQueue, resumeQueue, cancelQueue, cancelFile, toggleSelect, selectAll, selectNone, pushSelectedToAnalysis,
  } = useStore()
  const [dragOver, setDragOver] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)

  const pickExportDir = async () => {
    const dir = await open({ directory: true })
    if (typeof dir === "string") {
      setExportDir(dir)
      toast.success("Đã đặt thư mục lưu Excel", { description: dir })
    }
  }
  const exportRow = async (id: string, path: string) => {
    setExportingId(id)
    try {
      const r = await exportXlsx(path, useStore.getState().exportDir, useStore.getState().fileEdits(id))
      toast.success("Đã xuất Excel", { description: r.out_path })
    } catch (e) {
      toast.error("Xuất Excel lỗi", { description: e instanceof Error ? e.message : String(e) })
    } finally {
      setExportingId(null)
    }
  }

  const done = files.filter((f) => f.status === "done").length
  const processing = files.filter((f) => f.status === "processing").length
  const totalConflicts = files.reduce((s, f) => s + (f.status === "done" ? f.conflicts : 0), 0)
  const pending = files.filter((f) => f.status === "queued" || f.status === "error")
  const selectedPending = pending.filter((f) => selected.has(f.id)).length
  const selectedDone = files.filter((f) => f.status === "done" && selected.has(f.id)).length
  const allSelected = files.length > 0 && selected.size === files.length

  const goAnalyze = () => {
    if (selectedDone > 0) {
      pushSelectedToAnalysis()
      onAnalyze()
    } else {
      toast.info("Chọn (tick) file đã chuyển đổi để phân tích", { description: "Hoặc vào tab Phân tích để tải Excel lên." })
      onAnalyze()
    }
  }

  // Hotkey ⌘K (macOS) / Ctrl+K (Windows/Linux) -> Phân tích
  const goRef = useRef(goAnalyze)
  goRef.current = goAnalyze
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((IS_MAC ? e.metaKey : e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault()
        goRef.current()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  // Sắp xếp: mặc định file mới trên đầu; bấm header để sort theo cột.
  const [sort, setSort] = useState<SortState>(null)
  const onSort = (k: SortKey) =>
    setSort((s) => (!s || s.key !== k ? { key: k, dir: "asc" } : s.dir === "asc" ? { key: k, dir: "desc" } : null))

  const displayFiles = useMemo(() => {
    if (!sort) return files
    const dir = sort.dir === "asc" ? 1 : -1
    const val = (f: QFile): string | number => {
      switch (sort.key) {
        case "name": return f.name.toLowerCase()
        case "size": return f.sizeMB ?? -1
        case "status": return STATUS_RANK[f.status] ?? -1
        case "found": return f.status === "done" ? f.found : -1
        case "balance": return f.balanceOk === true ? 2 : f.balanceOk === false ? 1 : 0
      }
    }
    return [...files].sort((a, b) => {
      const va = val(a), vb = val(b)
      if (typeof va === "string" && typeof vb === "string") return va.localeCompare(vb, "vi") * dir
      return ((va as number) - (vb as number)) * dir
    })
  }, [files, sort])

  const pickFiles = async () => {
    const sel = await open({ multiple: true, filters: [{ name: "PDF", extensions: ["pdf"] }] })
    if (!sel) return
    const n = addPaths(Array.isArray(sel) ? sel : [sel])
    if (n) toast.success(`Đã thêm ${n} file`)
  }
  const pickFolder = async () => {
    const dir = await open({ directory: true })
    if (!dir || typeof dir !== "string") return
    const pdfs = await listDir(dir)
    const n = addPaths(pdfs)
    n ? toast.success(`Đã thêm ${n} PDF từ thư mục`) : toast.info("Thư mục không có PDF mới")
  }

  // Kéo-thả PDF thật (Tauri drag-drop)
  useEffect(() => {
    let un: (() => void) | undefined
    getCurrentWebview()
      .onDragDropEvent((e) => {
        if (e.payload.type === "over" || e.payload.type === "enter") setDragOver(true)
        else if (e.payload.type === "leave") setDragOver(false)
        else if (e.payload.type === "drop") {
          setDragOver(false)
          const n = addPaths(e.payload.paths)
          if (n) toast.success(`Đã thêm ${n} file`)
        }
      })
      .then((f) => (un = f))
    return () => un?.()
  }, [addPaths])

  const stats = [
    { label: "Tổng file", value: files.length, tone: "text-foreground" },
    { label: "Hoàn tất", value: done, tone: "text-primary" },
    { label: "Đang xử lý", value: processing, tone: "text-foreground" },
    { label: "Ô cần soát", value: totalConflicts, tone: "text-warn" },
  ]

  return (
    <>
      <header className="flex items-center justify-between gap-4 border-b border-border bg-background/55 px-6 py-3 backdrop-blur-xl">
        <div className="shrink-0">
          <h1 className="text-[15px] font-semibold tracking-tight">Dashboard</h1>
          <p className="text-xs text-muted-foreground">{files.length} file · {selected.size > 0 ? `đã chọn ${selected.size}` : "tối đa 150/lần"} · xử lý ngay trên máy</p>
        </div>
        <button onClick={goAnalyze} className="group hidden min-w-0 max-w-md flex-1 items-center gap-2.5 rounded-lg border border-border bg-card/60 px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground md:flex cursor-pointer">
          <Sparkle weight="fill" className="size-4 text-primary" />
          <span className="truncate">Phân tích tài chính</span>
          <kbd className="ml-auto rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{HOTKEY}</kbd>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="outline" size="sm" className="cursor-pointer" onClick={pickFiles}><FilePlus className="size-4" /> Thêm file</Button>
          <Button variant="outline" size="sm" className="cursor-pointer" onClick={pickFolder}><FolderPlus className="size-4" /> Thêm thư mục</Button>
          <button onClick={pickExportDir} title={exportDir ? `Lưu Excel vào: ${exportDir}` : "Mặc định: cạnh PDF (Excel_output). Bấm để đổi thư mục lưu."} className="inline-flex max-w-[150px] items-center gap-1.5 rounded-md border border-border bg-card/60 px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground cursor-pointer">
            <FolderOpen className="size-3.5 shrink-0" /><span className="truncate">{exportDir ? exportDir.split(/[/\\]/).pop() : "cạnh PDF"}</span>
          </button>

          {!converting && selectedDone > 0 && (
            <Button size="sm" variant="outline" className="cursor-pointer" onClick={goAnalyze}><ChartLineUp className="size-4" /> Phân tích ({selectedDone})</Button>
          )}
          {converting ? (
            <>
              {paused ? (
                <Button size="sm" variant="outline" className="cursor-pointer" onClick={resumeQueue}><Play weight="fill" className="size-4" /> Tiếp tục</Button>
              ) : (
                <Button size="sm" variant="outline" className="cursor-pointer" onClick={pauseQueue}><Pause weight="fill" className="size-4" /> Tạm dừng</Button>
              )}
              <Button size="sm" variant="destructive" className="cursor-pointer" onClick={cancelQueue}><StopCircle weight="fill" className="size-4" /> Huỷ tất cả</Button>
            </>
          ) : (
            <Button size="sm" disabled={selectedPending === 0} onClick={() => convertSelected()} className="sheen cursor-pointer font-medium shadow-lg shadow-primary/25 disabled:opacity-50">
              <Play weight="fill" className="size-4" /> Chuyển đổi{selectedPending > 0 ? ` (${selectedPending})` : ""}
            </Button>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 p-6">
        <div className="grid grid-cols-4 gap-3">
          {stats.map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.3, ease: [0.16, 1, 0.3, 1] }} className="rounded-lg border border-border bg-card/60 px-4 py-3 backdrop-blur-sm">
              <div className="text-xs text-muted-foreground">{s.label}</div>
              <div className={cn("mt-1 font-mono text-2xl font-semibold tabular-nums", s.tone)}>{s.value}</div>
            </motion.div>
          ))}
        </div>

        <button onClick={pickFiles} className={cn("group flex items-center justify-center gap-3 rounded-lg border border-dashed py-4 text-sm transition-colors cursor-pointer", dragOver ? "border-primary bg-primary/10 text-foreground" : "border-border bg-card/40 text-muted-foreground hover:border-primary/50 hover:text-foreground")}>
          <UploadSimple className="size-5 transition-transform group-hover:-translate-y-0.5" />
          {dragOver ? "Thả để thêm vào hàng đợi" : "Kéo-thả PDF vào đây, hoặc bấm để chọn"}
        </button>

        <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-card">
          <div className={cn("grid items-center gap-3 border-b border-border px-4 py-2.5 text-[11px] font-medium text-muted-foreground", COLS)}>
            <CheckBox on={allSelected} onClick={() => (allSelected ? selectNone() : selectAll())} title={allSelected ? "Bỏ chọn tất cả" : "Chọn tất cả"} />
            <SortHeader label="Tên file" sortKey="name" sort={sort} onSort={onSort} />
            <SortHeader label="Dung lượng" sortKey="size" sort={sort} onSort={onSort} />
            <SortHeader label="Trạng thái" sortKey="status" sort={sort} onSort={onSort} />
            <SortHeader label="Báo cáo" sortKey="found" sort={sort} onSort={onSort} />
            <SortHeader label="Cân đối" sortKey="balance" sort={sort} onSort={onSort} />
            <span className="text-right uppercase tracking-wide">Thao tác</span>
          </div>
          <ScrollArea className="flex-1">
            {files.length === 0 ? (
              <div className="grid h-40 place-items-center text-sm text-muted-foreground">Chưa có file. Bấm "Thêm file" hoặc kéo-thả PDF vào.</div>
            ) : displayFiles.map((f) => (
              <div key={f.id} onClick={() => f.status === "done" && onOpenReview(f.id)}
                className={cn("grid items-center gap-3 border-b border-border/60 px-4 py-3 text-sm transition-colors", COLS, f.status === "done" ? "cursor-pointer hover:bg-accent/50" : "cursor-default", selected.has(f.id) && "bg-primary/5")}>
                <CheckBox on={selected.has(f.id)} onClick={(e) => { e.stopPropagation(); toggleSelect(f.id) }} title="Chọn file" />
                <div className="flex min-w-0 items-center gap-2.5">
                  <FilePdf weight="fill" className={cn("size-4 shrink-0", f.status === "done" ? "text-primary" : "text-muted-foreground")} />
                  <span className="truncate">{f.name}</span>
                </div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">{f.sizeMB ? fmtSize(f.sizeMB) : "—"}</span>
                <StatusCell f={f} />
                <FoundBadge found={f.found} status={f.status} />
                <BalanceCell f={f} />
                <div className="flex items-center justify-end gap-1">
                  {f.status === "processing" ? (
                    <>
                      {paused ? (
                        <button title="Tiếp tục" onClick={(e) => { e.stopPropagation(); resumeQueue() }} className="grid size-7 place-items-center rounded-md text-primary transition-colors hover:bg-accent cursor-pointer"><Play weight="fill" className="size-4" /></button>
                      ) : (
                        <button title="Tạm dừng" onClick={(e) => { e.stopPropagation(); pauseQueue() }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer"><Pause weight="fill" className="size-4" /></button>
                      )}
                      <button title="Huỷ file này" onClick={(e) => { e.stopPropagation(); cancelFile(f.id) }} className="grid size-7 place-items-center rounded-md text-warn transition-colors hover:bg-warn/15 cursor-pointer"><X className="size-4" /></button>
                    </>
                  ) : converting && f.status === "queued" && selected.has(f.id) ? (
                    <button title="Bỏ khỏi lượt chạy" onClick={(e) => { e.stopPropagation(); cancelFile(f.id) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer"><X className="size-4" /></button>
                  ) : (
                    <>
                      {f.status === "done" && (
                        <>
                          <button title="Xuất Excel" disabled={exportingId === f.id} onClick={(e) => { e.stopPropagation(); exportRow(f.id, f.path) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer">
                            {exportingId === f.id ? <CircleNotch className="size-4 animate-spin" /> : <FileXls className="size-4" />}
                          </button>
                          <button title="Soát báo cáo" onClick={(e) => { e.stopPropagation(); onOpenReview(f.id) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer"><Eye className="size-4" /></button>
                        </>
                      )}
                      <button title="Xoá khỏi hàng đợi" onClick={(e) => { e.stopPropagation(); removeFile(f.id) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive cursor-pointer"><Trash className="size-4" /></button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </ScrollArea>
        </div>
      </div>
    </>
  )
}
