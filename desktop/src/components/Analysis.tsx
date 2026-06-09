import { useEffect, useState } from "react"
import {
  ShieldCheck, Sparkle, TrendUp, Scales, Coins, ChartLineUp, WarningCircle, CircleNotch, ShieldWarning,
} from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { ratios, type RatiosResult, type RatioItem } from "@/lib/api"
import { useStore } from "@/lib/store"

const GROUP_ICON: Record<string, typeof Coins> = {
  thanh_khoan: Coins,
  don_bay: Scales,
  sinh_loi: TrendUp,
  hoat_dong_dong_tien: ChartLineUp,
}

function fmtRatio(v: number | null, unit: RatioItem["unit"]): string {
  if (v === null || v === undefined) return "—"
  if (unit === "%") return `${v.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`
  if (unit === "x") return `${v.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}×`
  return v.toLocaleString("vi-VN")
}

const TONE: Record<string, string> = {
  ok: "text-primary",
  warn: "text-warn",
  bad: "text-destructive",
  neutral: "text-foreground",
}

export function Analysis({ fileId }: { fileId: string }) {
  const file = useStore((s) => s.files.find((f) => f.id === fileId))
  const isDone = file?.status === "done"
  const [state, setState] = useState<{ loading: boolean; data?: RatiosResult; err?: string }>({ loading: false })

  useEffect(() => {
    if (!file || !isDone) { setState({ loading: false }); return }
    let cancelled = false
    setState({ loading: true })
    ratios(file.path)
      .then((d) => !cancelled && setState({ loading: false, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, err: String(e?.message || e) }))
    return () => { cancelled = true }
  }, [file?.path, isDone])

  if (!file)
    return (
      <div className="grid h-full place-items-center text-center text-sm text-muted-foreground">
        Chưa chọn file. Vào Hàng đợi → soát 1 file đã chuyển đổi, rồi mở Phân tích.
      </div>
    )

  return (
    <>
      <header className="flex items-center justify-between border-b border-border bg-background/55 px-6 py-3.5 backdrop-blur-xl">
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold tracking-tight">Phân tích tài chính & rủi ro</h1>
          <p className="truncate text-xs text-muted-foreground">{file.name}</p>
        </div>
        <Button
          size="sm"
          className="sheen shrink-0 cursor-pointer font-medium shadow-lg shadow-primary/30"
          onClick={() => toast.info("Diễn giải bằng AI đang phát triển", { description: "Sẽ gửi CHỈ các tỉ số dưới đây lên cloud (có xác nhận), số do máy tính." })}
        >
          <Sparkle weight="fill" className="size-4" /> Phân tích bằng AI
        </Button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-auto p-6">
        {/* Privacy notice */}
        <div className="flex items-start gap-3 rounded-lg border border-primary/25 bg-primary/8 px-4 py-3">
          <ShieldCheck weight="fill" className="mt-0.5 size-5 shrink-0 text-primary" />
          <div className="text-sm">
            <div className="font-medium">Riêng tư: chỉ gửi chỉ số tổng hợp lên cloud</div>
            <p className="mt-0.5 text-muted-foreground">
              Tỉ số tính ngay trên máy (tất định). Khi bấm "Phân tích bằng AI", chỉ các con số tỉ số (không PDF/bản gốc) được gửi để diễn giải; bạn sẽ xem trước nội dung gửi đi.
            </p>
          </div>
        </div>

        {!isDone && (
          <div className="rounded-lg border border-border bg-card/50 px-4 py-6 text-sm text-muted-foreground">
            File <span className="text-foreground">{file.name}</span> chưa được chuyển đổi. Vào Hàng đợi bấm "Chuyển đổi", rồi quay lại đây để xem tỉ số.
          </div>
        )}

        {state.loading && (
          <div className="flex items-center gap-3 rounded-lg border border-border bg-card/50 px-4 py-6 text-sm text-muted-foreground">
            <CircleNotch className="size-5 animate-spin text-primary" /> Đang tính chỉ số trên máy…
          </div>
        )}

        {state.err && (
          <div className="rounded-lg border border-warn/30 bg-warn/10 px-4 py-3 text-sm text-warn">
            Không lấy được chỉ số (sidecar offline?). {state.err}
          </div>
        )}

        {state.data && (
          <>
            {/* Altman + cờ */}
            <div className="grid grid-cols-[260px_1fr] gap-3 max-lg:grid-cols-1">
              <AltmanCard altman={state.data.altman} />
              <FlagsCard flags={state.data.flags} />
            </div>

            {/* Nhóm tỉ số */}
            <div>
              <div className="mb-2 text-xs text-muted-foreground">Tỉ số tính tất định trên máy (chưa cần AI)</div>
              <div className="grid grid-cols-2 gap-3 max-xl:grid-cols-1">
                {state.data.groups.map((g) => {
                  const Icon = GROUP_ICON[g.key] ?? Coins
                  return (
                    <div key={g.key} className="rounded-lg border border-border bg-card p-4">
                      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                        <Icon className="size-4 text-primary" /> {g.label}
                      </div>
                      <div className="space-y-2">
                        {g.items.map((it) => (
                          <div key={it.label} className="flex items-baseline justify-between gap-3">
                            <span className="text-xs text-muted-foreground" title={it.formula}>{it.label}</span>
                            <span className={cn("font-mono text-sm font-semibold tabular-nums", TONE[it.tone])}>
                              {fmtRatio(it.value, it.unit)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Khoảnh khắc AI */}
            <div className="ai-glow overflow-hidden rounded-xl p-6">
              <div className="relative z-10 flex items-center gap-5">
                <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-primary to-[oklch(0.72_0.13_47)] text-primary-foreground shadow-lg shadow-primary/30">
                  <Sparkle weight="fill" className="size-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">Diễn giải & đánh giá rủi ro bằng AI</h3>
                    <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">Sắp có</span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Xếp hạng rủi ro, điểm mạnh-yếu và cảnh báo dựa trên các tỉ số ở trên. Số do máy tính tất định, AI chỉ diễn giải; chỉ tỉ số được gửi đi.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}

function AltmanCard({ altman }: { altman: RatiosResult["altman"] }) {
  const zoneTone = altman?.zone === "an_toan" ? "text-primary" : altman?.zone === "nguy_hiem" ? "text-destructive" : "text-warn"
  const ZoneIcon = altman?.zone === "an_toan" ? ShieldCheck : ShieldWarning
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
        <ZoneIcon weight="fill" className={cn("size-4", zoneTone)} /> Điểm rủi ro Altman Z″
      </div>
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
