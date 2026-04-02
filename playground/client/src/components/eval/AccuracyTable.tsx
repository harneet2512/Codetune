import { colors, fonts } from '../../theme/tokens'
import { categories } from '../../data/eval'

function AccuracyCell({ value, color }: { value: number; color: string }) {
  return (
    <td style={{ padding: '8px 10px', verticalAlign: 'middle' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 60,
            height: 6,
            borderRadius: 3,
            background: 'rgba(255,255,255,0.06)',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: `${Math.min(100, value)}%`,
              height: '100%',
              background: color,
              borderRadius: 3,
            }}
          />
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, color, fontFamily: fonts.mono }}>
          {value}%
        </span>
      </div>
    </td>
  )
}

export function AccuracyTable() {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: `1px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 700, fontFamily: fonts.mono, color: colors.text }}>
          Accuracy by Category
        </span>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {[
            { label: 'Base', color: colors.red },
            { label: 'SFT', color: colors.amber },
            { label: 'GRPO', color: colors.green },
          ].map(({ label, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, background: color, borderRadius: 2 }} />
              <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textTertiary }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: fonts.mono }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
            {['Category', 'Tasks', 'Base', 'SFT', 'GRPO', 'Δ'].map((col) => (
              <th
                key={col}
                style={{
                  padding: '8px 10px',
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: colors.textMuted,
                  textAlign: col === 'Category' ? 'left' : 'right',
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {categories.map((cat) => {
            const delta = cat.grpo - cat.base
            return (
              <tr key={cat.name} style={{ borderBottom: `1px solid rgba(255,255,255,0.03)` }}>
                <td style={{ padding: '8px 10px', fontSize: 12, color: colors.text, fontWeight: 500 }}>
                  {cat.name}
                </td>
                <td style={{ padding: '8px 10px', fontSize: 12, color: colors.textSecondary, textAlign: 'right' }}>
                  {cat.tasks}
                </td>
                <AccuracyCell value={cat.base} color={colors.red} />
                <AccuracyCell value={cat.sft} color={colors.amber} />
                <AccuracyCell value={cat.grpo} color={colors.green} />
                <td style={{ padding: '8px 10px', fontSize: 12, color: colors.green, textAlign: 'right', fontWeight: 700 }}>
                  +{delta}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
