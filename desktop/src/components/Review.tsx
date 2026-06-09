import { useState } from "react"
import {
  ArrowLeft, CaretLeft, CaretRight, MagnifyingGlassPlus, MagnifyingGlassMinus,
  CheckCircle, WarningCircle, ArrowsClockwise, PencilSimple, FileXls, FilePdf,
} from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { fmtVN } from "@/lib/format"
import { MOCK_STATEMENTS, MOCK_BALANCE, type Row, type Statement } from "@/lib/mock"

export function Review({ fileId, onBack }: { fileId: string; onBack: () => void }) {
  const statements = MOCK_STATEMENTS[fileId] ?? MOCK_STATEMENTS.f03
  const balanceOk = MOCK_BALANCE.every((b) => b.ok)

  return (
    <>
      <header className="flex items-center justify-between gap-4 border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground cursor-pointer">
            <ArrowLeft className="size-4" />
          </button>
          <div className="flex items-center gap-2">
            <FilePdf weight="fill" className="size-4 text-primary" />
            <span className="text-sm font-medium">03_CTCP DV Bến Thành 2025.pdf</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-muted px-2 py-1 font-mono text-[11px] text-muted-foreground">Năm 2025</span>
          <Button size="sm" className="cursor-pointer">
            <FileXls className="size-4" /> Xuất Excel
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(440px,560px)]">
        <PdfPane />
        <DataPane statements={statements} balanceOk={balanceOk} />
      </div>
    </>
  )
}

function PdfPane() {
  const [page, setPage] = useState(8)
  return (
    <div className="flex min-w-0 flex-col border-r border-border bg-[oklch(0.13_0.004_260)]">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-1">
          <IconBtn onClick={() => setPage((p) => Math.max(1, p - 1))}><CaretLeft className="size-4" /></IconBtn>
          <span className="px-1 font-mono text-xs text-muted-foreground">Trang {page} / 41</span>
          <IconBtn onClick={() => setPage((p) => Math.min(41, p + 1))}><CaretRight className="size-4" /></IconBtn>
        </div>
        <div className="flex items-center gap-1">
          <IconBtn><MagnifyingGlassMinus className="size-4" /></IconBtn>
          <span className="px-1 font-mono text-xs text-muted-foreground">100%</span>
          <IconBtn><MagnifyingGlassPlus className="size-4" /></IconBtn>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="grid place-items-center p-6">
          {/* Khung trang PDF — pdf.js sẽ render trang thật vào đây */}
          <div className="aspect-[1/1.414] w-full max-w-[460px] rounded-sm border border-border bg-[oklch(0.94_0.004_90)] shadow-2xl shadow-black/40">
            <div className="grid h-full place-items-center p-6 text-center">
              <div className="text-[oklch(0.45_0.02_260)]">
                <FilePdf weight="thin" className="mx-auto size-12 opacity-40" />
                <p className="mt-3 text-sm font-medium">Khung xem PDF (pdf.js)</p>
                <p className="mt-1 text-xs opacity-70">
                  Trang {page} sẽ render ở đây. Bấm vào một ô số bên phải để nhảy tới vùng tương ứng trên trang.
                </p>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

function DataPane({ statements, balanceOk }: { statements: Statement[]; balanceOk: boolean }) {
  const [tab, setTab] = useState(statements[0].key)
  return (
    <div className="flex min-h-0 flex-col bg-card/30">
      <BalancePanel ok={balanceOk} />
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
            <StatementTable statement={s} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

function BalancePanel({ ok }: { ok: boolean }) {
  return (
    <div className="border-b border-border px-4 py-3">
      <div className="mb-2 flex items-center gap-2">
        {ok ? (
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
            <CheckCircle weight="fill" className="size-4" /> Cân đối khớp
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-warn">
            <WarningCircle weight="fill" className="size-4" /> Lệch cân đối
          </span>
        )}
        <span className="text-xs text-muted-foreground">· 3 phép kiểm</span>
      </div>
      <div className="space-y-1">
        {MOCK_BALANCE.map((b) => (
          <div key={b.label} className="flex items-center gap-2 text-xs">
            {b.ok ? (
              <CheckCircle weight="fill" className="size-3.5 shrink-0 text-primary" />
            ) : (
              <WarningCircle weight="fill" className="size-3.5 shrink-0 text-warn" />
            )}
            <span className="text-muted-foreground">{b.label}</span>
            <span className="ml-auto font-mono text-[11px] tabular-nums text-muted-foreground/70">{b.detail}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatementTable({ statement }: { statement: Statement }) {
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
            <RowLine key={i} r={r} skey={statement.key} />
          ))}
        </tbody>
      </table>
    </ScrollArea>
  )
}

function RowLine({ r, skey }: { r: Row; skey: string }) {
  const isGroup = r.kind === "header" || r.kind === "section" || r.kind === "total"
  return (
    <tr className={cn("border-b border-border/40", isGroup && "bg-muted/30")}>
      <td className={cn("px-4 py-1.5", isGroup && "font-semibold")} style={{ paddingLeft: `${16 + r.level * 14}px` }}>
        {r.label}
      </td>
      <td className="py-1.5 text-center font-mono text-xs text-muted-foreground">{r.code ?? ""}</td>
      <ValueCell value={r.cur} flag={r.flagCur} code={r.code} col="cuối năm" skey={skey} bold={isGroup} />
      <ValueCell value={r.prior} flag={r.flagPrior} code={r.code} col="đầu năm" skey={skey} bold={isGroup} />
    </tr>
  )
}

function ValueCell({
  value, flag, code, col, skey, bold,
}: { value: number | null; flag?: boolean; code: string | null; col: string; skey: string; bold?: boolean }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value)

  if (value === null && !flag)
    return <td className="px-3 py-1.5 text-right font-mono text-xs text-muted-foreground/40">·</td>

  if (editing)
    return (
      <td className="px-2 py-1">
        <input
          autoFocus
          defaultValue={val ?? ""}
          onBlur={(e) => { setVal(Number(e.target.value.replace(/\D/g, "")) || null); setEditing(false) }}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          className="w-full rounded border border-primary bg-background px-2 py-0.5 text-right font-mono text-xs tabular-nums outline-none"
        />
      </td>
    )

  return (
    <td className={cn("group/cell relative px-3 py-1.5 text-right font-mono text-xs tabular-nums", flag && "bg-flag/15", bold && "font-semibold")}>
      <span className={cn(flag && "text-warn")}>{fmtVN(val)}</span>
      <span className="absolute inset-y-0 right-1.5 hidden items-center gap-0.5 group-hover/cell:flex">
        <button title="Sửa giá trị" onClick={() => setEditing(true)} className="grid size-5 place-items-center rounded bg-background/80 text-muted-foreground hover:text-foreground cursor-pointer">
          <PencilSimple className="size-3" />
        </button>
        {flag && (
          <button
            title="Đọc lại ô (re-OCR)"
            onClick={() => toast.info(`Đọc lại ô ${skey} · mã ${code} · ${col}`, { description: "Re-OCR vùng ô ở DPI cao + whitelist số (B-A3)." })}
            className="grid size-5 place-items-center rounded bg-background/80 text-warn hover:text-foreground cursor-pointer"
          >
            <ArrowsClockwise className="size-3" />
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
