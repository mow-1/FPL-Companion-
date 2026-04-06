/**
 * FPL-style football pitch SVG background.
 * Renders as an absolutely-positioned full-size element behind player cards.
 * Based on standard FIFA pitch proportions scaled to the viewBox.
 */
export default function PitchSVG({ className = '' }) {
  // ViewBox: 380 wide × 520 tall (portrait, ~1:1.37 ratio close to real pitch)
  // Inner pitch area: x=14, y=14 → w=352, h=492
  const W = 380, H = 520
  const px = 14, py = 14          // pitch margin
  const pw = 352, ph = 492         // pitch width / height
  const cx = W / 2                 // center x = 190
  const cy = py + ph / 2           // center y = 14 + 246 = 260

  // Stripe height — 14 horizontal stripes
  const stripes = 14
  const sh = ph / stripes           // ≈ 35px each

  // Penalty area (FIFA: 40.32m wide, 16.5m deep out of 68m × 105m)
  const paW = Math.round(pw * 40.32 / 68)   // ≈ 208px
  const paH = Math.round(ph * 16.5 / 105)   // ≈ 77px
  const paX = cx - paW / 2

  // 6-yard box (18.32m × 5.5m)
  const gbW = Math.round(pw * 18.32 / 68)   // ≈ 95px
  const gbH = Math.round(ph * 5.5 / 105)    // ≈ 26px
  const gbX = cx - gbW / 2

  // Penalty spot (11m from goal line)
  const psD = Math.round(ph * 11 / 105)     // ≈ 51px

  // Penalty arc radius (9.15m)
  const arcR = Math.round(ph * 9.15 / 105)  // ≈ 43px

  // Center circle radius (9.15m)
  const ccR = arcR                           // same radius

  // Corner arc radius (1m)
  const cornerR = Math.round(ph * 1 / 105)  // ≈ 5px

  // Line style
  const line = { stroke: 'rgba(255,255,255,0.75)', strokeWidth: 1.5, fill: 'none' }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={`absolute inset-0 w-full h-full ${className}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <defs>
        {/* Edge vignette */}
        <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
          <stop offset="60%" stopColor="transparent" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.35)" />
        </radialGradient>
      </defs>

      {/* ── Base green ── */}
      <rect width={W} height={H} fill="#1a6b3c" />

      {/* ── Alternating mow stripes ── */}
      {Array.from({ length: stripes }).map((_, i) =>
        i % 2 === 0 ? (
          <rect
            key={i}
            x={px}
            y={py + i * sh}
            width={pw}
            height={sh}
            fill="rgba(255,255,255,0.04)"
          />
        ) : null
      )}

      {/* ── Vignette overlay ── */}
      <rect width={W} height={H} fill="url(#vignette)" />

      {/* ── Pitch boundary ── */}
      <rect x={px} y={py} width={pw} height={ph} {...line} />

      {/* ── Halfway line ── */}
      <line x1={px} y1={cy} x2={px + pw} y2={cy} {...line} />

      {/* ── Center circle & spot ── */}
      <circle cx={cx} cy={cy} r={ccR} {...line} />
      <circle cx={cx} cy={cy} r={2.5} fill="rgba(255,255,255,0.75)" />

      {/* ── TOP end ── */}
      {/* Penalty area */}
      <rect x={paX} y={py} width={paW} height={paH} {...line} />
      {/* 6-yard box */}
      <rect x={gbX} y={py} width={gbW} height={gbH} {...line} />
      {/* Penalty spot */}
      <circle cx={cx} cy={py + psD} r={2.5} fill="rgba(255,255,255,0.75)" />
      {/* Penalty arc (D) — only portion outside penalty area */}
      <path
        d={describeArc(cx, py + psD, arcR, 127, 53)}
        {...line}
        clipPath="url(#topArcClip)"
      />
      <clipPath id="topArcClip">
        <rect x={0} y={py + paH} width={W} height={H} />
      </clipPath>

      {/* ── BOTTOM end ── */}
      {/* Penalty area */}
      <rect x={paX} y={py + ph - paH} width={paW} height={paH} {...line} />
      {/* 6-yard box */}
      <rect x={gbX} y={py + ph - gbH} width={gbW} height={gbH} {...line} />
      {/* Penalty spot */}
      <circle cx={cx} cy={py + ph - psD} r={2.5} fill="rgba(255,255,255,0.75)" />
      {/* Penalty arc (D) — only portion outside penalty area */}
      <path
        d={describeArc(cx, py + ph - psD, arcR, 307, 233)}
        {...line}
        clipPath="url(#botArcClip)"
      />
      <clipPath id="botArcClip">
        <rect x={0} y={0} width={W} height={py + ph - paH} />
      </clipPath>

      {/* ── Corner arcs ── */}
      {/* Top-left */}
      <path d={`M ${px} ${py + cornerR} A ${cornerR} ${cornerR} 0 0 1 ${px + cornerR} ${py}`} {...line} />
      {/* Top-right */}
      <path d={`M ${px + pw - cornerR} ${py} A ${cornerR} ${cornerR} 0 0 1 ${px + pw} ${py + cornerR}`} {...line} />
      {/* Bottom-left */}
      <path d={`M ${px + cornerR} ${py + ph} A ${cornerR} ${cornerR} 0 0 1 ${px} ${py + ph - cornerR}`} {...line} />
      {/* Bottom-right */}
      <path d={`M ${px + pw} ${py + ph - cornerR} A ${cornerR} ${cornerR} 0 0 1 ${px + pw - cornerR} ${py + ph}`} {...line} />
    </svg>
  )
}

/** Convert polar arc params to SVG path data. */
function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg - 90) * (Math.PI / 180)
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  }
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end   = polarToCartesian(cx, cy, r, startAngle)
  const large = Math.abs(startAngle - endAngle) > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`
}
