import { colors, fonts } from '../../theme/tokens'
import { trainingData } from '../../data/eval'

function barColor(label: string): string {
  if (label === 'BASE') return colors.red
  if (label.startsWith('S')) return colors.amber
  return colors.green
}

export function TrainingCurve() {
  const { labels, values } = trainingData
  const chartHeight = 120
  const topPad = 18
  const bottomPad = 20
  const usableHeight = chartHeight - topPad - bottomPad
  const maxVal = 65

  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '14px 16px 0',
          fontSize: 13,
          fontFamily: fonts.mono,
          fontWeight: 700,
          color: colors.text,
          marginBottom: 10,
        }}
      >
        Training Progress
      </div>
      <div style={{ padding: '0 16px 10px' }}>
        <svg width="100%" viewBox={`0 0 ${labels.length * 36} ${chartHeight}`} style={{ display: 'block' }}>
          {labels.map((label, i) => {
            const val = values[i]
            const barH = (val / maxVal) * usableHeight
            const barW = 24
            const x = i * 36 + 6
            const y = topPad + usableHeight - barH
            const col = barColor(label)

            return (
              <g key={label}>
                <rect x={x} y={y} width={barW} height={barH} rx={3} fill={col} opacity={0.8} />
                <text
                  x={x + barW / 2}
                  y={y - 4}
                  textAnchor="middle"
                  fill={colors.textMuted}
                  fontSize={8}
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight={600}
                >
                  {val}%
                </text>
                <text
                  x={x + barW / 2}
                  y={chartHeight - 4}
                  textAnchor="middle"
                  fill={colors.textFaintest}
                  fontSize={7}
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight={500}
                >
                  {label}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      {/* Legend */}
      <div
        style={{
          padding: '8px 16px 12px',
          borderTop: `1px solid ${colors.border}`,
          display: 'flex',
          gap: 16,
        }}
      >
        {[
          { label: 'Base', color: colors.red },
          { label: 'SFT Steps', color: colors.amber },
          { label: 'GRPO Steps', color: colors.green },
        ].map(({ label, color }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: color, opacity: 0.8 }} />
            <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textMuted }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
