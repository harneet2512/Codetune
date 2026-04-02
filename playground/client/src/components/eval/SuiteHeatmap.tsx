import { colors, fonts } from '../../theme/tokens'
import { heatmapCheckpoints, heatmapData } from '../../data/eval'

function cellColor(value: number): string {
  // Red (#f87171) at 0%, Amber (#fbbf24) at 50%, Green (#34d399) at 100%
  if (value <= 50) {
    const t = value / 50
    const r = Math.round(248 + (251 - 248) * t)
    const g = Math.round(113 + (191 - 113) * t)
    const b = Math.round(113 + (36 - 113) * t)
    return `rgb(${r},${g},${b})`
  }
  const t = (value - 50) / 50
  const r = Math.round(251 + (52 - 251) * t)
  const g = Math.round(191 + (211 - 191) * t)
  const b = Math.round(36 + (153 - 36) * t)
  return `rgb(${r},${g},${b})`
}

function textColor(value: number): string {
  return value > 40 && value < 70 ? '#1a1a1a' : '#ffffff'
}

export function SuiteHeatmap() {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        padding: '14px 16px',
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontFamily: fonts.mono,
          fontWeight: 700,
          color: colors.text,
          marginBottom: 14,
        }}
      >
        Checkpoint Comparison
      </div>

      {/* Column headers */}
      <div style={{ display: 'flex', marginBottom: 6, paddingLeft: 120 }}>
        {heatmapCheckpoints.map((cp) => (
          <div
            key={cp}
            style={{
              width: 60,
              marginRight: 4,
              fontSize: 8,
              fontFamily: fonts.mono,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: colors.textMuted,
              textAlign: 'center',
            }}
          >
            {cp}
          </div>
        ))}
      </div>

      {/* Rows */}
      {heatmapData.map((row) => (
        <div key={row.category} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
          <div
            style={{
              width: 120,
              fontSize: 11,
              fontFamily: fonts.mono,
              color: colors.textSecondary,
              paddingRight: 8,
            }}
          >
            {row.category}
          </div>
          {row.values.map((val, i) => (
            <div
              key={i}
              style={{
                width: 60,
                height: 36,
                marginRight: 4,
                borderRadius: 4,
                background: cellColor(val),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontFamily: fonts.mono,
                fontWeight: 600,
                color: textColor(val),
              }}
            >
              {val}%
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
