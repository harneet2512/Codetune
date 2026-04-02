import { colors, fonts } from '../../theme/tokens'

interface Props {
  trace: {
    tool_calls_used: number
    optimal_tool_calls: number
    steps: number
    restraint: string
    evidence_count: number
    confidence: string
  }
}

export function StatsFooter({ trace }: Props) {
  const cells = [
    { label: 'TOOLS', value: `${trace.tool_calls_used}/${trace.optimal_tool_calls}` },
    { label: 'STEPS', value: String(trace.steps) },
    { label: 'RESTRAINT', value: trace.restraint },
    { label: 'EVIDENCE', value: String(trace.evidence_count) },
  ]

  return (
    <div style={{
      display: 'flex',
      borderTop: `1px solid ${colors.border}`,
      background: 'rgba(0,0,0,0.15)',
      flexShrink: 0,
    }}>
      {cells.map((cell, i) => (
        <div key={cell.label} style={{
          flex: 1,
          padding: '6px 8px',
          textAlign: 'center',
          borderRight: i < cells.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
          fontFamily: fonts.mono,
        }}>
          <div style={{
            fontSize: 9,
            fontWeight: 600,
            color: colors.textMuted,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 1,
          }}>
            {cell.label}
          </div>
          <div style={{
            fontSize: 13,
            fontWeight: 700,
            color: colors.text,
          }}>
            {cell.value}
          </div>
        </div>
      ))}
    </div>
  )
}
