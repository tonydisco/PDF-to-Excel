import { useEffect, useState } from "react"
import {
  ShieldCheck, Sparkle, TrendUp, Scales, Coins, ChartLineUp, WarningCircle, CircleNotch, ShieldWarning,
  Gear, ThumbsUp, ThumbsDown, Warning, Lightbulb, FileXls, FilePdf, FilePlus, Trophy, Star, X,
} from "@phosphor-icons/react"
import { open } from "@tauri-apps/plugin-dialog"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import {
  ratios, analyzePreview, analyze, analyzeComparePreview, analyzeCompare,
  type RatiosResult, type RatioItem, type AnalysisResult, type CompareResult, type CompareItem,
} from "@/lib/api"
import { useStore, type AnalysisItem, type AnalysisMode } from "@/lib/store"
import { useLlm } from "@/lib/llm"

const GROUP_ICON: Record<string, typeof Coins> = {
  thanh_khoan: Coins,
  don_bay: Scales,
  sinh_loi: TrendUp,
  hoat_dong_dong_tien: ChartLineUp,
}

const RISK: Record<AnalysisResult["risk_rating"], { label: string; tone: string; icon: typeof ShieldCheck }> = {
  thap: { label: "Rủi ro thấp", tone: "text-primary", icon: ShieldCheck },
  trung_binh: { label: "Rủi ro trung bình", tone: "text-warn", icon: ShieldWarning },
  cao: { label: "Rủi ro cao", tone: "text-destructive", icon: ShieldWarning },
}

function fmtRatio(v: number | null, unit: RatioItem["unit"]): string {
  if (v === null || v === undefined) return "—"
  if (unit === "%") return `${v.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`
  if (unit === "x") return `${v.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}×`
  return v.toLocaleString("vi-VN")
}

const TONE: Record<string, string> = { ok: "text-primary", warn: "text-warn", bad: "text-destructive", neutral: "text-foreground" }

const providerName = (p: string) => (p === "anthropic" ? "Claude" : "Gemini")

// ============================================================ orchestrator
export function Analysis() {
  const items = useStore((s) => s.analysis)
  const mode = useStore((s) => s.analysisMode)
  const setMode = useStore((s) => s.setAnalysisMode)
  const addExcel = useStore((s) => s.addAnalysisExcel)
  const removeItem = useStore((s) => s.removeAnalysisItem)
  const [activePath, setActivePath] = useState(items[0]?.path ?? "")

  useEffect(() => {
    if (items.length && !items.some((i) => i.path === activePath)) setActivePath(items[0].path)
  }, [items, activePath])

  const pickExcel = async () => {
    const sel = await open({ multiple: true, filters: [{ name: "Excel", extensions: ["xlsx", "xls"] }] })
    if (!sel) return
    const paths = Array.isArray(sel) ? sel : [sel]
    let n = 0
    paths.forEach((p) => { if (addExcel(p)) n++ })
    n ? toast.success(`Đã thêm ${n} file Excel`) : toast.info("Không thêm được (trùng hoặc không phải .xlsx)")
  }

  const active = items.find((i) => i.path === activePath) ?? items[0]

  return (
    <>
      <header className="flex items-center justify-between gap-3 border-b border-border bg-background/55 px-6 py-3 backdrop-blur-xl">
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold tracking-tight">Phân tích tài chính & rủi ro</h1>
          <p className="text-xs text-muted-foreground">{items.length} báo cáo · số do máy tính tất định, AI chỉ diễn giải</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {items.length > 0 && (
            <div className="grid grid-cols-2 gap-0.5 rounded-lg bg-muted p-0.5">
              {(["each", "compare"] as AnalysisMode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={cn("rounded-md px-3 py-1 text-xs font-medium transition-colors cursor-pointer", mode === m ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
                  {m === "each" ? "Từng file" : "So sánh"}
                </button>
              ))}
            </div>
          )}
          <Button size="sm" variant="outline" className="cursor-pointer" onClick={pickExcel}><FilePlus className="size-4" /> Thêm Excel</Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
        {items.length === 0 ? (
          <EmptyState onPickExcel={pickExcel} />
        ) : (
          <>
            <FileChips items={items} mode={mode} activePath={active?.path ?? ""} onPick={setActivePath} onRemove={removeItem} />
            {mode === "each"
              ? active && <SingleAnalysis key={active.path} path={active.path} name={active.name} />
              : <CompareAnalysis items={items} />}
          </>
        )}
      </div>
    </>
  )
}

function EmptyState({ onPickExcel }: { onPickExcel: () => void }) {
  return (
    <div className="grid flex-1 place-items-center text-center text-sm text-muted-foreground">
      <div className="max-w-md space-y-3">
        <ChartLineUp className="mx-auto size-10 opacity-40" />
        <p>Chưa có báo cáo nào để phân tích.</p>
        <p className="text-xs leading-relaxed">
          Vào <span className="text-foreground">Hàng đợi</span> → tick các file đã chuyển đổi → bấm <span className="text-foreground">"Phân tích đã chọn"</span>; hoặc tải file Excel (do app này xuất) lên.
        </p>
        <Button size="sm" variant="outline" onClick={onPickExcel} className="cursor-pointer"><FilePlus className="size-4" /> Thêm Excel</Button>
      </div>
    </div>
  )
}

function FileChips({ items, mode, activePath, onPick, onRemove }: {
  items: AnalysisItem[]; mode: AnalysisMode; activePath: string; onPick: (p: string) => void; onRemove: (p: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => {
        const Icon = it.kind === "excel" ? FileXls : FilePdf
        const active = mode === "each" && it.path === activePath
        return (
          <div key={it.path} className={cn("inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-colors", active ? "border-primary/50 bg-primary/10 text-foreground" : "border-border bg-card/60 text-muted-foreground")}>
            <button onClick={() => mode === "each" && onPick(it.path)} className={cn("inline-flex min-w-0 max-w-[200px] items-center gap-1.5", mode === "each" && "cursor-pointer hover:text-foreground")}>
              <Icon weight={active ? "fill" : "regular"} className={cn("size-3.5 shrink-0", it.kind === "excel" && "text-primary")} />
              <span className="truncate">{it.name}</span>
            </button>
            <button onClick={() => onRemove(it.path)} title="Bỏ khỏi phân tích" className="text-muted-foreground/60 transition-colors hover:text-destructive cursor-pointer"><X className="size-3" /></button>
          </div>
        )
      })}
    </div>
  )
}

function PrivacyNotice({ compare }: { compare?: boolean }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-primary/25 bg-primary/8 px-4 py-3">
      <ShieldCheck weight="fill" className="mt-0.5 size-5 shrink-0 text-primary" />
      <div className="text-sm">
        <div className="font-medium">Riêng tư: chỉ gửi chỉ số tổng hợp lên cloud</div>
        <p className="mt-0.5 text-muted-foreground">
          Tỉ số tính ngay trên máy (tất định). Khi bấm phân tích{compare ? " so sánh" : ""}, chỉ các con số tỉ số (không PDF/Excel/bản gốc) được gửi để diễn giải; bạn sẽ xem trước nội dung gửi đi.
        </p>
      </div>
    </div>
  )
}

// ============================================================ từng file
function SingleAnalysis({ path, name }: { path: string; name: string }) {
  const provider = useLlm((s) => s.provider)
  const [state, setState] = useState<{ loading: boolean; data?: RatiosResult; err?: string }>({ loading: true })
  const [aiResult, setAiResult] = useState<AnalysisResult | null>(null)
  const [consentOpen, setConsentOpen] = useState(false)

  useEffect(() => {
    setAiResult(null)
    setState({ loading: true })
    let cancelled = false
    ratios(path)
      .then((d) => !cancelled && setState({ loading: false, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, err: String(e?.message || e) }))
    return () => { cancelled = true }
  }, [path])

  const providerLabel = providerName(provider)

  return (
    <div className="space-y-5">
      <PrivacyNotice />

      {state.loading && (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-card/50 px-4 py-6 text-sm text-muted-foreground">
          <CircleNotch className="size-5 animate-spin text-primary" /> Đang tính chỉ số trên máy…
        </div>
      )}
      {state.err && (
        <div className="rounded-lg border border-warn/30 bg-warn/10 px-4 py-3 text-sm text-warn">Không lấy được chỉ số. {state.err}</div>
      )}

      {state.data && (
        <>
          <div className="grid grid-cols-[260px_1fr] gap-3 max-lg:grid-cols-1">
            <AltmanCard altman={state.data.altman} />
            <FlagsCard flags={state.data.flags} />
          </div>

          <div>
            <div className="mb-2 text-xs text-muted-foreground">Tỉ số tính tất định trên máy (chưa cần AI)</div>
            <div className="grid grid-cols-2 gap-3 max-xl:grid-cols-1">
              {state.data.groups.map((g) => {
                const Icon = GROUP_ICON[g.key] ?? Coins
                return (
                  <div key={g.key} className="rounded-lg border border-border bg-card p-4">
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium"><Icon className="size-4 text-primary" /> {g.label}</div>
                    <div className="space-y-2">
                      {g.items.map((it) => (
                        <div key={it.label} className="flex items-baseline justify-between gap-3">
                          <span className="text-xs text-muted-foreground" title={it.formula}>{it.label}</span>
                          <span className={cn("font-mono text-sm font-semibold tabular-nums", TONE[it.tone])}>{fmtRatio(it.value, it.unit)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {aiResult ? (
            <AiResultCard result={aiResult} providerLabel={providerLabel} onRerun={() => setConsentOpen(true)} />
          ) : (
            <button onClick={() => setConsentOpen(true)} className="ai-glow group overflow-hidden rounded-xl p-6 text-left cursor-pointer">
              <div className="relative z-10 flex items-center gap-5">
                <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary to-[oklch(0.72_0.13_47)] text-primary-foreground shadow-lg shadow-primary/30">
                  <Sparkle weight="fill" className="size-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold">Diễn giải & đánh giá rủi ro bằng AI</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Xếp hạng rủi ro, điểm mạnh-yếu và khuyến nghị dựa trên các tỉ số ở trên. Chỉ tỉ số được gửi đi (có xem trước).</p>
                </div>
                <span className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-transform group-hover:translate-x-0.5">Phân tích →</span>
              </div>
            </button>
          )}
        </>
      )}

      <ConsentDialog
        open={consentOpen}
        onClose={() => setConsentOpen(false)}
        title={`Xác nhận gửi: ${name}`}
        getPreview={() => analyzePreview(path)}
        submit={async () => {
          const res = await analyze(path, useLlm.getState().provider, useLlm.getState().model || undefined)
          setAiResult(res.result)
        }}
      />
    </div>
  )
}

// ============================================================ so sánh
function CompareAnalysis({ items }: { items: AnalysisItem[] }) {
  const provider = useLlm((s) => s.provider)
  const [result, setResult] = useState<CompareResult | null>(null)
  const [consentOpen, setConsentOpen] = useState(false)
  const cItems: CompareItem[] = items.map((i) => ({ path: i.path, label: i.name }))
  const enough = items.length >= 2

  useEffect(() => { setResult(null) }, [items])

  return (
    <div className="space-y-5">
      <PrivacyNotice compare />

      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium"><Scales className="size-4 text-primary" /> So sánh {items.length} báo cáo</div>
        <div className="mb-4 flex flex-wrap gap-1.5">
          {items.map((it) => (
            <span key={it.path} className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card/60 px-2 py-1 text-xs text-muted-foreground">
              {it.kind === "excel" ? <FileXls className="size-3.5 text-primary" /> : <FilePdf className="size-3.5" />} {it.name}
            </span>
          ))}
        </div>
        {!enough && <p className="mb-3 text-xs text-warn">Cần ít nhất 2 báo cáo để so sánh. Thêm file hoặc đổi sang "Từng file".</p>}
        <Button size="sm" disabled={!enough} onClick={() => setConsentOpen(true)} className="sheen cursor-pointer font-medium shadow-lg shadow-primary/25">
          <Sparkle weight="fill" className="size-4" /> Phân tích so sánh bằng AI
        </Button>
      </div>

      {result && <CompareResultCard result={result} providerLabel={providerName(provider)} />}

      <ConsentDialog
        open={consentOpen}
        onClose={() => setConsentOpen(false)}
        title={`Xác nhận gửi: so sánh ${items.length} báo cáo`}
        getPreview={() => analyzeComparePreview(cItems)}
        submit={async () => {
          const r = await analyzeCompare(cItems, useLlm.getState().provider, useLlm.getState().model || undefined)
          setResult(r.result)
        }}
      />
    </div>
  )
}

function CompareResultCard({ result, providerLabel }: { result: CompareResult; providerLabel: string }) {
  const lists: { title: string; items: string[]; icon: typeof Trophy; tone: string }[] = [
    { title: "Xếp hạng rủi ro", items: result.ranking, icon: Trophy, tone: "text-primary" },
    { title: "Điểm nổi bật khi đối chiếu", items: result.highlights, icon: Star, tone: "text-warn" },
    { title: "Khuyến nghị", items: result.recommendations, icon: Lightbulb, tone: "text-foreground" },
  ]
  return (
    <div className="overflow-hidden rounded-xl border border-primary/25 bg-card">
      <div className="flex items-center gap-4 border-b border-border bg-primary/5 p-5">
        <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-background text-primary"><Scales weight="fill" className="size-6" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-base font-semibold">So sánh báo cáo</span>
            <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">AI · {providerLabel}</span>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">{result.summary}</p>
        </div>
      </div>
      <div className="divide-y divide-border">
        {lists.map((l) => {
          const LIcon = l.icon
          return (
            <div key={l.title} className="p-4">
              <div className={cn("mb-2 flex items-center gap-2 text-sm font-medium", l.tone)}><LIcon weight="fill" className="size-4" /> {l.title}</div>
              {l.items.length ? (
                <ul className="space-y-1.5">
                  {l.items.map((it, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground"><span className="mt-1.5 size-1 shrink-0 rounded-full bg-current opacity-50" /> {it}</li>
                  ))}
                </ul>
              ) : <p className="text-sm text-muted-foreground/60">—</p>}
            </div>
          )
        })}
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground/70">Số do máy tính tất định; AI chỉ diễn giải. Tham khảo, không thay thế tư vấn chuyên môn.</p>
    </div>
  )
}

// ============================================================ consent dùng chung
function ConsentDialog({ open, onClose, title, getPreview, submit }: {
  open: boolean; onClose: () => void; title: string
  getPreview: () => Promise<string>; submit: () => Promise<void>
}) {
  const { provider, model, status, openSettings } = useLlm()
  const [payload, setPayload] = useState("")
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const ps = status?.[provider]
  const hasKey = !!ps?.hasKey
  const providerLabel = providerName(provider)
  const modelLabel = model || ps?.models?.[0] || "mặc định"

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setPayload("")
    getPreview()
      .then(setPayload)
      .catch((e) => toast.error(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
    // chỉ chạy khi mở dialog
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const run = async () => {
    setRunning(true)
    try {
      await submit()
      toast.success("Đã có kết quả phân tích")
      onClose()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="flex max-h-[85vh] flex-col sm:max-w-lg">
        <DialogHeader className="shrink-0">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Đây chính là nội dung sẽ gửi tới <span className="text-foreground">{providerLabel}</span> ({modelLabel}). Chỉ tỉ số tổng hợp — không PDF/Excel, không bản gốc.
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-border bg-muted/40">
          {loading ? (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground"><CircleNotch className="size-4 animate-spin" /> Đang tính tỉ số trên máy…</div>
          ) : (
            <pre className="whitespace-pre-wrap p-3 font-mono text-[11px] leading-relaxed text-foreground/90">{payload || "—"}</pre>
          )}
        </div>

        {!hasKey && (
          <div className="flex shrink-0 items-center justify-between gap-3 rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-warn">
            <span className="inline-flex items-center gap-1.5"><WarningCircle weight="fill" className="size-4" /> Chưa có API key cho {providerLabel}.</span>
            <Button size="sm" variant="outline" onClick={() => { onClose(); openSettings() }} className="cursor-pointer"><Gear className="size-4" /> Cài đặt</Button>
          </div>
        )}

        <DialogFooter className="shrink-0">
          <Button variant="outline" onClick={onClose} className="cursor-pointer">Huỷ</Button>
          <Button onClick={run} disabled={loading || running || !hasKey || !payload} className="sheen cursor-pointer">
            {running ? <CircleNotch className="size-4 animate-spin" /> : <Sparkle weight="fill" className="size-4" />}
            {running ? "Đang phân tích…" : "Gửi & phân tích"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ============================================================ thẻ kết quả 1 file
function AiResultCard({ result, providerLabel, onRerun }: { result: AnalysisResult; providerLabel: string; onRerun: () => void }) {
  const rm = RISK[result.risk_rating] ?? RISK.trung_binh
  const RIcon = rm.icon
  const lists: { title: string; items: string[]; icon: typeof ThumbsUp; tone: string }[] = [
    { title: "Điểm mạnh", items: result.strengths, icon: ThumbsUp, tone: "text-primary" },
    { title: "Điểm yếu", items: result.weaknesses, icon: ThumbsDown, tone: "text-warn" },
    { title: "Cảnh báo rủi ro", items: result.warnings, icon: Warning, tone: "text-destructive" },
    { title: "Khuyến nghị", items: result.recommendations, icon: Lightbulb, tone: "text-foreground" },
  ]
  return (
    <div className="overflow-hidden rounded-xl border border-primary/25 bg-card">
      <div className="flex items-center gap-4 border-b border-border bg-primary/5 p-5">
        <div className={cn("grid size-12 shrink-0 place-items-center rounded-xl bg-background", rm.tone)}><RIcon weight="fill" className="size-6" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={cn("text-base font-semibold", rm.tone)}>{result.risk_label || rm.label}</span>
            <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">AI · {providerLabel}</span>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">{result.summary}</p>
        </div>
        <Button size="sm" variant="outline" onClick={onRerun} className="shrink-0 cursor-pointer" title="Phân tích lại"><Sparkle className="size-4" /> Chạy lại</Button>
      </div>
      <div className="grid grid-cols-2 gap-px bg-border max-md:grid-cols-1">
        {lists.map((l) => {
          const LIcon = l.icon
          return (
            <div key={l.title} className="bg-card p-4">
              <div className={cn("mb-2 flex items-center gap-2 text-sm font-medium", l.tone)}><LIcon weight="fill" className="size-4" /> {l.title}</div>
              {l.items.length ? (
                <ul className="space-y-1.5">
                  {l.items.map((it, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground"><span className="mt-1.5 size-1 shrink-0 rounded-full bg-current opacity-50" /> {it}</li>
                  ))}
                </ul>
              ) : <p className="text-sm text-muted-foreground/60">—</p>}
            </div>
          )
        })}
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground/70">Số do máy tính tất định; AI chỉ diễn giải. Tham khảo, không thay thế tư vấn chuyên môn.</p>
    </div>
  )
}

function AltmanCard({ altman }: { altman: RatiosResult["altman"] }) {
  const zoneTone = altman?.zone === "an_toan" ? "text-primary" : altman?.zone === "nguy_hiem" ? "text-destructive" : "text-warn"
  const ZoneIcon = altman?.zone === "an_toan" ? ShieldCheck : ShieldWarning
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground"><ZoneIcon weight="fill" className={cn("size-4", zoneTone)} /> Điểm rủi ro Altman Z″</div>
      {altman ? (
        <div className="flex items-end gap-2">
          <span className={cn("font-mono text-3xl font-semibold tabular-nums", zoneTone)}>{altman.value}</span>
          <span className={cn("mb-1 text-sm font-medium", zoneTone)}>{altman.label}</span>
        </div>
      ) : (
        <div className="mt-2 text-sm text-muted-foreground">Chưa đủ chỉ tiêu để tính</div>
      )}
      <p className="mt-1 text-[11px] text-muted-foreground/70">&gt;2.6 an toàn · 1.1–2.6 cảnh báo · &lt;1.1 nguy hiểm</p>
    </div>
  )
}

function FlagsCard({ flags }: { flags: string[] }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <WarningCircle weight="fill" className={cn("size-4", flags.length ? "text-warn" : "text-primary")} />
        {flags.length ? `${flags.length} điểm cần lưu ý` : "Không có cảnh báo nổi bật"}
      </div>
      {flags.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {flags.map((f) => (
            <span key={f} className="rounded-full border border-warn/30 bg-warn/10 px-2.5 py-1 text-[11px] text-warn">{f}</span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Các tỉ số đều trong ngưỡng lành mạnh.</p>
      )}
    </div>
  )
}
