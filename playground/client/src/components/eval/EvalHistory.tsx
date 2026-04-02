import { Filter, Download } from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import { evalHistory } from '../../data/eval'

const columnDefs = [
  { key: 'runId', label: 'Run ID', align: 'left' as const },
  { key: 'model', label: 'Model', align: 'left' as const },
  { key: 'suite', label: 'Suite', align: 'left' as const },
  { key: 'tasks', label: 'Tasks', align: 'right' as const },
  { key: 'accuracy', label: 'Accuracy', align: 'right' as const },
  { key: 'toolPrecision', label: 'Tool Prec.', align: 'right' as const },
  { key: 'restraint', label: 'Restraint', align: 'right' as const },
  { key: 'duration', label: 'Duration', align: 'right' as const },
  { key: 'timestamp', label: 'Timestamp', align: 'right' as const },
]

function accuracyColor(val: number): string {
  if (val >= 60) return colors.green
  if (val >= 30) return colors.amber
  return colors.red
}

function modelColor(model: string): string {
  if (model.startsWith('Base')) return colors.red
  if (model.startsWith('SFT')) return colors.amber
  return colors.green
}

export function EvalHistory() {
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
          Eval Run History
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            style={{
              background: 'transparent',
              border: `1px solid ${colors.border}`,
              borderRadius: 4,
              padding: '4px 8px',
              color: colors.textTertiary,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Filter size={12} />
          </button>
          <button
            style={{
              background: 'transparent',
              border: `1px solid ${colors.border}`,
              borderRadius: 4,
              padding: '4px 8px',
              color: colors.textTertiary,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Download size={12} />
          </button>
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: fonts.mono }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
            {columnDefs.map((col) => (
              <th
                key={col.key}
                style={{
                  padding: '8px 10px',
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: colors.textMuted,
                  textAlign: col.align,
                }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {evalHistory.map((run) => (
            <tr key={run.runId} style={{ borderBottom: `1px solid rgba(255,255,255,0.03)` }}>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textSecondary }}>{run.runId}</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: modelColor(run.model), fontWeight: 600 }}>{run.model}</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.text }}>{run.suite}</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textSecondary, textAlign: 'right' }}>{run.tasks}</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: accuracyColor(run.accuracy), textAlign: 'right', fontWeight: 600 }}>{run.accuracy}%</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textSecondary, textAlign: 'right' }}>{run.toolPrecision}%</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textSecondary, textAlign: 'right' }}>{run.restraint}%</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textSecondary, textAlign: 'right' }}>{run.duration}</td>
              <td style={{ padding: '7px 10px', fontSize: 11, color: colors.textMuted, textAlign: 'right' }}>{run.timestamp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
