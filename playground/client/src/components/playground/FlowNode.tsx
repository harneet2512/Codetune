import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { colors, fonts } from '../../theme/tokens'

const accentMap: Record<string, string> = {
  think: colors.purple,
  tool_call: colors.pink,
  observe: colors.green,
  observation: colors.green,
  answer: colors.blue,
  error: colors.red,
  failure_terminal: colors.red,
  warning_terminal: colors.amber,
}

const iconMap: Record<string, string> = {
  think: '\u25c6',
  tool_call: '\u25b6',
  observe: '\u25cf',
  observation: '\u25cf',
  answer: '\u2713',
  error: '\u2717',
  failure_terminal: '\u2717',
  warning_terminal: '!',
}

interface FlowNodeData {
  nodeType: string
  title: string
  summary: string
  decision?: string
  isSelected: boolean
  onClick: () => void
  [key: string]: unknown
}

function FlowNodeInner({ data }: NodeProps & { data: FlowNodeData }) {
  const { nodeType, title, summary, decision, isSelected, onClick } = data
  const accent = accentMap[nodeType] || colors.textSecondary
  const icon = iconMap[nodeType] || '\u25cf'
  const isTerminal = nodeType === 'answer' || nodeType === 'error' || nodeType === 'failure_terminal' || nodeType === 'warning_terminal'

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 1, height: 1 }} />
      <div
        onClick={onClick}
        style={{
          width: 200,
          padding: '7px 9px',
          background: colors.surfaceElevated,
          borderLeft: `3px solid ${accent}`,
          borderTop: `1px solid ${isSelected ? accent : colors.border}`,
          borderRight: `1px solid ${isSelected ? accent : colors.border}`,
          borderBottom: `1px solid ${isSelected ? accent : colors.border}`,
          borderRadius: 4,
          cursor: 'pointer',
          transition: 'all 0.15s',
          fontFamily: fonts.mono,
        }}
      >
        {/* Type label */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
          <span style={{ color: accent, fontSize: 7, lineHeight: 1 }}>{icon}</span>
          <span style={{
            fontSize: 9,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: accent,
          }}>
            {nodeType.replace('_', ' ')}
          </span>
        </div>

        {/* Title */}
        <div style={{
          fontSize: 11,
          fontWeight: 600,
          color: colors.text,
          marginBottom: 1,
          lineHeight: 1.3,
        }}>
          {title}
        </div>

        {/* Summary */}
        <div style={{
          fontSize: 10,
          color: colors.textSecondary,
          lineHeight: 1.35,
        }}>
          {summary}
        </div>

        {/* Decision */}
        {decision && (
          <div style={{
            fontSize: 9,
            color: accent,
            marginTop: 3,
            fontStyle: 'italic',
            opacity: 0.85,
          }}>
            \u2192 {decision}
          </div>
        )}

        {/* Terminal badge */}
        {isTerminal && (
          <div style={{
            marginTop: 4,
            padding: '1px 5px',
            borderRadius: 3,
            background: accent,
            color: colors.bg,
            fontSize: 8,
            fontWeight: 700,
            display: 'inline-block',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}>
            {nodeType === 'answer' ? 'DONE' : nodeType === 'warning_terminal' ? 'PARTIAL' : 'FAIL'}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 1, height: 1 }} />
    </>
  )
}

export const PlaygroundFlowNode = memo(FlowNodeInner)
