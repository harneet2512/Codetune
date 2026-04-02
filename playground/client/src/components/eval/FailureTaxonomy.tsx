import { colors, fonts } from '../../theme/tokens'
import { failureModes } from '../../data/eval'

function barColor(count: number, maxCount: number): string {
  const ratio = count / maxCount
  if (ratio >= 0.7) return colors.red
  if (ratio >= 0.3) return colors.amber
  return colors.green
}

export function FailureTaxonomy() {
  const maxCount = Math.max(...failureModes.map((f) => f.count))

  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontSize: 13, fontFamily: fonts.mono, fontWeight: 700, color: colors.text, marginBottom: 3 }}>
          Failure Taxonomy
        </div>
        <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textMuted }}>
          Distribution of failure modes across latest GRPO eval run.
        </div>
      </div>
      {failureModes.map((fm, i) => {
        const col = barColor(fm.count, maxCount)
        return (
          <div
            key={fm.name}
            style={{
              padding: '10px 16px',
              borderBottom: i < failureModes.length - 1 ? '1px solid rgba(255,255,255,0.03)' : undefined,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <span style={{ fontSize: 12, fontFamily: fonts.mono, fontWeight: 600, color: colors.text, minWidth: 160 }}>
                {fm.name}
              </span>
              <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textTertiary, minWidth: 70 }}>
                {fm.count} ({fm.percentage}%)
              </span>
              <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
                <div
                  style={{
                    width: `${(fm.count / maxCount) * 100}%`,
                    height: '100%',
                    borderRadius: 3,
                    background: col,
                    opacity: 0.8,
                  }}
                />
              </div>
            </div>
            <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textTertiary, fontStyle: 'italic', paddingLeft: 0 }}>
              {fm.example}
            </div>
          </div>
        )
      })}
    </div>
  )
}
