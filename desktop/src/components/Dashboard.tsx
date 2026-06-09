import { useEffect, useState } from "react"
import {
  FilePlus, FolderPlus, Play, FilePdf, Eye, Trash, CheckCircle,
  WarningCircle, CircleNotch, Clock, UploadSimple, Sparkle,
} from "@phosphor-icons/react"
import { motion } from "motion/react"
import { open } from "@tauri-apps/plugin-dialog"
import { getCurrentWebview } from "@tauri-apps/api/webview"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { fmtSize } from "@/lib/format"
import { listDir } from "@/lib/api"
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

export function Dashboard({ onOpenReview, onAskAI }: { onOpenReview: (id: string) => void; onAskAI: () => void }) {
  const { files, addPaths, convertAll, removeFile, converting } = useStore()
  const [dragOver, setDragOver] = useState(false)

  const done = files.filter((f) => f.status === "done").length
  const processing = files.filter((f) => f.status === "processing").length
  const totalConflicts = files.reduce((s, f) => s + (f.status === "done" ? f.conflicts : 0), 0)
  const queued = files.filter((f) => f.status === "queued" || f.status === "error").length

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
          <h1 className="text-[15px] font-semibold tracking-tight">Hàng đợi chuyển đổi</h1>
          <p className="text-xs text-muted-foreground">{files.length} file · tối đa 150/lần · xử lý ngay trên máy</p>
        </div>
        <button onClick={onAskAI} className="group hidden min-w-0 max-w-md flex-1 items-center gap-2.5 rounded-lg border border-border bg-card/60 px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground md:flex cursor-pointer">
          <Sparkle weight="fill" className="size-4 text-primary" />
          <span className="truncate">Hỏi AI về sức khỏe tài chính, rủi ro doanh nghiệp…</span>
          <kbd className="ml-auto rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">⌘K</kbd>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="outline" size="sm" className="cursor-pointer" onClick={pickFiles}><FilePlus className="size-4" /> Thêm file</Button>
          <Button variant="outline" size="sm" className="cursor-pointer" onClick={pickFolder}><FolderPlus className="size-4" /> Thêm thư mục</Button>
          <Button size="sm" disabled={converting || queued === 0} onClick={() => convertAll()} className="sheen cursor-pointer font-medium shadow-lg shadow-primary/25 disabled:opacity-50">
            {converting ? <CircleNotch className="size-4 animate-spin" /> : <Play weight="fill" className="size-4" />}
            {converting ? "Đang chuyển…" : "Chuyển đổi"}
          </Button>
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
          <div className="grid grid-cols-[1fr_88px_140px_92px_110px_72px] items-center gap-3 border-b border-border px-4 py-2.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            <span>Tên file</span><span>Dung lượng</span><span>Trạng thái</span><span>Báo cáo</span><span>Cân đối</span><span className="text-right">Thao tác</span>
          </div>
          <ScrollArea className="flex-1">
            {files.length === 0 ? (
              <div className="grid h-40 place-items-center text-sm text-muted-foreground">Chưa có file. Bấm "Thêm file" hoặc kéo-thả PDF vào.</div>
            ) : files.map((f) => (
              <div key={f.id} onClick={() => f.status === "done" && onOpenReview(f.id)}
                className={cn("grid grid-cols-[1fr_88px_140px_92px_110px_72px] items-center gap-3 border-b border-border/60 px-4 py-3 text-sm transition-colors", f.status === "done" ? "cursor-pointer hover:bg-accent/50" : "cursor-default")}>
                <div className="flex min-w-0 items-center gap-2.5">
                  <FilePdf weight="fill" className={cn("size-4 shrink-0", f.status === "done" ? "text-primary" : "text-muted-foreground")} />
                  <span className="truncate">{f.name}</span>
                </div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">{f.sizeMB ? fmtSize(f.sizeMB) : "—"}</span>
                <StatusCell f={f} />
                <FoundBadge found={f.found} status={f.status} />
                <BalanceCell f={f} />
                <div className="flex items-center justify-end gap-1">
                  {f.status === "done" && (
                    <button title="Soát báo cáo" onClick={(e) => { e.stopPropagation(); onOpenReview(f.id) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer"><Eye className="size-4" /></button>
                  )}
                  <button title="Xoá khỏi hàng đợi" onClick={(e) => { e.stopPropagation(); removeFile(f.id) }} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive cursor-pointer"><Trash className="size-4" /></button>
                </div>
              </div>
            ))}
          </ScrollArea>
        </div>
      </div>
    </>
  )
}
