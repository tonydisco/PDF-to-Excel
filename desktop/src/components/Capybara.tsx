import { useEffect, useRef, useState } from "react"
import capyUrl from "@/assets/capybara.png"

// Capybara đi bộ lúc chuyển đổi (sprite sheet 200x60: 5 khung x 2 hàng, 40x30/khung;
// hàng 0 = đi phải, hàng 1 = đi trái). Sprite: "Capybara Sprite Sheet" by Rainloaf.
const S = 1.8 // hệ số phóng (pixel-art)
const FW = 40 * S // 72
const FH = 30 * S // 54
const COLS = 5
const SPEED = 2.4 // px mỗi nhịp
const TICK = 55 // ms mỗi nhịp
const PAD = 10 // lề ngang

export function Capybara({ label }: { label?: string }) {
  const trackRef = useRef<HTMLDivElement>(null)
  const xRef = useRef(PAD)
  const dirRef = useRef<1 | -1>(1)
  const [x, setX] = useState(PAD)
  const [dir, setDir] = useState<1 | -1>(1)

  useEffect(() => {
    const id = setInterval(() => {
      const w = trackRef.current?.clientWidth ?? 320
      const max = Math.max(PAD, w - FW - PAD)
      let nx = xRef.current + SPEED * dirRef.current
      if (nx >= max) {
        nx = max
        dirRef.current = -1
        setDir(-1)
      } else if (nx <= PAD) {
        nx = PAD
        dirRef.current = 1
        setDir(1)
      }
      xRef.current = nx
      setX(nx)
    }, TICK)
    return () => clearInterval(id)
  }, [])

  return (
    <div ref={trackRef} className="relative h-16 shrink-0 overflow-hidden rounded-lg border border-border bg-card/40">
      {/* mặt đất */}
      <div className="absolute inset-x-3 bottom-2 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
      {/* nhãn */}
      {label && (
        <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-xs text-muted-foreground/70">
          {label}
        </span>
      )}
      {/* bóng dưới chân */}
      <div
        className="absolute bottom-[7px] h-1 rounded-full bg-black/30 blur-[2px] transition-none"
        style={{ width: FW * 0.6, transform: `translateX(${x + FW * 0.2}px)` }}
      />
      {/* capybara */}
      <div
        title="Capybara sprite by Rainloaf (rainloaf.itch.io)"
        className="capy-sprite absolute bottom-2"
        style={{
          width: FW,
          height: FH,
          transform: `translateX(${x}px)`,
          backgroundImage: `url(${capyUrl})`,
          backgroundSize: `${200 * S}px ${60 * S}px`,
          backgroundPositionY: dir === 1 ? "0px" : `${-FH}px`,
          ["--capy-shift" as string]: `${-COLS * FW}px`,
          imageRendering: "pixelated",
        }}
      />
    </div>
  )
}
