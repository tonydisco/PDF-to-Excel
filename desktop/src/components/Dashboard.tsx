import { useState } from "react"
import {
  FilePlus, FolderPlus, Play, FilePdf, Eye, Trash, CheckCircle,
  WarningCircle, CircleNotch, Clock, UploadSimple,
} from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { fmtSize } from "@/lib/format"
import { MOCK_FILES, type QueueFile } from "@/lib/mock"

function StatusCell({ f }: { f: QueueFile }) {
  if (f.status === "done")
    return (
      <span className="inline-flex items-center gap-1.5 text-primary">
        <CheckCircle weight="fill" className="size-4" /> Hoàn tất
      </span>
    )
  if (f.status === "error")
    return (
      <span className="inline-flex items-center gap-1.5 text-destructive">
        <WarningCircle weight="fill" className="size-4" /> Mẫu khác (NH)
      </span>
    )
  if (f.status === "processing")
    return (
      <div className="flex items-center gap-2">
        <CircleNotch className="size-4 animate-spin text-primary" />
        <Progress value={f.progress * 100} className="h-1.5 w-20" />
        <span className="font-mono text-xs text-muted-foreground">{Math.round(f.progress * 100)}%</span>
      </div>
    )
  return (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground">
      <Clock className="size-4" /> Chờ
    </span>
  )
}

function FoundBadge({ found }: { found: number }) {
  const tone = found === 3 ? "text-primary" : found === 0 ? "text-muted-foreground" : "text-warn"
  return (
    <div className="flex items-center gap-1">
      <span className={cn("font-mono text-xs font-medium", tone)}>{found}/3</span>
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <span key={i} className={cn("h-3.5 w-1 rounded-full", i < found ? "bg-primary" : "bg-muted")} />
        ))}
      </div>
    </div>
  )
}

export function Dashboard({ onOpenReview }: { onOpenReview: (id: string) => void }) {
  const [files] = useState<QueueFile[]>(MOCK_FILES)
  const done = files.filter((f) => f.status === "done").length
  const processing = files.filter((f) => f.status === "processing").length
  const totalConflicts = files.reduce((s, f) => s + f.conflicts, 0)

  const stats = [
    { label: "Tổng file", value: files.length, tone: "text-foreground" },
    { label: "Hoàn tất", value: done, tone: "text-primary" },
    { label: "Đang xử lý", value: processing, tone: "text-foreground" },
    { label: "Ô cần soát", value: totalConflicts, tone: "text-warn" },
  ]

  return (
    <>
      {/* Topbar */}
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-3.5">
        <div>
          <h1 className="text-[15px] font-semibold tracking-tight">Hàng đợi chuyển đổi</h1>
          <p className="text-xs text-muted-foreground">
            {files.length} file · tối đa 150/lần · dữ liệu xử lý ngay trên máy
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="cursor-pointer">
            <FilePlus className="size-4" /> Thêm file
          </Button>
          <Button variant="outline" size="sm" className="cursor-pointer">
            <FolderPlus className="size-4" /> Thêm thư mục
          </Button>
          <Button size="sm" className="cursor-pointer font-medium">
            <Play weight="fill" className="size-4" /> Chuyển đổi
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 p-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-3">
          {stats.map((s) => (
            <div key={s.label} className="rounded-lg border border-border bg-card px-4 py-3">
              <div className="text-xs text-muted-foreground">{s.label}</div>
              <div className={cn("mt-1 font-mono text-2xl font-semibold tabular-nums", s.tone)}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Dropzone */}
        <button className="group flex items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-card/40 py-4 text-sm text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground cursor-pointer">
          <UploadSimple className="size-5 transition-transform group-hover:-translate-y-0.5" />
          Kéo-thả PDF vào đây, hoặc bấm để chọn
        </button>

        {/* File list */}
        <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-card">
          <div className="grid grid-cols-[1fr_88px_120px_92px_110px_72px] items-center gap-3 border-b border-border px-4 py-2.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            <span>Tên file</span>
            <span>Dung lượng</span>
            <span>Trạng thái</span>
            <span>Báo cáo</span>
            <span>Cân đối</span>
            <span className="text-right">Thao tác</span>
          </div>
          <ScrollArea className="flex-1">
            {files.map((f) => (
              <div
                key={f.id}
                onClick={() => f.status === "done" && onOpenReview(f.id)}
                className={cn(
                  "grid grid-cols-[1fr_88px_120px_92px_110px_72px] items-center gap-3 border-b border-border/60 px-4 py-3 text-sm transition-colors",
                  f.status === "done" ? "cursor-pointer hover:bg-accent/50" : "cursor-default",
                )}
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <FilePdf weight="fill" className={cn("size-4 shrink-0", f.status === "done" ? "text-primary" : "text-muted-foreground")} />
                  <span className="truncate">{f.name}</span>
                </div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">{fmtSize(f.sizeMB)}</span>
                <StatusCell f={f} />
                <FoundBadge found={f.found} />
                <BalanceCell f={f} />
                <div className="flex items-center justify-end gap-1">
                  {f.status === "done" && (
                    <button
                      title="Soát báo cáo"
                      onClick={(e) => { e.stopPropagation(); onOpenReview(f.id) }}
                      className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer"
                    >
                      <Eye className="size-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => e.stopPropagation()}
                    className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive cursor-pointer"
                  >
                    <Trash className="size-4" />
                  </button>
                </div>
              </div>
            ))}
          </ScrollArea>
        </div>
      </div>
    </>
  )
}

function BalanceCell({ f }: { f: QueueFile }) {
  if (f.balanceOk === null) return <span className="text-xs text-muted-foreground">—</span>
  if (f.balanceOk)
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/12 px-2 py-0.5 text-xs font-medium text-primary">
        <CheckCircle weight="fill" className="size-3.5" /> Khớp
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-warn/12 px-2 py-0.5 text-xs font-medium text-warn">
      <WarningCircle weight="fill" className="size-3.5" /> Lệch
    </span>
  )
}
