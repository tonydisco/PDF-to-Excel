import { useEffect, useRef, useState } from "react"
import {
  ArrowLeft, CaretLeft, CaretRight, MagnifyingGlassPlus, MagnifyingGlassMinus,
  CheckCircle, WarningCircle, ArrowsClockwise, PencilSimple, FileXls, FilePdf, CircleNotch, FolderOpen,
} from "@phosphor-icons/react"
import { open } from "@tauri-apps/plugin-dialog"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { fmtVN } from "@/lib/format"
import { type Row, type Statement, type BalanceCheck } from "@/lib/types"
import { convert, exportXlsx, reocr, pageUrl, type ConvertResult } from "@/lib/api"
import { useStore } from "@/lib/store"

export function Review({ fileId, onBack }: { fileId: string; onBack: () => void }) {
  const file = useStore((s) => s.files.find((f) => f.id === fileId))
  const cached = useStore((s) => s.results[fileId])
  const exportDir = useStore((s) => s.exportDir)
  const setExportDir = useStore((s) => s.setExportDir)
  const editCount = useStore((s) => Object.keys(s.editsByFile[fileId] ?? {}).length)
  const [exporting, setExporting] = useState(false)
  const [state, setState] = useState<{ loading: boolean; data?: ConvertResult; err?: string }>({ loading: !cached })

  const pickDir = async () => {
    const dir = await open({ directory: true })
    if (typeof dir === "string") {
      setExportDir(dir)
      toast.success("Đã đặt thư mục lưu", { description: dir })
    }
  }
  const doExport = async () => {
    if (!file) return
    setExporting(true)
    try {
      const r = await exportXlsx(file.path, exportDir, useStore.getState().fileEdits(fileId))
      toast.success(editCount ? `Đã xuất Excel (kèm ${editCount} ô đã sửa)` : "Đã xuất Excel", { description: r.out_path })
    } catch (e) {
      toast.error("Xuất Excel lỗi", { description: e instanceof Error ? e.message : String(e) })
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    if (!file) return
    if (cached) { setState({ loading: false, data: cached }); return }
    let cancelled = false
    setState({ loading: true })
    convert(file.path)
      .then((d) => !cancelled && setState({ loading: false, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, err: String(e?.message || e) }))
    return () => { cancelled = true }
  }, [file?.path, cached])

  if (!file) {
    return (
      <div className="grid h-full place-items-center text-center text-sm text-muted-foreground">
        <div>
          <p>Chưa chọn file để soát.</p>
          <button onClick={onBack} className="mt-2 text-primary hover:underline cursor-pointer">← Về Hàng đợi</button>
        </div>
      </div>
    )
  }

  const statements: Statement[] = state.data?.statements ?? []
  const balance: BalanceCheck[] = state.data?.balance ?? []
  const balanceOk = state.data ? state.data.balanceOk : null

  return (
    <>
      <header className="flex items-center justify-between gap-4 border-b border-border bg-background/55 px-5 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer">
            <ArrowLeft className="size-4" />
          </button>
          <div className="flex items-center gap-2">
            <FilePdf weight="fill" className="size-4 text-primary" />
            <span className="text-sm font-medium">{file.name}</span>
            {state.loading && <CircleNotch className="size-4 animate-spin text-primary" />}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {state.err && <span className="max-w-[180px] truncate text-xs text-warn" title={state.err}>Lỗi: {state.err}</span>}
          {editCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/12 px-2 py-0.5 text-[11px] font-medium text-primary" title="Số ô đã sửa sẽ ghi vào Excel">
              <PencilSimple weight="fill" className="size-3" /> {editCount} ô đã sửa
            </span>
          )}
          <button
            onClick={pickDir}
            title={exportDir ? `Lưu vào: ${exportDir}` : "Mặc định: cạnh PDF (Excel_output). Bấm để đổi thư mục."}
            className="inline-flex max-w-[200px] items-center gap-1.5 rounded-md border border-border bg-card/60 px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground cursor-pointer"
          >
            <FolderOpen className="size-3.5 shrink-0" />
            <span className="truncate">{exportDir ? exportDir.split(/[/\\]/).pop() : "cạnh PDF"}</span>
          </button>
          <Button size="sm" className="cursor-pointer" disabled={exporting || state.loading} onClick={doExport}>
            {exporting ? <CircleNotch className="size-4 animate-spin" /> : <FileXls className="size-4" />} Xuất Excel
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(440px,560px)] grid-rows-[minmax(0,1fr)]">
        <PdfPane
          path={file.path}
          pageCount={state.data?.pageCount ?? file.pages ?? 1}
          initialPage={state.data?.pages?.[statements[0]?.key] ?? state.data?.pages?.CDKT ?? 1}
          located={state.data?.pages ?? {}}
          available={!!state.data}
        />
        <DataPane statements={statements} balance={balance} balanceOk={balanceOk} loading={state.loading} fileId={fileId} />
      </div>
    </>
  )
}

const ZOOM_STEPS = [60, 75, 90, 100, 120, 145, 175]
const STMT_LABEL: Record<string, string> = { CDKT: "Cân đối KT", KQHDKD: "Kết quả KD", LCTT: "Lưu chuyển TT" }

function PageImage({ src }: { src: string }) {
  const [loaded, setLoaded] = useState(false)
  return (
    <>
      {!loaded && (
        <div className="absolute inset-0 grid place-items-center">
          <CircleNotch className="size-6 animate-spin text-[oklch(0.5_0.02_260)]" />
        </div>
      )}
      <img
        src={src}
        alt=""
        draggable={false}
        onLoad={() => setLoaded(true)}
        className={cn("h-full w-full object-contain transition-opacity duration-150", loaded ? "opacity-100" : "opacity-0")}
      />
    </>
  )
}

function PdfPane({
  path, pageCount, initialPage, located, available,
}: { path: string; pageCount: number; initialPage: number; located: Record<string, number>; available: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const pageEls = useRef<Map<number, HTMLDivElement>>(new Map())
  const [current, setCurrent] = useState(initialPage)
  const [visible, setVisible] = useState<Set<number>>(new Set())
  const [zi, setZi] = useState(3) // ZOOM_STEPS index = 100%
  const [pageInput, setPageInput] = useState(String(initialPage))
  useEffect(() => setPageInput(String(current)), [current])

  const jumpTo = (n: number) => {
    const p = Math.max(1, Math.min(pageCount, Math.round(n) || 1))
    pageEls.current.get(p)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  // Lazy-load (chỉ render ảnh trang gần viewport) + theo dõi trang hiện tại
  useEffect(() => {
    if (!available) return
    const root = scrollRef.current
    if (!root) return
    const lazy = new IntersectionObserver((ents) => {
      setVisible((prev) => {
        let changed = false
        const next = new Set(prev)
        for (const e of ents) if (e.isIntersecting) {
          const p = Number((e.target as HTMLElement).dataset.page)
          if (!next.has(p)) { next.add(p); changed = true }
        }
        return changed ? next : prev
      })
    }, { root, rootMargin: "900px 0px" })
    const center = new IntersectionObserver((ents) => {
      for (const e of ents) if (e.isIntersecting) setCurrent(Number((e.target as HTMLElement).dataset.page))
    }, { root, rootMargin: "-48% 0px -48% 0px" })
    pageEls.current.forEach((el) => { lazy.observe(el); center.observe(el) })
    return () => { lazy.disconnect(); center.disconnect() }
  }, [available, pageCount])

  // Mở đúng trang báo cáo lần đầu
  useEffect(() => {
    if (!available) return
    const t = setTimeout(() => pageEls.current.get(initialPage)?.scrollIntoView({ block: "start" }), 80)
    return () => clearTimeout(t)
  }, [available, initialPage])

  const chips = (["CDKT", "KQHDKD", "LCTT"] as const).filter((k) => located[k])

  return (
    <div className="flex min-h-0 min-w-0 flex-col border-r border-border bg-[oklch(0.12_0.004_260)]">
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <div className="flex items-center gap-1">
          <IconBtn onClick={() => jumpTo(current - 1)}><CaretLeft className="size-4" /></IconBtn>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <input
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => e.key === "Enter" && jumpTo(Number(pageInput))}
              onBlur={() => jumpTo(Number(pageInput))}
              title="Nhập số trang rồi Enter để nhảy tới"
              className="w-9 rounded border border-border bg-muted px-1 py-0.5 text-center font-mono text-xs outline-none focus:border-primary"
            />
            <span className="font-mono">/ {pageCount}</span>
          </div>
          <IconBtn onClick={() => jumpTo(current + 1)}><CaretRight className="size-4" /></IconBtn>
        </div>

        {chips.length > 0 && (
          <div className="hidden items-center gap-1 xl:flex">
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground/60">Nhảy tới</span>
            {chips.map((k) => (
              <button
                key={k}
                onClick={() => jumpTo(located[k])}
                className="rounded-md border border-border bg-card/60 px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground cursor-pointer"
              >
                {STMT_LABEL[k]}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1">
          <IconBtn onClick={() => setZi((z) => Math.max(0, z - 1))}><MagnifyingGlassMinus className="size-4" /></IconBtn>
          <span className="w-10 px-1 text-center font-mono text-xs text-muted-foreground">{ZOOM_STEPS[zi]}%</span>
          <IconBtn onClick={() => setZi((z) => Math.min(ZOOM_STEPS.length - 1, z + 1))}><MagnifyingGlassPlus className="size-4" /></IconBtn>
        </div>
      </div>

      <div ref={scrollRef} className="relative flex-1 overflow-auto">
        {available ? (
          <div
            className="mx-auto flex flex-col items-center gap-4 px-4 py-5"
            style={{ width: `${ZOOM_STEPS[zi]}%`, maxWidth: ZOOM_STEPS[zi] <= 100 ? 800 : undefined }}
          >
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
              <div
                key={p}
                data-page={p}
                ref={(el) => { if (el) pageEls.current.set(p, el); else pageEls.current.delete(p) }}
                className="relative aspect-[1/1.414] w-full scroll-mt-3 overflow-hidden rounded-sm border border-border bg-[oklch(0.96_0.004_90)] shadow-xl shadow-black/40"
              >
                {visible.has(p) ? (
                  <PageImage src={pageUrl(path, p, 140)} />
                ) : (
                  <div className="absolute inset-0 grid place-items-center">
                    <span className="font-mono text-xs text-[oklch(0.55_0.02_260)] opacity-60">Trang {p}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="grid h-full place-items-center p-6 text-center text-[oklch(0.55_0.02_260)]">
            <div>
              <FilePdf weight="thin" className="mx-auto size-12 opacity-40" />
              <p className="mt-3 text-sm font-medium">Đang chờ OCR…</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DataPane({
  statements, balance, balanceOk, loading, fileId,
}: { statements: Statement[]; balance: BalanceCheck[]; balanceOk: boolean | null; loading: boolean; fileId: string }) {
  const [tab, setTab] = useState<Statement["key"]>(statements[0]?.key ?? "CDKT")
  useEffect(() => { if (statements[0]) setTab(statements[0].key) }, [statements])

  if (loading) return <LoadingPane />

  if (statements.length === 0)
    return (
      <div className="grid min-h-0 flex-1 place-items-center bg-card/30 p-6 text-center text-sm text-muted-foreground">
        <div>
          <WarningCircle className="mx-auto size-7 text-warn" />
          <p className="mt-2">Không bóc được báo cáo nào theo mẫu Thông tư 200.</p>
          <p className="mt-1 text-xs">File có thể theo mẫu khác (ngân hàng/TCTD) hoặc sidecar chưa sẵn sàng.</p>
        </div>
      </div>
    )

  return (
    <div className="flex min-h-0 flex-col bg-card/30">
      <BalancePanel balance={balance} ok={balanceOk} />
      <Tabs value={tab} onValueChange={(v) => setTab(v as Statement["key"])} className="flex min-h-0 flex-1 flex-col">
        <div className="px-4 pt-3">
          <TabsList className="w-full">
            {statements.map((s) => (
              <TabsTrigger key={s.key} value={s.key} className="flex-1 cursor-pointer text-xs">
                {s.key === "CDKT" ? "Cân đối KT" : s.key === "KQHDKD" ? "Kết quả KD" : "Lưu chuyển TT"}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        {statements.map((s) => (
          <TabsContent key={s.key} value={s.key} className="mt-0 min-h-0 flex-1">
            <StatementTable statement={s} fileId={fileId} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

function LoadingPane() {
  return (
    <div className="flex min-h-0 flex-col items-center justify-center gap-3 bg-card/30 text-center">
      <CircleNotch className="size-7 animate-spin text-primary" />
      <div>
        <p className="text-sm font-medium">Đang đọc OCR trên máy…</p>
        <p className="mt-1 text-xs text-muted-foreground">Định vị báo cáo · bóc số · kiểm cân đối</p>
      </div>
    </div>
  )
}

function BalancePanel({ balance, ok }: { balance: BalanceCheck[]; ok: boolean | null }) {
  return (
    <div className="border-b border-border px-4 py-3">
      <div className="mb-2 flex items-center gap-2">
        {ok === null ? (
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
            <WarningCircle className="size-4" /> Chưa đủ chỉ tiêu để kiểm
          </span>
        ) : ok ? (
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
            <CheckCircle weight="fill" className="size-4" /> Cân đối khớp
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-warn">
            <WarningCircle weight="fill" className="size-4" /> Lệch cân đối
          </span>
        )}
        {balance.length > 0 && <span className="text-xs text-muted-foreground">· {balance.length} phép kiểm</span>}
      </div>
      <div className="space-y-1">
        {balance.map((b, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            {b.ok ? (
              <CheckCircle weight="fill" className="size-3.5 shrink-0 text-primary" />
            ) : (
              <WarningCircle weight="fill" className="size-3.5 shrink-0 text-warn" />
            )}
            <span className="truncate text-muted-foreground">{b.label}</span>
            <span className="ml-auto shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground/70">{b.detail}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatementTable({ statement, fileId }: { statement: Statement; fileId: string }) {
  return (
    <ScrollArea className="h-full">
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10 bg-card">
          <tr className="border-b border-border text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2 text-left font-medium">Chỉ tiêu</th>
            <th className="w-12 py-2 text-center font-medium">Mã</th>
            <th className="w-32 px-3 py-2 text-right font-medium">Cuối năm</th>
            <th className="w-32 px-3 py-2 text-right font-medium">Đầu năm</th>
          </tr>
        </thead>
        <tbody>
          {statement.rows.map((r, i) => (
            <RowLine key={i} r={r} skey={statement.key} fileId={fileId} />
          ))}
        </tbody>
      </table>
    </ScrollArea>
  )
}

function RowLine({ r, skey, fileId }: { r: Row; skey: string; fileId: string }) {
  const isGroup = r.kind === "header" || r.kind === "section" || r.kind === "total"
  return (
    <tr className={cn("border-b border-border/40", isGroup && "bg-muted/30")}>
      <td className={cn("px-4 py-1.5", isGroup && "font-semibold")} style={{ paddingLeft: `${16 + r.level * 14}px` }}>
        {r.label}
      </td>
      <td className="py-1.5 text-center font-mono text-xs text-muted-foreground">{r.code ?? ""}</td>
      <ValueCell value={r.cur} flag={r.flagCur} code={r.code} col="cur" skey={skey} fileId={fileId} bold={isGroup} />
      <ValueCell value={r.prior} flag={r.flagPrior} code={r.code} col="prior" skey={skey} fileId={fileId} bold={isGroup} />
    </tr>
  )
}

function ValueCell({
  value, flag, code, col, skey, fileId, bold,
}: { value: number | null; flag?: boolean; code: string | null; col: "cur" | "prior"; skey: string; fileId: string; bold?: boolean }) {
  const edit = useStore((s) => (code ? s.editsByFile[fileId]?.[`${skey}|${code}|${col}`] : undefined))
  const setEdit = useStore((s) => s.setEdit)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)

  const edited = edit !== undefined
  const shown = edited ? edit : value

  const commit = (raw: string) => {
    setEditing(false)
    if (!code) return
    const cleaned = raw.replace(/[^\d]/g, "")
    setEdit(fileId, skey, code, col, cleaned === "" ? null : Number(cleaned))
  }

  const onReocr = async () => {
    if (!code || busy) return
    setBusy(true)
    try {
      const v = await reocr(fileId, skey, code, col) // fileId === path
      setEdit(fileId, skey, code, col, v)
      toast.success(`Đã đọc lại mã ${code}`, { description: `Giá trị: ${v === null ? "—" : v.toLocaleString("vi-VN")}` })
    } catch (e) {
      toast.error("Re-OCR lỗi", { description: e instanceof Error ? e.message : String(e) })
    } finally {
      setBusy(false)
    }
  }

  if (shown === null && !flag && !edited)
    return <td className="px-3 py-1.5 text-right font-mono text-xs text-muted-foreground/40">·</td>

  if (editing)
    return (
      <td className="px-2 py-1">
        <input
          autoFocus
          defaultValue={shown ?? ""}
          onBlur={(e) => commit(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          className="w-full rounded border border-primary bg-background px-2 py-0.5 text-right font-mono text-xs tabular-nums outline-none"
        />
      </td>
    )

  return (
    <td className={cn("group/cell relative px-3 py-1.5 text-right font-mono text-xs tabular-nums", flag && !edited && "bg-flag/15", edited && "bg-primary/10", bold && "font-semibold")}>
      <span className={cn(edited ? "text-primary" : flag && "text-warn")} title={edited ? "Đã sửa (sẽ ghi vào Excel)" : undefined}>
        {busy ? "…" : fmtVN(shown)}
      </span>
      <span className="absolute inset-y-0 right-1.5 hidden items-center gap-0.5 group-hover/cell:flex">
        <button title="Sửa giá trị" onClick={() => setEditing(true)} className="grid size-5 place-items-center rounded bg-background/80 text-muted-foreground hover:text-foreground cursor-pointer">
          <PencilSimple className="size-3" />
        </button>
        {code && (
          <button
            title="Đọc lại ô (re-OCR ở DPI cao)"
            onClick={onReocr}
            disabled={busy}
            className={cn("grid size-5 place-items-center rounded bg-background/80 hover:text-foreground cursor-pointer", flag && !edited ? "text-warn" : "text-muted-foreground")}
          >
            {busy ? <CircleNotch className="size-3 animate-spin" /> : <ArrowsClockwise className="size-3" />}
          </button>
        )}
      </span>
    </td>
  )
}

function IconBtn({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button onClick={onClick} className="grid size-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer">
      {children}
    </button>
  )
}
