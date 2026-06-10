import { useEffect, useState } from "react"
import { ShieldCheck, CheckCircle, WarningCircle, FloppyDisk, Trash, Check, EnvelopeSimple } from "@phosphor-icons/react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { saveKey, type Provider } from "@/lib/api"
import { useLlm } from "@/lib/llm"
import { useTheme, ACCENTS } from "@/lib/theme"

const PROVIDER_META: Record<Provider, { name: string; hint: string }> = {
  anthropic: { name: "Claude (Anthropic)", hint: "Lấy API key tại console.anthropic.com — trả phí theo token, không train trên dữ liệu." },
  google: { name: "Gemini (Google)", hint: "Lấy API key tại aistudio.google.com — có bậc MIỄN PHÍ (Flash)." },
}
const PROVIDERS: Provider[] = ["anthropic", "google"]

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/80">{children}</div>
}

export function Settings() {
  const { settingsOpen, closeSettings, provider, model, status, setProvider, setModel, refreshStatus } = useLlm()
  const accent = useTheme((s) => s.accent)
  const setAccent = useTheme((s) => s.setAccent)
  const [keyInput, setKeyInput] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (settingsOpen) {
      refreshStatus()
      setKeyInput("")
    }
  }, [settingsOpen, provider, refreshStatus])

  const ps = status?.[provider]
  const meta = PROVIDER_META[provider]
  const models = ps?.models ?? []

  const onSave = async () => {
    if (!keyInput.trim()) return
    setSaving(true)
    try {
      const { status: st } = await saveKey(provider, keyInput.trim())
      useLlm.setState({ status: st })
      setKeyInput("")
      toast.success(`Đã lưu khoá ${meta.name} vào keychain`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const onDelete = async () => {
    setSaving(true)
    try {
      const { status: st } = await saveKey(provider, "")
      useLlm.setState({ status: st })
      toast.info(`Đã xoá khoá ${meta.name} khỏi keychain`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={settingsOpen} onOpenChange={(o) => !o && closeSettings()}>
      <DialogContent className="flex max-h-[85vh] flex-col sm:max-w-md">
        <DialogHeader className="shrink-0">
          <DialogTitle>Cài đặt</DialogTitle>
        </DialogHeader>

        <div className="min-h-0 flex-1 space-y-6 overflow-auto pr-1">
          {/* ---------- AI (BYOK) ---------- */}
          <section>
            <SectionTitle>Diễn giải bằng AI (BYOK)</SectionTitle>
            <p className="mb-2.5 text-xs text-muted-foreground">
              Tự cấp API key. Khoá lưu trong keychain hệ điều hành — không vào file/repo, chỉ gửi tới đúng nhà cung cấp bạn chọn.
            </p>

            <div className="mb-3 grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
              {PROVIDERS.map((p) => (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  className={cn("rounded-md px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer", provider === p ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
                >
                  {PROVIDER_META[p].name}
                </button>
              ))}
            </div>

            <div className="mb-2.5 flex flex-wrap items-center gap-2 text-xs">
              {ps?.hasKey ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/12 px-2 py-0.5 font-medium text-primary">
                  <CheckCircle weight="fill" className="size-3.5" /> {ps.inKeychain ? "Đã lưu khoá" : `Khoá từ ${ps.envVar}`}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-warn/12 px-2 py-0.5 font-medium text-warn">
                  <WarningCircle weight="fill" className="size-3.5" /> Chưa có khoá
                </span>
              )}
              {ps && !ps.sdk && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/12 px-2 py-0.5 font-medium text-destructive">
                  <WarningCircle weight="fill" className="size-3.5" /> Thiếu SDK
                </span>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">API key</label>
              <div className="flex items-center gap-2">
                <Input
                  type="password"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  placeholder={ps?.hasKey ? "•••••••• (nhập để thay khoá)" : "Dán API key…"}
                  className="font-mono"
                />
                <Button size="sm" onClick={onSave} disabled={saving || !keyInput.trim()} className="shrink-0 cursor-pointer"><FloppyDisk className="size-4" /> Lưu</Button>
                {ps?.inKeychain && (
                  <Button size="sm" variant="outline" onClick={onDelete} disabled={saving} title="Xoá khoá khỏi keychain" className="shrink-0 cursor-pointer"><Trash className="size-4" /></Button>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">{meta.hint}</p>
            </div>

            <div className="mt-3 space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Model</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="">Mặc định ({models[0] ?? "—"})</option>
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <p className="text-[11px] text-muted-foreground">
                {provider === "google" ? "Model Gemini có thể đổi theo thời gian; nếu báo 'không tồn tại', chọn model khác." : "Sonnet 4.6 cân bằng; Opus 4.8 phân tích sâu hơn."}
              </p>
            </div>

            <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-primary/20 bg-primary/6 px-3 py-2.5 text-xs">
              <ShieldCheck weight="fill" className="mt-0.5 size-4 shrink-0 text-primary" />
              <p className="text-muted-foreground">Chỉ các <span className="text-foreground">tỉ số tổng hợp</span> được gửi đi (không PDF/Excel/bản gốc). Bạn xem trước nội dung trước khi xác nhận.</p>
            </div>
          </section>

          {/* ---------- Giao diện ---------- */}
          <section className="border-t border-border pt-4">
            <SectionTitle>Giao diện · Màu nhấn</SectionTitle>
            <div className="flex flex-wrap items-center gap-2.5">
              {ACCENTS.map((a) => {
                const on = accent === a.id
                return (
                  <button
                    key={a.id}
                    onClick={() => setAccent(a.id)}
                    title={a.name}
                    className={cn("grid size-8 place-items-center rounded-full ring-2 ring-offset-2 ring-offset-popover transition-all cursor-pointer", on ? "ring-foreground/60" : "ring-transparent hover:ring-border")}
                    style={{ background: `oklch(${a.primary})` }}
                  >
                    {on && <Check weight="bold" className="size-4" style={{ color: `oklch(${a.fg})` }} />}
                  </button>
                )
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">Đang dùng: <span className="text-foreground">{ACCENTS.find((a) => a.id === accent)?.name ?? "—"}</span></p>
          </section>

          {/* ---------- Giới thiệu ---------- */}
          <section className="border-t border-border pt-4">
            <SectionTitle>Giới thiệu</SectionTitle>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between border-b border-border/60 pb-2">
                <span className="text-muted-foreground">Ứng dụng</span><span className="font-medium">BCTC → Excel · Thông tư 200</span>
              </div>
              <div className="flex items-center justify-between border-b border-border/60 pb-2">
                <span className="text-muted-foreground">Phiên bản</span><span className="font-mono text-xs">v2.0 · Tauri + React</span>
              </div>
              <div className="flex items-center justify-between border-b border-border/60 pb-2">
                <span className="text-muted-foreground">Lõi xử lý</span><span className="font-mono text-xs">PyMuPDF + Tesseract (local)</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Tác giả</span>
                <a href="mailto:tantaingo.dev@gmail.com" className="inline-flex items-center gap-1.5 font-mono text-xs text-primary hover:underline">
                  <EnvelopeSimple className="size-3.5" /> tantaingo.dev@gmail.com
                </a>
              </div>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground/80">OCR và tính tỉ số 100% trên máy. Diễn giải bằng AI là tuỳ chọn (BYOK), chỉ gửi tỉ số tổng hợp khi bạn xác nhận.</p>
            <p className="mt-1.5 text-[11px] text-muted-foreground/60">Capybara: "Capybara Sprite Sheet" by Rainloaf (rainloaf.itch.io).</p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
