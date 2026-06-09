// Nền tối SẠCH, chỉ điểm xuyết "water flow" trong VÙNG NHỎ (không full màn hình):
// 2 màu xanh lá + xanh blue THẪM cuộn vào nhau bằng mix-blend screen, bọc trong
// orb có mask mờ viền ở góc trên-trái (gần brand) + 1 orb mờ nhỏ góc dưới-phải.
const SOFT_MASK =
  "radial-gradient(circle at 50% 50%, #000 24%, transparent 70%)"

function WaterOrb({ className, intensity = 1 }: { className: string; intensity?: number }) {
  return (
    <div
      className={"absolute " + className}
      style={{ maskImage: SOFT_MASK, WebkitMaskImage: SOFT_MASK, opacity: intensity }}
    >
      <div
        className="water-swirl absolute -inset-1/4 blur-[60px]"
        style={{
          background:
            "conic-gradient(from 0deg at 50% 50%, oklch(0.62 0.13 165 / 85%), oklch(0.40 0.13 256 / 90%), oklch(0.62 0.13 165 / 80%), oklch(0.36 0.12 258 / 90%), oklch(0.62 0.13 165 / 85%))",
        }}
      />
      <div
        className="water-swirl-rev absolute -inset-1/4 blur-[70px]"
        style={{
          background:
            "conic-gradient(from 140deg at 50% 50%, oklch(0.38 0.13 256 / 85%), oklch(0.64 0.12 168 / 75%), oklch(0.34 0.12 258 / 88%), oklch(0.6 0.13 162 / 75%), oklch(0.38 0.13 256 / 85%))",
        }}
      />
    </div>
  )
}

export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.15_0.005_262)]">
      <WaterOrb className="-top-[16%] -left-[8%] size-[42vw]" intensity={0.9} />
      <WaterOrb className="-bottom-[18%] right-[-6%] size-[30vw]" intensity={0.5} />
      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
