import { ShieldCheck, Sparkle, TrendUp, Scales, Coins, Info } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const RATIOS = [
  { group: "Thanh khoản", icon: Coins, items: [
    { label: "Hệ số thanh toán hiện hành", value: "7,33", tone: "ok" },
    { label: "Hệ số thanh toán nhanh", value: "7,33", tone: "ok" },
  ]},
  { group: "Đòn bẩy", icon: Scales, items: [
    { label: "Nợ / Vốn chủ sở hữu", value: "0,10", tone: "ok" },
    { label: "Nợ / Tổng tài sản", value: "9,0%", tone: "ok" },
  ]},
  { group: "Sinh lời", icon: TrendUp, items: [
    { label: "ROA", value: "6,5%", tone: "neutral" },
    { label: "ROE", value: "7,1%", tone: "neutral" },
    { label: "Biên lợi nhuận gộp", value: "39,5%", tone: "ok" },
  ]},
]

export function Analysis() {
  return (
    <>
      <header className="flex items-center justify-between border-b border-border px-6 py-3.5">
        <div>
          <h1 className="text-[15px] font-semibold tracking-tight">Phân tích tài chính & rủi ro</h1>
          <p className="text-xs text-muted-foreground">03_CTCP DV Bến Thành 2025 · năm 2025 so với 2024</p>
        </div>
        <Button size="sm" className="cursor-pointer">
          <Sparkle weight="fill" className="size-4" /> Phân tích bằng AI
        </Button>
      </header>

      <ScrollableBody>
        {/* Privacy notice */}
        <div className="flex items-start gap-3 rounded-lg border border-primary/25 bg-primary/8 px-4 py-3">
          <ShieldCheck weight="fill" className="mt-0.5 size-5 shrink-0 text-primary" />
          <div className="text-sm">
            <div className="font-medium">Riêng tư: chỉ gửi chỉ số tổng hợp lên cloud</div>
            <p className="mt-0.5 text-muted-foreground">
              Tỉ số được tính ngay trên máy. Khi bấm "Phân tích bằng AI", chỉ các con số tỉ số (không PDF, không bản gốc) được gửi để diễn giải, và bạn sẽ xem trước đúng nội dung gửi đi.
            </p>
          </div>
        </div>

        {/* Local ratios */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
            <Info className="size-3.5" /> Tỉ số tính tất định trên máy (chưa cần AI)
          </div>
          <div className="grid grid-cols-3 gap-3">
            {RATIOS.map((g) => {
              const Icon = g.icon
              return (
                <div key={g.group} className="rounded-lg border border-border bg-card p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <Icon className="size-4 text-primary" /> {g.group}
                  </div>
                  <div className="space-y-2.5">
                    {g.items.map((it) => (
                      <div key={it.label} className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground">{it.label}</span>
                        <span className={cn("font-mono text-sm font-semibold tabular-nums", it.tone === "ok" ? "text-primary" : "text-foreground")}>
                          {it.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* AI placeholder */}
        <div className="grid place-items-center rounded-lg border border-dashed border-border bg-card/40 py-12 text-center">
          <div className="max-w-sm">
            <Sparkle className="mx-auto size-7 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">Diễn giải & đánh giá rủi ro bằng AI</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Sắp có: nhận định điểm mạnh/yếu, xếp hạng rủi ro (Thấp/TB/Cao) và cảnh báo, dựa trên các tỉ số ở trên. Số liệu do máy tính, AI chỉ diễn giải.
            </p>
          </div>
        </div>
      </ScrollableBody>
    </>
  )
}

function ScrollableBody({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-auto p-6">{children}</div>
}
