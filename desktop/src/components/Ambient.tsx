import { useReducedMotion } from "motion/react"

// Nền tối SẠCH + điểm xuyết "dòng nước" trong VÙNG NHỎ:
// xanh lá + xanh blue THẪM cuộn vào nhau (mix-blend screen), được làm méo bằng
// SVG turbulence + displacement có animate -> khối màu CHẢY như dòng nước.
const SOFT_MASK = "radial-gradient(circle at 50% 50%, #000 24%, transparent 70%)"

function WaterOrb({ className, intensity = 1 }: { className: string; intensity?: number }) {
  return (
    <div
      className={"absolute " + className}
      style={{ maskImage: SOFT_MASK, WebkitMaskImage: SOFT_MASK, opacity: intensity }}
    >
      <div
        className="water-swirl absolute -inset-1/4"
        style={{
          filter: "url(#liquid) blur(34px)",
          background:
            "conic-gradient(from 0deg at 50% 50%, oklch(0.62 0.13 165 / 85%), oklch(0.40 0.13 256 / 92%), oklch(0.62 0.13 165 / 80%), oklch(0.36 0.12 258 / 92%), oklch(0.62 0.13 165 / 85%))",
        }}
      />
      <div
        className="water-swirl-rev absolute -inset-1/4"
        style={{
          filter: "url(#liquid) blur(40px)",
          background:
            "conic-gradient(from 140deg at 50% 50%, oklch(0.38 0.13 256 / 88%), oklch(0.64 0.12 168 / 75%), oklch(0.34 0.12 258 / 90%), oklch(0.6 0.13 162 / 75%), oklch(0.38 0.13 256 / 88%))",
        }}
      />
    </div>
  )
}

export function Ambient() {
  const reduce = useReducedMotion()
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.15_0.005_262)]">
      {/* Bộ lọc "chất lỏng": turbulence + displacement, animate baseFrequency để màu CHẢY */}
      <svg className="absolute size-0" aria-hidden focusable="false">
        <defs>
          <filter id="liquid" x="-30%" y="-30%" width="160%" height="160%">
            <feTurbulence type="fractalNoise" baseFrequency="0.009 0.013" numOctaves="2" seed="7" result="noise">
              {!reduce && (
                <animate
                  attributeName="baseFrequency"
                  dur="22s"
                  values="0.009 0.013; 0.014 0.008; 0.007 0.012; 0.009 0.013"
                  repeatCount="indefinite"
                />
              )}
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="120" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      <WaterOrb className="-top-[16%] -left-[8%] size-[42vw]" intensity={0.9} />
      <WaterOrb className="-bottom-[18%] right-[-6%] size-[30vw]" intensity={0.5} />
      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
